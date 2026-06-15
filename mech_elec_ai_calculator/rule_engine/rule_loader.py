import os
import json
import yaml
from typing import Dict, Any, Optional
from framework.exceptions import RuleEngineError
from framework.file_utils import FileUtils

class RuleLoader:
    def __init__(self, rules_path: str = './rules'):
        self._rules_path = rules_path
        self._rules: Dict[str, Any] = {}
    
    def load_rules(self, version: str = 'latest') -> Dict[str, Any]:
        rules_file = self._find_rules_file(version)
        
        if not rules_file:
            raise RuleEngineError(f"Rules file not found for version: {version}")
        
        return self._load_rules_file(rules_file)
    
    def _find_rules_file(self, version: str) -> Optional[str]:
        if version == 'latest':
            files = sorted(
                [f for f in os.listdir(self._rules_path) if f.endswith('.json') or f.endswith('.yaml')],
                reverse=True
            )
            return os.path.join(self._rules_path, files[0]) if files else None
        
        filename = f"rules_{version}.json"
        filepath = os.path.join(self._rules_path, filename)
        
        if os.path.exists(filepath):
            return filepath
        
        filename_yaml = f"rules_{version}.yaml"
        filepath_yaml = os.path.join(self._rules_path, filename_yaml)
        
        if os.path.exists(filepath_yaml):
            return filepath_yaml
        
        return None
    
    def _load_rules_file(self, filepath: str) -> Dict[str, Any]:
        ext = os.path.splitext(filepath)[1].lower()
        
        try:
            if ext == '.json':
                return self._load_json(filepath)
            elif ext in ('.yaml', '.yml'):
                return self._load_yaml(filepath)
            else:
                raise RuleEngineError(f"Unsupported rules file format: {ext}")
        except Exception as e:
            raise RuleEngineError(f"Failed to load rules file {filepath}: {str(e)}")
    
    def _load_json(self, filepath: str) -> Dict[str, Any]:
        content = FileUtils.read_file(filepath)
        return json.loads(content)
    
    def _load_yaml(self, filepath: str) -> Dict[str, Any]:
        content = FileUtils.read_file(filepath)
        return yaml.safe_load(content)
    
    def load_specification(self, spec_name: str) -> str:
        spec_path = os.path.join(
            os.path.dirname(self._rules_path), 'docs', 'specs', f"{spec_name}.md"
        )
        
        if not os.path.exists(spec_path):
            raise RuleEngineError(f"Specification file not found: {spec_name}")
        
        return FileUtils.read_file(spec_path)
    
    def list_available_rules(self) -> list:
        files = []
        for f in os.listdir(self._rules_path):
            if f.endswith('.json') or f.endswith('.yaml'):
                version = f.replace('rules_', '').replace('.json', '').replace('.yaml', '').replace('.yml', '')
                files.append({
                    'filename': f,
                    'version': version if version else 'latest'
                })
        return sorted(files, key=lambda x: x['version'], reverse=True)