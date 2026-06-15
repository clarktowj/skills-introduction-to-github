import os
import hashlib
from typing import Optional
from .exceptions import FileError

class FileUtils:
    @staticmethod
    def read_file(path: str, mode: str = 'r') -> str:
        try:
            with open(path, mode, encoding='utf-8' if mode == 'r' else None) as f:
                return f.read()
        except Exception as e:
            raise FileError(f"Failed to read file {path}: {str(e)}")
    
    @staticmethod
    def write_file(path: str, content: str, mode: str = 'w') -> None:
        try:
            directory = os.path.dirname(path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
            
            with open(path, mode, encoding='utf-8' if mode in ('w', 'a') else None) as f:
                f.write(content)
        except Exception as e:
            raise FileError(f"Failed to write file {path}: {str(e)}")
    
    @staticmethod
    def file_exists(path: str) -> bool:
        return os.path.exists(path)
    
    @staticmethod
    def get_file_size(path: str) -> int:
        try:
            return os.path.getsize(path)
        except Exception as e:
            raise FileError(f"Failed to get file size {path}: {str(e)}")
    
    @staticmethod
    def get_file_hash(path: str) -> str:
        try:
            sha256_hash = hashlib.sha256()
            with open(path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except Exception as e:
            raise FileError(f"Failed to compute file hash {path}: {str(e)}")
    
    @staticmethod
    def get_file_extension(path: str) -> str:
        return os.path.splitext(path)[1].lower()
    
    @staticmethod
    def generate_unique_filename(original_name: str) -> str:
        name, ext = os.path.splitext(original_name)
        timestamp = str(int(os.time()))
        return f"{name}_{timestamp}{ext}"
    
    @staticmethod
    def copy_file(src: str, dst: str) -> None:
        try:
            import shutil
            shutil.copy2(src, dst)
        except Exception as e:
            raise FileError(f"Failed to copy file {src} to {dst}: {str(e)}")
    
    @staticmethod
    def delete_file(path: str) -> None:
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception as e:
            raise FileError(f"Failed to delete file {path}: {str(e)}")