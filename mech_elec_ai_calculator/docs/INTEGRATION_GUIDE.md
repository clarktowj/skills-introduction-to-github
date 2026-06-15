# 对接要点文档

## 目录

1. [对接概述](#1-对接概述)
2. [内部模块对接](#2-内部模块对接)
3. [外部系统对接](#3-外部系统对接)
4. [数据格式对接](#4-数据格式对接)
5. [接口协议对接](#5-接口协议对接)
6. [安全对接](#6-安全对接)

---

## 1. 对接概述

### 1.1 对接架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              外部系统                                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐                   │
│  │ BIM软件  │  │ ERP系统  │  │ OA系统   │  │ 移动端   │                   │
│  │ Revit    │  │ 用友/金蝶 │  │ 钉钉/企业 │  │ 微信小程序│                   │
│  │ ArchiCAD │  │ SAP      │  │ 飞书     │  │ 企业微信  │                   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘                   │
│       │            │            │            │                          │
│       └────────────┴────────────┴────────────┘                          │
│                            │                                             │
│                            ▼                                             │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │                        API网关 / Webhook                            │  │
│  └────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           机电AI自动算量系统                                  │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                    │
│  │  REST API   │    │  WebSocket  │    │   gRPC      │                    │
│  └─────────────┘    └─────────────┘    └─────────────┘                    │
│         │                  │                  │                           │
│         └──────────────────┴──────────────────┘                           │
│                            │                                             │
│                            ▼                                             │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │                      业务逻辑层 (Business Layer)                   │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │  │
│  │  │图纸解析  │  │电气算量  │  │BIM建模   │  │AI审核   │            │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘            │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                            │                                             │
│                            ▼                                             │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │                      数据访问层 (Data Layer)                        │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐                         │  │
│  │  │ 文件存储  │  │ 数据库   │  │  缓存    │                         │  │
│  │  └──────────┘  └──────────┘  └──────────┘                         │  │
│  └────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 对接模式

| 模式 | 适用场景 | 协议 | 特点 |
|------|----------|------|------|
| 同步请求 | 简单操作、实时返回 | HTTP REST | 简单直接 |
| 异步任务 | 复杂计算、长耗时 | HTTP REST + WebSocket | 高效可靠 |
| 文件上传 | 大文件传输 | multipart/form-data | 支持大文件 |
| 实时推送 | 进度通知 | WebSocket | 即时性强 |
| 批量处理 | 大批量数据 | REST Batch API | 减少开销 |

---

## 2. 内部模块对接

### 2.1 模块间调用规范

```python
# 正确调用方式

# 1. 直接实例化（无状态模块）
from drawing_parser import DrawingProcessor
processor = DrawingProcessor()
result = processor.process(file_path)

# 2. 单例获取（有状态模块）
from rule_engine import RuleManager
rule_manager = RuleManager()  # 自动获取单例
rule_manager.load_rules('latest')

# 3. 通过应用实例获取
from framework import Application
app = Application()
logger = app.logger
logger.info("操作日志")
```

### 2.2 数据传递规范

```python
# 使用Pydantic模型传递数据

from common.models import DrawingData, CalculationResult

def business_operation(drawing_data: DrawingData) -> CalculationResult:
    """
    业务操作：接收 DrawingData，返回 CalculationResult
    
    Args:
        drawing_data: 图纸数据（必须使用模型）
    
    Returns:
        CalculationResult: 算量结果（必须使用模型）
    """
    calculator = ElectricalCalculator()
    return calculator.calculate(drawing_data)
```

### 2.3 异常处理规范

```python
# 模块间异常处理

from framework.exceptions import ParseError, CalculationError

def safe_call(module_func, *args, **kwargs):
    """安全的模块调用封装"""
    try:
        return module_func(*args, **kwargs)
    except ParseError as e:
        logger.error(f"解析错误: {str(e)}")
        raise  # 可恢复错误可重试
    except CalculationError as e:
        logger.error(f"算量错误: {str(e)}")
        raise  # 需要检查参数
    except Exception as e:
        logger.error(f"未知错误: {str(e)}")
        raise  # 系统错误
```

---

## 3. 外部系统对接

### 3.1 BIM软件对接

```python
# BIM软件对接适配器

class BIMSoftwareAdapter:
    """BIM软件对接基类"""
    
    def __init__(self, config: dict):
        self.config = config
        self.connection = None
    
    def connect(self) -> bool:
        """建立连接"""
        raise NotImplementedError
    
    def disconnect(self) -> bool:
        """断开连接"""
        raise NotImplementedError
    
    def import_drawing(self, file_path: str) -> DrawingData:
        """从BIM软件导入图纸"""
        raise NotImplementedError
    
    def export_model(self, components: list, file_path: str) -> bool:
        """导出模型到BIM软件"""
        raise NotImplementedError


class RevitAdapter(BIMSoftwareAdapter):
    """Revit对接适配器"""
    
    def connect(self) -> bool:
        # Revit API 连接逻辑
        pass
    
    def import_drawing(self, file_path: str) -> DrawingData:
        # 从Revit导出DWG/DXF后解析
        pass
    
    def export_model(self, components: list, file_path: str) -> bool:
        # 创建Revit族文件
        pass


class ArchiCADAdapter(BIMSoftwareAdapter):
    """ArchiCAD对接适配器"""
    
    def connect(self) -> bool:
        # ArchiCAD API 连接逻辑
        pass
    
    def import_drawing(self, file_path: str) -> DrawingData:
        # 从ArchiCAD导出DXF后解析
        pass
    
    def export_model(self, components: list, file_path: str) -> bool:
        # 创建ArchiCAD对象
        pass
```

### 3.2 ERP系统对接

```python
# ERP系统对接

class ERPAdapter:
    """ERP系统对接基类"""
    
    def __init__(self, config: dict):
        self.config = config
    
    def sync_project(self, project_info: dict) -> str:
        """同步项目信息到ERP"""
        raise NotImplementedError
    
    def sync_quantity(self, quantity_data: dict) -> bool:
        """同步工程量到ERP"""
        raise NotImplementedError
    
    def get_bom(self, project_id: str) -> list:
        """获取物料清单"""
        raise NotImplementedError


class YonyouAdapter(ERPAdapter):
    """用友ERP对接适配器"""
    
    def sync_project(self, project_info: dict) -> str:
        # 调用用友API同步项目
        pass
    
    def sync_quantity(self, quantity_data: dict) -> bool:
        # 调用用友API同步工程量
        pass


class KingdeeAdapter(ERPAdapter):
    """金蝶ERP对接适配器"""
    
    def sync_project(self, project_info: dict) -> str:
        # 调用金蝶API同步项目
        pass
    
    def sync_quantity(self, quantity_data: dict) -> bool:
        # 调用金蝶API同步工程量
        pass
```

### 3.3 消息队列对接

```python
# 消息队列对接

import pika
from typing import Callable

class MessageQueueAdapter:
    """消息队列适配器"""
    
    def __init__(self, config: dict):
        self.config = config
        self.connection = None
        self.channel = None
    
    def connect(self) -> bool:
        credentials = pika.PlainCredentials(
            self.config['username'],
            self.config['password']
        )
        parameters = pika.ConnectionParameters(
            host=self.config['host'],
            port=self.config['port'],
            credentials=credentials
        )
        self.connection = pika.BlockingConnection(parameters)
        self.channel = self.connection.channel()
        return True
    
    def publish(self, queue: str, message: dict) -> bool:
        """发送消息"""
        self.channel.queue_declare(queue=queue, durable=True)
        self.channel.basic_publish(
            exchange='',
            routing_key=queue,
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=2  # 持久化
            )
        )
        return True
    
    def subscribe(self, queue: str, callback: Callable) -> None:
        """订阅消息"""
        self.channel.queue_declare(queue=queue, durable=True)
        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(
            queue=queue,
            on_message_callback=callback
        )
        self.channel.start_consuming()


# 使用示例
def task_callback(ch, method, properties, body):
    message = json.loads(body)
    task_id = message['task_id']
    
    # 处理任务
    result = process_task(task_id)
    
    # 发送结果
    publish_result(task_id, result)
    
    ch.basic_ack(delivery_tag=method.delivery_tag)
```

---

## 4. 数据格式对接

### 4.1 输入数据格式

```python
# 支持的输入格式

INPUT_FORMATS = {
    'dxf': {
        'description': 'AutoCAD DXF格式',
        'extensions': ['.dxf'],
        'parser': 'DXFParser',
        'max_size': '50MB'
    },
    'dwg': {
        'description': 'AutoCAD DWG格式',
        'extensions': ['.dwg'],
        'parser': 'DWGParser',
        'max_size': '100MB',
        'requires_conversion': True  # 需要转换为DXF
    },
    'pdf_vector': {
        'description': '矢量PDF',
        'extensions': ['.pdf'],
        'parser': 'PDFParser',
        'max_size': '100MB'
    },
    'pdf_image': {
        'description': '扫描版PDF',
        'extensions': ['.pdf'],
        'parser': 'ImageParser',
        'max_size': '50MB'
    },
    'image': {
        'description': '图片格式',
        'extensions': ['.jpg', '.jpeg', '.png', '.bmp', '.tiff'],
        'parser': 'ImageParser',
        'max_size': '30MB'
    }
}
```

### 4.2 输出数据格式

```python
# 支持的输出格式

OUTPUT_FORMATS = {
    'excel': {
        'description': 'Excel清单',
        'extensions': ['.xlsx'],
        'mime_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'template': 'standard'
    },
    'csv': {
        'description': 'CSV清单',
        'extensions': ['.csv'],
        'mime_type': 'text/csv',
        'encoding': 'utf-8-sig'
    },
    'json': {
        'description': 'JSON数据',
        'extensions': ['.json'],
        'mime_type': 'application/json',
        'pretty': True
    },
    'ifc': {
        'description': 'IFC BIM模型',
        'extensions': ['.ifc'],
        'mime_type': 'application/octet-stream',
        'version': 'IFC4'
    },
    'gbxml': {
        'description': 'Green Building XML',
        'extensions': ['.xml'],
        'mime_type': 'application/xml'
    }
}
```

### 4.3 数据转换示例

```python
# 数据格式转换

class DataConverter:
    """数据格式转换器"""
    
    @staticmethod
    def drawing_to_ifc(drawing_data: DrawingData) -> str:
        """DrawingData 转 IFC"""
        generator = BIMGenerator()
        components = generator.generate_from_drawing(
            drawing_data.devices,
            drawing_data.cables
        )
        exporter = IFCExporter()
        return exporter.export(components, '/tmp/output.ifc')
    
    @staticmethod
    def calculation_to_excel(calculation: CalculationResult, output_path: str) -> str:
        """CalculationResult 转 Excel"""
        generator = SummaryGenerator()
        summary = generator.generate(calculation)
        exporter = ExcelExporter()
        return exporter.export(summary, output_path)
    
    @staticmethod
    def to_json(data: BaseModel) -> str:
        """Pydantic模型转JSON"""
        return data.model_dump_json(indent=2)
    
    @staticmethod
    def from_json(json_str: str, model_class: type) -> BaseModel:
        """JSON转Pydantic模型"""
        return model_class.model_validate_json(json_str)
```

---

## 5. 接口协议对接

### 5.1 HTTP接口对接

```python
# HTTP客户端封装

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class HTTPClient:
    """HTTP客户端封装"""
    
    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url
        self.session = requests.Session()
        
        # 配置重试策略
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def post(self, endpoint: str, data: dict, headers: dict = None) -> dict:
        """POST请求"""
        url = f"{self.base_url}{endpoint}"
        response = self.session.post(
            url,
            json=data,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    
    def get(self, endpoint: str, params: dict = None, headers: dict = None) -> dict:
        """GET请求"""
        url = f"{self.base_url}{endpoint}"
        response = self.session.get(
            url,
            params=params,
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    
    def upload_file(self, endpoint: str, file_path: str, metadata: dict = None) -> dict:
        """文件上传"""
        url = f"{self.base_url}{endpoint}"
        
        with open(file_path, 'rb') as f:
            files = {'file': f}
            data = metadata or {}
            response = self.session.post(url, files=files, data=data)
        
        response.raise_for_status()
        return response.json()
```

### 5.2 WebSocket对接

```python
# WebSocket客户端封装

import websocket
import json
import threading

class WebSocketClient:
    """WebSocket客户端封装"""
    
    def __init__(self, url: str, token: str):
        self.url = url
        self.token = token
        self.ws = None
        self.callbacks = {}
        self.running = False
    
    def connect(self) -> bool:
        """建立连接"""
        headers = [f"Authorization: Bearer {self.token}"]
        self.ws = websocket.WebSocketApp(
            self.url,
            header=headers,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
            on_open=self._on_open
        )
        self.running = True
        thread = threading.Thread(target=self.ws.run_forever)
        thread.daemon = True
        thread.start()
        return True
    
    def disconnect(self) -> None:
        """断开连接"""
        self.running = False
        if self.ws:
            self.ws.close()
    
    def subscribe(self, event_type: str, callback: Callable) -> None:
        """订阅事件"""
        self.callbacks[event_type] = callback
        self.send({
            'type': 'subscribe',
            'event': event_type
        })
    
    def send(self, message: dict) -> None:
        """发送消息"""
        if self.ws and self.running:
            self.ws.send(json.dumps(message))
    
    def _on_message(self, ws, message) -> None:
        """消息处理"""
        data = json.loads(message)
        event_type = data.get('type')
        callback = self.callbacks.get(event_type)
        if callback:
            callback(data)
    
    def _on_error(self, ws, error) -> None:
        """错误处理"""
        print(f"WebSocket error: {error}")
    
    def _on_close(self, ws, close_status_code, close_msg) -> None:
        """连接关闭"""
        self.running = False
        print(f"WebSocket closed: {close_status_code}")
    
    def _on_open(self, ws) -> None:
        """连接建立"""
        print("WebSocket opened")
```

---

## 6. 安全对接

### 6.1 认证对接

```python
# 认证管理器

class AuthManager:
    """认证管理器"""
    
    def __init__(self, config: dict):
        self.config = config
        self.token = None
        self.refresh_token = None
    
    def authenticate(self, credentials: dict) -> str:
        """用户认证"""
        response = requests.post(
            f"{self.config['auth_url']}/login",
            json=credentials
        )
        data = response.json()
        self.token = data['access_token']
        self.refresh_token = data['refresh_token']
        return self.token
    
    def refresh(self) -> str:
        """刷新Token"""
        response = requests.post(
            f"{self.config['auth_url']}/refresh",
            json={'refresh_token': self.refresh_token}
        )
        data = response.json()
        self.token = data['access_token']
        return self.token
    
    def get_headers(self) -> dict:
        """获取认证头"""
        return {
            'Authorization': f'Bearer {self.token}'
        }
```

### 6.2 加密传输

```python
# 加密传输

from cryptography.fernet import Fernet
import base64

class EncryptionHandler:
    """加密处理器"""
    
    def __init__(self, key: str):
        # key需要是32位的base64编码
        self.cipher = Fernet(base64.urlsafe_b64encode(key.encode()[:32]))
    
    def encrypt(self, data: bytes) -> bytes:
        """加密数据"""
        return self.cipher.encrypt(data)
    
    def decrypt(self, encrypted_data: bytes) -> bytes:
        """解密数据"""
        return self.cipher.decrypt(encrypted_data)
    
    def encrypt_file(self, input_path: str, output_path: str) -> None:
        """加密文件"""
        with open(input_path, 'rb') as f:
            data = f.read()
        encrypted = self.encrypt(data)
        with open(output_path, 'wb') as f:
            f.write(encrypted)
```

---

## 附录

### A. 对接检查清单

```markdown
## 对接前检查清单

### 基础检查
- [ ] API文档已获取
- [ ] 测试环境已搭建
- [ ] 认证方式已确认
- [ ] 接口限流已了解

### 数据检查
- [ ] 数据格式已确认
- [ ] 字段映射已定义
- [ ] 数据校验规则已了解
- [ ] 异常数据处理方案已制定

### 安全检查
- [ ] 认证流程已测试
- [ ] 权限配置已确认
- [ ] 敏感数据加密方案已确定
- [ ] HTTPS配置已验证

### 集成检查
- [ ] 单元测试通过
- [ ] 集成测试通过
- [ ] 性能测试通过
- [ ] 错误处理验证通过
```

### B. 常见对接问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 连接超时 | 网络问题、防火墙 | 检查网络配置、开放端口 |
| 认证失败 | Token过期、权限不足 | 刷新Token、检查权限 |
| 数据格式错误 | 编码问题、字段不匹配 | 统一编码、修正映射 |
| 限流触发 | 请求过于频繁 | 实现请求间隔控制 |
| 数据丢失 | 网络中断、缓冲区满 | 实现重试机制、增加缓冲区 |
