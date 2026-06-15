from typing import Dict, Any, List
from framework.exceptions import RuleEngineError

class RuleValidator:
    REQUIRED_SECTIONS = [
        'reserve_lengths',
        'correction_factors',
        'device_classification',
        'validation_thresholds',
        'quantity_rules'
    ]
    
    def validate(self, rules: Dict[str, Any]) -> bool:
        self._check_required_sections(rules)
        self._validate_reserve_lengths(rules.get('reserve_lengths', {}))
        self._validate_correction_factors(rules.get('correction_factors', {}))
        self._validate_device_classification(rules.get('device_classification', {}))
        # block_matching 为可选部分
        if 'block_matching' in rules:
            self._validate_block_matching(rules.get('block_matching', {}))
        self._validate_validation_thresholds(rules.get('validation_thresholds', {}))
        self._validate_quantity_rules(rules.get('quantity_rules', {}))
        return True
    
    def _check_required_sections(self, rules: Dict[str, Any]) -> None:
        missing = [s for s in self.REQUIRED_SECTIONS if s not in rules]
        if missing:
            raise RuleEngineError(f"Missing required sections in rules: {', '.join(missing)}")
    
    def _validate_reserve_lengths(self, reserve_lengths: Dict[str, Any]) -> None:
        required_fields = ['cabinet', 'outdoor', 'vertical', 'elbow']
        for field in required_fields:
            if field not in reserve_lengths:
                raise RuleEngineError(f"Missing reserve length field: {field}")
            if not isinstance(reserve_lengths[field], (int, float)) or reserve_lengths[field] < 0:
                raise RuleEngineError(f"Invalid value for reserve length '{field}'")
    
    def _validate_correction_factors(self, correction_factors: Dict[str, Any]) -> None:
        for key, value in correction_factors.items():
            if not isinstance(value, (int, float)) or value < 0:
                raise RuleEngineError(f"Invalid correction factor '{key}': {value}")
    
    def _validate_device_classification(self, classification: Dict[str, Any]) -> None:
        if not isinstance(classification, dict):
            raise RuleEngineError("Device classification must be a dictionary")
        
        # 动态检查：device_type字段存在即可，不限制具体类型名称
        for device_type, config in classification.items():
            if 'keywords' not in config or not isinstance(config['keywords'], list):
                raise RuleEngineError(f"Missing or invalid keywords for device type '{device_type}'")
    
    def _validate_block_matching(self, block_matching: Dict[str, Any]) -> None:
        if not isinstance(block_matching, dict):
            raise RuleEngineError("Block matching must be a dictionary")
        
        for block_name, config in block_matching.items():
            if 'device_type' not in config:
                raise RuleEngineError(f"Missing device_type for block '{block_name}'")
            if 'match_type' not in config:
                raise RuleEngineError(f"Missing match_type for block '{block_name}'")
            if config['match_type'] not in ['exact', 'contains', 'regex']:
                raise RuleEngineError(f"Invalid match_type '{config['match_type']}' for block '{block_name}'")
    
    def _validate_validation_thresholds(self, thresholds: Dict[str, Any]) -> None:
        if not isinstance(thresholds, dict):
            raise RuleEngineError("Validation thresholds must be a dictionary")
        
        for key, value in thresholds.items():
            if not isinstance(value, (int, float)):
                raise RuleEngineError(f"Invalid threshold value for '{key}'")
    
    def _validate_quantity_rules(self, quantity_rules: Dict[str, Any]) -> None:
        if not isinstance(quantity_rules, dict):
            raise RuleEngineError("Quantity rules must be a dictionary")
        
        for rule_name, rule in quantity_rules.items():
            if 'unit' not in rule:
                raise RuleEngineError(f"Missing unit for quantity rule '{rule_name}'")
            if 'calculation_method' not in rule:
                raise RuleEngineError(f"Missing calculation_method for quantity rule '{rule_name}'")