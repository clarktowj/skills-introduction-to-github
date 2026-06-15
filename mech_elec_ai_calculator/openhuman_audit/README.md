# OpenHuman AI 审核模块

## 模块职责

本模块负责对接 OpenHuman AI 服务，对本地 DXF 解析和算量结果进行智能审核：

1. **图纸分析** - AI 读取图纸信息，理解电气系统结构
2. **清单校验** - 对比初版清单与图纸实际内容
3. **漏项检测** - 发现本地规则漏识别的设备/线缆
4. **错项修正** - 识别分类错误、数量错误
5. **智能建议** - 提供修正方案和补充说明

## 接入方式

```python
from openhuman_audit import OpenHumanClient, AuditProcessor

# 初始化客户端
client = OpenHumanClient()

# 提交审核
result = client.audit(
    drawing_info=drawing_data,
    quantity_list=quantity_items,
    rules_summary=rules
)

# 处理审核结果
processor = AuditProcessor(confidence_threshold=0.6)
processed = processor.process(result, quantity_list)

# 应用修正
if processed.has_auto_changes():
    corrected = processor.apply_corrections(processed, quantity_list, auto_apply=True)
```

## 支持的 AI 服务

- [x] OpenAI GPT-4 (需配置API Key)
- [x] Anthropic Claude (需配置API Key)
- [x] 本地规则引擎 (已内置，无需配置)
- [x] 其他兼容 API (可扩展)

## 核心组件

| 组件 | 文件 | 说明 |
|------|------|------|
| 审核客户端 | [audit_client.py](audit_client.py) | AI服务接口封装 |
| 本地审核器 | [local_auditor.py](local_auditor.py) | 规则引擎fallback |
| 结果处理器 | [audit_processor.py](audit_processor.py) | 自动修正逻辑 |

## 审核规则 (本地)

- 完整性检查: 设备数量对比
- 合理性检查: 数量/长度阈值
- 一致性检查: 设备-线缆匹配
- 辅材检查: 电缆头、接线端子等
