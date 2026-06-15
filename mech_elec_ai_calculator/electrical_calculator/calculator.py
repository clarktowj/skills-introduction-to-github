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
            self._calculate_cables(drawing_data.cables, result)
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
            
            result.devices.append(QuantityItem(
                component_id=items[0].id if items else '',
                code=self._get_device_code(device_type),
                name=self._get_device_name(device_type),
                unit='个',
                quantity=float(count),
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
    
    def _calculate_cables(self, cables: List[CableModel], result: CalculationResult) -> None:
        cable_groups = self._group_cables(cables)
        
        for cable_model, items in cable_groups.items():
            total_length = 0.0
            
            for cable in items:
                length = cable.length
                reserve = self._calculate_reserve(cable)
                correction = self._calculate_correction(cable)
                total_length += (length + reserve) * correction
            
            cable_info = self._get_cable_info(cable_model)
            
            result.cables.append(QuantityItem(
                component_id=items[0].id if items else '',
                code=cable_info.get('code', 'DL101'),
                name=f"{cable_model}电缆",
                unit='米',
                quantity=total_length,
                category='线缆',
                sub_category=cable_info.get('type', 'power')
            ))
    
    def _group_cables(self, cables: List[CableModel]) -> Dict[str, List[CableModel]]:
        groups = {}
        for cable in cables:
            model = cable.model if cable.model else 'Unknown'
            if model not in groups:
                groups[model] = []
            groups[model].append(cable)
        return groups
    
    def _calculate_reserve(self, cable: CableModel) -> float:
        reserve_length = self._rule_manager.get_reserve_length('cabinet')
        return reserve_length
    
    def _calculate_correction(self, cable: CableModel) -> float:
        laying_method = cable.laying_method.value
        return self._rule_manager.get_correction_factor(laying_method)
    
    def _get_cable_info(self, cable_model: str) -> Dict[str, str]:
        specs = self._rule_manager.get_rule('material_specifications.cables', {})
        return specs.get(cable_model, {'type': 'power', 'code': 'DL101'})
    
    def _calculate_trunking(self, drawing_data: DrawingData, result: CalculationResult) -> None:
        trunking_lines = self._identify_trunking_lines(drawing_data)
        
        if trunking_lines:
            total_length = sum(self._calculate_distance(line.start_point, line.end_point) for line in trunking_lines)
            
            result.trunkings.append(QuantityItem(
                component_id='trunking_001',
                code='DL201',
                name='桥架',
                unit='米',
                quantity=total_length,
                category='桥架'
            ))
    
    def _identify_trunking_lines(self, drawing_data: DrawingData) -> List[Any]:
        layer_mapping = self._rule_manager.get_rule('layer_mapping', {})
        trunking_layers = layer_mapping.get('桥架层', [])
        
        return [line for line in drawing_data.lines 
                if any(layer.lower() in line.layer.lower() for layer in trunking_layers)]
    
    def _calculate_pipes(self, drawing_data: DrawingData, result: CalculationResult) -> None:
        pipe_lines = self._identify_pipe_lines(drawing_data)
        
        if pipe_lines:
            total_length = sum(self._calculate_distance(line.start_point, line.end_point) for line in pipe_lines)
            
            result.pipes.append(QuantityItem(
                component_id='pipe_001',
                code='DL301',
                name='配管',
                unit='米',
                quantity=total_length,
                category='配管'
            ))
    
    def _identify_pipe_lines(self, drawing_data: DrawingData) -> List[Any]:
        layer_mapping = self._rule_manager.get_rule('layer_mapping', {})
        pipe_layers = layer_mapping.get('配管层', [])
        
        return [line for line in drawing_data.lines 
                if any(layer.lower() in line.layer.lower() for layer in pipe_layers)]
    
    def _calculate_accessories(self, result: CalculationResult) -> None:
        device_count = sum(item.quantity for item in result.devices)
        cable_count = len(result.cables)
        
        result.accessories.append(QuantityItem(
            component_id='accessory_001',
            code='DL401',
            name='电缆头',
            unit='个',
            quantity=cable_count * 2,
            category='辅材'
        ))
        
        result.accessories.append(QuantityItem(
            component_id='accessory_002',
            code='DL402',
            name='接线端子',
            unit='个',
            quantity=device_count * 4,
            category='辅材'
        ))
    
    def _calculate_total_cost(self, result: CalculationResult) -> None:
        cost_rates = self._rule_manager.get_rule('cost_rates', {})
        labor_rate = cost_rates.get('labor_rate', 180.0)
        material_rate = cost_rates.get('material_rate', 1.0)
        
        total_cost = 0.0
        
        for item in result.devices + result.cables + result.trunkings + result.pipes + result.accessories:
            unit_price = self._get_unit_price(item.code)
            item.unit_price = unit_price
            item.total_price = item.quantity * unit_price * material_rate
            total_cost += item.total_price
        
        total_cost *= (1 + cost_rates.get('management_rate', 0.15))
        total_cost *= (1 + cost_rates.get('profit_rate', 0.08))
        
        result.total_cost = total_cost
    
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