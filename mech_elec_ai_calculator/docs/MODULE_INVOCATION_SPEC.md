# 模块调用逻辑规范

## 目录

1. [模块依赖关系](#1-模块依赖关系)
2. [调用时序规范](#2-调用时序规范)
3. [数据传递规范](#3-数据传递规范)
4. [错误处理规范](#4-错误处理规范)
5. [状态管理规范](#5-状态管理规范)

---

## 1. 模块依赖关系

### 1.1 禁止反向依赖

```python
# ✅ 正确：高层模块引用低层模块
from common.models import DrawingData        # Common 被 Business 引用
from rule_engine.rule_manager import RuleManager  # Business 引用 Rule Engine

# ❌ 错误：低层模块引用高层模块
# rule_engine 不应该引用 routing
# common 不应该引用 business
```

### 1.2 禁止跨层依赖

```python
# ✅ 正确：逐层调用
routing.scheduler → drawing_parser → common
routing.scheduler → electrical_calculator → rule_engine

# ❌ 错误：跨层调用
routing.scheduler → common → rule_engine  # 跳过了 business 层
```

### 1.3 共享模块使用规范

```python
# storage_log 和 framework 可以被所有模块使用
# 但必须通过接口访问

# ✅ 正确：通过框架获取日志
from framework.app import Application
app = Application()
logger = app.logger
logger.info("操作日志")

# ❌ 错误：直接实例化
from storage_log.log_manager import LogManager
logger = LogManager()  # 禁止直接实例化
```

---

## 2. 调用时序规范

### 2.1 标准调用流程

```python
# 标准调用流程示例

def standard_workflow(input_file: str):
    """
    标准工作流程
    
    执行顺序：
    1. 初始化应用
    2. 解析图纸
    3. 执行算量
    4. 生成模型
    5. 汇总清单
    """
    
    # Step 1: 初始化（只执行一次）
    app = Application()
    app.initialize()
    
    # Step 2: 解析图纸（可选重试）
    max_retries = 3
    for attempt in range(max_retries):
        try:
            processor = DrawingProcessor()
            drawing_data = processor.process(input_file)
            break
        except ParseError as e:
            if attempt == max_retries - 1:
                raise
            logger.warning(f"解析失败，重试 {attempt + 1}/{max_retries}")
    
    # Step 3: 执行算量
    calculator = ElectricalCalculator()
    calculation_result = calculator.calculate(drawing_data)
    
    # Step 4: 生成模型（如启用）
    if config.enable_modeling:
        generator = BIMGenerator()
        components = generator.generate_from_drawing(
            drawing_data.devices,
            drawing_data.cables
        )
    
    # Step 5: 汇总清单
    summary_gen = SummaryGenerator()
    summary = summary_gen.generate(calculation_result)
    
    return summary
```

### 2.2 条件调用规则

```python
# 条件调用示例

def conditional_workflow(task_config: TaskConfig):
    
    # 1. 图纸解析 - 始终执行
    processor = DrawingProcessor()
    drawing_data = processor.process(task_config.input_files[0])
    
    # 2. 电气算量 - 始终执行
    calculator = ElectricalCalculator()
    calculation_result = calculator.calculate(drawing_data)
    
    # 3. BIM建模 - 根据配置决定
    components = []
    if task_config.enable_modeling:
        generator = BIMGenerator()
        components = generator.generate_from_drawing(
            drawing_data.devices,
            drawing_data.cables
        )
    
    # 4. AI审核 - 根据配置决定
    audit_result = None
    if task_config.enable_audit:
        audit_client = OpenHumanAuditClient()
        audit_result = audit_client.audit(drawing_data, calculation_result)
    
    # 5. 清单汇总 - 始终执行
    summary_gen = SummaryGenerator()
    summary = summary_gen.generate(
        calculation_result,
        audit_result
    )
    
    return summary, components
```

### 2.3 并行调用规则

```python
# 并行调用示例

from concurrent.futures import ThreadPoolExecutor, as_completed

def parallel_workflow(input_files: list):
    """
    并行处理多个图纸
    
    注意：只允许在独立任务级别并行
    同一任务内的模块调用必须串行
    """
    
    results = []
    
    # 使用线程池并行处理不同文件
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(process_single_file, f): f 
            for f in input_files
        }
        
        for future in as_completed(futures):
            file_path = futures[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                logger.error(f"处理 {file_path} 失败: {str(e)}")
    
    return results

def process_single_file(file_path: str):
    """
    处理单个文件（内部必须串行）
    """
    # ❌ 禁止在单个文件内并行调用模块
    # processor.parse() 和 calculator.calculate() 不能并行
    
    # ✅ 正确：串行执行
    processor = DrawingProcessor()
    drawing_data = processor.process(file_path)
    
    calculator = ElectricalCalculator()
    calculation_result = calculator.calculate(drawing_data)
    
    return calculation_result
```

---

## 3. 数据传递规范

### 3.1 标准数据模型

```python
# 数据传递必须使用 Pydantic 模型

from pydantic import BaseModel
from typing import List, Optional

class DrawingData(BaseModel):
    """图纸数据 - 模块间传递的标准格式"""
    id: str
    filename: str
    file_type: str
    devices: List[DeviceModel] = []
    cables: List[CableModel] = []
    layers: List[LayerInfo] = []

class CalculationResult(BaseModel):
    """算量结果 - 模块间传递的标准格式"""
    id: str
    drawing_id: str
    devices: List[QuantityItem] = []
    cables: List[QuantityItem] = []
    total_cost: float = 0.0
```

### 3.2 禁止使用字典传递

```python
# ❌ 错误：使用字典传递数据
def calculate(data: dict):
    devices = data['devices']
    cables = data['cables']

# ✅ 正确：使用 Pydantic 模型
def calculate(data: DrawingData):
    devices = data.devices
    cables = data.cables
```

### 3.3 数据验证规范

```python
# 在模块边界进行数据验证

class DrawingProcessor:
    def process(self, file_path: str) -> DrawingData:
        # 验证输入
        if not file_path:
            raise ValueError("文件路径不能为空")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        # 处理数据
        result = self._do_process(file_path)
        
        # 验证输出
        if not isinstance(result, DrawingData):
            raise ValueError("返回类型错误")
        
        return result
```

---

## 4. 错误处理规范

### 4.1 异常分类

```python
# 异常分类体系

class MechElecAIException(Exception):
    """基础异常类"""
    code = 500
    message = "未知错误"

# 业务异常（可恢复）
class ParseError(MechElecAIException):
    """解析异常"""
    code = 1001
    message = "图纸解析失败"

class CalculationError(MechElecAIException):
    """算量异常"""
    code = 1002
    message = "工程量计算失败"

# 系统异常（不可恢复）
class ConfigurationError(MechElecAIException):
    """配置异常"""
    code = 2001
    message = "系统配置错误"

class DependencyError(MechElecAIException):
    """依赖异常"""
    code = 2002
    message = "依赖缺失"
```

### 4.2 异常处理策略

```python
# 异常处理策略

"""
1. 业务异常：记录日志，继续处理或重试
2. 系统异常：记录日志，终止流程
3. 输入异常：返回错误信息，不抛异常
"""

def handle_exception(e: Exception, context: str) -> None:
    if isinstance(e, ParseError):
        # 业务异常：记录并继续
        logger.warning(f"{context}: {str(e)}")
        
    elif isinstance(e, CalculationError):
        # 业务异常：记录并继续
        logger.warning(f"{context}: {str(e)}")
        
    elif isinstance(e, MechElecAIException):
        # 系统异常：记录并终止
        logger.error(f"{context}: {str(e)}")
        raise
        
    else:
        # 未知异常：记录并包装
        logger.error(f"{context}: {str(e)}")
        raise MechElecAIException(f"未知错误: {str(e)}")
```

### 4.3 重试机制

```python
# 重试机制示例

from functools import wraps
import time

def retry(max_attempts: int = 3, delay: float = 1.0):
    """重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except (ParseError, CalculationError) as e:
                    if attempt == max_attempts - 1:
                        raise
                    logger.warning(f"重试 {attempt + 1}/{max_attempts}: {str(e)}")
                    time.sleep(delay)
            return None
        return wrapper
    return decorator

@retry(max_attempts=3, delay=2.0)
def parse_with_retry(file_path: str) -> DrawingData:
    processor = DrawingProcessor()
    return processor.process(file_path)
```

---

## 5. 状态管理规范

### 5.1 任务状态定义

```python
# 任务状态枚举

from enum import Enum

class TaskStatus(str, Enum):
    PENDING = "pending"          # 等待执行
    RUNNING = "running"          # 执行中
    COMPLETED = "completed"       # 已完成
    FAILED = "failed"            # 执行失败
    CANCELLED = "cancelled"      # 已取消
    PAUSED = "paused"            # 已暂停

class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
```

### 5.2 状态转换规则

```python
# 状态转换规则

"""
有效转换：
- pending → running → completed
- pending → running → failed
- pending → cancelled
- running → paused
- paused → running
- paused → cancelled

无效转换：
- completed → any
- failed → any (除非重启任务)
- cancelled → any (除非新建任务)
"""

class TaskStateMachine:
    def __init__(self):
        self._state = TaskStatus.PENDING
    
    def can_transition(self, new_state: TaskStatus) -> bool:
        valid_transitions = {
            TaskStatus.PENDING: [TaskStatus.RUNNING, TaskStatus.CANCELLED],
            TaskStatus.RUNNING: [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.PAUSED],
            TaskStatus.PAUSED: [TaskStatus.RUNNING, TaskStatus.CANCELLED],
            TaskStatus.COMPLETED: [],
            TaskStatus.FAILED: [TaskStatus.PENDING],  # 允许重启
            TaskStatus.CANCELLED: [TaskStatus.PENDING]  # 允许新建
        }
        
        return new_state in valid_transitions.get(self._state, [])
    
    def transition(self, new_state: TaskStatus) -> None:
        if not self.can_transition(new_state):
            raise ValueError(f"无效的状态转换: {self._state} → {new_state}")
        
        self._state = new_state
```

### 5.3 进度跟踪

```python
# 进度跟踪示例

class ProgressTracker:
    def __init__(self, total_steps: int):
        self.total_steps = total_steps
        self.completed_steps = 0
        self.current_step = ""
        self.step_results = {}
    
    def start_step(self, step_name: str) -> None:
        self.current_step = step_name
        logger.info(f"开始步骤: {step_name}")
    
    def complete_step(self, step_name: str, result: Any = None) -> None:
        self.completed_steps += 1
        self.step_results[step_name] = result
        progress = self.get_progress()
        logger.info(f"完成步骤: {step_name} ({progress:.0%})")
    
    def fail_step(self, step_name: str, error: Exception) -> None:
        self.step_results[step_name] = {"error": str(error)}
        logger.error(f"步骤失败: {step_name} - {str(error)}")
    
    def get_progress(self) -> float:
        return self.completed_steps / self.total_steps if self.total_steps > 0 else 0
    
    def get_status_summary(self) -> dict:
        return {
            "progress": self.get_progress(),
            "current_step": self.current_step,
            "completed": self.completed_steps,
            "total": self.total_steps,
            "results": self.step_results
        }
```

---

## 附录

### A. 快速参考

```python
# 调用顺序参考

1. Application.initialize()        # 应用初始化
2. RuleManager.load_rules()        # 加载规则
3. DrawingProcessor.process()      # 解析图纸
4. ElectricalCalculator.calculate() # 执行算量
5. BIMGenerator.generate()         # 生成模型
6. OpenHumanAuditClient.audit()    # AI审核
7. SummaryGenerator.generate()      # 生成清单
8. ExcelExporter.export()           # 导出Excel
```

### B. 注意事项

```python
# 注意事项

1. 单例模式：RuleManager、Application 使用单例
2. 配置加载：配置变更后需要重新加载
3. 缓存清理：规则更新后需要清理缓存
4. 异常恢复：任务失败后支持从断点恢复
5. 并发控制：多任务时需要加锁保护共享资源
```
