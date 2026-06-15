import ezdxf
from typing import List, Dict, Any, Optional
from common.models import DrawingData, DeviceModel, CableModel, Coordinate, DeviceType, LayerInfo, BlockInfo, LineInfo, TextInfo
from rule_engine.rule_manager import RuleManager
from framework.exceptions import ParseError
import math


class DXFParser:
    def __init__(self, rule_manager: RuleManager = None):
        if rule_manager is not None:
            self._rule_manager = rule_manager
        else:
            self._rule_manager = RuleManager()
            self._rule_manager.load_rules()

    def parse(self, file_path: str) -> DrawingData:
        try:
            doc = ezdxf.readfile(file_path)
            msp = doc.modelspace()

            drawing_data = DrawingData(
                filename=file_path,
                file_type='dxf'
            )

            # 1. 提取图层并过滤
            self._extract_layers(doc, drawing_data)

            # 2. 提取图块引用
            self._extract_blocks(msp, drawing_data)

            # 3. 提取线条
            self._extract_lines(msp, drawing_data)

            # 4. 提取文字标注
            self._extract_texts(msp, drawing_data)

            # 5. 识别设备（从图块）
            self._identify_devices(drawing_data)

            # 6. 识别线缆（从线条）
            self._identify_cables(drawing_data)

            # 7. 识别桥架和配管
            self._identify_trunkings_and_pipes(drawing_data)

            # 8. 生成识别摘要
            drawing_data.attributes = self._generate_summary(drawing_data)

            return drawing_data

        except Exception as e:
            raise ParseError(f"Failed to parse DXF file: {str(e)}")

    def _extract_layers(self, doc, drawing_data: DrawingData) -> None:
        """提取并过滤图层"""
        layer_names = []
        for layer in doc.layers:
            try:
                name = str(layer.dxf.name)
            except Exception:
                name = str(layer)
            layer_names.append(name)

        # 过滤出电气相关图层
        electrical_layers = self._rule_manager.filter_layers(layer_names)

        for name, category in electrical_layers.items():
            # 尝试获取颜色信息
            try:
                color_val = None
                for layer_obj in doc.layers:
                    try:
                        if str(layer_obj.dxf.name) == name:
                            color_val = str(layer_obj.dxf.color)
                            break
                    except Exception:
                        continue
                color = color_val if color_val else '7'
            except Exception:
                color = '7'

            drawing_data.layers.append(LayerInfo(
                name=name,
                color=color,
                line_type='CONTINUOUS',
                visible=True,
                locked=False,
                category=category
            ))

    def _extract_blocks(self, msp, drawing_data: DrawingData) -> None:
        """提取所有图块引用"""
        try:
            # 获取电气相关图层集合用于过滤
            electrical_layer_names = {layer.name for layer in drawing_data.layers}

            for block_ref in msp.query('INSERT'):
                try:
                    block_name = str(block_ref.dxf.name)
                    layer = str(block_ref.dxf.layer)

                    # 图层过滤：只处理电气相关图层中的图块
                    if layer not in electrical_layer_names:
                        continue

                    insert = block_ref.dxf.insert

                    # 提取图块属性
                    attributes = {}
                    try:
                        for attrib in block_ref.attribs:
                            try:
                                tag = str(attrib.dxf.tag)
                                value = str(attrib.dxf.text)
                                attributes[tag] = value
                            except Exception:
                                continue
                    except Exception:
                        pass

                    drawing_data.blocks.append(BlockInfo(
                        name=block_name,
                        insertion_point=Coordinate(
                            x=float(insert[0]),
                            y=float(insert[1]),
                            z=float(insert[2]) if len(insert) > 2 else 0.0
                        ),
                        layer=layer,
                        attributes=attributes
                    ))
                except Exception:
                    continue
        except Exception:
            pass

    def _extract_lines(self, msp, drawing_data: DrawingData) -> None:
        """提取所有LINE和LWPOLYLINE实体"""
        electrical_layer_names = {layer.name for layer in drawing_data.layers}

        # 处理 LINE 实体
        for line in msp.query('LINE'):
            try:
                layer = str(line.dxf.layer)

                # 图层过滤
                if layer not in electrical_layer_names:
                    continue

                start = line.dxf.start
                end = line.dxf.end

                # 获取颜色
                try:
                    color = str(line.dxf.color)
                except Exception:
                    color = '7'

                # 获取线型
                try:
                    line_type = str(line.dxf.linetype)
                except Exception:
                    line_type = 'CONTINUOUS'

                drawing_data.lines.append(LineInfo(
                    start_point=Coordinate(
                        x=float(start[0]),
                        y=float(start[1]),
                        z=float(start[2]) if len(start) > 2 else 0.0
                    ),
                    end_point=Coordinate(
                        x=float(end[0]),
                        y=float(end[1]),
                        z=float(end[2]) if len(end) > 2 else 0.0
                    ),
                    layer=layer,
                    color=color,
                    line_type=line_type
                ))
            except Exception:
                continue

        # 处理 LWPOLYLINE 实体（轻量多段线 - 常见的线条类型）
        for polyline in msp.query('LWPOLYLINE'):
            try:
                layer = str(polyline.dxf.layer)

                if layer not in electrical_layer_names:
                    continue

                try:
                    color = str(polyline.dxf.color)
                except Exception:
                    color = '7'

                try:
                    line_type = str(polyline.dxf.linetype)
                except Exception:
                    line_type = 'CONTINUOUS'

                # 提取多段线的点
                points = list(polyline.get_points())

                # 将多段线转换为多条线段
                for i in range(len(points) - 1):
                    start = points[i]
                    end = points[i + 1]

                    drawing_data.lines.append(LineInfo(
                        start_point=Coordinate(
                            x=float(start[0]),
                            y=float(start[1]),
                            z=float(start[2]) if len(start) > 2 else 0.0
                        ),
                        end_point=Coordinate(
                            x=float(end[0]),
                            y=float(end[1]),
                            z=float(end[2]) if len(end) > 2 else 0.0
                        ),
                        layer=layer,
                        color=color,
                        line_type=line_type
                    ))

                # 如果是闭合的多段线，添加最后一条线
                if len(points) > 2 and points[0] != points[-1]:
                    start = points[-1]
                    end = points[0]
                    drawing_data.lines.append(LineInfo(
                        start_point=Coordinate(
                            x=float(start[0]),
                            y=float(start[1]),
                            z=float(start[2]) if len(start) > 2 else 0.0
                        ),
                        end_point=Coordinate(
                            x=float(end[0]),
                            y=float(end[1]),
                            z=float(end[2]) if len(end) > 2 else 0.0
                        ),
                        layer=layer,
                        color=color,
                        line_type=line_type
                    ))
            except Exception:
                continue

        # 处理 ARC 实体（弧线，简化处理为直线两端点）
        for arc in msp.query('ARC'):
            try:
                layer = str(arc.dxf.layer)

                if layer not in electrical_layer_names:
                    continue

                try:
                    color = str(arc.dxf.color)
                except Exception:
                    color = '7'

                start_point = arc.start_point
                end_point = arc.end_point

                drawing_data.lines.append(LineInfo(
                    start_point=Coordinate(
                        x=float(start_point[0]),
                        y=float(start_point[1]),
                        z=float(start_point[2]) if len(start_point) > 2 else 0.0
                    ),
                    end_point=Coordinate(
                        x=float(end_point[0]),
                        y=float(end_point[1]),
                        z=float(end_point[2]) if len(end_point) > 2 else 0.0
                    ),
                    layer=layer,
                    color=color,
                    line_type='ARC'
                ))
            except Exception:
                continue

        # 处理 POLYLINE 实体（3D多段线）
        for polyline in msp.query('POLYLINE'):
            try:
                layer = str(polyline.dxf.layer)

                if layer not in electrical_layer_names:
                    continue

                try:
                    color = str(polyline.dxf.color)
                except Exception:
                    color = '7'

                try:
                    line_type = str(polyline.dxf.linetype)
                except Exception:
                    line_type = 'CONTINUOUS'

                # 提取顶点
                vertices = []
                try:
                    for point in polyline.points():
                        vertices.append((point[0], point[1], point[2] if len(point) > 2 else 0.0))
                except Exception:
                    continue

                for i in range(len(vertices) - 1):
                    start = vertices[i]
                    end = vertices[i + 1]

                    drawing_data.lines.append(LineInfo(
                        start_point=Coordinate(x=float(start[0]), y=float(start[1]), z=float(start[2])),
                        end_point=Coordinate(x=float(end[0]), y=float(end[1]), z=float(end[2])),
                        layer=layer,
                        color=color,
                        line_type=line_type
                    ))
            except Exception:
                continue

    def _extract_texts(self, msp, drawing_data: DrawingData) -> None:
        """提取所有文字标注"""
        electrical_layer_names = {layer.name for layer in drawing_data.layers}

        # TEXT 实体
        for text in msp.query('TEXT'):
            try:
                layer = str(text.dxf.layer)

                if layer not in electrical_layer_names:
                    continue

                position = text.dxf.insert

                drawing_data.texts.append(TextInfo(
                    content=str(text.dxf.text),
                    position=Coordinate(
                        x=float(position[0]),
                        y=float(position[1]),
                        z=float(position[2]) if len(position) > 2 else 0.0
                    ),
                    layer=layer,
                    font_size=float(text.dxf.height),
                    rotation=float(text.dxf.rotation)
                ))
            except Exception:
                continue

        # MTEXT 实体（多行文字）
        for mtext in msp.query('MTEXT'):
            try:
                layer = str(mtext.dxf.layer)

                if layer not in electrical_layer_names:
                    continue

                position = mtext.dxf.insert

                # 去除格式控制符
                content = str(mtext.text)
                import re
                content = re.sub(r'\\[a-zA-Z]+[^;]*;', '', content)

                drawing_data.texts.append(TextInfo(
                    content=content,
                    position=Coordinate(
                        x=float(position[0]),
                        y=float(position[1]),
                        z=float(position[2]) if len(position) > 2 else 0.0
                    ),
                    layer=layer,
                    font_size=float(mtext.dxf.char_height),
                    rotation=float(mtext.dxf.rotation)
                ))
            except Exception:
                continue

    def _identify_devices(self, drawing_data: DrawingData) -> None:
        """从图块中识别设备"""
        # 获取附近的文字，用于辅助识别
        nearby_text_map = self._build_nearby_text_map(drawing_data)

        for block in drawing_data.blocks:
            # 1. 首先使用图块名进行识别
            result = self._rule_manager.classify_device_with_confidence(block.name)
            raw_device_type = result['device_type']
            confidence = result['confidence']
            matched_kw = result['matched_keywords']

            # 将规则库类型归一化为系统支持的类型
            device_type = self._rule_manager.normalize_device_type(raw_device_type)

            # 2. 如果图块名识别失败，尝试使用附近的文字
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

            # 3. 添加到设备列表
            device = DeviceModel(
                name=block.name,
                type=DeviceType(device_type),
                coordinates=block.insertion_point,
                quantity=1,
                layer=block.layer or '',
                block_name=block.name,
                attributes={
                    **(block.attributes if isinstance(block.attributes, dict) else {}),
                    'confidence': round(confidence, 2),
                    'matched_keywords': matched_kw,
                    'match_method': result.get('match_method', 'keyword'),
                    'raw_type': raw_device_type
                }
            )
            drawing_data.devices.append(device)

    def _build_nearby_text_map(self, drawing_data: DrawingData) -> Dict[int, List[str]]:
        """为每个图块构建附近的文字查找表"""
        text_map = {}

        if not drawing_data.blocks or not drawing_data.texts:
            return text_map

        # 搜索半径（根据图纸尺寸动态调整）
        search_radius = 300.0

        for block in drawing_data.blocks:
            nearby_texts = []
            for text in drawing_data.texts:
                distance = self._calculate_distance(block.insertion_point, text.position)
                if distance < search_radius:
                    nearby_texts.append(text.content)

            # 按距离排序，取最近的几个
            if nearby_texts:
                text_map[id(block)] = nearby_texts[:5]

        return text_map

    def _identify_cables(self, drawing_data: DrawingData) -> None:
        """从线条中识别线缆，并按敷设方式分组"""
        cable_lines_by_method: Dict[str, List[LineInfo]] = {}

        for line in drawing_data.lines:
            layer_category = self._rule_manager.get_layer_category(line.layer)

            # 只将标记为线缆或电气的线条作为候选
            if layer_category not in ['cable', 'electrical', 'trunking', 'pipe']:
                continue

            # 通过颜色、图层、线型综合判断
            cable_info = self._rule_manager.identify_cable_type(
                text='',
                layer=line.layer,
                color=line.color,
                line_type=line.line_type
            )

            cable_type = cable_info['cable_type']
            laying_method = cable_info['laying_method']

            # 对于桥架和配管，根据颜色进一步过滤
            if cable_type == 'power' or layer_category in ['cable', 'electrical']:
                key = f'{cable_type}_{laying_method}'
                if key not in cable_lines_by_method:
                    cable_lines_by_method[key] = []
                cable_lines_by_method[key].append(line)

        # 为每个分组创建线缆对象
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
                    'source': 'dxf',
                    'line_count': len(lines),
                    'layer': lines[0].layer,
                    'color': lines[0].color,
                    'line_type': lines[0].line_type
                }
            ))

    def _identify_trunkings_and_pipes(self, drawing_data: DrawingData) -> None:
        """识别桥架和配管"""
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

        # 处理桥架
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

        # 处理配管
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

        # 如果上述识别未找到桥架，尝试通过图层分类补充识别
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
        """生成识别摘要"""
        # 按设备类型统计
        device_by_type: Dict[str, int] = {}
        for device in drawing_data.devices:
            key = device.type.value
            device_by_type[key] = device_by_type.get(key, 0) + 1

        # 按敷设方式统计线缆
        cable_by_method: Dict[str, float] = {}
        for cable in drawing_data.cables:
            key = cable.laying_method or 'unknown'
            cable_by_method[key] = cable_by_method.get(key, 0.0) + cable.length

        # 按类型统计线缆
        cable_by_type: Dict[str, int] = {}
        for cable in drawing_data.cables:
            key = cable.type.value if hasattr(cable.type, 'value') else str(cable.type)
            cable_by_type[key] = cable_by_type.get(key, 0) + 1

        return {
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
