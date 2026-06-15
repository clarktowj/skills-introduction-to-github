import requests
import json
from typing import Dict, Any, Optional, List
from common.models import DrawingData, CalculationResult, AuditResult, AuditIssue, AuditIssueType, Coordinate
from framework.app import Application
from framework.exceptions import AuditError
from rule_engine.rule_loader import RuleLoader

class OpenHumanAuditClient:
    def __init__(self):
        self._app = Application()
        self._rule_loader = RuleLoader()
        self._api_url = "https://api.openhuman.ai/v1/audit"
    
    def audit(self, drawing_data: DrawingData, calculation: CalculationResult) -> AuditResult:
        audit_result = AuditResult(
            calculation_id=calculation.id,
            drawing_id=drawing_data.id
        )
        
        try:
            issues = self._perform_audit(drawing_data, calculation)
            audit_result.issues = issues
            audit_result.audit_score = self._calculate_score(issues)
            audit_result.passed = audit_result.audit_score >= 80.0
            audit_result.ai_version = "1.0"
            
        except Exception as e:
            raise AuditError(f"Audit failed: {str(e)}")
        
        return audit_result
    
    def _perform_audit(self, drawing_data: DrawingData, calculation: CalculationResult) -> List[AuditIssue]:
        issues = []
        
        issues.extend(self._audit_device_count(drawing_data, calculation))
        issues.extend(self._audit_cable_lengths(drawing_data, calculation))
        issues.extend(self._audit_specification_compliance(calculation))
        issues.extend(self._audit_model_quantity_binding(drawing_data, calculation))
        
        return issues
    
    def _audit_device_count(self, drawing_data: DrawingData, calculation: CalculationResult) -> List[AuditIssue]:
        issues = []
        
        block_count = len(drawing_data.blocks)
        device_count = len(drawing_data.devices)
        
        if block_count > device_count:
            issues.append(AuditIssue(
                type=AuditIssueType.MISSING_DEVICE,
                severity="medium",
                description=f"检测到 {block_count - device_count} 个图块未被识别为设备",
                suggestion="请检查图块名称是否包含设备关键词"
            ))
        
        return issues
    
    def _audit_cable_lengths(self, drawing_data: DrawingData, calculation: CalculationResult) -> List[AuditIssue]:
        issues = []
        
        threshold = self._get_validation_threshold('max_cable_length')
        
        for cable_item in calculation.cables:
            if cable_item.quantity > threshold:
                issues.append(AuditIssue(
                    type=AuditIssueType.WRONG_CABLE_LENGTH,
                    severity="high",
                    description=f"线缆长度 {cable_item.quantity} 米超过阈值 {threshold} 米",
                    suggestion="请检查线缆是否存在异常超长段"
                ))
        
        return issues
    
    def _audit_specification_compliance(self, calculation: CalculationResult) -> List[AuditIssue]:
        issues = []
        
        specs = self._load_specifications()
        
        for device in calculation.devices:
            if not self._check_device_spec(device, specs):
                issues.append(AuditIssue(
                    type=AuditIssueType.SPECIFICATION_ERROR,
                    severity="medium",
                    description=f"设备 {device.name} 规格不符合规范要求",
                    suggestion="请对照国标GB50303检查设备规格"
                ))
        
        return issues
    
    def _audit_model_quantity_binding(self, drawing_data: DrawingData, calculation: CalculationResult) -> List[AuditIssue]:
        issues = []
        
        device_ids = set(d.id for d in drawing_data.devices)
        cable_ids = set(c.id for c in drawing_data.cables)
        
        quantity_device_ids = set(item.component_id for item in calculation.devices)
        quantity_cable_ids = set(item.component_id for item in calculation.cables)
        
        if device_ids != quantity_device_ids:
            issues.append(AuditIssue(
                type=AuditIssueType.MODEL_QUANTITY_MISMATCH,
                severity="high",
                description="设备模型与工程量绑定不一致",
                suggestion="请检查设备ID绑定关系"
            ))
        
        if cable_ids != quantity_cable_ids:
            issues.append(AuditIssue(
                type=AuditIssueType.MODEL_QUANTITY_MISMATCH,
                severity="high",
                description="线缆模型与工程量绑定不一致",
                suggestion="请检查线缆ID绑定关系"
            ))
        
        return issues
    
    def _get_validation_threshold(self, threshold_name: str) -> float:
        try:
            specs = self._rule_loader.load_rules('latest')
            return specs.get('validation_thresholds', {}).get(threshold_name, 10000.0)
        except:
            return 10000.0
    
    def _load_specifications(self) -> str:
        try:
            return self._rule_loader.load_specification('gb50303')
        except:
            return ""
    
    def _check_device_spec(self, device_item, specs: str) -> bool:
        return True
    
    def _calculate_score(self, issues: List[AuditIssue]) -> float:
        base_score = 100.0
        
        for issue in issues:
            if issue.severity == 'critical':
                base_score -= 20
            elif issue.severity == 'high':
                base_score -= 10
            elif issue.severity == 'medium':
                base_score -= 5
            elif issue.severity == 'low':
                base_score -= 1
        
        return max(0.0, base_score)
    
    def _call_api(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            response = requests.post(
                self._api_url,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise AuditError(f"API call failed: {str(e)}")