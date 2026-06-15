from typing import List, Dict, Any
from common.models import AuditIssue, AuditIssueType, CalculationResult, DrawingData
from rule_engine.rule_manager import RuleManager

class AuditProcessor:
    def __init__(self):
        self._rule_manager = RuleManager()
    
    def process_audit_results(self, issues: List[AuditIssue], calculation: CalculationResult) -> CalculationResult:
        for issue in issues:
            if issue.type == AuditIssueType.WRONG_CABLE_LENGTH:
                self._correct_cable_length(issue, calculation)
            elif issue.type == AuditIssueType.WRONG_DEVICE:
                self._correct_device(issue, calculation)
        
        return calculation
    
    def _correct_cable_length(self, issue: AuditIssue, calculation: CalculationResult) -> None:
        if issue.related_quantity_id:
            for cable in calculation.cables:
                if cable.id == issue.related_quantity_id:
                    threshold = self._rule_manager.get_validation_threshold('max_cable_length')
                    if cable.quantity > threshold:
                        cable.quantity = threshold
                        issue.suggestion = f"已自动修正为阈值 {threshold} 米"
    
    def _correct_device(self, issue: AuditIssue, calculation: CalculationResult) -> None:
        if issue.related_quantity_id:
            for device in calculation.devices:
                if device.id == issue.related_quantity_id:
                    device.name = f"{device.name}_修正"
                    issue.suggestion = "已标记需人工复核"
    
    def prioritize_issues(self, issues: List[AuditIssue]) -> List[AuditIssue]:
        priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        
        return sorted(issues, key=lambda x: priority_order.get(x.severity, 4))
    
    def generate_report(self, issues: List[AuditIssue]) -> str:
        report = ["## 审核报告"]
        
        critical = [i for i in issues if i.severity == 'critical']
        high = [i for i in issues if i.severity == 'high']
        medium = [i for i in issues if i.severity == 'medium']
        low = [i for i in issues if i.severity == 'low']
        
        if critical:
            report.append("### 严重问题")
            for i, issue in enumerate(critical, 1):
                report.append(f"{i}. {issue.description}")
        
        if high:
            report.append("### 高优先级问题")
            for i, issue in enumerate(high, 1):
                report.append(f"{i}. {issue.description}")
        
        if medium:
            report.append("### 中等优先级问题")
            for i, issue in enumerate(medium, 1):
                report.append(f"{i}. {issue.description}")
        
        if low:
            report.append("### 低优先级问题")
            for i, issue in enumerate(low, 1):
                report.append(f"{i}. {issue.description}")
        
        if not issues:
            report.append("### 审核通过")
            report.append("未发现问题")
        
        return '\n'.join(report)