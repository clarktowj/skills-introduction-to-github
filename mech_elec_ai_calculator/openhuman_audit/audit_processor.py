"""
审核结果处理器
负责将审核结果应用到工程量清单，实现自动修正
"""
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from .audit_client import AuditResult, AuditItem


class AuditProcessor:
    """
    审核结果处理器

    功能：
    1. 解析审核结果
    2. 自动修正清单
    3. 生成修正报告
    """

    def __init__(self, confidence_threshold: float = 0.5):
        """
        Args:
            confidence_threshold: 置信度阈值，只有高于此值的修正才会自动应用
        """
        self._confidence_threshold = confidence_threshold

    def process(
        self,
        audit_result: AuditResult,
        original_list: List[Dict[str, Any]]
    ) -> 'ProcessedResult':
        """
        处理审核结果

        Args:
            audit_result: 审核结果
            original_list: 原始工程量清单

        Returns:
            ProcessedResult: 处理后的结果
        """
        additions = []  # 需要添加的项
        modifications = []  # 需要修改的项
        manual_review = []  # 需要人工复核的项

        # 过滤高置信度的修正
        for item in audit_result.corrections:
            if item.confidence >= self._confidence_threshold:
                if item.item_type == 'missing':
                    additions.append(item)
                elif item.item_type == 'error':
                    modifications.append(item)
            else:
                manual_review.append(item)

        # 添加警告项到人工复核
        for item in audit_result.warnings:
            if item.confidence >= 0.7:
                manual_review.append(item)

        return ProcessedResult(
            original_list=original_list,
            additions=additions,
            modifications=modifications,
            manual_review=manual_review,
            suggestions=audit_result.suggestions,
            summary=audit_result.summary,
            confidence_score=audit_result.confidence_score
        )

    def apply_corrections(
        self,
        processed_result: 'ProcessedResult',
        original_list: List[Dict[str, Any]],
        auto_apply: bool = True
    ) -> List[Dict[str, Any]]:
        """
        应用修正到清单

        Args:
            processed_result: 处理后的结果
            original_list: 原始清单
            auto_apply: 是否自动应用修正

        Returns:
            修正后的清单
        """

        # 复制原始清单
        result_list = [dict(item) for item in original_list]

        # 获取已存在的名称集合
        existing_names = {item.get('name', '') for item in result_list}

        # 1. 应用添加
        if auto_apply:
            for addition in processed_result.additions:
                name = addition.suggested_name or addition.original_name

                # 检查是否已存在
                if name in existing_names:
                    # 合并数量
                    for item in result_list:
                        if item.get('name') == name:
                            item['quantity'] = item.get('quantity', 0) + (addition.suggested_quantity or 0)
                            item['description'] = item.get('description', '') + f"\n[AUDIT] {addition.reason}"
                            break
                else:
                    # 添加新项
                    result_list.append({
                        'name': name,
                        'quantity': addition.suggested_quantity or 1,
                        'unit': addition.suggested_unit or '个',
                        'category': self._map_category(addition.category),
                        'code': self._generate_code(addition.category),
                        'unit_price': 0,  # 将在后续填充
                        'description': f"[AUDIT] {addition.reason}",
                        'audit_confidence': addition.confidence
                    })
                    existing_names.add(name)

        # 2. 应用修改
        if auto_apply:
            for modification in processed_result.modifications:
                original_name = modification.original_name
                suggested_name = modification.suggested_name

                # 查找并修改
                for item in result_list:
                    if item.get('name') == original_name:
                        if suggested_name and suggested_name != original_name:
                            item['name'] = suggested_name
                        if modification.suggested_quantity:
                            item['quantity'] = modification.suggested_quantity
                        item['description'] = item.get('description', '') + f"\n[AUDIT] {modification.reason}"
                        item['audit_confidence'] = modification.confidence
                        break

        return result_list

    def _map_category(self, audit_category: str) -> str:
        """映射审核类别到清单类别"""
        mapping = {
            'device': '设备',
            'cable': '线缆',
            'trunking': '桥架',
            'pipe': '配管',
            'accessory': '辅材',
            'quantity': '设备',
            'classification': '设备',
            'consistency': '其他',
            'other': '其他'
        }
        return mapping.get(audit_category, '其他')

    def _generate_code(self, category: str) -> str:
        """生成定额编号"""
        codes = {
            'device': 'DL001',
            'cable': 'DL101',
            'trunking': 'DL201',
            'pipe': 'DL301',
            'accessory': 'DL401',
            'other': 'DL999'
        }
        return codes.get(category, 'DL999')

    def generate_report(
        self,
        processed_result: 'ProcessedResult',
        include_manual_review: bool = True
    ) -> str:
        """生成修正报告"""

        lines = []
        lines.append("=" * 80)
        lines.append("工程量清单审核报告")
        lines.append("=" * 80)
        lines.append("")

        # 摘要
        lines.append(f"审核置信度: {processed_result.confidence_score:.1%}")
        lines.append(f"摘要: {processed_result.summary}")
        lines.append("")

        # 自动应用项
        if processed_result.additions:
            lines.append("-" * 80)
            lines.append(f"【自动添加】{len(processed_result.additions)} 项")
            lines.append("-" * 80)
            for item in processed_result.additions:
                lines.append(f"  + {item.suggested_name} x {item.suggested_quantity} {item.suggested_unit or '个'}")
                lines.append(f"    原因: {item.reason}")
                lines.append(f"    置信度: {item.confidence:.1%}")
                lines.append("")

        if processed_result.modifications:
            lines.append("-" * 80)
            lines.append(f"【自动修正】{len(processed_result.modifications)} 项")
            lines.append("-" * 80)
            for item in processed_result.modifications:
                lines.append(f"  ~ {item.original_name} -> {item.suggested_name or item.original_name}")
                if item.suggested_quantity:
                    lines.append(f"    数量: {item.original_quantity} -> {item.suggested_quantity}")
                lines.append(f"    原因: {item.reason}")
                lines.append("")

        # 人工复核项
        if include_manual_review and processed_result.manual_review:
            lines.append("-" * 80)
            lines.append(f"【人工复核】{len(processed_result.manual_review)} 项")
            lines.append("-" * 80)
            for item in processed_result.manual_review:
                lines.append(f"  ? {item.original_name or item.suggested_name}")
                lines.append(f"    类型: {item.item_type} | 类别: {item.category}")
                lines.append(f"    原因: {item.reason}")
                lines.append(f"    置信度: {item.confidence:.1%}")
                lines.append(f"    建议: {item.suggestion}")
                lines.append("")

        # 建议
        if processed_result.suggestions:
            lines.append("-" * 80)
            lines.append("【优化建议】")
            lines.append("-" * 80)
            for i, suggestion in enumerate(processed_result.suggestions, 1):
                lines.append(f"  {i}. {suggestion}")
            lines.append("")

        lines.append("=" * 80)

        return "\n".join(lines)


@dataclass
class ProcessedResult:
    """处理后的结果"""
    original_list: List[Dict[str, Any]]
    additions: List[AuditItem]
    modifications: List[AuditItem]
    manual_review: List[AuditItem]
    suggestions: List[str]
    summary: str
    confidence_score: float

    def has_auto_changes(self) -> bool:
        """是否有自动应用的变更"""
        return len(self.additions) > 0 or len(self.modifications) > 0

    def get_change_count(self) -> int:
        """获取变更总数"""
        return len(self.additions) + len(self.modifications)
