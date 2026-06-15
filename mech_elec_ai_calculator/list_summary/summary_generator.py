from typing import List, Dict, Any
from common.models import ListSummary, CalculationResult, QuantityItem, AuditResult
from framework.exceptions import CalculationError

class SummaryGenerator:
    def __init__(self):
        pass
    
    def generate(self, calculation: CalculationResult, audit_result: AuditResult = None, project_name: str = "", project_code: str = "") -> ListSummary:
        summary = ListSummary(
            project_name=project_name,
            project_code=project_code,
            calculation_id=calculation.id
        )
        
        if audit_result:
            summary.audit_id = audit_result.id
        
        self._add_items(summary, calculation.devices, '设备')
        self._add_items(summary, calculation.cables, '线缆')
        self._add_items(summary, calculation.trunkings, '桥架')
        self._add_items(summary, calculation.pipes, '配管')
        self._add_items(summary, calculation.accessories, '辅材')
        
        self._calculate_totals(summary)
        
        return summary
    
    def _add_items(self, summary: ListSummary, items: List[QuantityItem], category: str) -> None:
        for item in items:
            summary_item = QuantityItem(
                id=item.id,
                component_id=item.component_id,
                code=item.code,
                name=item.name,
                unit=item.unit,
                quantity=item.quantity,
                unit_price=item.unit_price,
                total_price=item.total_price,
                category=category,
                sub_category=item.sub_category,
                description=item.description,
                attributes=item.attributes
            )
            summary.items.append(summary_item)
    
    def _calculate_totals(self, summary: ListSummary) -> None:
        summary.total_quantity = sum(item.quantity for item in summary.items)
        summary.total_cost = sum(item.total_price for item in summary.items)
    
    def group_by_category(self, summary: ListSummary) -> Dict[str, List[QuantityItem]]:
        groups = {}
        for item in summary.items:
            if item.category not in groups:
                groups[item.category] = []
            groups[item.category].append(item)
        return groups
    
    def filter_by_category(self, summary: ListSummary, category: str) -> List[QuantityItem]:
        return [item for item in summary.items if item.category == category]
    
    def get_category_totals(self, summary: ListSummary) -> Dict[str, float]:
        totals = {}
        for item in summary.items:
            if item.category not in totals:
                totals[item.category] = 0.0
            totals[item.category] += item.total_price
        return totals