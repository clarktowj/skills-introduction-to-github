import asyncio
from typing import Callable, Any, Dict, List
from concurrent.futures import ThreadPoolExecutor

class TaskQueue:
    def __init__(self, max_workers: int = 4):
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._tasks: List[Dict[str, Any]] = []
    
    def submit(self, task: Callable, *args, **kwargs) -> Any:
        future = self._executor.submit(task, *args, **kwargs)
        return future
    
    def submit_async(self, task: Callable, *args, **kwargs) -> asyncio.Future:
        loop = asyncio.get_event_loop()
        return loop.run_in_executor(self._executor, task, *args, **kwargs)
    
    def map(self, func: Callable, iterable: List[Any]) -> List[Any]:
        return list(self._executor.map(func, iterable))
    
    def shutdown(self, wait: bool = True) -> None:
        self._executor.shutdown(wait=wait)
    
    def add_task(self, name: str, func: Callable, *args, **kwargs) -> None:
        self._tasks.append({
            'name': name,
            'func': func,
            'args': args,
            'kwargs': kwargs
        })
    
    def execute_all(self) -> List[Any]:
        results = []
        for task in self._tasks:
            result = task['func'](*task['args'], **task['kwargs'])
            results.append(result)
        return results