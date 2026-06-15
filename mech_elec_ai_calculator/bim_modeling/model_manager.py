from typing import List, Dict, Optional
from common.models import BIMComponent, CalculationResult
from framework.exceptions import ModelingError

class ModelManager:
    def __init__(self):
        self._components: List[BIMComponent] = []
        self._id_mapping: Dict[str, BIMComponent] = {}
    
    def add_components(self, components: List[BIMComponent]) -> None:
        for component in components:
            self._components.append(component)
            self._id_mapping[component.id] = component
    
    def get_component(self, component_id: str) -> Optional[BIMComponent]:
        return self._id_mapping.get(component_id)
    
    def get_components_by_type(self, component_type) -> List[BIMComponent]:
        return [c for c in self._components if c.type == component_type]
    
    def validate_quantity_binding(self, calculation: CalculationResult) -> bool:
        quantity_ids = set()
        
        for item in calculation.devices:
            quantity_ids.add(item.component_id)
        for item in calculation.cables:
            quantity_ids.add(item.component_id)
        for item in calculation.trunkings:
            quantity_ids.add(item.component_id)
        for item in calculation.pipes:
            quantity_ids.add(item.component_id)
        
        model_ids = set(c.id for c in self._components)
        
        missing_in_model = quantity_ids - model_ids
        missing_in_quantity = model_ids - quantity_ids
        
        if missing_in_model:
            raise ModelingError(f"Missing components in model: {', '.join(missing_in_model)}")
        
        if missing_in_quantity:
            raise ModelingError(f"Missing quantities for components: {', '.join(missing_in_quantity)}")
        
        return True
    
    def update_component_position(self, component_id: str, new_position) -> None:
        component = self.get_component(component_id)
        if component:
            component.position = new_position
        else:
            raise ModelingError(f"Component not found: {component_id}")
    
    def export_to_dict(self) -> List[Dict]:
        return [component.model_dump() for component in self._components]
    
    def clear(self) -> None:
        self._components = []
        self._id_mapping = {}
    
    @property
    def component_count(self) -> int:
        return len(self._components)