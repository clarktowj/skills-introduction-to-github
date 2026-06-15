import os
import json
import pickle
from typing import Any, Optional
from .exceptions import FileError

class CacheManager:
    def __init__(self, cache_path: str = './cache'):
        self._cache_path = cache_path
        self._ensure_cache_dir()
    
    def _ensure_cache_dir(self) -> None:
        if not os.path.exists(self._cache_path):
            os.makedirs(self._cache_path, exist_ok=True)
    
    def get(self, key: str) -> Optional[Any]:
        cache_file = os.path.join(self._cache_path, f"{key}.cache")
        
        if not os.path.exists(cache_file):
            return None
        
        try:
            with open(cache_file, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            raise FileError(f"Failed to read cache {key}: {str(e)}")
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        cache_file = os.path.join(self._cache_path, f"{key}.cache")
        
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump({
                    'value': value,
                    'ttl': ttl,
                    'timestamp': int(os.time())
                }, f)
        except Exception as e:
            raise FileError(f"Failed to write cache {key}: {str(e)}")
    
    def delete(self, key: str) -> None:
        cache_file = os.path.join(self._cache_path, f"{key}.cache")
        
        if os.path.exists(cache_file):
            try:
                os.remove(cache_file)
            except Exception as e:
                raise FileError(f"Failed to delete cache {key}: {str(e)}")
    
    def clear_all(self) -> None:
        try:
            for filename in os.listdir(self._cache_path):
                if filename.endswith('.cache'):
                    os.remove(os.path.join(self._cache_path, filename))
        except Exception as e:
            raise FileError(f"Failed to clear cache: {str(e)}")
    
    def exists(self, key: str) -> bool:
        cache_file = os.path.join(self._cache_path, f"{key}.cache")
        return os.path.exists(cache_file)