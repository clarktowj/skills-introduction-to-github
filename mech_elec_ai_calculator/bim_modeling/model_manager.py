"""
BIM 构件管理器 —— 量模 ID 双向绑定
"""
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from common.models import BIMComponent, CalculationResult, Coordinate
from framework.exceptions import ModelingError


@dataclass
class BindingRecord:
    component_id: str
    quantity_id: Optional[str]
    device_id: Optional[str]
    cable_id: Optional[str]


class ModelManager:
    def __init__(self):
        self._components: List[BIMComponent] = []
        self._component_index: Dict[str, BIMComponent] = {}
        self._component_to_quantity: Dict[str, str] = {}
        self._quantity_to_component: Dict[str, str] = {}
        self._component_to_device: Dict[str, str] = {}
        self._change_log: List[Dict[str, Any]] = []

    def add_components(self, components: List[BIMComponent]) -> None:
        for comp in components:
            self.add_component(comp)

    def add_component(self, component: BIMComponent) -> None:
        if component.id in self._component_index:
            return
        self._components.append(component)
        self._component_index[component.id] = component
        if component.quantity_id:
            self.bind_quantity(component.id, component.quantity_id)
        if isinstance(component.attributes, dict) and 'device_id' in component.attributes:
            self._component_to_device[component.id] = component.attributes['device_id']

    def get_component(self, component_id: str) -> Optional[BIMComponent]:
        return self._component_index.get(component_id)

    def get_components_by_type(self, component_type) -> List[BIMComponent]:
        return [c for c in self._components if str(c.type) == str(component_type) or
                (hasattr(c.type, 'value') and c.type.value == str(component_type))]

    # ============ 量模绑定 ============

    def bind_quantity(self, component_id: str, quantity_id: str) -> None:
        if component_id not in self._component_index:
            raise ModelingError(f"构件不存在: {component_id}")
        self._component_to_quantity[component_id] = quantity_id
        self._quantity_to_component[quantity_id] = component_id
        comp = self._component_index[component_id]
        if isinstance(comp.attributes, dict):
            comp.attributes['quantity_id'] = quantity_id
        else:
            comp.quantity_id = quantity_id

    def bind_from_calculation(self, calculation) -> int:
        """
        从算量结果自动绑定构件 ↔ 工程量
        优先精确匹配（component_id），其次按分类+位置批量绑定
        """
        all_items = (
            list(calculation.devices) +
            list(calculation.cables) +
            list(calculation.trunkings) +
            list(calculation.pipes) +
            list(calculation.accessories)
        )

        bound_count = 0

        # Phase 1: 精确 component_id 匹配
        for item in all_items:
            if item.component_id and item.component_id in self._component_index:
                self.bind_quantity(item.component_id, item.id)
                bound_count += 1

        if bound_count > 0:
            return bound_count

        # Phase 2: 按分类映射 (例如 cabinet → 配电柜, cable → 电力电缆)
        type_to_category_map = {
            'cabinet': ['配电柜', '开关柜', 'AP', '配电柜'],
            'distribution_box': ['配电箱', '配电盘', 'AL', 'ALE', 'AT'],
            'equipment': ['电气设备', '电机', '马达', 'MCC', '设备'],
            'fixture': ['开关', '插座', '灯具', '照明'],
            'cable': ['电缆', '电力', '控制', 'BV', 'YJV'],
            'cable_tray': ['桥架', '线槽'],
            'pipe': ['配管', '钢管', 'PVC', 'JDG'],
        }

        # 通过构件类型找到对应的算量项，按顺序绑定
        remaining_items = list(all_items)
        for comp_id, comp in self._component_index.items():
            if comp_id in self._component_to_quantity:
                continue

            comp_type = comp.type.value if hasattr(comp.type, 'value') else str(comp.type)
            candidate_categories = type_to_category_map.get(comp_type, [])

            matched_item = None
            for idx, item in enumerate(remaining_items):
                if any(cat in item.name for cat in candidate_categories):
                    matched_item = item
                    remaining_items.pop(idx)
                    break

            if matched_item is None:
                # 兜底：按 item.category 匹配
                for idx, item in enumerate(remaining_items):
                    if item.category and comp_type in item.category.lower():
                        matched_item = item
                        remaining_items.pop(idx)
                        break

            if matched_item:
                self.bind_quantity(comp_id, matched_item.id)
                if isinstance(comp.attributes, dict):
                    comp.attributes['quantity'] = matched_item.quantity
                    comp.attributes['unit'] = matched_item.unit
                    comp.attributes['unit_price'] = matched_item.unit_price
                    comp.attributes['total_price'] = matched_item.total_price
                    comp.attributes['code'] = matched_item.code
                    comp.attributes['quantity_id'] = matched_item.id
                bound_count += 1

        return bound_count

    # ============ 查询 ============

    def get_quantity_for_component(self, component_id: str) -> Optional[str]:
        return self._component_to_quantity.get(component_id)

    def get_component_for_quantity(self, quantity_id: str) -> Optional[BIMComponent]:
        comp_id = self._quantity_to_component.get(quantity_id)
        return self._component_index.get(comp_id) if comp_id else None

    def get_binding_report(self) -> Dict[str, Any]:
        total = len(self._components)
        bound = len(self._component_to_quantity)
        return {
            'total_components': total,
            'components_with_quantity': bound,
            'coverage': round(bound / total, 3) if total else 0.0,
            'bindings': list(self._component_to_quantity.items()),
        }

    # ============ 联动更新 ============

    def update_component_quantity(self, component_id: str, new_quantity: float,
                                   new_unit_price: Optional[float] = None) -> bool:
        import datetime
        comp = self._component_index.get(component_id)
        if not comp:
            return False
        if isinstance(comp.attributes, dict):
            old_q = comp.attributes.get('quantity', 0)
            comp.attributes['quantity'] = new_quantity
            if new_unit_price is not None:
                comp.attributes['unit_price'] = new_unit_price
                comp.attributes['total_price'] = round(new_quantity * new_unit_price, 2)
            self._change_log.append({
                'action': 'update_quantity',
                'component_id': component_id,
                'old': old_q,
                'new': new_quantity,
                'timestamp': datetime.datetime.now().isoformat()
            })
            return True
        return False

    def update_component_position(self, component_id: str, new_position: Coordinate) -> bool:
        comp = self._component_index.get(component_id)
        if not comp:
            return False
        old = comp.position
        comp.position = new_position
        self._change_log.append({
            'action': 'update_position',
            'component_id': component_id,
            'old': (old.x, old.y, old.z),
            'new': (new_position.x, new_position.y, new_position.z),
        })
        return True

    def get_changes_since(self, since_index: int = 0) -> List[Dict[str, Any]]:
        return self._change_log[since_index:]

    # ============ 导出 ============

    def export_to_dict(self) -> Dict[str, Any]:
        return {
            'components': [
                {
                    'id': c.id,
                    'name': c.name,
                    'type': c.type.value if hasattr(c.type, 'value') else str(c.type),
                    'position': {
                        'x': c.position.x,
                        'y': c.position.y,
                        'z': c.position.z,
                    },
                    'dimensions': {
                        'width': c.dimensions[0],
                        'depth': c.dimensions[1],
                        'height': c.dimensions[2],
                    },
                    'quantity_id': c.quantity_id,
                    'attributes': c.attributes if isinstance(c.attributes, dict) else {},
                }
                for c in self._components
            ],
            'bindings': self.get_binding_report(),
            'change_count': len(self._change_log),
        }

    def clear(self) -> None:
        self._components.clear()
        self._component_index.clear()
        self._component_to_quantity.clear()
        self._quantity_to_component.clear()
        self._component_to_device.clear()
        self._change_log.clear()

    @property
    def component_count(self) -> int:
        return len(self._components)

    @property
    def components(self) -> List[BIMComponent]:
        return self._components

    def validate_quantity_binding(self, calculation: CalculationResult) -> bool:
        report = self.get_binding_report()
        if report['coverage'] < 0.5:
            raise ModelingError(
                f"量模绑定覆盖率仅 {report['coverage']*100:.0f}%，"
                f"建议检查构件与工程量的匹配关系"
            )
        return True
