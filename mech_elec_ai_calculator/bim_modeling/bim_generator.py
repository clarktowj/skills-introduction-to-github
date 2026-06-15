from typing import List, Dict, Any
from common.models import BIMComponent, BIMComponentType, DeviceModel, CableModel, CalculationResult, Coordinate
from framework.exceptions import ModelingError

class BIMGenerator:
    def __init__(self):
        pass
    
    def generate_from_drawing(self, devices: List[DeviceModel], cables: List[CableModel]) -> List[BIMComponent]:
        components = []
        
        for device in devices:
            component = self._create_device_component(device)
            if component:
                components.append(component)
        
        for cable in cables:
            component = self._create_cable_component(cable)
            if component:
                components.append(component)
        
        return components
    
    def generate_from_calculation(self, calculation: CalculationResult) -> List[BIMComponent]:
        components = []
        
        for item in calculation.devices:
            component = self._create_quantity_component(item, BIMComponentType.EQUIPMENT)
            if component:
                components.append(component)
        
        for item in calculation.cables:
            component = self._create_quantity_component(item, BIMComponentType.CABLE)
            if component:
                components.append(component)
        
        for item in calculation.trunkings:
            component = self._create_quantity_component(item, BIMComponentType.CABLE_TRAY)
            if component:
                components.append(component)
        
        for item in calculation.pipes:
            component = self._create_quantity_component(item, BIMComponentType.PIPE)
            if component:
                components.append(component)
        
        return components
    
    def _create_device_component(self, device: DeviceModel) -> BIMComponent:
        bim_type = self._map_device_type(device.type.value)
        
        dimensions = self._get_device_dimensions(device.type.value)
        
        component = BIMComponent(
            name=device.name,
            type=bim_type,
            position=device.coordinates,
            dimensions=dimensions,
            attributes={
                'device_type': device.type.value,
                'spec': device.spec,
                'quantity': device.quantity
            }
        )
        
        device.component_id = component.id
        
        return component
    
    def _create_cable_component(self, cable: CableModel) -> BIMComponent:
        mid_point = Coordinate(
            x=(cable.start_point.x + cable.end_point.x) / 2,
            y=(cable.start_point.y + cable.end_point.y) / 2,
            z=(cable.start_point.z + cable.end_point.z) / 2
        )
        
        length = cable.length
        diameter = self._get_cable_diameter(cable.model)
        
        component = BIMComponent(
            name=f"Cable_{cable.model}",
            type=BIMComponentType.CABLE,
            position=mid_point,
            dimensions=(length, diameter, diameter),
            attributes={
                'model': cable.model,
                'length': cable.length,
                'start_point': {
                    'x': cable.start_point.x,
                    'y': cable.start_point.y,
                    'z': cable.start_point.z
                },
                'end_point': {
                    'x': cable.end_point.x,
                    'y': cable.end_point.y,
                    'z': cable.end_point.z
                }
            }
        )
        
        cable.component_id = component.id
        
        return component
    
    def _create_quantity_component(self, item, bim_type: BIMComponentType) -> BIMComponent:
        return BIMComponent(
            name=item.name,
            type=bim_type,
            position=Coordinate(x=0.0, y=0.0, z=0.0),
            dimensions=(1.0, 1.0, 1.0),
            quantity_id=item.id,
            attributes={
                'code': item.code,
                'quantity': item.quantity,
                'unit': item.unit,
                'unit_price': item.unit_price,
                'total_price': item.total_price
            }
        )
    
    def _map_device_type(self, device_type: str) -> BIMComponentType:
        mapping = {
            'cabinet': BIMComponentType.CABINET,
            'equipment': BIMComponentType.EQUIPMENT,
            'distribution_box': BIMComponentType.DISTRIBUTION_BOX,
            'switch': BIMComponentType.FIXTURE,
            'socket': BIMComponentType.FIXTURE,
            'lighting': BIMComponentType.FIXTURE,
            'other': BIMComponentType.OTHER
        }
        return mapping.get(device_type, BIMComponentType.OTHER)
    
    def _get_device_dimensions(self, device_type: str) -> tuple:
        dimensions = {
            'cabinet': (0.8, 0.6, 2.0),
            'equipment': (1.0, 1.0, 1.0),
            'distribution_box': (0.4, 0.3, 0.2),
            'switch': (0.1, 0.1, 0.05),
            'socket': (0.08, 0.08, 0.02),
            'lighting': (0.3, 0.3, 0.2),
            'other': (0.5, 0.5, 0.5)
        }
        return dimensions.get(device_type, (0.5, 0.5, 0.5))
    
    def _get_cable_diameter(self, model: str) -> float:
        specs = {
            'BV-2.5': 0.006,
            'BV-4': 0.008,
            'BV-6': 0.01,
            'YJV-4x10': 0.03,
            'YJV-4x16': 0.035,
            'YJV-4x25': 0.04
        }
        return specs.get(model, 0.01)