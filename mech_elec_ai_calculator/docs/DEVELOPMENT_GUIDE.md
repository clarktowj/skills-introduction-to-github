# 机电AI自动算量系统 - 开发规范文档

## 目录

1. [核心代码模板](#1-核心代码模板)
2. [模块调用逻辑](#2-模块调用逻辑)
3. [交互接口规范](#3-交互接口规范)
4. [运行流程说明](#4-运行流程说明)
5. [对接要点](#5-对接要点)
6. [落地注意事项](#6-落地注意事项)

---

## 1. 核心代码模板

### 1.1 应用初始化模板

```python
# app_initialization_template.py
from framework.app import Application
from common.models import TaskConfig
from routing.scheduler import TaskScheduler

def initialize_app(config_path: str = None) -> Application:
    """
    应用初始化标准流程
    
    Args:
        config_path: 配置文件路径，默认使用 ./config/config.yaml
    
    Returns:
        Application: 已初始化的应用实例
    
    Raises:
        AppStartupError: 初始化失败时抛出
    """
    app = Application()
    app.initialize(config_path)
    return app

def create_task_config(
    input_files: list,
    output_path: str = "./outputs",
    rule_version: str = "latest",
    enable_audit: bool = True,
    enable_modeling: bool = True
) -> TaskConfig:
    """
    创建任务配置标准方法
    
    Args:
        input_files: 输入图纸文件列表
        output_path: 输出目录路径
        rule_version: 规则库版本
        enable_audit: 是否启用AI审核
        enable_modeling: 是否启用BIM建模
    
    Returns:
        TaskConfig: 任务配置对象
    """
    return TaskConfig(
        task_name="电气算量任务",
        input_files=input_files,
        output_path=output_path,
        rule_version=rule_version,
        enable_audit=enable_audit,
        enable_modeling=enable_modeling,
        parameters={
            "project_name": "项目名称",
            "project_code": "项目编号"
        }
    )
```

### 1.2 图纸解析调用模板

```python
# drawing_parser_template.py
from drawing_parser.drawing_processor import DrawingProcessor
from common.models import DrawingData

def parse_drawing(file_path: str) -> DrawingData:
    """
    图纸解析标准调用流程
    
    Args:
        file_path: 图纸文件路径（支持 .dxf, .pdf, .jpg, .png）
    
    Returns:
        DrawingData: 结构化图纸数据
    
    Raises:
        ParseError: 解析失败时抛出
    """
    processor = DrawingProcessor()
    
    # 支持的文件类型
    supported_types = ['.dxf', '.pdf', '.jpg', '.jpeg', '.png', '.bmp', '.tiff']
    
    if not processor.is_supported(file_path):
        raise ValueError(f"不支持的文件类型: {file_path}")
    
    # 执行解析
    drawing_data = processor.process(file_path)
    
    # 验证解析结果
    if not drawing_data.devices and not drawing_data.cables:
        print(f"警告: 图纸 {file_path} 未识别到任何设备或线缆")
    
    return drawing_data

def parse_multiple_drawings(file_paths: list) -> list:
    """批量解析图纸"""
    results = []
    for file_path in file_paths:
        try:
            result = parse_drawing(file_path)
            results.append(result)
        except Exception as e:
            print(f"解析失败 {file_path}: {str(e)}")
    return results
```

### 1.3 电气算量调用模板

```python
# electrical_calculator_template.py
from electrical_calculator.calculator import ElectricalCalculator
from rule_engine.rule_manager import RuleManager
from common.models import DrawingData, CalculationResult

def calculate_quantities(drawing_data: DrawingData, rule_version: str = "latest") -> CalculationResult:
    """
    电气算量标准调用流程
    
    Args:
        drawing_data: 解析后的图纸数据
        rule_version: 规则库版本
    
    Returns:
        CalculationResult: 算量结果
    
    Raises:
        CalculationError: 算量失败时抛出
    """
    # 加载规则库
    rule_manager = RuleManager()
    rule_manager.load_rules(rule_version)
    
    # 执行算量
    calculator = ElectricalCalculator()
    result = calculator.calculate(drawing_data)
    
    # 输出统计信息
    print(f"设备数量: {len(result.devices)}")
    print(f"线缆数量: {len(result.cables)}")
    print(f"桥架数量: {len(result.trunkings)}")
    print(f"配管数量: {len(result.pipes)}")
    print(f"辅材数量: {len(result.accessories)}")
    print(f"总造价: {result.total_cost:.2f} 元")
    
    return result

def calculate_with_custom_rules(
    drawing_data: DrawingData,
    custom_reserve_lengths: dict = None,
    custom_correction_factors: dict = None
) -> CalculationResult:
    """使用自定义规则进行算量"""
    calculator = ElectricalCalculator()
    
    # 自定义预留长度
    if custom_reserve_lengths:
        for reserve_type, length in custom_reserve_lengths.items():
            # 这里可以通过扩展RuleManager来实现
            pass
    
    return calculator.calculate(drawing_data)
```

### 1.4 BIM建模调用模板

```python
# bim_modeling_template.py
from bim_modeling.bim_generator import BIMGenerator
from bim_modeling.ifc_exporter import IFCExporter
from bim_modeling.model_manager import ModelManager
from common.models import DrawingData, CalculationResult, BIMComponent

def generate_bim_model(
    drawing_data: DrawingData,
    calculation: CalculationResult = None
) -> list:
    """
    BIM模型生成标准调用流程
    
    Args:
        drawing_data: 图纸数据
        calculation: 算量结果（可选，用于量模绑定）
    
    Returns:
        list[BIMComponent]: BIM构件列表
    """
    generator = BIMGenerator()
    
    # 从图纸数据生成模型
    components = generator.generate_from_drawing(
        devices=drawing_data.devices,
        cables=drawing_data.cables
    )
    
    # 如果有算量结果，执行量模绑定验证
    if calculation:
        manager = ModelManager()
        manager.add_components(components)
        
        try:
            manager.validate_quantity_binding(calculation)
            print("量模绑定验证通过")
        except Exception as e:
            print(f"量模绑定警告: {str(e)}")
    
    return components

def export_ifc_model(components: list, output_path: str) -> str:
    """
    导出IFC模型
    
    Args:
        components: BIM构件列表
        output_path: 输出文件路径
    
    Returns:
        str: 实际保存的文件路径
    """
    exporter = IFCExporter()
    return exporter.export(components, output_path)

def get_model_statistics(components: list) -> dict:
    """获取模型统计信息"""
    from common.models import BIMComponentType
    
    stats = {
        "total": len(components),
        "by_type": {}
    }
    
    for comp_type in BIMComponentType:
        count = sum(1 for c in components if c.type == comp_type)
        if count > 0:
            stats["by_type"][comp_type.value] = count
    
    return stats
```

### 1.5 AI审核调用模板

```python
# openhuman_audit_template.py
from openhuman_audit.audit_client import OpenHumanAuditClient
from openhuman_audit.audit_processor import AuditProcessor
from common.models import DrawingData, CalculationResult, AuditResult

def audit_with_ai(
    drawing_data: DrawingData,
    calculation: CalculationResult,
    api_key: str = None
) -> AuditResult:
    """
    AI审核标准调用流程
    
    Args:
        drawing_data: 图纸数据
        calculation: 算量结果
        api_key: OpenHuman API密钥（可选）
    
    Returns:
        AuditResult: 审核结果
    """
    client = OpenHumanAuditClient()
    
    # 执行审核
    result = client.audit(drawing_data, calculation)
    
    # 输出审核结果
    print(f"审核分数: {result.audit_score:.1f}")
    print(f"审核状态: {'通过' if result.passed else '未通过'}")
    print(f"发现问题: {len(result.issues)} 个")
    
    # 处理审核结果
    processor = AuditProcessor()
    
    # 按优先级排序问题
    sorted_issues = processor.prioritize_issues(result.issues)
    
    # 生成审核报告
    report = processor.generate_report(sorted_issues)
    print(report)
    
    return result

def auto_correct_issues(audit_result: AuditResult, calculation: CalculationResult) -> CalculationResult:
    """
    根据审核结果自动修正算量
    
    Args:
        audit_result: 审核结果
        calculation: 原始算量结果
    
    Returns:
        CalculationResult: 修正后的算量结果
    """
    processor = AuditProcessor()
    return processor.process_audit_results(audit_result.issues, calculation)
```

### 1.6 清单汇总调用模板

```python
# list_summary_template.py
from list_summary.summary_generator import SummaryGenerator
from list_summary.excel_exporter import ExcelExporter
from common.models import CalculationResult, AuditResult, ListSummary

def generate_quantity_list(
    calculation: CalculationResult,
    audit_result: AuditResult = None,
    project_name: str = "",
    project_code: str = ""
) -> ListSummary:
    """
    生成工程量清单标准流程
    
    Args:
        calculation: 算量结果
        audit_result: 审核结果（可选）
        project_name: 项目名称
        project_code: 项目编号
    
    Returns:
        ListSummary: 工程量清单
    """
    generator = SummaryGenerator()
    
    summary = generator.generate(
        calculation=calculation,
        audit_result=audit_result,
        project_name=project_name,
        project_code=project_code
    )
    
    # 输出汇总统计
    category_totals = generator.get_category_totals(summary)
    print("分类汇总:")
    for category, total in category_totals.items():
        print(f"  {category}: {total:.2f} 元")
    
    print(f"\n总计: {summary.total_cost:.2f} 元")
    
    return summary

def export_to_excel(summary: ListSummary, output_path: str) -> str:
    """
    导出Excel清单
    
    Args:
        summary: 工程量清单
        output_path: 输出路径
    
    Returns:
        str: 实际保存的文件路径
    """
    exporter = ExcelExporter()
    return exporter.export(summary, output_path)
```

---

## 2. 模块调用逻辑

### 2.1 模块依赖关系图

```
┌─────────────────────────────────────────────────────────────────┐
│                         框架模块 (Framework)                      │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐ │
│  │ App     │  │ Config  │  │ Logger  │  │ File    │  │ Cache   │ │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘ │
└───────┼───────────┼───────────┼───────────┼───────────┼──────────┘
        │           │           │           │           │
        └───────────┴───────────┴───────────┴───────────┘
                              │
                    ┌─────────▼─────────┐
                    │  公共接口 (Common)  │
                    │   Pydantic模型    │
                    └─────────┬─────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐   ┌─────────────────┐   ┌─────────────────┐
│  规则库模块    │   │  图纸解析模块   │   │   AI审核模块    │
│ (Rule Engine) │   │(Drawing Parser)│   │(OpenHuman Audit)│
└───────┬───────┘   └────────┬────────┘   └────────┬────────┘
        │                    │                      │
        └────────────────────┴──────────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │   电气算量模块     │
                    │(Electrical Calc)  │
                    └─────────┬─────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐   ┌─────────────────┐   ┌─────────────────┐
│  三维BIM模块   │   │   清单汇总模块   │   │  路由调度模块    │
│(BIM Modeling) │   │(List Summary)  │   │   (Routing)     │
└───────────────┘   └─────────────────┘   └────────┬────────┘
                                                    │
                                          ┌─────────▼─────────┐
                                          │   存储日志模块     │
                                          │ (Storage & Log)   │
                                          └───────────────────┘
```

### 2.2 单向依赖原则

```
【规则】所有模块必须遵守单向依赖原则：

1. Framework → Common → Rule Engine → Business Modules → Routing → AI Audit
2. Storage & Log 模块被所有模块共享使用
3. 禁止反向依赖（低层模块不能引用高层模块）
4. 禁止跨层依赖（不能跳过中间层）
```

### 2.3 调用时序图

```
用户/外部系统
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│                      路由调度 (TaskScheduler)                    │
└────────────────────────────┬────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
   ┌─────────┐        ┌───────────┐        ┌───────────┐
   │图纸解析 │        │ 电气算量  │        │ BIM建模   │
   └────┬────┘        └─────┬─────┘        └─────┬─────┘
        │                   │                   │
        └───────────────────┴───────────────────┘
                            │
                    ┌───────▼───────┐
                    │   AI审核      │
                    └───────┬───────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                    │
        ▼                   ▼                    ▼
   ┌─────────┐        ┌───────────┐        ┌───────────┐
   │清单汇总 │        │ Excel导出 │        │ IFC导出   │
   └────┬────┘        └───────────┘        └───────────┘
        │
        ▼
   ┌─────────────────┐
   │  返回任务结果    │
   └─────────────────┘
```

---

## 3. 交互接口规范

### 3.1 数据模型命名规范

```python
# 命名规则：
# - 类名：PascalCase
# - 字段名：snake_case
# - 枚举值：UPPER_SNAKE_CASE
# - 常量：UPPER_SNAKE_CASE

# 示例：
class DeviceModel(BaseModel):
    device_id: str          # 设备ID
    device_name: str         # 设备名称
    device_type: DeviceType  # 设备类型枚举
    coordinates: Coordinate  # 坐标对象
```

### 3.2 统一响应格式

```python
# 所有接口返回统一格式：

class ApiResponse(BaseModel):
    """统一API响应格式"""
    success: bool                    # 是否成功
    code: int                        # 状态码
    message: str                     # 消息
    data: Optional[Any]              # 数据
    errors: Optional[List[str]]      # 错误列表
    timestamp: datetime               # 时间戳

# 状态码定义
class ResponseCode:
    SUCCESS = 200
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    INTERNAL_ERROR = 500
    SERVICE_UNAVAILABLE = 503
```

### 3.3 错误处理规范

```python
# 异常类定义
class MechElecAIException(Exception):
    """基础异常类"""
    code = 500
    message = "未知错误"

# 特定异常类
class ParseError(MechElecAIException):
    """图纸解析错误"""
    code = 1001
    message = "图纸解析失败"

class CalculationError(MechElecAIException):
    """算量错误"""
    code = 1002
    message = "工程量计算失败"

class ValidationError(MechElecAIException):
    """验证错误"""
    code = 1003
    message = "数据验证失败"

# 全局异常处理
def handle_exception(e: Exception) -> ApiResponse:
    if isinstance(e, MechElecAIException):
        return ApiResponse(
            success=False,
            code=e.code,
            message=e.message,
            errors=[str(e)]
        )
    else:
        return ApiResponse(
            success=False,
            code=500,
            message="系统内部错误",
            errors=[str(e)]
        )
```

### 3.4 API端点定义

```yaml
# api_endpoints.yaml

openapi: 3.0.0
info:
  title: 机电AI自动算量系统 API
  version: 1.0.0

paths:
  /api/v1/parse:
    post:
      summary: 解析图纸
      requestBody:
        content:
          multipart/form-data:
            schema:
              type: object
              properties:
                file:
                  type: string
                  format: binary
                file_type:
                  type: string
                  enum: [dxf, pdf, image]
      responses:
        200:
          description: 解析成功
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/DrawingData'

  /api/v1/calculate:
    post:
      summary: 执行算量
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CalculationRequest'
      responses:
        200:
          description: 算量成功
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/CalculationResult'

  /api/v1/audit:
    post:
      summary: AI审核
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/AuditRequest'
      responses:
        200:
          description: 审核成功
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/AuditResult'

  /api/v1/export:
    post:
      summary: 导出清单
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ExportRequest'
      responses:
        200:
          description: 导出成功
          content:
            application/octet-stream:
              schema:
                type: string
                format: binary
```

---

## 4. 运行流程说明

### 4.1 完整执行流程

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           完整运行流程                                       │
└─────────────────────────────────────────────────────────────────────────────┘

1. 应用启动
   ├── 加载配置文件 (config.yaml)
   ├── 初始化日志系统
   ├── 创建必要目录
   └── 验证依赖环境

2. 任务接收
   ├── 解析命令行参数/API请求
   ├── 验证输入文件
   ├── 创建任务配置 (TaskConfig)
   └── 加载规则库

3. 图纸解析
   ├── 判断文件类型
   ├── 调用对应解析器
   │   ├── DXF → DXFParser
   │   ├── PDF → PDFParser
   │   └── Image → ImageParser
   ├── 提取设备信息
   ├── 提取线缆信息
   └── 返回 DrawingData

4. 自动算量
   ├── 加载规则库
   ├── 统计设备数量
   ├── 计算线缆长度
   │   ├── 基础长度
   │   ├── 预留长度
   │   └── 修正系数
   ├── 计算桥架长度
   ├── 计算配管长度
   ├── 统计辅材
   └── 计算总造价

5. BIM建模 (可选)
   ├── 创建设备构件
   ├── 创建线缆构件
   ├── 执行量模绑定
   └── 导出IFC文件

6. AI审核 (可选)
   ├── 检查设备完整性
   ├── 检查线缆合理性
   ├── 验证规范符合性
   ├── 检查量模一致性
   └── 生成审核报告

7. 清单汇总
   ├── 合并所有工程量
   ├── 分类汇总
   ├── 计算小计
   └── 计算总价

8. 输出结果
   ├── 生成Excel清单
   ├── 保存IFC模型
   ├── 生成审核报告
   └── 返回任务结果
```

### 4.2 流程控制参数

```python
# 流程控制选项
TASK_CONFIG_PARAMETERS = {
    # 必须参数
    "input_files": ["required", "list"],           # 输入文件
    "output_path": ["required", "string"],         # 输出目录
    
    # 可选参数
    "rule_version": ["optional", "string", "latest"],    # 规则版本
    "enable_audit": ["optional", "bool", True],           # 启用AI审核
    "enable_modeling": ["optional", "bool", True],        # 启用BIM建模
    
    # 高级参数
    "custom_rules": ["optional", "dict", None],           # 自定义规则
    "parallel_processing": ["optional", "bool", False],   # 并行处理
    "cache_enabled": ["optional", "bool", True],           # 启用缓存
}
```

---

## 5. 对接要点

### 5.1 外部系统对接

```python
# 对接外部系统的标准接口

class ExternalSystemAdapter:
    """外部系统适配器基类"""
    
    def connect(self) -> bool:
        """建立连接"""
        raise NotImplementedError
    
    def disconnect(self) -> bool:
        """断开连接"""
        raise NotImplementedError
    
    def send_data(self, data: Any) -> bool:
        """发送数据"""
        raise NotImplementedError
    
    def receive_data(self) -> Any:
        """接收数据"""
        raise NotImplementedError


# BIM软件对接示例 (Revit, ArchiCAD等)
class BIMSoftwareAdapter(ExternalSystemAdapter):
    """BIM软件对接适配器"""
    
    def __init__(self, software_type: str, connection_string: str):
        self.software_type = software_type
        self.connection_string = connection_string
        self.connection = None
    
    def connect(self) -> bool:
        # 实现连接逻辑
        pass
    
    def export_to_bim(self, components: list, format: str = "ifc") -> str:
        """导出到BIM软件"""
        exporter = IFCExporter()
        temp_path = f"/tmp/bim_export.{format}"
        exporter.export(components, temp_path)
        return temp_path
    
    def import_from_bim(self, file_path: str) -> DrawingData:
        """从BIM软件导入"""
        # 实现导入逻辑
        pass
```

### 5.2 数据交换格式

```python
# JSON数据交换格式

{
    "header": {
        "version": "1.0.0",
        "timestamp": "2024-01-01T00:00:00Z",
        "source": "mech_elec_ai_calculator",
        "project_id": "PROJECT-001"
    },
    "payload": {
        "type": "CALCULATION_RESULT",
        "data": {
            # 具体数据内容
        }
    },
    "signature": {
        "algorithm": "RSA-SHA256",
        "value": "base64_encoded_signature"
    }
}
```

### 5.3 Webhook回调规范

```python
# Webhook回调配置

WEBHOOK_CONFIG = {
    "endpoints": {
        "on_task_start": {
            "url": "https://external.system/webhook/task/start",
            "method": "POST",
            "retry": 3,
            "timeout": 30
        },
        "on_task_complete": {
            "url": "https://external.system/webhook/task/complete",
            "method": "POST",
            "retry": 3,
            "timeout": 30
        },
        "on_task_error": {
            "url": "https://external.system/webhook/task/error",
            "method": "POST",
            "retry": 5,
            "timeout": 30
        }
    },
    "payload_format": {
        "include_result": True,
        "include_errors": True,
        "include_metadata": True
    }
}

# Webhook发送示例
def send_webhook(event_type: str, payload: dict):
    config = WEBHOOK_CONFIG["endpoints"].get(event_type)
    if not config:
        return
    
    response = requests.post(
        config["url"],
        json=payload,
        timeout=config["timeout"]
    )
    return response
```

---

## 6. 落地注意事项

### 6.1 环境配置要点

```yaml
# 生产环境配置示例 - config/production.yaml

app:
  name: 机电AI自动算量系统
  version: 1.0.0
  debug: false
  environment: production

storage:
  data_path: /data/mech_elec_ai/storage
  output_path: /data/mech_elec_ai/outputs
  log_path: /var/log/mech_elec_ai
  cache_path: /data/mech_elec_ai/cache
  
  # 存储配置
  storage_type: s3  # local, s3, minio
  s3:
    endpoint: http://minio.local:9000
    bucket: mech-elec-ai
    access_key: ${S3_ACCESS_KEY}
    secret_key: ${S3_SECRET_KEY}

logging:
  level: INFO
  format: json  # text, json
  output: file  # file, stdout, both
  rotation:
    max_size: 100MB
    backup_count: 30

openhuman:
  api_url: https://api.openhuman.ai/v1
  api_key: ${OPENHUMAN_API_KEY}
  timeout: 120
  retry: 3

performance:
  max_workers: 4
  queue_size: 100
  cache_ttl: 3600
```

### 6.2 性能优化要点

```python
# 性能优化配置

PERFORMANCE_OPTIMIZATION = {
    # 并行处理
    "parallel_parsing": {
        "enabled": True,
        "max_workers": 4,
        "chunk_size": 10
    },
    
    # 缓存策略
    "caching": {
        "enabled": True,
        "ttl": 3600,
        "max_size": "1GB",
        "strategy": "lru"  # lru, lfu, fifo
    },
    
    # 内存管理
    "memory": {
        "max_heap_size": "4GB",
        "gc_threshold": 0.8,
        "cleanup_interval": 300
    },
    
    # 大文件处理
    "large_file": {
        "chunk_size": "50MB",
        "temp_dir": "/tmp/mech_elec_ai",
        "delete_after_process": False
    }
}
```

### 6.3 安全配置要点

```yaml
# 安全配置 - config/security.yaml

security:
  # 认证配置
  authentication:
    enabled: True
    type: jwt  # jwt, api_key, oauth2
    jwt:
      secret_key: ${JWT_SECRET_KEY}
      algorithm: HS256
      expiry: 3600
    
    api_key:
      header_name: X-API-Key
      validation: sha256
    
    oauth2:
      provider: keycloak
      client_id: ${OAUTH_CLIENT_ID}
      client_secret: ${OAUTH_CLIENT_SECRET}
  
  # 授权配置
  authorization:
    enabled: True
    rbac:
      admin: ["*"]
      user: ["parse", "calculate", "export"]
      guest: ["parse"]
  
  # 数据加密
  encryption:
    enabled: True
    algorithm: AES-256-GCM
    key_rotation: 90  # days
  
  # 文件上传安全
  upload:
    max_size: 100MB
    allowed_types: [".dxf", ".pdf", ".jpg", ".jpeg", ".png"]
    scan_virus: True
    quarantine_dir: /data/quarantine
```

### 6.4 监控与告警

```python
# 监控指标定义

METRICS = {
    # 业务指标
    "business": {
        "tasks_total": "任务总数",
        "tasks_success": "成功任务数",
        "tasks_failed": "失败任务数",
        "avg_processing_time": "平均处理时间",
        "calculation_accuracy": "算量精度"
    },
    
    # 系统指标
    "system": {
        "cpu_usage": "CPU使用率",
        "memory_usage": "内存使用率",
        "disk_usage": "磁盘使用率",
        "network_io": "网络IO"
    },
    
    # 性能指标
    "performance": {
        "parsing_speed": "解析速度 (文件/秒)",
        "calculation_speed": "算量速度 (构件/秒)",
        "model_generation_speed": "建模速度 (构件/秒)"
    }
}

# 告警规则

ALERT_RULES = [
    {
        "name": "high_error_rate",
        "condition": "tasks_failed / tasks_total > 0.1",
        "severity": "critical",
        "notification": ["email", "sms", "webhook"]
    },
    {
        "name": "slow_processing",
        "condition": "avg_processing_time > 300",
        "severity": "warning",
        "notification": ["webhook"]
    },
    {
        "name": "disk_space_low",
        "condition": "disk_usage > 0.9",
        "severity": "critical",
        "notification": ["email", "sms"]
    }
]
```

### 6.5 部署检查清单

```markdown
# 部署前检查清单

## 环境准备
- [ ] Python 3.10+ 已安装
- [ ] 所有依赖包已安装
- [ ] 数据库已配置（如使用）
- [ ] 缓存服务已配置（如Redis）
- [ ] 文件存储已配置（如S3/MinIO）

## 配置验证
- [ ] 配置文件路径正确
- [ ] 环境变量已设置
- [ ] 规则库文件存在且格式正确
- [ ] 规范文档目录存在

## 权限检查
- [ ] 应用目录读写权限
- [ ] 日志目录写入权限
- [ ] 输出目录写入权限
- [ ] 临时目录权限

## 安全检查
- [ ] API密钥已配置
- [ ] 认证功能已启用
- [ ] HTTPS配置（如需要）
- [ ] 防火墙规则已配置

## 监控检查
- [ ] 日志收集已配置
- [ ] 监控指标已设置
- [ ] 告警规则已配置
- [ ] 健康检查端点已启用

## 备份计划
- [ ] 配置文件备份
- [ ] 规则库备份
- [ ] 数据备份策略
- [ ] 灾难恢复计划
```

### 6.6 常见问题处理

```python
# 常见问题及解决方案

TROUBLESHOOTING_GUIDE = {
    "问题1: 图纸解析失败": {
        "原因": ["文件格式不支持", "文件损坏", "编码问题"],
        "排查": [
            "1. 检查文件扩展名",
            "2. 验证文件完整性",
            "3. 检查文件编码"
        ],
        "解决": [
            "1. 转换为支持的格式",
            "2. 重新下载文件",
            "3. 使用编码转换工具"
        ]
    },
    
    "问题2: 算量结果偏差大": {
        "原因": ["规则库配置错误", "识别精度不足", "图纸质量问题"],
        "排查": [
            "1. 检查规则库版本",
            "2. 验证识别结果",
            "3. 对比图纸标注"
        ],
        "解决": [
            "1. 更新规则库",
            "2. 启用AI审核",
            "3. 人工复核"
        ]
    },
    
    "问题3: BIM模型导出失败": {
        "原因": ["IFC格式不支持", "构件数据不完整", "磁盘空间不足"],
        "排查": [
            "1. 检查构件完整性",
            "2. 验证磁盘空间",
            "3. 测试IFC库"
        ],
        "解决": [
            "1. 补充构件数据",
            "2. 清理磁盘空间",
            "3. 使用替代格式"
        ]
    },
    
    "问题4: AI审核超时": {
        "原因": ["网络问题", "API限流", "服务不可用"],
        "排查": [
            "1. 检查网络连接",
            "2. 查看API配额",
            "3. 验证服务状态"
        ],
        "解决": [
            "1. 重试请求",
            "2. 联系API提供商",
            "3. 跳过审核继续"
        ]
    }
}
```

---

## 附录

### A. 版本历史

| 版本 | 日期 | 修改内容 | 作者 |
|------|------|----------|------|
| 1.0.0 | 2024-01-01 | 初始版本 | MechElecAI Team |

### B. 联系方式

- 技术支持: support@mecheleai.com
- 问题反馈: issues@mecheleai.com
- 文档更新: docs@mecheleai.com
