import os
import json
from typing import Dict, Any, Optional
from framework.exceptions import FileError

class StorageManager:
    def __init__(self, base_path: str = './data'):
        self._base_path = base_path
        self._ensure_directory(base_path)
    
    def _ensure_directory(self, path: str) -> None:
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
    
    def save_data(self, data: Any, filename: str, sub_dir: str = '') -> str:
        full_path = self._get_full_path(filename, sub_dir)
        
        try:
            directory = os.path.dirname(full_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
            
            with open(full_path, 'w', encoding='utf-8') as f:
                if isinstance(data, dict) or isinstance(data, list):
                    json.dump(data, f, ensure_ascii=False, indent=2)
                else:
                    f.write(str(data))
            
            return full_path
        
        except Exception as e:
            raise FileError(f"Failed to save data: {str(e)}")
    
    def load_data(self, filename: str, sub_dir: str = '') -> Any:
        full_path = self._get_full_path(filename, sub_dir)
        
        if not os.path.exists(full_path):
            raise FileError(f"File not found: {full_path}")
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    return content
        
        except Exception as e:
            raise FileError(f"Failed to load data: {str(e)}")
    
    def delete_data(self, filename: str, sub_dir: str = '') -> None:
        full_path = self._get_full_path(filename, sub_dir)
        
        if os.path.exists(full_path):
            try:
                os.remove(full_path)
            except Exception as e:
                raise FileError(f"Failed to delete data: {str(e)}")
    
    def exists(self, filename: str, sub_dir: str = '') -> bool:
        full_path = self._get_full_path(filename, sub_dir)
        return os.path.exists(full_path)
    
    def list_files(self, sub_dir: str = '') -> list:
        full_path = self._get_full_path('', sub_dir)
        
        if not os.path.exists(full_path):
            return []
        
        try:
            return [f for f in os.listdir(full_path) if os.path.isfile(os.path.join(full_path, f))]
        except Exception as e:
            raise FileError(f"Failed to list files: {str(e)}")
    
    def _get_full_path(self, filename: str, sub_dir: str) -> str:
        if sub_dir:
            return os.path.join(self._base_path, sub_dir, filename)
        return os.path.join(self._base_path, filename)