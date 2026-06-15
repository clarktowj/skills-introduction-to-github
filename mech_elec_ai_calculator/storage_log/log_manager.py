import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Dict, Any

class LogManager:
    def __init__(self, log_path: str = './logs'):
        self._log_path = log_path
        self._ensure_directory(log_path)
        self._loggers = {}
    
    def _ensure_directory(self, path: str) -> None:
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
    
    def get_logger(self, name: str, level: str = 'INFO') -> logging.Logger:
        if name in self._loggers:
            return self._loggers[name]
        
        logger = logging.getLogger(name)
        logger.setLevel(self._get_log_level(level))
        logger.propagate = False
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        file_handler = RotatingFileHandler(
            os.path.join(self._log_path, f'{name}.log'),
            maxBytes=10485760,
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        self._loggers[name] = logger
        
        return logger
    
    def _get_log_level(self, level: str) -> int:
        level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        return level_map.get(level.upper(), logging.INFO)
    
    def log_to_file(self, message: str, level: str = 'INFO', filename: str = 'app') -> None:
        logger = self.get_logger(filename)
        log_method = getattr(logger, level.lower(), logger.info)
        log_method(message)
    
    def debug(self, message: str, logger_name: str = 'app') -> None:
        self.get_logger(logger_name).debug(message)
    
    def info(self, message: str, logger_name: str = 'app') -> None:
        self.get_logger(logger_name).info(message)
    
    def warning(self, message: str, logger_name: str = 'app') -> None:
        self.get_logger(logger_name).warning(message)
    
    def error(self, message: str, logger_name: str = 'app') -> None:
        self.get_logger(logger_name).error(message)
    
    def critical(self, message: str, logger_name: str = 'app') -> None:
        self.get_logger(logger_name).critical(message)