# 运行流程说明

## 目录

1. [流程概述](#1-流程概述)
2. [启动流程](#2-启动流程)
3. [执行流程](#3-执行流程)
4. [结束流程](#4-结束流程)
5. [状态机](#5-状态机)
6. [异常处理流程](#6-异常处理流程)

---

## 1. 流程概述

### 1.1 整体流程图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              用户发起请求                                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           1. 任务接收与验证                                  │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐                  │
│  │ 验证参数 │───▶│ 检查权限 │───▶│ 分配资源 │───▶│ 创建任务 │                  │
│  └─────────┘    └─────────┘    └─────────┘    └─────────┘                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           2. 图纸解析阶段                                    │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐                  │
│  │ 加载文件 │───▶│ 识别类型 │───▶│ 执行解析 │───▶│ 验证结果 │                  │
│  └─────────┘    └─────────┘    └─────────┘    └─────────┘                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           3. 电气算量阶段                                    │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐                  │
│  │ 加载规则 │───▶│ 计算设备 │───▶│ 计算线缆 │───▶│ 计算总价 │                  │
│  └─────────┘    └─────────┘    └─────────┘    └─────────┘                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
                    ▼                 ▼                 ▼
┌───────────────────┐ ┌───────────────┐ ┌───────────────┐
│  3.1 BIM建模     │ │ 3.2 AI审核    │ │ 3.3 清单汇总  │
│  (可选)          │ │ (可选)        │ │               │
└───────────────────┘ └───────────────┘ └───────────────┘
         │                  │                  │
         └──────────────────┼──────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           4. 结果输出阶段                                    │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐                  │
│  │ 生成清单 │───▶│ 导出文件 │───▶│ 保存结果 │───▶│ 通知用户 │                  │
│  └─────────┘    └─────────┘    └─────────┘    └─────────┘                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              任务完成                                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 流程阶段说明

| 阶段 | 说明 | 必选 | 预计耗时 |
|------|------|------|----------|
| 任务接收 | 接收用户请求，验证参数 | 是 | <1秒 |
| 图纸解析 | 解析DXF/PDF/图片图纸 | 是 | 1-30秒 |
| 电气算量 | 执行工程量计算 | 是 | 1-10秒 |
| BIM建模 | 生成三维BIM模型 | 否 | 5-60秒 |
| AI审核 | AI智能审核查漏 | 否 | 10-120秒 |
| 清单汇总 | 生成工程量清单 | 是 | 1-5秒 |
| 结果输出 | 导出Excel/IFC文件 | 是 | 1-30秒 |

---

## 2. 启动流程

### 2.1 应用启动

```python
# 启动流程伪代码

def startup():
    """
    应用启动流程
    """
    # 1. 加载配置文件
    config = ConfigManager().load_config()
    
    # 2. 初始化日志系统
    logger = Logger(config.logging)
    logger.info("应用启动中...")
    
    # 3. 验证必要目录
    verify_directories(config.storage)
    
    # 4. 初始化依赖服务
    init_services(config)
    
    # 5. 注册信号处理器
    register_signal_handlers()
    
    # 6. 启动HTTP服务（可选）
    if config.server.enabled:
        start_http_server(config.server)
    
    logger.info("应用启动完成")
```

### 2.2 配置加载

```python
# 配置加载优先级

"""
1. 命令行参数（最高优先级）
2. 环境变量
3. 项目配置文件 (config.yaml)
4. 默认配置（最低优先级）
"""

def load_config_with_priority():
    # 加载默认配置
    config = load_default_config()
    
    # 加载配置文件
    file_config = load_file_config("config.yaml")
    config.merge(file_config)
    
    # 加载环境变量
    env_config = load_env_config()
    config.merge(env_config)
    
    # 加载命令行参数
    cli_config = load_cli_config()
    config.merge(cli_config)
    
    return config
```

---

## 3. 执行流程

### 3.1 任务执行主流程

```python
# 任务执行主流程

class TaskExecutor:
    def __init__(self, task_config: TaskConfig):
        self.config = task_config
        self.state = TaskStateMachine()
        self.progress = ProgressTracker(total_steps=7)
    
    def execute(self) -> TaskResult:
        """
        主执行流程
        """
        try:
            # Step 1: 初始化
            self._step_init()
            
            # Step 2: 图纸解析
            self._step_parse_drawing()
            
            # Step 3: 电气算量
            self._step_calculate()
            
            # Step 4: BIM建模（可选）
            if self.config.enable_modeling:
                self._step_generate_model()
            
            # Step 5: AI审核（可选）
            if self.config.enable_audit:
                self._step_audit()
            
            # Step 6: 清单汇总
            self._step_summarize()
            
            # Step 7: 结果输出
            self._step_export()
            
            # 完成
            self.state.transition(TaskStatus.COMPLETED)
            return self._build_result()
            
        except Exception as e:
            self._handle_error(e)
            raise
    
    def _step_init(self):
        """步骤1: 初始化"""
        self.progress.start_step("初始化")
        
        # 加载规则库
        rule_manager = RuleManager()
        rule_manager.load_rules(self.config.rule_version)
        
        self.progress.complete_step("初始化")
    
    def _step_parse_drawing(self):
        """步骤2: 图纸解析"""
        self.progress.start_step("图纸解析")
        
        processor = DrawingProcessor()
        self.drawing_data = processor.process(
            self.config.input_files[0]
        )
        
        self.progress.complete_step("图纸解析")
    
    def _step_calculate(self):
        """步骤3: 电气算量"""
        self.progress.start_step("电气算量")
        
        calculator = ElectricalCalculator()
        self.calculation_result = calculator.calculate(
            self.drawing_data
        )
        
        self.progress.complete_step("电气算量")
    
    def _step_generate_model(self):
        """步骤4: BIM建模"""
        self.progress.start_step("BIM建模")
        
        generator = BIMGenerator()
        self.bim_components = generator.generate_from_drawing(
            self.drawing_data.devices,
            self.drawing_data.cables
        )
        
        self.progress.complete_step("BIM建模")
    
    def _step_audit(self):
        """步骤5: AI审核"""
        self.progress.start_step("AI审核")
        
        audit_client = OpenHumanAuditClient()
        self.audit_result = audit_client.audit(
            self.drawing_data,
            self.calculation_result
        )
        
        self.progress.complete_step("AI审核")
    
    def _step_summarize(self):
        """步骤6: 清单汇总"""
        self.progress.start_step("清单汇总")
        
        generator = SummaryGenerator()
        self.list_summary = generator.generate(
            self.calculation_result,
            self.audit_result
        )
        
        self.progress.complete_step("清单汇总")
    
    def _step_export(self):
        """步骤7: 结果输出"""
        self.progress.start_step("结果输出")
        
        exporter = ExcelExporter()
        self.output_files = exporter.export(
            self.list_summary,
            self.config.output_path
        )
        
        self.progress.complete_step("结果输出")
```

### 3.2 流程状态流转

```
                    ┌─────────────┐
                    │   PENDING   │
                    └──────┬──────┘
                           │ start()
                           ▼
                    ┌─────────────┐
         ┌─────────▶│   RUNNING   │◀────────┐
         │          └──────┬──────┘         │
         │                 │                │
         │     ┌────────────┼────────────┐   │
         │     │            │            │   │
         │     ▼            ▼            ▼   │
         │ ┌──────┐   ┌──────────┐   ┌──────┐ │
         │ │PAUSED│   │COMPLETED │   │FAILED│ │
         │ └──────┘   └──────────┘   └──────┘ │
         │     │                                      │
         │     │ resume()                            │
         │     └──────────────────────────────────────┘
         │
         │ cancel()
         ▼
  ┌─────────────┐
  │ CANCELLED   │
  └─────────────┘
```

---

## 4. 结束流程

### 4.1 正常结束

```python
def normal_shutdown(result: TaskResult):
    """
    正常结束流程
    """
    # 1. 保存执行结果
    save_task_result(result)
    
    # 2. 生成执行报告
    generate_execution_report(result)
    
    # 3. 清理临时文件
    cleanup_temp_files(result.task_id)
    
    # 4. 释放资源
    release_resources(result.task_id)
    
    # 5. 发送通知
    send_notification(result)
    
    # 6. 更新统计信息
    update_statistics(result)
```

### 4.2 异常结束

```python
def error_shutdown(error: Exception, context: dict):
    """
    异常结束流程
    """
    # 1. 记录错误日志
    logger.error(f"任务异常: {str(error)}", exc_info=True)
    
    # 2. 保存错误状态
    save_error_state(context, error)
    
    # 3. 清理已分配资源
    cleanup_resources(context.task_id)
    
    # 4. 发送错误通知
    send_error_notification(error, context)
    
    # 5. 更新错误统计
    increment_error_count(error.__class__.__name__)
```

---

## 5. 状态机

### 5.1 状态定义

```python
from enum import Enum

class TaskState(Enum):
    """任务状态枚举"""
    PENDING = "pending"      # 等待执行
    INITIALIZING = "initializing"  # 初始化中
    PARSING = "parsing"      # 解析中
    CALCULATING = "calculating"  # 计算中
    MODELING = "modeling"      # 建模中
    AUDITING = "auditing"      # 审核中
    SUMMARIZING = "summarizing"  # 汇总中
    EXPORTING = "exporting"    # 导出中
    COMPLETED = "completed"    # 已完成
    FAILED = "failed"         # 已失败
    CANCELLED = "cancelled"   # 已取消
    PAUSED = "paused"         # 已暂停
```

### 5.2 状态转换规则

```python
class StateTransition:
    """状态转换规则"""
    
    RULES = {
        # (当前状态, 操作) -> 新状态
        (TaskState.PENDING, 'start'): TaskState.INITIALIZING,
        (TaskState.INITIALIZING, 'complete'): TaskState.PARSING,
        (TaskState.PARSING, 'complete'): TaskState.CALCULATING,
        (TaskState.CALCULATING, 'complete'): TaskState.MODELING,
        (TaskState.MODELING, 'complete'): TaskState.AUDITING,
        (TaskState.AUDITING, 'complete'): TaskState.SUMMARIZING,
        (TaskState.SUMMARIZING, 'complete'): TaskState.EXPORTING,
        (TaskState.EXPORTING, 'complete'): TaskState.COMPLETED,
        
        # 失败转换
        (TaskState.INITIALIZING, 'error'): TaskState.FAILED,
        (TaskState.PARSING, 'error'): TaskState.FAILED,
        (TaskState.CALCULATING, 'error'): TaskState.FAILED,
        (TaskState.MODELING, 'error'): TaskState.FAILED,
        (TaskState.AUDITING, 'error'): TaskState.FAILED,
        (TaskState.SUMMARIZING, 'error'): TaskState.FAILED,
        (TaskState.EXPORTING, 'error'): TaskState.FAILED,
        
        # 取消转换
        (TaskState.PENDING, 'cancel'): TaskState.CANCELLED,
        (TaskState.INITIALIZING, 'cancel'): TaskState.CANCELLED,
        (TaskState.PARSING, 'cancel'): TaskState.CANCELLED,
        (TaskState.CALCULATING, 'cancel'): TaskState.CANCELLED,
        
        # 暂停转换
        (TaskState.RUNNING, 'pause'): TaskState.PAUSED,
        (TaskState.PAUSED, 'resume'): TaskState.RUNNING,
        (TaskState.PAUSED, 'cancel'): TaskState.CANCELLED,
        
        # 重试转换
        (TaskState.FAILED, 'retry'): TaskState.PENDING,
    }
    
    @classmethod
    def can_transition(cls, current_state: TaskState, action: str) -> bool:
        return (current_state, action) in cls.RULES
    
    @classmethod
    def get_next_state(cls, current_state: TaskState, action: str) -> TaskState:
        return cls.RULES.get((current_state, action))
```

---

## 6. 异常处理流程

### 6.1 异常分类处理

```python
class ExceptionHandler:
    """异常处理器"""
    
    def handle(self, exception: Exception, context: dict) -> None:
        if isinstance(exception, ParseError):
            self._handle_parse_error(exception, context)
        elif isinstance(exception, CalculationError):
            self._handle_calculation_error(exception, context)
        elif isinstance(exception, AuditError):
            self._handle_audit_error(exception, context)
        else:
            self._handle_unknown_error(exception, context)
    
    def _handle_parse_error(self, error: ParseError, context: dict):
        """
        解析错误处理
        - 记录日志
        - 尝试重试（最多3次）
        - 如果仍然失败，返回部分结果或终止任务
        """
        logger.warning(f"解析失败: {str(error)}")
        
        if context.get('retry_count', 0) < 3:
            context['retry_count'] = context.get('retry_count', 0) + 1
            # 返回需要重试的信号
            return {'action': 'retry', 'context': context}
        else:
            return {'action': 'fail', 'error': error}
    
    def _handle_calculation_error(self, error: CalculationError, context: dict):
        """
        算量错误处理
        - 记录日志
        - 返回错误详情
        - 可能需要人工介入
        """
        logger.error(f"算量失败: {str(error)}")
        return {'action': 'fail', 'error': error}
    
    def _handle_audit_error(self, error: AuditError, context: dict):
        """
        审核错误处理
        - 审核失败不应终止任务
        - 跳过审核继续执行
        - 记录警告
        """
        logger.warning(f"审核失败，跳过: {str(error)}")
        return {'action': 'skip', 'message': '审核失败但继续执行'}
```

### 6.2 重试策略

```python
class RetryStrategy:
    """重试策略配置"""
    
    # 不同错误类型的重试策略
    STRATEGIES = {
        'parse': {
            'max_attempts': 3,
            'delay': 2.0,  # 秒
            'backoff': 'exponential',  # 指数退避
            'retryable_errors': [ParseError]
        },
        'calculate': {
            'max_attempts': 2,
            'delay': 1.0,
            'backoff': 'linear',
            'retryable_errors': [CalculationError]
        },
        'audit': {
            'max_attempts': 3,
            'delay': 5.0,
            'backoff': 'fixed',
            'retryable_errors': [AuditError, TimeoutError]
        },
        'export': {
            'max_attempts': 2,
            'delay': 1.0,
            'backoff': 'linear',
            'retryable_errors': [ExportError]
        }
    }
    
    @classmethod
    def should_retry(cls, error: Exception, operation: str) -> bool:
        strategy = cls.STRATEGIES.get(operation, {})
        return (
            error.__class__ in strategy.get('retryable_errors', []) and
            error.attempt_count < strategy.get('max_attempts', 1)
        )
```

---

## 附录

### A. 流程耗时估算

| 操作 | 最小 | 最大 | 平均 |
|------|------|------|------|
| 图纸解析(DXF) | 1秒 | 30秒 | 5秒 |
| 图纸解析(PDF) | 2秒 | 60秒 | 10秒 |
| 图纸解析(图片) | 5秒 | 120秒 | 30秒 |
| 电气算量 | 1秒 | 10秒 | 3秒 |
| BIM建模 | 5秒 | 60秒 | 20秒 |
| AI审核 | 10秒 | 120秒 | 30秒 |
| Excel导出 | 1秒 | 10秒 | 3秒 |
| IFC导出 | 2秒 | 30秒 | 8秒 |

### B. 资源占用估算

| 资源 | 单任务 | 并发4任务 |
|------|--------|-----------|
| CPU | 100% | 400% |
| 内存 | 500MB | 2GB |
| 磁盘IO | 10MB/s | 40MB/s |
| 网络 | 1MB/s | 4MB/s |
