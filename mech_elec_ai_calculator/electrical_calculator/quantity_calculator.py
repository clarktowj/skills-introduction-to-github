from typing import List, Dict, Any
from common.models import QuantityItem, DeviceModel, CableModel
from rule_engine.rule_manager import RuleManager

class QuantityCalculator:
    def __init__(self):
        self._rule_manager = RuleManager()
    
    def calculate_device_quantity(self, devices: List[DeviceModel]) -> List[QuantityItem]:
        items = []
        device_groups = self._group_by_type(devices)
        
        for device_type, device_list in device_groups.items():
            count = sum(d.quantity for d in device_list)
            code = self._get_device_code(device_type)
            
            items.append(QuantityItem(
                component_id=device_list[0].id if device_list else '',
                code=code,
                name=self._get_device_name(device_type),
                unit='个',
                quantity=float(count),
                category='设备',
                sub_category=device_type
            ))
        
        return items
    
    def calculate_cable_quantity(self, cables: List[CableModel]) -> List[QuantityItem]:
        items = []
        cable_groups = self._group_by_model(cables)
        
        for model, cable_list in cable_groups.items():
            total_length = 0.0
            
            for cable in cable_list:
                length = cable.length
                reserve = self._calculate_reserve_length(cable)
                correction = self._calculate_correction_factor(cable)
                total_length += (length + reserve) * correction
            
            items.append(QuantityItem(
                component_id=cable_list[0].id if cable_list else '',
                code=self._get_cable_code(model),
                name=f"{model}电缆",
                unit='米',
                quantity=total_length,
                category='线缆'
            ))
        
        return items
    
    def _group_by_type(self, devices: List[DeviceModel]) -> Dict[str, List[DeviceModel]]:
        groups = {}
        for device in devices:
            device_type = device.type.value
            if device_type not in groups:
                groups[device_type] = []
            groups[device_type].append(device)
        return groups
    
    def _group_by_model(self, cables: List[CableModel]) -> Dict[str, List[CableModel]]:
        groups = {}
        for cable in cables:
            model = cable.model if cable.model else 'Unknown'
            if model not in groups:
                groups[model] = []
            groups[model].append(cable)
        return groups
    
    def _calculate_reserve_length(self, cable: CableModel) -> float:
        return self._rule_manager.get_reserve_length('cabinet')
    
    def _calculate_correction_factor(self, cable: CableModel) -> float:
        return self._rule_manager.get_correction_factor(cable.laying_method.value)
    
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
    
    def _get_cable_code(self, model: str) -> str:
        return 'DL101'