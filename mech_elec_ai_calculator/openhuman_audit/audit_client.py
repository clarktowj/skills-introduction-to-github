"""
OpenHuman AI 审核客户端
支持多种AI服务：OpenAI GPT、Claude、本地规则引擎fallback
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import json
import logging
from framework.exceptions import ValidationError

logger = logging.getLogger(__name__)


class AIServiceType(Enum):
    """支持的AI服务类型"""
    OPENAI = "openai"
    CLAUDE = "claude"
    LOCAL_RULES = "local_rules"  # 本地规则引擎作为fallback


@dataclass
class AuditItem:
    """审核项"""
    item_type: str  # 'missing', 'error', 'warning', 'suggestion'
    category: str  # 'device', 'cable', 'trunking', 'quantity', 'classification'
    original_name: str
    suggested_name: Optional[str] = None
    original_quantity: Optional[float] = None
    suggested_quantity: Optional[float] = None
    original_unit: Optional[str] = None
    suggested_unit: Optional[str] = None
    reason: str = ""
    confidence: float = 0.0
    suggestion: str = ""
    position_hint: str = ""  # 位置提示

    def to_dict(self) -> Dict[str, Any]:
        return {
            'item_type': self.item_type,
            'category': self.category,
            'original_name': self.original_name,
            'suggested_name': self.suggested_name,
            'original_quantity': self.original_quantity,
            'suggested_quantity': self.suggested_quantity,
            'reason': self.reason,
            'confidence': self.confidence,
            'suggestion': self.suggestion
        }


@dataclass
class AuditResult:
    """审核结果"""
    has_issues: bool = False
    needs_correction: bool = False
    corrections: List[AuditItem] = field(default_factory=list)
    warnings: List[AuditItem] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    summary: str = ""
    confidence_score: float = 0.0
    missing_items: List[str] = field(default_factory=list)
    error_items: List[str] = field(default_factory=list)
    raw_response: Optional[str] = None
    service_used: str = ""
    processing_time: float = 0.0
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'has_issues': self.has_issues,
            'needs_correction': self.needs_correction,
            'corrections': [c.to_dict() for c in self.corrections],
            'warnings': [w.to_dict() for w in self.warnings],
            'suggestions': self.suggestions,
            'summary': self.summary,
            'confidence_score': self.confidence_score,
            'missing_items': self.missing_items,
            'error_items': self.error_items,
            'service_used': self.service_used
        }

    def get_additions(self) -> List[Dict[str, Any]]:
        """获取需要添加的项"""
        additions = []
        for item in self.corrections:
            if item.item_type == 'missing':
                additions.append({
                    'name': item.suggested_name or item.original_name,
                    'quantity': item.suggested_quantity or 1,
                    'unit': item.suggested_unit or '个',
                    'category': item.category,
                    'reason': item.reason
                })
        return additions

    def get_modifications(self) -> List[Dict[str, Any]]:
        """获取需要修改的项"""
        modifications = []
        for item in self.corrections:
            if item.item_type == 'error':
                modifications.append({
                    'original_name': item.original_name,
                    'suggested_name': item.suggested_name,
                    'original_quantity': item.original_quantity,
                    'suggested_quantity': item.suggested_quantity,
                    'reason': item.reason
                })
        return modifications


class OpenHumanClient:
    """
    OpenHuman AI 审核客户端

    支持多种AI服务，按优先级尝试：
    1. OpenAI GPT-4
    2. Anthropic Claude
    3. 本地规则引擎 (fallback)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self._config = config or {}
        self._service_type = self._config.get('service_type', 'local_rules')
        self._api_key = self._config.get('api_key', '')
        self._api_base = self._config.get('api_base', 'https://api.openai.com/v1')
        self._model = self._config.get('model', 'gpt-4')
        self._temperature = self._config.get('temperature', 0.1)
        self._timeout = self._config.get('timeout', 60)
        self._max_tokens = self._config.get('max_tokens', 4000)
        self._local_rules_enabled = self._config.get('local_rules_enabled', True)

        self._local_auditor = None
        if self._local_rules_enabled:
            from .local_auditor import LocalAuditor
            self._local_auditor = LocalAuditor()

    @property
    def service_type(self) -> AIServiceType:
        return AIServiceType(self._service_type)

    def audit(
        self,
        drawing_info: Dict[str, Any],
        quantity_list: List[Dict[str, Any]],
        rules_summary: Optional[Dict[str, Any]] = None,
        enable_local_fallback: bool = True
    ) -> AuditResult:
        """
        执行AI审核

        Args:
            drawing_info: 图纸信息 (设备、线缆、图层等)
            quantity_list: 初版工程量清单
            rules_summary: 规则摘要 (用于AI参考)
            enable_local_fallback: 是否启用本地规则引擎作为fallback

        Returns:
            AuditResult: 审核结果
        """
        import time
        start_time = time.time()

        result = AuditResult()

        try:
            # 根据服务类型选择审核方式
            if self._service_type == 'local_rules':
                result = self._audit_with_local_rules(drawing_info, quantity_list, rules_summary)
                result.service_used = 'local_rules'
            elif self._service_type == 'openai':
                result = self._audit_with_openai(drawing_info, quantity_list, rules_summary)
                result.service_used = f'openai/{self._model}'
            elif self._service_type == 'claude':
                result = self._audit_with_claude(drawing_info, quantity_list, rules_summary)
                result.service_used = f'claude/{self._model}'
            else:
                raise ValidationError(f"Unsupported service type: {self._service_type}")

        except Exception as e:
            logger.error(f"AI audit failed: {str(e)}")

            # 如果启用了本地fallback且当前不是本地规则
            if enable_local_fallback and self._service_type != 'local_rules' and self._local_auditor:
                logger.info("Falling back to local rules engine...")
                result = self._audit_with_local_rules(drawing_info, quantity_list, rules_summary)
                result.service_used = 'local_rules_fallback'
                result.error_message = str(e)
            else:
                result.error_message = str(e)
                result.summary = f"审核失败: {str(e)}"

        result.processing_time = time.time() - start_time
        return result

    def _audit_with_local_rules(
        self,
        drawing_info: Dict[str, Any],
        quantity_list: List[Dict[str, Any]],
        rules_summary: Optional[Dict[str, Any]] = None
    ) -> AuditResult:
        """使用本地规则引擎审核"""
        if not self._local_auditor:
            from .local_auditor import LocalAuditor
            self._local_auditor = LocalAuditor()

        return self._local_auditor.audit(drawing_info, quantity_list, rules_summary)

    def _audit_with_openai(
        self,
        drawing_info: Dict[str, Any],
        quantity_list: List[Dict[str, Any]],
        rules_summary: Optional[Dict[str, Any]] = None
    ) -> AuditResult:
        """使用OpenAI GPT审核"""
        try:
            from openai import OpenAI
            client = OpenAI(
                api_key=self._api_key,
                base_url=self._api_base if self._api_base != 'https://api.openai.com/v1' else None,
                timeout=self._timeout
            )
        except ImportError:
            raise ValidationError("openai package not installed. Run: pip install openai>=1.0.0")

        # 构建prompt
        prompt = self._build_audit_prompt(drawing_info, quantity_list, rules_summary)

        # 调用API
        response = client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "user", "content": prompt}
            ],
            temperature=self._temperature,
            max_tokens=self._max_tokens
        )

        result_text = response.choices[0].message.content
        return self._parse_audit_response(result_text, drawing_info, quantity_list)

    def _audit_with_claude(
        self,
        drawing_info: Dict[str, Any],
        quantity_list: List[Dict[str, Any]],
        rules_summary: Optional[Dict[str, Any]] = None
    ) -> AuditResult:
        """使用Anthropic Claude审核"""
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self._api_key)
        except ImportError:
            raise ValidationError("anthropic package not installed. Run: pip install anthropic")

        # 构建prompt
        prompt = self._build_audit_prompt(drawing_info, quantity_list, rules_summary)

        # 调用API
        response = client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        result_text = response.content[0].text
        return self._parse_audit_response(result_text, drawing_info, quantity_list)

    def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        return """你是一位专业的电气工程量审核专家，擅长审核机电工程的工程量清单。

你的职责是：
1. 检查工程量清单是否有漏项（设备、线缆、桥架等）
2. 检查分类是否正确（配电柜、配电箱、开关等）
3. 检查数量是否合理
4. 对照图纸和规则给出修正建议

请严格按照JSON格式返回审核结果，不要添加任何额外解释。"""

    def _build_audit_prompt(
        self,
        drawing_info: Dict[str, Any],
        quantity_list: List[Dict[str, Any]],
        rules_summary: Optional[Dict[str, Any]] = None
    ) -> str:
        """构建审核prompt"""

        # 提取关键信息
        device_summary = self._summarize_devices(drawing_info)
        cable_summary = self._summarize_cables(drawing_info)
        layer_summary = self._summarize_layers(drawing_info)

        # 格式化清单
        quantity_str = self._format_quantity_list(quantity_list)

        prompt = f"""## 图纸信息摘要

### 识别到的设备
{device_summary}

### 识别到的线缆
{cable_summary}

### 图层信息
{layer_summary}

### 当前工程量清单
{quantity_str}

"""

        if rules_summary:
            rules_str = json.dumps(rules_summary, ensure_ascii=False, indent=2)
            prompt += f"""### 规则摘要
{rules_str}

"""

        prompt += """## 审核要求

请分析上述信息，找出：
1. 漏识别的设备或线缆
2. 分类错误的项
3. 数量异常的项
4. 需要补充的辅材

请以JSON格式返回审核结果：
```json
{
    "has_issues": true/false,
    "needs_correction": true/false,
    "confidence_score": 0.0-1.0,
    "summary": "简要说明",
    "corrections": [
        {
            "item_type": "missing/error/warning",
            "category": "device/cable/trunking/quantity/classification",
            "original_name": "原始名称",
            "suggested_name": "建议名称（如有）",
            "original_quantity": 数量（如有）,
            "suggested_quantity": 建议数量（如有）,
            "reason": "原因说明",
            "confidence": 0.0-1.0,
            "suggestion": "修正建议"
        }
    ],
    "suggestions": ["建议1", "建议2"]
}
```"""

        return prompt

    def _summarize_devices(self, drawing_info: Dict[str, Any]) -> str:
        """汇总设备信息"""
        devices = drawing_info.get('devices', [])
        if not devices:
            return "无设备信息"

        # 按类型分组
        by_type = {}
        for d in devices:
            t = d.get('type', 'unknown')
            if t not in by_type:
                by_type[t] = []
            by_type[t].append(d.get('name', ''))

        lines = []
        for t, names in sorted(by_type.items()):
            lines.append(f"- {t}: {len(names)}个 - {', '.join(names[:5])}")
            if len(names) > 5:
                lines[-1] += f" 等{len(names)}个"

        return '\n'.join(lines) if lines else "无设备"

    def _summarize_cables(self, drawing_info: Dict[str, Any]) -> str:
        """汇总线缆信息"""
        cables = drawing_info.get('cables', [])
        if not cables:
            return "无线缆信息"

        lines = []
        for c in cables:
            model = c.get('model', 'Unknown')
            cable_type = c.get('type', 'power')
            laying = c.get('laying_method', 'cable_tray')
            length = c.get('length', 0)
            lines.append(f"- {model}({cable_type}, {laying}): {length}m")

        return '\n'.join(lines) if lines else "无线缆"

    def _summarize_layers(self, drawing_info: Dict[str, Any]) -> str:
        """汇总图层信息"""
        layers = drawing_info.get('layers', [])
        if not layers:
            return "无图层信息"

        names = [l.get('name', '') for l in layers]
        return ', '.join(names[:20]) + ('...' if len(names) > 20 else '')

    def _format_quantity_list(self, quantity_list: List[Dict[str, Any]]) -> str:
        """格式化清单为文本"""
        if not quantity_list:
            return "清单为空"

        lines = []
        for i, item in enumerate(quantity_list, 1):
            name = item.get('name', 'Unknown')
            quantity = item.get('quantity', 0)
            unit = item.get('unit', '个')
            category = item.get('category', '')
            lines.append(f"{i}. [{category}] {name}: {quantity} {unit}")

        return '\n'.join(lines)

    def _parse_audit_response(
        self,
        response_text: str,
        drawing_info: Dict[str, Any],
        quantity_list: List[Dict[str, Any]]
    ) -> AuditResult:
        """解析AI响应为结构化结果"""
        result = AuditResult(raw_response=response_text)

        try:
            # 提取JSON部分
            json_str = self._extract_json(response_text)
            if json_str:
                data = json.loads(json_str)
                result.has_issues = data.get('has_issues', False)
                result.needs_correction = data.get('needs_correction', False)
                result.confidence_score = data.get('confidence_score', 0.0)
                result.summary = data.get('summary', '')

                # 解析corrections
                for c in data.get('corrections', []):
                    item = AuditItem(
                        item_type=c.get('item_type', 'warning'),
                        category=c.get('category', 'other'),
                        original_name=c.get('original_name', ''),
                        suggested_name=c.get('suggested_name'),
                        original_quantity=c.get('original_quantity'),
                        suggested_quantity=c.get('suggested_quantity'),
                        reason=c.get('reason', ''),
                        confidence=c.get('confidence', 0.5),
                        suggestion=c.get('suggestion', '')
                    )
                    if item.item_type == 'missing':
                        result.corrections.append(item)
                        result.missing_items.append(item.suggested_name or item.original_name)
                    elif item.item_type == 'error':
                        result.corrections.append(item)
                        result.error_items.append(item.original_name)
                    else:
                        result.warnings.append(item)

                result.suggestions = data.get('suggestions', [])

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse AI response as JSON: {e}")
            # 尝试从文本中提取信息
            result.summary = response_text[:500]
            result.error_message = "JSON解析失败，请检查AI返回格式"

        return result

    def _extract_json(self, text: str) -> Optional[str]:
        """从文本中提取JSON部分"""
        # 尝试提取 ```json ... ``` 块
        import re

        # 方法1: 提取代码块
        pattern = r'```(?:json)?\s*([\s\S]*?)```'
        matches = re.findall(pattern, text)
        for match in matches:
            try:
                json.loads(match.strip())
                return match.strip()
            except:
                continue

        # 方法2: 尝试找到第一个 { 到最后一个 }
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1 and end > start:
            candidate = text[start:end+1]
            try:
                json.loads(candidate)
                return candidate
            except:
                pass

        return None


def create_audit_client(service_type: str = 'local_rules', **kwargs) -> OpenHumanClient:
    """工厂函数：创建审核客户端"""
    config = {
        'service_type': service_type,
        **kwargs
    }
    return OpenHumanClient(config)
