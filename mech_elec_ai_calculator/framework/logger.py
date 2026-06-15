import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Dict, Any

class Logger:
    def __init__(self, log_config: Dict[str, Any]):
        self._log_config = log_config
        self._logger = self._setup_logger()
    
    def _setup_logger(self) -> logging.Logger:
        logger = logging.getLogger('mech_elec_ai')
        logger.setLevel(self._get_log_level())
        logger.propagate = False
        
        formatter = logging.Formatter(self._log_config.get('format'))
        
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        log_path = self._log_config.get('log_path', './logs')
        if not os.path.exists(log_path):
            os.makedirs(log_path, exist_ok=True)
        
        file_handler = RotatingFileHandler(
            os.path.join(log_path, 'app.log'),
            maxBytes=self._log_config.get('file_max_size', 10485760),
            backupCount=self._log_config.get('file_backup_count', 5),
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        return logger
    
    def _get_log_level(self) -> int:
        level = self._log_config.get('level', 'INFO').upper()
        return getattr(logging, level, logging.INFO)
    
    def debug(self, message: str, **kwargs) -> None:
        self._logger.debug(message, **kwargs)
    
    def info(self, message: str, **kwargs) -> None:
        self._logger.info(message, **kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        self._logger.warning(message, **kwargs)
    
    def error(self, message: str, **kwargs) -> None:
        self._logger.error(message, **kwargs)
    
    def critical(self, message: str, **kwargs) -> None:
        self._logger.critical(message, **kwargs)
    
    def get_logger(self) -> logging.Logger:
        return self._logger