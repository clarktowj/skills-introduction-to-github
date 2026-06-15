import yaml
import os
from typing import Any, Dict, Optional
from .exceptions import ConfigError

class ConfigManager:
    def __init__(self, config_path: Optional[str] = None):
        self._config_path = config_path or os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 'config', 'config.yaml'
        )
        self._config: Dict[str, Any] = {}
        self._default_config = self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        return {
            'app': {
                'name': '机电AI自动算量系统',
                'version': '1.0.0',
                'debug': False,
            },
            'storage': {
                'data_path': './data',
                'output_path': './outputs',
                'log_path': './logs',
                'cache_path': './cache',
            },
            'logging': {
                'level': 'INFO',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'file_max_size': 10485760,
                'file_backup_count': 5,
            },
            'rule_engine': {
                'rules_path': './rules',
                'specs_path': './docs/specs',
            },
            'openhuman': {
                'api_url': 'https://api.openhuman.ai/v1',
                'api_key': '',
                'timeout': 60,
            },
            'drawing_parser': {
                'dxf_max_size': 52428800,
                'pdf_max_size': 104857600,
                'image_max_size': 52428800,
            },
            'bim_modeling': {
                'output_format': 'ifc',
                'unit': 'meter',
            },
        }
    
    def load_config(self) -> None:
        self._config = self._default_config.copy()
        
        if os.path.exists(self._config_path):
            try:
                with open(self._config_path, 'r', encoding='utf-8') as f:
                    user_config = yaml.safe_load(f)
                    if user_config:
                        self._merge_config(self._config, user_config)
            except yaml.YAMLError as e:
                raise ConfigError(f"Failed to parse config file: {str(e)}")
            except Exception as e:
                raise ConfigError(f"Failed to load config file: {str(e)}")
    
    def _merge_config(self, base: Dict[str, Any], override: Dict[str, Any]) -> None:
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split('.')
        config = self._config
        
        try:
            for k in keys:
                config = config[k]
            return config
        except KeyError:
            return default
    
    def set(self, key: str, value: Any) -> None:
        keys = key.split('.')
        config = self._config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def save_config(self, path: Optional[str] = None) -> None:
        save_path = path or self._config_path
        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                yaml.dump(self._config, f, default_flow_style=False, allow_unicode=True)
        except Exception as e:
            raise ConfigError(f"Failed to save config file: {str(e)}")