import ezdxf
import os
from typing import List, Dict, Any
from common.models import DrawingData, LayerInfo, BlockInfo, LineInfo, TextInfo, DeviceModel, CableModel, Coordinate, DeviceType
from framework.exceptions import ParseError
from rule_engine.rule_manager import RuleManager

class DXFParser:
    def __init__(self):
        self._rule_manager = RuleManager()
    
    def parse(self, file_path: str) -> DrawingData:
        if not os.path.exists(file_path):
            raise ParseError(f"File not found: {file_path}")
        
        try:
            doc = ezdxf.readfile(file_path)
            msp = doc.modelspace()
            
            drawing_data = DrawingData(
                filename=os.path.basename(file_path),
                file_type='dxf'
            )
            
            self._extract_layers(doc, drawing_data)
            self._extract_blocks(msp, drawing_data)
            self._extract_lines(msp, drawing_data)
            self._extract_texts(msp, drawing_data)
            self._identify_devices(drawing_data)
            self._identify_cables(drawing_data)
            
            return drawing_data
        
        except ezdxf.DXFStructureError as e:
            raise ParseError(f"Invalid DXF file structure: {str(e)}")
        except Exception as e:
            raise ParseError(f"Failed to parse DXF file: {str(e)}")
    
    def _extract_layers(self, doc: ezdxf.Drawing, drawing_data: DrawingData) -> None:
        try:
            for layer in doc.layers:
                layer_name = str(layer)
                drawing_data.layers.append(LayerInfo(
                    name=layer_name,
                    color=str(layer.dxf.color) if hasattr(layer, 'dxf') else '7',
                    line_type=str(layer.dxf.linetype) if hasattr(layer, 'dxf') else '',
                    visible=True,
                    locked=False
                ))
        except Exception:
            # 如果无法获取图层信息，忽略错误继续解析
            pass
    
    def _extract_blocks(self, msp: ezdxf.layouts.Modelspace, drawing_data: DrawingData) -> None:
        for block_ref in msp.query('INSERT'):
            attrs = {}
            if hasattr(block_ref, 'attribs'):
                for attrib in block_ref.attribs:
                    attrs[attrib.tag] = attrib.text
            
            insertion_point = block_ref.dxf.insert
            drawing_data.blocks.append(BlockInfo(
                name=block_ref.dxf.name,
                insertion_point=Coordinate(
                    x=float(insertion_point[0]),
                    y=float(insertion_point[1]),
                    z=float(insertion_point[2]) if len(insertion_point) > 2 else 0.0
                ),
                rotation=float(block_ref.dxf.rotation),
                scale=float(block_ref.dxf.xscale),
                attributes=attrs
            ))
    
    def _extract_lines(self, msp: ezdxf.layouts.Modelspace, drawing_data: DrawingData) -> None:
        for line in msp.query('LINE'):
            start = line.dxf.start
            end = line.dxf.end
            layer = line.dxf.layer
            
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
                layer=layer
            ))
    
    def _extract_texts(self, msp: ezdxf.layouts.Modelspace, drawing_data: DrawingData) -> None:
        for text in msp.query('TEXT'):
            position = text.dxf.insert
            drawing_data.texts.append(TextInfo(
                content=text.dxf.text,
                position=Coordinate(
                    x=float(position[0]),
                    y=float(position[1]),
                    z=float(position[2]) if len(position) > 2 else 0.0
                ),
                layer=text.dxf.layer,
                font_size=float(text.dxf.height),
                rotation=float(text.dxf.rotation)
            ))
    
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
        
        for i in range(len(cable_lines) - 1):
            line1 = cable_lines[i]
            line2 = cable_lines[i + 1]
            
            if self._is_connected(line1, line2):
                start_point = line1.start_point
                end_point = line2.end_point
                
                drawing_data.cables.append(CableModel(
                    model='Unknown',
                    type='power',
                    start_point=start_point,
                    end_point=end_point,
                    length=self._calculate_distance(start_point, end_point),
                    attributes={'source': 'dxf'}
                ))
    
    def _is_cable_line(self, line: LineInfo) -> bool:
        layer_mapping = self._rule_manager.get_rule('layer_mapping', {})
        cable_layers = layer_mapping.get('线缆层', [])
        
        for cable_layer in cable_layers:
            if cable_layer.lower() in line.layer.lower():
                return True
        return False
    
    def _is_connected(self, line1: LineInfo, line2: LineInfo) -> bool:
        threshold = 0.01
        dist1 = self._calculate_distance(line1.end_point, line2.start_point)
        dist2 = self._calculate_distance(line1.end_point, line2.end_point)
        return dist1 < threshold or dist2 < threshold
    
    def _calculate_distance(self, p1: Coordinate, p2: Coordinate) -> float:
        return ((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2 + (p1.z - p2.z) ** 2) ** 0.5