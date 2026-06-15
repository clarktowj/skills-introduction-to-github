from typing import Dict, Any, Optional, List
from .rule_loader import RuleLoader
from .rule_validator import RuleValidator
from framework.exceptions import RuleEngineError

class RuleManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._rules = {}
            cls._instance._rule_loader = RuleLoader()
            cls._instance._rule_validator = RuleValidator()
        return cls._instance
    
    def load_rules(self, version: str = 'latest') -> None:
        self._rules = self._rule_loader.load_rules(version)
        self._rule_validator.validate(self._rules)
    
    def get_rule(self, key: str, default: Any = None) -> Any:
        keys = key.split('.')
        value = self._rules
        
        try:
            for k in keys:
                value = value[k]
            return value
        except KeyError:
            return default
    
    def get_reserve_length(self, reserve_type: str) -> float:
        return self.get_rule(f'reserve_lengths.{reserve_type}', 0.0)
    
    def get_correction_factor(self, factor_name: str) -> float:
        return self.get_rule(f'correction_factors.{factor_name}', 1.0)
    
    def classify_device(self, block_name: str) -> Optional[str]:
        device_classification = self.get_rule('device_classification', {})
        
        # 按优先级排序 (priority 数字越小优先级越高)
        sorted_configs = sorted(
            device_classification.items(),
            key=lambda x: x[1].get('priority', 99)
        )
        
        # 按优先级依次匹配
        for device_type, config in sorted_configs:
            keywords = config.get('keywords', [])
            for keyword in keywords:
                if keyword.lower() in block_name.lower():
                    return device_type
        
        return self.get_rule('device_classification.other.device_type', 'other')
    
    def match_block(self, block_name: str) -> Optional[Dict[str, Any]]:
        block_matching = self.get_rule('block_matching', {})
        
        for pattern, config in block_matching.items():
            match_type = config.get('match_type', 'contains')
            
            if match_type == 'exact' and block_name == pattern:
                return config
            elif match_type == 'contains' and pattern.lower() in block_name.lower():
                return config
        
        return None
    
    def get_quantity_rule(self, rule_name: str) -> Optional[Dict[str, Any]]:
        return self.get_rule(f'quantity_rules.{rule_name}')
    
    def get_validation_threshold(self, threshold_name: str) -> float:
        return self.get_rule(f'validation_thresholds.{threshold_name}', 0.0)
    
    def list_rules(self) -> List[str]:
        def _flatten_rules(prefix: str, rules: Dict[str, Any]) -> List[str]:
            result = []
            for key, value in rules.items():
                new_prefix = f"{prefix}.{key}" if prefix else key
                if isinstance(value, dict):
                    result.extend(_flatten_rules(new_prefix, value))
                else:
                    result.append(new_prefix)
            return result
        
        return _flatten_rules('', self._rules)