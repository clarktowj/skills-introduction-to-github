import fitz
import os
import math
from typing import List, Dict, Any, Optional, Tuple
from common.models import DrawingData, DeviceModel, CableModel, Coordinate, DeviceType, CableType, LayingMethod, LayerInfo, BlockInfo, LineInfo, TextInfo
from rule_engine.rule_manager import RuleManager
from framework.exceptions import ParseError


class PDFParser:
    """
    矢量PDF图纸解析器
    
    使用 PyMuPDF (fitz) 提取 PDF 中的矢量图形：
    - 线条 (drawing items: l, re, c, qu)
    - 文字 (text blocks)
    - 矩形/多边形作为设备符号
    
    策略：
    1. 将 PDF 坐标 (左上原点) 转换为 CAD 风格 (左下原点)
    2. 从颜色/线型合成"虚拟图层"用于分类
    3. 使用与 DXF 相同的 RuleManager 进行设备/线缆/桥架识别
    4. 检测矩形/闭合多边形作为设备图块
    5. 检测平行线作为桥架/线槽
    """

    def __init__(self, rule_manager: RuleManager = None):
        if rule_manager is not None:
            self._rule_manager = rule_manager
        else:
            self._rule_manager = RuleManager()
            self._rule_manager.load_rules()

        self._page_height = 0.0
        self._page_width = 0.0

    def parse(self, file_path: str) -> DrawingData:
        if not os.path.exists(file_path):
            raise ParseError(f"File not found: {file_path}")

        try:
            doc = fitz.open(file_path)

            drawing_data = DrawingData(
                filename=os.path.basename(file_path),
                file_type='pdf'
            )

            # 1. 提取并建立虚拟图层
            self._extract_and_setup_layers(doc, drawing_data)

            # 2. 提取所有图元（先文字后图元，便于矩形匹配设备名称）
            for page in doc:
                self._extract_page_text(page, drawing_data)
                self._extract_page_drawings(page, drawing_data)

            # 3. 检测设备图块（矩形/多边形 + 附近文字）
            self._detect_device_blocks(drawing_data)

            # 4. 识别设备
            self._identify_devices(drawing_data)

            # 5. 识别线缆
            self._identify_cables(drawing_data)

            # 6. 识别桥架和配管
            self._identify_trunkings_and_pipes(drawing_data)

            # 7. 生成识别摘要
            drawing_data.attributes = self._generate_summary(drawing_data)

            doc.close()
            return drawing_data

        except Exception as e:
            raise ParseError(f"Failed to parse PDF file: {str(e)}")

    def _convert_y(self, pdf_y: float) -> float:
        """将 PDF 坐标 (y 向下为正) 转换为 CAD 风格 (y 向上为正)"""
        return self._page_height - pdf_y

    def _extract_and_setup_layers(self, doc: fitz.Document, drawing_data: DrawingData) -> None:
        """
        PDF 没有 DXF 那样的图层系统，我们从内容中合成虚拟图层。
        
        策略：
        - 扫描所有页面的 drawings 和 texts，收集颜色/类型信息
        - 为每种常见分类创建一个虚拟图层
        - 使用与 DXF 相同的规则进行分类
        """
        all_colors = set()
        has_lines = False
        has_text = False
        has_rectangles = False

        for page in doc:
            if self._page_height == 0:
                self._page_height = page.rect.height
                self._page_width = page.rect.width
                drawing_data.width = self._page_width
                drawing_data.height = self._page_height

            drawings = page.get_drawings()
            for d in drawings:
                stroke = d.get('stroke')
                if stroke:
                    color_str = self._rgb_to_color_str(stroke)
                    all_colors.add(color_str)
                for item in d.get('items', []):
                    if item[0] == 'l':
                        has_lines = True
                    elif item[0] in ('re', 'qu'):
                        has_rectangles = True

            if page.get_text("blocks"):
                has_text = True

        # 构建虚拟图层
        layer_candidates = [
            ('E-设备层', 'device'),
            ('E-电缆层', 'cable'),
            ('E-桥架层', 'trunking'),
            ('E-配管层', 'pipe'),
            ('E-文字标注', 'text'),
            ('E-电气', 'electrical'),
        ]

        for name, category in layer_candidates:
            drawing_data.layers.append(LayerInfo(
                name=name,
                color='7',
                line_type='CONTINUOUS',
                visible=True,
                locked=False,
                category=category
            ))

        # 添加基于颜色的图层
        for color in list(all_colors)[:5]:
            color_layer_name = f'E-{color}色线'
            drawing_data.layers.append(LayerInfo(
                name=color_layer_name,
                color=color,
                line_type='CONTINUOUS',
                visible=True,
                locked=False,
                category='electrical'
            ))

    @staticmethod
    def _rgb_to_color_str(rgb: Tuple[float, float, float]) -> str:
        """将 RGB (0-1) 映射为 AutoCAD 颜色代码"""
        if not rgb or len(rgb) < 3:
            return '7'
        r, g, b = rgb[0], rgb[1], rgb[2]
        if r > 0.5 and g < 0.5 and b < 0.5:
            return '1'  # 红色 - 电力线
        elif r < 0.5 and g > 0.5 and b < 0.5:
            return '3'  # 绿色 - 控制线
        elif r < 0.5 and g < 0.5 and b > 0.5:
            return '5'  # 蓝色 - 信号
        elif r > 0.5 and g > 0.5 and b < 0.5:
            return '2'  # 黄色
        elif r < 0.3 and g < 0.3 and b < 0.3:
            return '7'  # 黑色/白色
        else:
            return '8'

    def _extract_page_drawings(self, page: fitz.Page, drawing_data: DrawingData) -> None:
        """提取页面中的矢量图形"""
        if self._page_height == 0:
            self._page_height = page.rect.height
            self._page_width = page.rect.width

        drawings = page.get_drawings()
        electrical_layers = {layer.name: layer.category for layer in drawing_data.layers}

        device_rects = []  # 用于设备识别的矩形

        for drawing in drawings:
            stroke = drawing.get('stroke')
            fill = drawing.get('fill')
            color_str = self._rgb_to_color_str(stroke) if stroke else '7'
            line_width = drawing.get('width', 1.0)

            # 根据颜色推断虚拟图层
            if color_str == '1':
                layer_name = 'E-电缆层'
            elif color_str in ('3', '5'):
                layer_name = 'E-电缆层'
            elif line_width > 2.0:
                layer_name = 'E-桥架层'
            else:
                layer_name = 'E-电气层'

            for item in drawing.get('items', []):
                item_type = item[0]

                if item_type == 'l':  # Line
                    try:
                        _, x0, y0, x1, y1 = item[:5]
                    except (ValueError, IndexError):
                        continue

                    drawing_data.lines.append(LineInfo(
                        start_point=Coordinate(x=float(x0), y=self._convert_y(float(y0)), z=0.0),
                        end_point=Coordinate(x=float(x1), y=self._convert_y(float(y1)), z=0.0),
                        layer=layer_name,
                        color=color_str,
                        line_type='CONTINUOUS'
                    ))

                elif item_type == 're':  # Rectangle
                    try:
                        _, rect = item[:2]
                        x0, y0, x1, y1 = rect.x0, rect.y0, rect.x1, rect.y1
                    except (ValueError, IndexError, AttributeError):
                        continue

                    # 添加四条边作为线条
                    corners = [
                        (float(x0), float(y0)),
                        (float(x1), float(y0)),
                        (float(x1), float(y1)),
                        (float(x0), float(y1)),
                    ]
                    for i in range(4):
                        cx0, cy0 = corners[i]
                        cx1, cy1 = corners[(i + 1) % 4]
                        drawing_data.lines.append(LineInfo(
                            start_point=Coordinate(x=cx0, y=self._convert_y(cy0), z=0.0),
                            end_point=Coordinate(x=cx1, y=self._convert_y(cy1), z=0.0),
                            layer=layer_name,
                            color=color_str,
                            line_type='CONTINUOUS'
                        ))

                    # 记录矩形作为设备候选
                    device_rects.append({
                        'x0': float(x0),
                        'y0': float(y0),
                        'x1': float(x1),
                        'y1': float(y1),
                        'layer': layer_name,
                        'color': color_str,
                        'fill': fill is not None,
                    })

                elif item_type == 'qu':  # Quad (Bezier curve approximation)
                    try:
                        _, points = item[:2]
                        if not points or len(points) < 2:
                            continue
                    except (ValueError, IndexError):
                        continue

                    for i in range(len(points) - 1):
                        p0, p1 = points[i], points[i + 1]
                        drawing_data.lines.append(LineInfo(
                            start_point=Coordinate(x=float(p0[0]), y=self._convert_y(float(p0[1])), z=0.0),
                            end_point=Coordinate(x=float(p1[0]), y=self._convert_y(float(p1[1])), z=0.0),
                            layer=layer_name,
                            color=color_str,
                            line_type='CURVE'
                        ))

                elif item_type == 'c':  # Bezier curve
                    try:
                        pts = item[1:]
                        if len(pts) < 2:
                            continue
                    except (ValueError, IndexError):
                        continue

                    # 简化处理：取首末点连线
                    start = pts[0] if isinstance(pts[0], tuple) else (0, 0)
                    end = pts[-1] if isinstance(pts[-1], tuple) else (0, 0)
                    drawing_data.lines.append(LineInfo(
                        start_point=Coordinate(x=float(start[0]), y=self._convert_y(float(start[1])), z=0.0),
                        end_point=Coordinate(x=float(end[0]), y=self._convert_y(float(end[1])), z=0.0),
                        layer=layer_name,
                        color=color_str,
                        line_type='CURVE'
                    ))

        # 将设备矩形保存为图块，并匹配附近文字以获得设备名称
        for rect in device_rects:
            cx = (rect['x0'] + rect['x1']) / 2
            cy = (rect['y0'] + rect['y1']) / 2
            width = abs(rect['x1'] - rect['x0'])
            height = abs(rect['y1'] - rect['y0'])

            # 只保留合理尺寸的矩形作为设备候选
            if not (20 < width < 500 and 20 < height < 500):
                continue

            # 搜索矩形附近的文字标注（矩形下方或内部）
            nearby_text = self._find_nearby_text_for_rect(
                rect['x0'], rect['y0'], rect['x1'], rect['y1'],
                drawing_data.texts
            )

            # 使用附近文字作为图块名称（若包含设备关键词）
            block_name = nearby_text if nearby_text else f"RECT_{int(width)}x{int(height)}"
            # 限制名称长度
            if len(block_name) > 40:
                block_name = block_name[:40]

            drawing_data.blocks.append(BlockInfo(
                name=block_name,
                insertion_point=Coordinate(x=cx, y=self._convert_y(cy), z=0.0),
                rotation=0.0,
                scale=1.0,
                attributes={
                    'width': width,
                    'height': height,
                    'fill': rect['fill'],
                    'source': 'pdf_rect',
                    'nearby_text': nearby_text or ''
                },
                layer=rect['layer']
            ))

    def _extract_page_text(self, page: fitz.Page, drawing_data: DrawingData) -> None:
        """提取页面文字标注"""
        if self._page_height == 0:
            self._page_height = page.rect.height

        text_blocks = page.get_text("dict")

        if 'blocks' in text_blocks:
            for block in text_blocks['blocks']:
                block_type = block.get('type', 0)
                if block_type != 0:  # type 0 = text
                    continue

                for line in block.get('lines', []):
                    for span in line.get('spans', []):
                        text_content = span.get('text', '').strip()
                        if not text_content:
                            continue

                        bbox = span.get('bbox', [0, 0, 0, 0])
                        x0, y0, x1, y1 = bbox
                        size = span.get('size', 10)
                        angle = line.get('dir', [1, 0])
                        rotation = 0.0
                        if angle[0] != 0:
                            try:
                                rotation = math.degrees(math.atan2(angle[1], angle[0]))
                            except (ValueError, ZeroDivisionError):
                                pass

                        drawing_data.texts.append(TextInfo(
                            content=text_content,
                            position=Coordinate(
                                x=(x0 + x1) / 2,
                                y=self._convert_y((y0 + y1) / 2),
                                z=0.0
                            ),
                            layer='E-文字标注',
                            font_size=float(size),
                            rotation=rotation
                        ))

    def _detect_device_blocks(self, drawing_data: DrawingData) -> None:
        """
        从文字标注中补充识别设备图块
        
        PDF 中的设备图块通常是：矩形 + 附近文字（设备名称/型号）
        这里补充一种策略：如果文字包含设备关键词，
        则将其所在位置的矩形视为一个设备图块
        """
        if not drawing_data.texts:
            return

        device_keywords = set()
        for device_type, config in self._rule_manager.get_rule('device_classification', {}).items():
            for kw in config.get('keywords', []):
                device_keywords.add(kw)

        # 从文字中找到设备名称，用于补充图块
        existing_block_positions = {
            (round(b.insertion_point.x, 1), round(b.insertion_point.y, 1))
            for b in drawing_data.blocks
        }

        for text in drawing_data.texts:
            content = text.content
            # 检查是否包含设备关键词
            for kw in device_keywords:
                if kw in content and len(content) < 50:
                    # 检查附近是否已有图块
                    tx = round(text.position.x, 1)
                    ty = round(text.position.y, 1)
                    has_nearby = any(
                        abs(bx - tx) < 100 and abs(by - ty) < 100
                        for bx, by in existing_block_positions
                    )
                    if not has_nearby:
                        block_name = content.strip()[:30]
                        drawing_data.blocks.append(BlockInfo(
                            name=block_name,
                            insertion_point=Coordinate(
                                x=text.position.x,
                                y=text.position.y,
                                z=0.0
                            ),
                            rotation=0.0,
                            scale=1.0,
                            attributes={
                                'source': 'text_identified',
                                'keyword': kw,
                                'text': content,
                            },
                            layer='E-设备层'
                        ))
                        existing_block_positions.add((tx, ty))
                    break

    def _identify_devices(self, drawing_data: DrawingData) -> None:
        """从图块中识别设备（复用 DXF 相同逻辑）"""
        nearby_text_map = self._build_nearby_text_map(drawing_data)

        for block in drawing_data.blocks:
            # 1. 图块名识别
            result = self._rule_manager.classify_device_with_confidence(block.name)
            raw_device_type = result['device_type']
            confidence = result['confidence']
            matched_kw = result['matched_keywords']

            device_type = self._rule_manager.normalize_device_type(raw_device_type)

            # 2. 附近文字辅助识别
            if confidence < 0.4:
                nearby_texts = nearby_text_map.get(id(block), [])
                for text_content in nearby_texts:
                    result3 = self._rule_manager.classify_device_with_confidence(text_content)
                    if result3['confidence'] > confidence:
                        raw_device_type = result3['device_type']
                        device_type = self._rule_manager.normalize_device_type(raw_device_type)
                        confidence = result3['confidence']
                        matched_kw = result3['matched_keywords']
                        block.attributes['_identified_by_text'] = text_content
                        break

            # 3. 只有识别置信度达到阈值才添加
            if confidence >= 0.3:
                device = DeviceModel(
                    name=block.name,
                    type=DeviceType(device_type),
                    coordinates=block.insertion_point,
                    quantity=1,
                    layer=block.layer or 'E-设备层',
                    block_name=block.name,
                    attributes={
                        **(block.attributes if isinstance(block.attributes, dict) else {}),
                        'confidence': round(confidence, 2),
                        'matched_keywords': matched_kw,
                        'match_method': result.get('match_method', 'keyword'),
                        'raw_type': raw_device_type,
                        'source': 'pdf'
                    }
                )
                drawing_data.devices.append(device)

    def _build_nearby_text_map(self, drawing_data: DrawingData) -> Dict[int, List[str]]:
        """为每个图块构建附近文字查找表（复用 DXF 逻辑）"""
        text_map = {}
        if not drawing_data.blocks or not drawing_data.texts:
            return text_map

        search_radius = 150.0

        for block in drawing_data.blocks:
            nearby_texts = []
            for text in drawing_data.texts:
                distance = self._calculate_distance(block.insertion_point, text.position)
                if distance < search_radius:
                    nearby_texts.append(text.content)
            if nearby_texts:
                text_map[id(block)] = nearby_texts[:5]

        return text_map

    def _identify_cables(self, drawing_data: DrawingData) -> None:
        """从线条中识别线缆（复用 DXF 相同识别逻辑）"""
        cable_lines_by_method: Dict[str, List[LineInfo]] = {}

        for line in drawing_data.lines:
            layer_category = self._rule_manager.get_layer_category(line.layer)

            if layer_category not in ['cable', 'electrical', 'trunking', 'pipe']:
                continue

            cable_info = self._rule_manager.identify_cable_type(
                text='',
                layer=line.layer,
                color=line.color,
                line_type=line.line_type
            )

            cable_type = cable_info['cable_type']
            laying_method = cable_info['laying_method']

            if cable_type in ['power', 'control', 'signal', 'communication'] or layer_category in ['cable', 'electrical']:
                key = f'{cable_type}_{laying_method}'
                if key not in cable_lines_by_method:
                    cable_lines_by_method[key] = []
                cable_lines_by_method[key].append(line)

        for key, lines in cable_lines_by_method.items():
            if not lines:
                continue

            total_length = 0.0
            for line in lines:
                total_length += self._calculate_distance(line.start_point, line.end_point)

            if total_length < 0.1:
                continue

            parts = key.split('_', 1)
            cable_type = parts[0]
            laying_method = parts[1] if len(parts) > 1 else 'cable_tray'

            cable_name_mapping = {
                'power': '电力电缆',
                'control': '控制电缆',
                'signal': '信号电缆',
                'communication': '通信电缆'
            }

            drawing_data.cables.append(CableModel(
                model=cable_name_mapping.get(cable_type, '电缆'),
                type=cable_type,
                start_point=lines[0].start_point,
                end_point=lines[-1].end_point,
                length=round(total_length, 2),
                reserved_length=0.0,
                laying_method=laying_method,
                core_count=0,
                attributes={
                    'source': 'pdf',
                    'line_count': len(lines),
                    'layer': lines[0].layer,
                    'color': lines[0].color,
                    'line_type': lines[0].line_type
                }
            ))

    def _identify_trunkings_and_pipes(self, drawing_data: DrawingData) -> None:
        """识别桥架和配管（复用 DXF 相同逻辑）"""
        trunking_lines: Dict[str, List[LineInfo]] = {}

        for line in drawing_data.lines:
            trunking_type = self._rule_manager.identify_trunking(
                layer=line.layer,
                color=line.color,
                line_type=line.line_type
            )

            if trunking_type:
                if trunking_type not in trunking_lines:
                    trunking_lines[trunking_type] = []
                trunking_lines[trunking_type].append(line)

        if 'trunking' in trunking_lines:
            total_length = 0.0
            for line in trunking_lines['trunking']:
                total_length += self._calculate_distance(line.start_point, line.end_point)

            if total_length > 0.1:
                drawing_data.trunkings.append({
                    'name': '桥架',
                    'type': 'cable_tray',
                    'length': round(total_length, 2),
                    'line_count': len(trunking_lines['trunking'])
                })

        if 'pipe' in trunking_lines:
            total_length = 0.0
            for line in trunking_lines['pipe']:
                total_length += self._calculate_distance(line.start_point, line.end_point)

            if total_length > 0.1:
                drawing_data.trunkings.append({
                    'name': '配管',
                    'type': 'pipe',
                    'length': round(total_length, 2),
                    'line_count': len(trunking_lines['pipe'])
                })

        if not drawing_data.trunkings:
            for layer in drawing_data.layers:
                if layer.category == 'trunking':
                    length = sum(
                        self._calculate_distance(line.start_point, line.end_point)
                        for line in drawing_data.lines if line.layer == layer.name
                    )
                    if length > 0.1:
                        drawing_data.trunkings.append({
                            'name': f'桥架({layer.name})',
                            'type': 'cable_tray',
                            'length': round(length, 2),
                            'line_count': sum(1 for l in drawing_data.lines if l.layer == layer.name)
                        })

    def _generate_summary(self, drawing_data: DrawingData) -> Dict[str, Any]:
        """生成识别摘要（与 DXF 相同格式）"""
        device_by_type: Dict[str, int] = {}
        for device in drawing_data.devices:
            key = device.type.value
            device_by_type[key] = device_by_type.get(key, 0) + 1

        cable_by_method: Dict[str, float] = {}
        for cable in drawing_data.cables:
            key = cable.laying_method or 'unknown'
            cable_by_method[key] = cable_by_method.get(key, 0.0) + cable.length

        cable_by_type: Dict[str, int] = {}
        for cable in drawing_data.cables:
            key = cable.type.value if hasattr(cable.type, 'value') else str(cable.type)
            cable_by_type[key] = cable_by_type.get(key, 0) + 1

        return {
            'source': 'pdf',
            'total_devices': len(drawing_data.devices),
            'total_cables': len(drawing_data.cables),
            'total_trunkings': len(drawing_data.trunkings),
            'device_by_type': device_by_type,
            'cable_by_method': {k: round(v, 2) for k, v in cable_by_method.items()},
            'cable_by_type': cable_by_type,
            'total_layers': len(drawing_data.layers),
            'total_lines': len(drawing_data.lines),
            'total_blocks': len(drawing_data.blocks),
            'total_texts': len(drawing_data.texts)
        }

    @staticmethod
    def _calculate_distance(p1: Coordinate, p2: Coordinate) -> float:
        return math.sqrt(
            (p2.x - p1.x) ** 2 +
            (p2.y - p1.y) ** 2 +
            (p2.z - p1.z) ** 2
        )

    def _find_nearby_text_for_rect(
        self,
        rect_x0: float, rect_y0: float,
        rect_x1: float, rect_y1: float,
        texts: list
    ) -> Optional[str]:
        """
        在矩形附近搜索文字标注，优先匹配设备关键词

        注意：矩形使用 PDF 原始坐标（y向下为正）
             texts 中的 Y 已经转换为 CAD 风格（y向上为正）
        """
        if not texts:
            return None

        cx = (rect_x0 + rect_x1) / 2
        cy_pdf = (rect_y0 + rect_y1) / 2
        rect_width = abs(rect_x1 - rect_x0)
        rect_height = abs(rect_y1 - rect_y0)

        # 搜索范围：矩形下方扩展 + 矩形内部
        search_x_min = rect_x0 - rect_width * 0.5
        search_x_max = rect_x1 + rect_width * 0.5
        search_y_min_pdf = rect_y0 - rect_height * 0.5  # 上方
        search_y_max_pdf = rect_y1 + rect_height * 3.0   # 下方3倍高度范围

        device_keywords = [
            '配电柜', 'AP1', 'AP2', '开关柜', '配电箱', 'AL', 'ALE', 'AT',
            'MCC', '电机', '水泵', '风机', '开关', 'SB', '插座', 'SW',
            '灯', '照明', '设备', 'control', 'power', 'switch', 'panel',
            'cabinet', 'outlet', 'lighting'
        ]

        best_match = None
        best_distance = float('inf')

        for text in texts:
            tx = text.position.x
            # 文字 y 是 CAD 风格，需要转成 PDF 坐标
            ty_pdf = self._page_height - text.position.y

            # 检查x是否在搜索范围内
            if not (search_x_min <= tx <= search_x_max):
                continue
            # 检查y是否在搜索范围内（PDF坐标，y大在下）
            if not (search_y_min_pdf <= ty_pdf <= search_y_max_pdf):
                continue

            content = text.content.strip()
            if len(content) < 2:
                continue

            # 计算距离（像素）
            dist = math.sqrt((tx - cx) ** 2 + (ty_pdf - cy_pdf) ** 2)

            # 检查是否包含设备关键词
            has_keyword = any(kw.lower() in content.lower() for kw in device_keywords)

            if has_keyword and dist < best_distance:
                best_distance = dist
                best_match = content
            elif not best_match and dist < best_distance:
                # 即使没有关键词，记录最近的文本
                best_distance = dist
                best_match = content

        return best_match
