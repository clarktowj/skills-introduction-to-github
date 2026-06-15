from enum import Enum
from typing import List, Dict, Any, Callable

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class TaskStep:
    def __init__(self, name: str, func: Callable, dependencies: List[str] = None):
        self.name = name
        self.func = func
        self.dependencies = dependencies or []
        self.status = TaskStatus.PENDING
        self.result = None
        self.error = None

class TaskFlow:
    def __init__(self):
        self._steps: Dict[str, TaskStep] = {}
        self._step_order: List[str] = []
    
    def add_step(self, name: str, func: Callable, dependencies: List[str] = None) -> 'TaskFlow':
        self._steps[name] = TaskStep(name, func, dependencies)
        self._step_order.append(name)
        return self
    
    def execute(self, initial_data: Dict[str, Any] = None) -> Dict[str, Any]:
        data = initial_data or {}
        completed_steps = set()
        
        for step_name in self._step_order:
            step = self._steps[step_name]
            
            if not self._check_dependencies(step, completed_steps):
                step.status = TaskStatus.FAILED
                step.error = f"Missing dependencies: {step.dependencies}"
                continue
            
            try:
                step.status = TaskStatus.RUNNING
                step.result = step.func(data)
                
                if isinstance(step.result, dict):
                    data.update(step.result)
                
                step.status = TaskStatus.COMPLETED
                completed_steps.add(step_name)
                
            except Exception as e:
                step.status = TaskStatus.FAILED
                step.error = str(e)
        
        return data
    
    def _check_dependencies(self, step: TaskStep, completed_steps: set) -> bool:
        for dep in step.dependencies:
            if dep not in completed_steps:
                return False
        return True
    
    def get_status(self) -> Dict[str, str]:
        return {step.name: step.status.value for step in self._steps.values()}
    
    def get_results(self) -> Dict[str, Any]:
        return {step.name: step.result for step in self._steps.values()}
    
    def get_errors(self) -> Dict[str, str]:
        return {step.name: step.error for step in self._steps.values() if step.error}