import ezdxf
from typing import List
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
            
            self._extract_layers(doc, drawing_data)
            self._extract_blocks(doc, drawing_data)
            self._extract_lines(msp, drawing_data)
            self._extract_texts(msp, drawing_data)
            self._identify_devices(drawing_data)
            self._identify_cables(drawing_data)
            self._identify_trunkings(drawing_data)
            
            return drawing_data
        
        except Exception as e:
            raise ParseError(f"Failed to parse DXF file: {str(e)}")
    
    def _extract_layers(self, doc, drawing_data: DrawingData) -> None:
        try:
            for layer in doc.layers:
                layer_name = str(layer)
                try:
                    color = str(layer.dxf.color) if hasattr(layer, 'dxf') else '7'
                except Exception:
                    color = '7'
                try:
                    line_type = str(layer.dxf.linetype) if hasattr(layer, 'dxf') else 'CONTINUOUS'
                except Exception:
                    line_type = 'CONTINUOUS'
                
                drawing_data.layers.append(LayerInfo(
                    name=layer_name,
                    color=color,
                    line_type=line_type,
                    visible=True,
                    locked=False
                ))
        except Exception:
            pass
    
    def _extract_blocks(self, doc, drawing_data: DrawingData) -> None:
        try:
            for block_ref in doc.modelspace().query('INSERT'):
                try:
                    block_name = str(block_ref.dxf.name)
                    insert = block_ref.dxf.insert
                    
                    drawing_data.blocks.append(BlockInfo(
                        name=block_name,
                        insertion_point=Coordinate(
                            x=float(insert[0]),
                            y=float(insert[1]),
                            z=float(insert[2]) if len(insert) > 2 else 0.0
                        ),
                        layer=str(block_ref.dxf.layer),
                        attributes={}
                    ))
                except Exception:
                    continue
        except Exception:
            pass
    
    def _extract_lines(self, msp, drawing_data: DrawingData) -> None:
        # 提取所有 LINE 实体
        for line in msp.query('LINE'):
            try:
                start = line.dxf.start
                end = line.dxf.end
                layer = str(line.dxf.layer)
                
                # 提取颜色
                try:
                    color = str(line.dxf.color)
                except Exception:
                    color = '7'
                
                # 提取线型
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
    
    def _extract_texts(self, msp, drawing_data: DrawingData) -> None:
        for text in msp.query('TEXT'):
            try:
                position = text.dxf.insert
                drawing_data.texts.append(TextInfo(
                    content=str(text.dxf.text),
                    position=Coordinate(
                        x=float(position[0]),
                        y=float(position[1]),
                        z=float(position[2]) if len(position) > 2 else 0.0
                    ),
                    layer=str(text.dxf.layer),
                    font_size=float(text.dxf.height),
                    rotation=float(text.dxf.rotation)
                ))
            except Exception:
                continue
    
    def _identify_devices(self, drawing_data: DrawingData) -> None:
        for block in drawing_data.blocks:
            device_type = self._classify_block(block.name)
            if device_type != 'other':
                drawing_data.devices.append(DeviceModel(
                    name=block.name,
                    type=DeviceType(device_type),
                    coordinates=block.insertion_point,
                    quantity=1,
                    layer='',
                    block_name=block.name,
                    attributes=block.attributes
                ))
    
    def _classify_block(self, block_name: str) -> str:
        return self._rule_manager.classify_device(block_name)
    
    def _identify_cables(self, drawing_data: DrawingData) -> None:
        cable_lines = []
        for line in drawing_data.lines:
            if self._is_cable_line(line):
                cable_lines.append(line)
        
        # 按敷设方式分组
        cable_groups = {}
        for line in cable_lines:
            laying_method = self._detect_laying_method(line)
            if laying_method not in cable_groups:
                cable_groups[laying_method] = []
            cable_groups[laying_method].append(line)
        
        # 为每种敷设方式创建线缆
        for laying_method, lines in cable_groups.items():
            total_length = 0.0
            for line in lines:
                length = self._calculate_distance(line.start_point, line.end_point)
                total_length += length
            
            if total_length > 0.01:
                cable_type = self._detect_cable_type(lines[0])
                cable_name = self._detect_cable_name(lines[0])
                
                drawing_data.cables.append(CableModel(
                    model=cable_name,
                    type=cable_type,
                    start_point=lines[0].start_point,
                    end_point=lines[-1].end_point,
                    length=total_length,
                    reserved_length=0.0,
                    laying_method=laying_method,
                    core_count=0,
                    attributes={'source': 'dxf', 'line_count': len(lines)}
                ))
    
    def _is_cable_line(self, line) -> bool:
        layer = line.layer or ''
        
        # 通过图层名判断
        cable_keywords = ['电缆', '线缆', '导线', '缆', 'wire', 'cable']
        for keyword in cable_keywords:
            if keyword in layer:
                return True
        
        # 通过颜色判断 - 颜色1(红)、3(绿)、5(蓝)通常表示电力线
        color = getattr(line, 'color', '7')
        power_colors = ['1', '3', '5']
        if color in power_colors:
            return True
        
        # 通过线型判断
        line_type = getattr(line, 'line_type', 'CONTINUOUS')
        if line_type in ['CONTINUOUS', 'DASHED', 'PHANTOM']:
            # 连续线、虚线可能是线缆（需结合图层或颜色进一步判断）
            pass
        
        return False
    
    def _detect_cable_type(self, line) -> str:
        color = getattr(line, 'color', '7')
        layer = line.layer or ''
        
        # 通过颜色判断线缆类型
        if color in ['1', '3', '5']:
            return 'power'
        elif color in ['2']:
            return 'control'
        elif color in ['4']:
            return 'signal'
        elif color in ['6']:
            return 'communication'
        else:
            # 白色/默认颜色 - 通过图层判断
            if '控制' in layer:
                return 'control'
            elif '信号' in layer or '通信' in layer:
                return 'signal'
            else:
                return 'power'
    
    def _detect_cable_name(self, line) -> str:
        color = getattr(line, 'color', '7')
        color_names = {
            '1': '电力电缆 (红)',
            '2': '控制电缆 (黄)',
            '3': '电力电缆 (绿)',
            '4': '信号电缆 (青)',
            '5': '电力电缆 (蓝)',
            '6': '通信电缆 (品红)',
            '7': '通用电缆'
        }
        return color_names.get(color, '电力电缆')
    
    def _detect_laying_method(self, line) -> str:
        line_type = getattr(line, 'line_type', 'CONTINUOUS')
        layer = line.layer or ''
        
        # 通过线型判断敷设方式
        if 'DASHED' in line_type or 'dashed' in line_type.lower():
            return 'pipe'
        elif 'PHANTOM' in line_type or 'phantom' in line_type.lower():
            return 'ceiling'
        elif 'CENTER' in line_type:
            return 'cable_tray'
        
        # 通过图层判断
        if '管' in layer or '配管' in layer:
            return 'pipe'
        elif '桥架' in layer or '线槽' in layer:
            return 'cable_tray'
        elif '吊顶' in layer or '天' in layer:
            return 'ceiling'
        elif '墙' in layer:
            return 'wall'
        elif '埋' in layer or '地' in layer:
            return 'direct_burial'
        
        return 'cable_tray'
    
    def _identify_trunkings(self, drawing_data: DrawingData) -> None:
        trunking_lines = []
        for line in drawing_data.lines:
            if self._is_trunking_line(line):
                trunking_lines.append(line)
        
        if trunking_lines:
            total_length = 0.0
            for line in trunking_lines:
                length = self._calculate_distance(line.start_point, line.end_point)
                total_length += length
            
            if total_length > 0.01:
                drawing_data.trunkings.append({
                    'name': '桥架',
                    'type': 'cable_tray',
                    'length': total_length,
                    'layer': trunking_lines[0].layer,
                    'line_count': len(trunking_lines)
                })
    
    def _is_trunking_line(self, line) -> bool:
        layer = line.layer or ''
        
        # 通过图层名判断
        trunking_keywords = ['桥架', '线槽', 'trunk', 'tray']
        for keyword in trunking_keywords:
            if keyword in layer:
                return True
        
        return False
    
    def _is_connected(self, line1, line2) -> bool:
        tolerance = 1.0
        
        # 检查端点是否接近
        connections = [
            (line1.end_point, line2.start_point),
            (line1.end_point, line2.end_point),
            (line1.start_point, line2.start_point),
            (line1.start_point, line2.end_point),
        ]
        
        for p1, p2 in connections:
            if self._calculate_distance(p1, p2) < tolerance:
                return True
        
        return False
    
    @staticmethod
    def _calculate_distance(p1: Coordinate, p2: Coordinate) -> float:
        return math.sqrt(
            (p2.x - p1.x) ** 2 +
            (p2.y - p1.y) ** 2 +
            (p2.z - p1.z) ** 2
        )
