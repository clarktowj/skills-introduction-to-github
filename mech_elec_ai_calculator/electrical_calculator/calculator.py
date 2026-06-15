from typing import List, Dict, Any
from common.models import DrawingData, CalculationResult, QuantityItem, DeviceModel, CableModel, Coordinate
from rule_engine.rule_manager import RuleManager
from framework.exceptions import CalculationError


class ElectricalCalculator:
    def __init__(self):
        self._rule_manager = RuleManager()
    
    def calculate(self, drawing_data: DrawingData) -> CalculationResult:
        try:
            result = CalculationResult(drawing_id=drawing_data.id)
            
            self._calculate_devices(drawing_data.devices, result)
            self._calculate_cables(drawing_data.cables, result, drawing_data)
            self._calculate_trunking(drawing_data, result)
            self._calculate_pipes(drawing_data, result)
            self._calculate_accessories(result)
            
            self._calculate_total_cost(result)
            
            return result
        
        except Exception as e:
            raise CalculationError(f"Failed to calculate quantities: {str(e)}")
    
    def _calculate_devices(self, devices: List[DeviceModel], result: CalculationResult) -> None:
        device_groups = self._group_devices(devices)
        
        for device_type, items in device_groups.items():
            count = sum(device.quantity for device in items)
            
            device_name = self._get_device_name(device_type)
            device_code = self._get_device_code(device_type)
            unit_price = self._get_unit_price(device_code)
            
            result.devices.append(QuantityItem(
                component_id=items[0].id if items else '',
                code=device_code,
                name=device_name,
                unit='个',
                quantity=float(count),
                unit_price=unit_price,
                total_price=float(count) * unit_price,
                category='设备',
                sub_category=device_type
            ))
    
    def _group_devices(self, devices: List[DeviceModel]) -> Dict[str, List[DeviceModel]]:
        groups = {}
        for device in devices:
            device_type = device.type.value
            if device_type not in groups:
                groups[device_type] = []
            groups[device_type].append(device)
        return groups
    
    def _get_device_code(self, device_type: str) -> str:
        code_mapping = {
            'cabinet': 'DL001',
            'equipment': 'DL002',
            'distribution_box': 'DL003',
            'switch': 'DL004',
            'socket': 'DL005',
            'lighting': 'DL006',
            'other': 'DL999'
        }
        return code_mapping.get(device_type, 'DL999')
    
    def _get_device_name(self, device_type: str) -> str:
        name_mapping = {
            'cabinet': '配电柜',
            'equipment': '电气设备',
            'distribution_box': '配电箱',
            'switch': '开关',
            'socket': '插座',
            'lighting': '照明灯具',
            'other': '其他设备'
        }
        return name_mapping.get(device_type, '其他设备')
    
    def _calculate_cables(self, cables: List[CableModel], result: CalculationResult, drawing_data: DrawingData) -> None:
        if not cables:
            return
        
        # 先统计设备数量用于预留长度计算
        cabinet_count = sum(1 for d in drawing_data.devices if d.type.value == 'cabinet')
        distribution_box_count = sum(1 for d in drawing_data.devices if d.type.value == 'distribution_box')
        
        # 按线缆类型和敷设方式分组
        cable_groups = self._group_cables(cables)
        
        for (cable_type, laying_method), items in cable_groups.items():
            total_base_length = 0.0
            total_reserve = 0.0
            total_length = 0.0
            
            for cable in items:
                base_length = cable.length
                
                # 根据敷设方式计算预留长度
                reserve = self._calculate_reserve(cable, cabinet_count, distribution_box_count)
                
                # 根据敷设方式计算修正系数
                correction = self._calculate_correction(cable, laying_method)
                
                # 汇总: (基础长度 + 预留) * 修正系数
                cable_total = (base_length + reserve) * correction
                
                total_base_length += base_length
                total_reserve += reserve
                total_length += cable_total
            
            # 获取线缆信息
            cable_info = self._get_cable_price_info(cable_type, laying_method)
            
            result.cables.append(QuantityItem(
                component_id=items[0].id if items else '',
                code=cable_info.get('code', 'DL101'),
                name=self._format_cable_name(cable_type, laying_method),
                unit='米',
                quantity=round(total_length, 2),
                unit_price=cable_info.get('unit_price', 100.0),
                total_price=round(total_length, 2) * cable_info.get('unit_price', 100.0),
                category='线缆',
                sub_category=laying_method,
                description=f"基础长度: {total_base_length:.2f}m, 预留: {total_reserve:.2f}m, 敷设方式: {self._get_laying_method_name(laying_method)}"
            ))
    
    def _group_cables(self, cables: List[CableModel]) -> Dict[tuple, List[CableModel]]:
        groups = {}
        for cable in cables:
            cable_type = cable.type.value if hasattr(cable.type, 'value') else str(cable.type)
            laying_method = cable.laying_method if cable.laying_method else 'cable_tray'
            key = (cable_type, laying_method)
            if key not in groups:
                groups[key] = []
            groups[key].append(cable)
        return groups
    
    def _calculate_reserve(self, cable: CableModel, cabinet_count: int, distribution_box_count: int) -> float:
        """计算线缆预留长度"""
        reserve = 0.0
        
        # 设备端预留 (柜内预留)
        cabinet_reserve = self._rule_manager.get_reserve_length('cabinet')
        reserve += cabinet_reserve * max(cabinet_count, 1)
        
        # 配电箱端预留
        distribution_reserve = self._rule_manager.get_reserve_length('distribution_box')
        reserve += distribution_reserve * max(distribution_box_count, 1)
        
        # 弯头/接线预留
        elbow_reserve = self._rule_manager.get_reserve_length('elbow')
        reserve += elbow_reserve * 2  # 每根电缆至少两个弯头
        
        return reserve
    
    def _calculate_correction(self, cable: CableModel, laying_method: str) -> float:
        """根据敷设方式计算修正系数"""
        # 使用线缆自身的 laying_method，如果没有则使用传入的
        cable_laying = cable.laying_method if cable.laying_method else laying_method
        
        # 从规则库获取对应敷设方式的修正系数
        factor = self._rule_manager.get_correction_factor(cable_laying)
        
        # 如果没有找到特定敷设方式的系数，使用cable_tray系数
        if factor == 1.0 and cable_laying not in ['cable_tray']:
            factor = self._rule_manager.get_correction_factor('cable_tray')
        
        return factor
    
    def _get_cable_price_info(self, cable_type: str, laying_method: str) -> Dict[str, Any]:
        """根据线缆类型获取价格信息"""
        unit_prices = self._rule_manager.get_rule('unit_prices', {})
        
        price_key = f'cable_{cable_type}'
        unit_price = unit_prices.get(price_key, 100.0)
        
        # 根据敷设方式调整单价 (架空比穿管略便宜)
        if laying_method == 'pipe':
            unit_price = unit_price * 1.1  # 穿管敷设加10%材料成本
        elif laying_method == 'direct_burial':
            unit_price = unit_price * 1.15  # 直埋敷设加15%材料成本
        
        return {
            'code': self._get_cable_code(cable_type),
            'unit_price': unit_price
        }
    
    def _get_cable_code(self, cable_type: str) -> str:
        code_mapping = {
            'power': 'DL101',
            'control': 'DL102',
            'signal': 'DL103',
            'communication': 'DL104'
        }
        return code_mapping.get(cable_type, 'DL101')
    
    def _format_cable_name(self, cable_type: str, laying_method: str) -> str:
        type_names = {
            'power': '电力电缆',
            'control': '控制电缆',
            'signal': '信号电缆',
            'communication': '通信电缆'
        }
        method_names = {
            'pipe': '(穿管敷设)',
            'cable_tray': '(桥架敷设)',
            'ceiling': '(吊顶敷设)',
            'wall': '(沿墙敷设)',
            'direct_burial': '(直埋敷设)',
            'trunking': '(线槽敷设)'
        }
        
        type_name = type_names.get(cable_type, '电缆')
        method_name = method_names.get(laying_method, '')
        
        return f"{type_name}{method_name}"
    
    def _get_laying_method_name(self, laying_method: str) -> str:
        method_names = {
            'pipe': '穿管',
            'cable_tray': '桥架',
            'ceiling': '吊顶',
            'wall': '沿墙',
            'direct_burial': '直埋',
            'trunking': '线槽'
        }
        return method_names.get(laying_method, laying_method)
    
    def _calculate_trunking(self, drawing_data: DrawingData, result: CalculationResult) -> None:
        # 优先使用解析器识别的桥架
        if drawing_data.trunkings:
            for trunking in drawing_data.trunkings:
                length = trunking.get('length', 0)
                if length > 0:
                    result.trunkings.append(QuantityItem(
                        component_id='trunking_001',
                        code='DL201',
                        name='电缆桥架',
                        unit='米',
                        quantity=round(length, 2),
                        unit_price=300.0,
                        total_price=round(length, 2) * 300.0,
                        category='桥架'
                    ))
            return
        
        # 退而求其次：通过图层识别桥架
        layer_mapping = self._rule_manager.get_rule('layer_mapping', {})
        trunking_layers = layer_mapping.get('桥架层', [])
        
        trunking_lines = [
            line for line in drawing_data.lines
            if any(layer.lower() in line.layer.lower() for layer in trunking_layers)
        ]
        
        if trunking_lines:
            total_length = sum(self._calculate_distance(line.start_point, line.end_point) for line in trunking_lines)
            
            # 桥架修正系数
            correction = self._rule_manager.get_correction_factor('cable_tray')
            adjusted_length = total_length * correction
            
            result.trunkings.append(QuantityItem(
                component_id='trunking_001',
                code='DL201',
                name='电缆桥架',
                unit='米',
                quantity=round(adjusted_length, 2),
                unit_price=300.0,
                total_price=round(adjusted_length, 2) * 300.0,
                category='桥架'
            ))
    
    def _calculate_pipes(self, drawing_data: DrawingData, result: CalculationResult) -> None:
        layer_mapping = self._rule_manager.get_rule('layer_mapping', {})
        pipe_layers = layer_mapping.get('配管层', [])
        
        pipe_lines = [
            line for line in drawing_data.lines
            if any(layer.lower() in line.layer.lower() for layer in pipe_layers)
        ]
        
        if pipe_lines:
            total_length = sum(self._calculate_distance(line.start_point, line.end_point) for line in pipe_lines)
            
            # 配管修正系数
            correction = self._rule_manager.get_correction_factor('pipe')
            adjusted_length = total_length * correction
            
            result.pipes.append(QuantityItem(
                component_id='pipe_001',
                code='DL301',
                name='配管',
                unit='米',
                quantity=round(adjusted_length, 2),
                unit_price=50.0,
                total_price=round(adjusted_length, 2) * 50.0,
                category='配管'
            ))
    
    def _calculate_accessories(self, result: CalculationResult) -> None:
        device_count = sum(item.quantity for item in result.devices)
        cable_count = len(result.cables)
        
        if cable_count > 0:
            result.accessories.append(QuantityItem(
                component_id='accessory_001',
                code='DL401',
                name='电缆头',
                unit='个',
                quantity=cable_count * 2,
                unit_price=50.0,
                total_price=cable_count * 2 * 50.0,
                category='辅材'
            ))
        
        if device_count > 0:
            result.accessories.append(QuantityItem(
                component_id='accessory_002',
                code='DL402',
                name='接线端子',
                unit='个',
                quantity=device_count * 4,
                unit_price=5.0,
                total_price=device_count * 4 * 5.0,
                category='辅材'
            ))
    
    def _calculate_total_cost(self, result: CalculationResult) -> None:
        cost_rates = self._rule_manager.get_rule('cost_rates', {})
        labor_rate = cost_rates.get('labor_rate', 180.0)
        material_rate = cost_rates.get('material_rate', 1.0)
        
        total_cost = 0.0
        
        for item in result.devices + result.cables + result.trunkings + result.pipes + result.accessories:
            total_cost += item.total_price
        
        # 管理费率和利润率
        total_cost *= (1 + cost_rates.get('management_rate', 0.15))
        total_cost *= (1 + cost_rates.get('profit_rate', 0.08))
        
        result.total_cost = round(total_cost, 2)
    
    def _get_unit_price(self, code: str) -> float:
        price_mapping = {
            'DL001': 5000.0,
            'DL002': 2000.0,
            'DL003': 800.0,
            'DL004': 50.0,
            'DL005': 20.0,
            'DL006': 100.0,
            'DL101': 100.0,
            'DL201': 300.0,
            'DL301': 50.0,
            'DL401': 50.0,
            'DL402': 5.0,
        }
        return price_mapping.get(code, 100.0)
    
    def _calculate_distance(self, p1: Coordinate, p2: Coordinate) -> float:
        return ((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2 + (p1.z - p2.z) ** 2) ** 0.5
