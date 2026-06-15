# API 接口规范文档

## 目录

1. [接口概述](#1-接口概述)
2. [数据模型定义](#2-数据模型定义)
3. [RESTful API](#3-restful-api)
4. [WebSocket API](#4-websocket-api)
5. [错误码定义](#5-错误码定义)
6. [认证授权](#6-认证授权)

---

## 1. 接口概述

### 1.1 基本信息

- **API版本**: v1
- **基础URL**: `http://{host}:{port}/api/v1`
- **Content-Type**: `application/json`
- **字符编码**: UTF-8

### 1.2 请求格式

```http
POST /api/v1/calculate HTTP/1.1
Host: localhost:8080
Content-Type: application/json
Authorization: Bearer {token}
X-Request-ID: {uuid}
X-Correlation-ID: {uuid}

{
    "input_files": ["/path/to/drawing.dxf"],
    "output_path": "./outputs",
    "rule_version": "latest",
    "enable_audit": true,
    "enable_modeling": true
}
```

### 1.3 响应格式

```json
{
    "success": true,
    "code": 200,
    "message": "操作成功",
    "data": {
        "task_id": "uuid",
        "status": "completed",
        "result": {}
    },
    "timestamp": "2024-01-01T00:00:00Z",
    "request_id": "uuid"
}
```

---

## 2. 数据模型定义

### 2.1 任务配置

```json
// TaskConfig
{
    "task_name": "string",           // 任务名称
    "input_files": ["string"],       // 输入文件列表
    "output_path": "string",          // 输出路径
    "rule_version": "string",        // 规则版本
    "enable_audit": boolean,          // 启用AI审核
    "enable_modeling": boolean,       // 启用BIM建模
    "parameters": {
        "project_name": "string",
        "project_code": "string",
        "custom_key": "any"
    }
}
```

### 2.2 任务结果

```json
// TaskResult
{
    "task_id": "string",
    "task_name": "string",
    "status": "pending|running|completed|failed",
    "drawing_data": {
        "id": "string",
        "filename": "string",
        "file_type": "string",
        "devices": [...],
        "cables": [...]
    },
    "calculation_result": {
        "id": "string",
        "drawing_id": "string",
        "devices": [...],
        "cables": [...],
        "trunkings": [...],
        "pipes": [...],
        "accessories": [...],
        "total_cost": 0.0
    },
    "bim_components": [...],
    "audit_result": {
        "id": "string",
        "passed": boolean,
        "audit_score": 0.0,
        "issues": [...]
    },
    "list_summary": {
        "id": "string",
        "items": [...],
        "total_quantity": 0.0,
        "total_cost": 0.0
    },
    "output_files": ["string"],
    "error_message": "string",
    "started_at": "datetime",
    "completed_at": "datetime"
}
```

### 2.3 设备模型

```json
// DeviceModel
{
    "id": "string",
    "component_id": "string",
    "name": "string",
    "type": "cabinet|equipment|distribution_box|switch|socket|lighting|other",
    "spec": "string",
    "coordinates": {
        "x": 0.0,
        "y": 0.0,
        "z": 0.0
    },
    "quantity": 1,
    "layer": "string",
    "block_name": "string",
    "attributes": {}
}
```

### 2.4 线缆模型

```json
// CableModel
{
    "id": "string",
    "component_id": "string",
    "model": "string",
    "type": "power|control|signal|communication|other",
    "start_point": {"x": 0.0, "y": 0.0, "z": 0.0},
    "end_point": {"x": 0.0, "y": 0.0, "z": 0.0},
    "length": 0.0,
    "reserved_length": 0.0,
    "total_length": 0.0,
    "laying_method": "trunking|pipe|direct_burial|cable_tray|wall|ceiling",
    "core_count": 1,
    "cross_section": 1.0
}
```

### 2.5 审核问题

```json
// AuditIssue
{
    "id": "string",
    "type": "missing_device|wrong_device|missing_cable|wrong_cable_length|...",
    "severity": "low|medium|high|critical",
    "description": "string",
    "location": {"x": 0.0, "y": 0.0, "z": 0.0},
    "suggestion": "string",
    "related_component_id": "string",
    "related_quantity_id": "string"
}
```

---

## 3. RESTful API

### 3.1 任务管理

#### 创建任务

```http
POST /api/v1/tasks
```

**请求体**:
```json
{
    "task_name": "电气算量任务",
    "input_files": ["/data/drawing.dxf"],
    "output_path": "./outputs",
    "rule_version": "latest",
    "enable_audit": true,
    "enable_modeling": true
}
```

**响应**:
```json
{
    "success": true,
    "code": 201,
    "data": {
        "task_id": "550e8400-e29b-41d4-a716-446655440000"
    }
}
```

#### 查询任务状态

```http
GET /api/v1/tasks/{task_id}
```

**响应**:
```json
{
    "success": true,
    "code": 200,
    "data": {
        "task_id": "550e8400-e29b-41d4-a716-446655440000",
        "status": "running",
        "progress": 0.6,
        "current_step": "AI审核",
        "started_at": "2024-01-01T10:00:00Z"
    }
}
```

#### 获取任务结果

```http
GET /api/v1/tasks/{task_id}/result
```

**响应**:
```json
{
    "success": true,
    "code": 200,
    "data": {
        "calculation_result": {...},
        "list_summary": {...},
        "output_files": [
            "./outputs/工程量清单.xlsx",
            "./outputs/model.ifc"
        ]
    }
}
```

#### 取消任务

```http
DELETE /api/v1/tasks/{task_id}
```

### 3.2 图纸解析

#### 解析图纸

```http
POST /api/v1/parse
Content-Type: multipart/form-data

file: (binary)
```

**响应**:
```json
{
    "success": true,
    "code": 200,
    "data": {
        "id": "uuid",
        "filename": "drawing.dxf",
        "file_type": "dxf",
        "devices": [...],
        "cables": [...],
        "layers": [...],
        "blocks": [...]
    }
}
```

### 3.3 算量计算

#### 执行算量

```http
POST /api/v1/calculate
```

**请求体**:
```json
{
    "drawing_data_id": "uuid",
    "rule_version": "latest"
}
```

**响应**:
```json
{
    "success": true,
    "code": 200,
    "data": {
        "id": "uuid",
        "devices": [...],
        "cables": [...],
        "total_cost": 125000.00
    }
}
```

### 3.4 清单导出

#### 导出Excel

```http
POST /api/v1/export/excel
```

**请求体**:
```json
{
    "list_summary_id": "uuid",
    "template": "standard",
    "include_charts": true
}
```

**响应**:
```http
HTTP/1.1 200 OK
Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
Content-Disposition: attachment; filename="工程量清单.xlsx"

(binary data)
```

### 3.5 规则管理

#### 获取规则列表

```http
GET /api/v1/rules
```

**响应**:
```json
{
    "success": true,
    "code": 200,
    "data": {
        "versions": ["1.0", "1.1", "latest"],
        "current_version": "1.0"
    }
}
```

#### 验证规则

```http
POST /api/v1/rules/validate
```

**请求体**:
```json
{
    "rule_version": "1.0"
}
```

---

## 4. WebSocket API

### 4.1 连接

```javascript
// 建立WebSocket连接
const ws = new WebSocket('ws://localhost:8080/api/v1/ws?token={jwt_token}');

// 连接成功
ws.onopen = () => {
    console.log('WebSocket connected');
    
    // 订阅任务进度
    ws.send(JSON.stringify({
        type: 'subscribe',
        task_id: 'uuid'
    }));
};

// 接收消息
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    switch (data.type) {
        case 'progress':
            updateProgress(data.progress);
            break;
        case 'step_complete':
            showStepComplete(data.step);
            break;
        case 'error':
            showError(data.error);
            break;
        case 'complete':
            showComplete(data.result);
            break;
    }
};
```

### 4.2 消息格式

```json
// 进度更新
{
    "type": "progress",
    "task_id": "uuid",
    "progress": 0.5,
    "current_step": "电气算量",
    "message": "正在计算设备数量..."
}

// 步骤完成
{
    "type": "step_complete",
    "task_id": "uuid",
    "step": "图纸解析",
    "duration": 2.5,
    "result": {}
}

// 错误通知
{
    "type": "error",
    "task_id": "uuid",
    "step": "电气算量",
    "error_code": 1002,
    "message": "规则库加载失败"
}

// 任务完成
{
    "type": "complete",
    "task_id": "uuid",
    "status": "completed",
    "output_files": [...]
}
```

---

## 5. 错误码定义

### 5.1 业务错误码

| 错误码 | 名称 | 说明 |
|--------|------|------|
| 1001 | PARSE_ERROR | 图纸解析失败 |
| 1002 | CALCULATION_ERROR | 算量计算失败 |
| 1003 | VALIDATION_ERROR | 数据验证失败 |
| 1004 | MODEL_ERROR | 模型生成失败 |
| 1005 | EXPORT_ERROR | 导出失败 |
| 1006 | AUDIT_ERROR | 审核失败 |
| 1007 | RULE_ERROR | 规则执行失败 |

### 5.2 系统错误码

| 错误码 | 名称 | 说明 |
|--------|------|------|
| 2001 | CONFIG_ERROR | 配置错误 |
| 2002 | FILE_NOT_FOUND | 文件不存在 |
| 2003 | PERMISSION_DENIED | 权限不足 |
| 2004 | STORAGE_ERROR | 存储错误 |
| 2005 | NETWORK_ERROR | 网络错误 |

### 5.3 HTTP状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 201 | 已创建 |
| 400 | 请求参数错误 |
| 401 | 未认证 |
| 403 | 禁止访问 |
| 404 | 资源不存在 |
| 409 | 资源冲突 |
| 500 | 服务器内部错误 |
| 503 | 服务不可用 |

### 5.4 错误响应格式

```json
{
    "success": false,
    "code": 1001,
    "message": "图纸解析失败",
    "errors": [
        {
            "field": "file",
            "message": "不支持的文件格式"
        }
    ],
    "timestamp": "2024-01-01T00:00:00Z",
    "request_id": "uuid",
    "trace_id": "uuid"
}
```

---

## 6. 认证授权

### 6.1 JWT认证

```http
POST /api/v1/auth/login
Content-Type: application/json

{
    "username": "user",
    "password": "password"
}
```

**响应**:
```json
{
    "success": true,
    "data": {
        "access_token": "eyJhbGciOiJIUzI1NiIs...",
        "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
        "expires_in": 3600
    }
}
```

### 6.2 API Key认证

```http
GET /api/v1/tasks
X-API-Key: your_api_key_here
```

### 6.3 OAuth2认证

```http
GET /api/v1/oauth/authorize?client_id=xxx&redirect_uri=xxx&response_type=code
```

### 6.4 权限定义

```json
{
    "roles": {
        "admin": {
            "permissions": ["*"]
        },
        "user": {
            "permissions": [
                "task:create",
                "task:read",
                "task:cancel",
                "parse:execute",
                "calculate:execute",
                "export:execute"
            ]
        },
        "guest": {
            "permissions": [
                "task:read",
                "parse:execute"
            ]
        }
    }
}
```

---

## 附录

### A. 接口调用示例

```python
import requests
import json

class MechElecAPIClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.headers = {
            "Content-Type": "application/json",
            "X-API-Key": api_key
        }
    
    def create_task(self, input_file: str) -> dict:
        response = requests.post(
            f"{self.base_url}/api/v1/tasks",
            headers=self.headers,
            json={
                "input_files": [input_file],
                "enable_audit": True
            }
        )
        return response.json()
    
    def get_task_result(self, task_id: str) -> dict:
        response = requests.get(
            f"{self.base_url}/api/v1/tasks/{task_id}/result",
            headers=self.headers
        )
        return response.json()
    
    def download_file(self, file_path: str) -> bytes:
        response = requests.get(
            f"{self.base_url}/api/v1/files/{file_path}",
            headers=self.headers
        )
        return response.content
```

### B. 速率限制

| 端点 | 限制 | 窗口 |
|------|------|------|
| /api/v1/tasks | 100请求 | 1分钟 |
| /api/v1/parse | 50请求 | 1分钟 |
| /api/v1/export | 20请求 | 1分钟 |

### C. 超时设置

| 操作 | 超时 |
|------|------|
| 图纸解析 | 120秒 |
| 算量计算 | 300秒 |
| AI审核 | 180秒 |
| 文件导出 | 60秒 |
