import sys
import os
from typing import Dict, Any
from .config_manager import ConfigManager
from .logger import Logger
from .exceptions import AppStartupError

class Application:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def initialize(self, config_path: str = None) -> None:
        if self._initialized:
            return
        
        self._config_manager = ConfigManager(config_path)
        self._logger = Logger(self._config_manager.get_log_config())
        self._logger.info("Application initializing...")
        
        try:
            self._config_manager.load_config()
            self._logger.info("Configuration loaded successfully")
            
            self._setup_directories()
            self._logger.info("Directories setup completed")
            
            self._initialized = True
            self._logger.info("Application initialized successfully")
            
        except Exception as e:
            raise AppStartupError(f"Failed to initialize application: {str(e)}")
    
    def _setup_directories(self) -> None:
        dirs = [
            self.config_manager.get('storage.data_path'),
            self.config_manager.get('storage.output_path'),
            self.config_manager.get('storage.log_path'),
            self.config_manager.get('storage.cache_path'),
        ]
        
        for dir_path in dirs:
            if dir_path and not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)
                self._logger.debug(f"Created directory: {dir_path}")
    
    @property
    def config_manager(self) -> ConfigManager:
        return self._config_manager
    
    @property
    def logger(self) -> Logger:
        return self._logger
    
    def shutdown(self) -> None:
        self._logger.info("Application shutting down...")
        self._initialized = False
    
    def run(self, task_config: Dict[str, Any]) -> Any:
        from routing.scheduler import TaskScheduler
        
        if not self._initialized:
            raise AppStartupError("Application not initialized")
        
        self._logger.info(f"Starting task: {task_config.get('task_name', 'Unknown')}")
        
        try:
            scheduler = TaskScheduler()
            result = scheduler.execute(task_config)
            self._logger.info("Task completed successfully")
            return result
        except Exception as e:
            self._logger.error(f"Task execution failed: {str(e)}", exc_info=True)
            raise