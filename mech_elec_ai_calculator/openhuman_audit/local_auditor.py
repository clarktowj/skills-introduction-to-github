"""
本地规则审核器
当AI服务不可用时，使用本地规则进行基础审核
"""
from typing import List, Dict, Any, Optional, Set
from .audit_client import AuditResult, AuditItem
from rule_engine.rule_manager import RuleManager


class LocalAuditor:
    """
    本地规则审核器

    基于预定义规则进行清单审核：
    1. 完整性检查 - 是否漏项
    2. 合理性检查 - 数量/长度是否合理
    3. 一致性检查 - 设备与线缆是否匹配
    4. 辅材检查 - 是否缺少必要辅材
    """

    def __init__(self, rule_manager: Optional[RuleManager] = None):
        self._rule_manager = rule_manager or RuleManager()

    def audit(
        self,
        drawing_info: Dict[str, Any],
        quantity_list: List[Dict[str, Any]],
        rules_summary: Optional[Dict[str, Any]] = None
    ) -> AuditResult:
        """
        执行本地规则审核

        Args:
            drawing_info: 图纸信息 (devices, cables, layers等)
            quantity_list: 当前工程量清单
            rules_summary: 规则摘要 (可选)

        Returns:
            AuditResult: 审核结果
        """
        result = AuditResult(service_used='local_rules')

        # 获取图纸中的设备列表
        devices = drawing_info.get('devices', [])
        cables = drawing_info.get('cables', [])
        layers = drawing_info.get('layers', [])

        # 统计清单中的设备
        quantity_by_name = self._group_by_name(quantity_list)
        quantity_by_category = self._group_by_category(quantity_list)

        # 1. 完整性检查
        self._check_completeness(
            result,
            devices,
            cables,
            quantity_by_name,
            quantity_by_category
        )

        # 2. 合理性检查
        self._check_reasonableness(
            result,
            devices,
            cables,
            quantity_list
        )

        # 3. 一致性检查
        self._check_consistency(
            result,
            devices,
            cables,
            quantity_by_category
        )

        # 4. 辅材检查
        self._check_accessories(
            result,
            devices,
            cables,
            quantity_by_category
        )

        # 5. 计算置信度
        result.confidence_score = self._calculate_confidence(result)
        result.has_issues = len(result.corrections) > 0 or len(result.warnings) > 0
        result.needs_correction = len(result.corrections) > 0

        # 生成摘要
        result.summary = self._generate_summary(result)

        return result

    def _group_by_name(self, items: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """按名称分组清单项"""
        groups = {}
        for item in items:
            name = item.get('name', '')
            if name:
                if name not in groups:
                    groups[name] = []
                groups[name].append(item)
        return groups

    def _group_by_category(self, items: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """按类别分组清单项"""
        groups = {}
        for item in items:
            category = item.get('category', 'other')
            if category not in groups:
                groups[category] = []
            groups[category].append(item)
        return groups

    def _check_completeness(
        self,
        result: AuditResult,
        devices: List[Dict],
        cables: List[Dict],
        quantity_by_name: Dict[str, List[Dict]],
        quantity_by_category: Dict[str, List[Dict]]
    ) -> None:
        """检查清单完整性"""

        # 统计图纸中的设备
        device_count = {
            '配电柜': 0,
            '配电箱': 0,
            '开关': 0,
            '插座': 0,
            '照明灯具': 0,
            '电气设备': 0,
            '其他设备': 0
        }

        for device in devices:
            name = device.get('name', '')
            dtype = device.get('type', '')

            # 根据类型或名称判断
            if '柜' in name or dtype == 'cabinet':
                device_count['配电柜'] += 1
            elif '箱' in name or dtype == 'distribution_box':
                device_count['配电箱'] += 1
            elif '开关' in name or dtype == 'switch':
                device_count['开关'] += 1
            elif '插座' in name or dtype == 'socket':
                device_count['插座'] += 1
            elif '灯' in name or dtype == 'lighting':
                device_count['照明灯具'] += 1
            elif '电机' in name or 'M' in name or dtype == 'equipment':
                device_count['电气设备'] += 1
            else:
                device_count['其他设备'] += 1

        # 统计清单中的设备
        list_count = {}
        for category, items in quantity_by_category.items():
            if category == '设备':
                for item in items:
                    name = item.get('name', '')
                    list_count[name] = list_count.get(name, 0) + item.get('quantity', 0)

        # 检查是否漏项
        cabinet_expected = device_count['配电柜']
        cabinet_in_list = list_count.get('配电柜', 0)
        if cabinet_expected > 0 and cabinet_in_list < cabinet_expected * 0.8:
            result.corrections.append(AuditItem(
                item_type='missing',
                category='device',
                original_name='',
                suggested_name='配电柜',
                suggested_quantity=cabinet_expected,
                suggested_unit='个',
                reason=f'图纸中有{cabinet_expected}个配电柜，清单中只有{cabinet_in_list}个',
                confidence=0.8,
                suggestion='补充配电柜数量'
            ))

        # 检查配电箱
        box_expected = device_count['配电箱']
        box_in_list = list_count.get('配电箱', 0)
        if box_expected > 0 and box_in_list < box_expected * 0.8:
            result.corrections.append(AuditItem(
                item_type='missing',
                category='device',
                original_name='',
                suggested_name='配电箱',
                suggested_quantity=box_expected,
                suggested_unit='个',
                reason=f'图纸中有{box_expected}个配电箱，清单中只有{box_in_list}个',
                confidence=0.8,
                suggestion='补充配电箱数量'
            ))

        # 检查开关
        switch_expected = device_count['开关']
        switch_in_list = list_count.get('开关', 0)
        if switch_expected > 0 and switch_in_list < switch_expected * 0.8:
            result.corrections.append(AuditItem(
                item_type='missing',
                category='device',
                original_name='',
                suggested_name='开关',
                suggested_quantity=switch_expected,
                suggested_unit='个',
                reason=f'图纸中有{switch_expected}个开关，清单中只有{switch_in_list}个',
                confidence=0.7,
                suggestion='补充开关数量'
            ))

    def _check_reasonableness(
        self,
        result: AuditResult,
        devices: List[Dict],
        cables: List[Dict],
        quantity_list: List[Dict[str, Any]]
    ) -> None:
        """检查数量合理性"""

        for item in quantity_list:
            name = item.get('name', '')
            quantity = item.get('quantity', 0)
            unit = item.get('unit', '')
            category = item.get('category', '')

            # 设备数量合理性
            if category == '设备' and unit == '个':
                # 设备数量>100 通常不合理
                if quantity > 100:
                    result.warnings.append(AuditItem(
                        item_type='warning',
                        category='quantity',
                        original_name=name,
                        original_quantity=quantity,
                        reason=f'设备"{name}"数量{quantity}较大，请确认',
                        confidence=0.6,
                        suggestion='核实设备数量'
                    ))

                # 单个设备数量<1 不合理
                if quantity < 1:
                    result.corrections.append(AuditItem(
                        item_type='error',
                        category='quantity',
                        original_name=name,
                        original_quantity=quantity,
                        suggested_quantity=max(1, quantity),
                        reason='设备数量不能小于1',
                        confidence=0.9,
                        suggestion='修正设备数量'
                    ))

            # 线缆长度合理性
            if category == '线缆' and unit == '米':
                # 计算图纸中的线缆总长度
                total_cable_in_drawing = sum(c.get('length', 0) for c in cables)

                # 单段线缆>5000m 不合理
                if quantity > 5000:
                    result.warnings.append(AuditItem(
                        item_type='warning',
                        category='quantity',
                        original_name=name,
                        original_quantity=quantity,
                        reason=f'线缆"{name}"长度{quantity}m过大，请确认',
                        confidence=0.5,
                        suggestion='核实线缆长度计算'
                    ))

                # 清单总长度与图纸差异>50%
                if total_cable_in_drawing > 0:
                    ratio = quantity / total_cable_in_drawing
                    if ratio < 0.5 or ratio > 1.5:
                        result.warnings.append(AuditItem(
                            item_type='warning',
                            category='quantity',
                            original_name=name,
                            original_quantity=quantity,
                            reason=f'清单长度({quantity}m)与图纸长度({total_cable_in_drawing:.0f}m)差异较大',
                            confidence=0.7,
                            suggestion='检查线缆长度计算公式'
                        ))

    def _check_consistency(
        self,
        result: AuditResult,
        devices: List[Dict],
        cables: List[Dict],
        quantity_by_category: Dict[str, List[Dict]]
    ) -> None:
        """检查设备与线缆一致性"""

        # 统计设备数量
        device_count = len(devices)
        has_cabinets = any('柜' in d.get('name', '') for d in devices)

        # 统计清单中的线缆
        cable_items = quantity_by_category.get('线缆', [])
        cable_count = len(cable_items)

        # 有设备但无线缆
        if device_count > 5 and cable_count == 0:
            result.warnings.append(AuditItem(
                item_type='warning',
                category='consistency',
                original_name='',
                reason=f'有{device_count}个设备但清单中无线缆',
                confidence=0.8,
                suggestion='检查是否遗漏线缆'
            ))

        # 有主配电柜但无线缆
        if has_cabinets and cable_count == 0:
            result.warnings.append(AuditItem(
                item_type='warning',
                category='consistency',
                original_name='',
                reason='有配电柜但清单中无线缆',
                confidence=0.7,
                suggestion='配电柜通常需要配置进线电缆'
            ))

    def _check_accessories(
        self,
        result: AuditResult,
        devices: List[Dict],
        cables: List[Dict],
        quantity_by_category: Dict[str, List[Dict]]
    ) -> None:
        """检查辅材是否齐全"""

        # 统计主材数量
        cable_items = quantity_by_category.get('线缆', [])
        device_items = quantity_by_category.get('设备', [])
        trunking_items = quantity_by_category.get('桥架', [])

        has_cables = len(cable_items) > 0
        has_devices = len(device_items) > 0
        has_trunking = len(trunking_items) > 0

        # 辅材清单
        accessories = quantity_by_category.get('辅材', [])
        accessory_names = {a.get('name', '') for a in accessories}

        # 有线缆但无电缆头
        if has_cables and '电缆头' not in accessory_names:
            cable_count = len(cable_items)
            result.corrections.append(AuditItem(
                item_type='missing',
                category='accessory',
                original_name='',
                suggested_name='电缆头',
                suggested_quantity=cable_count * 2,  # 每根电缆2个头
                suggested_unit='个',
                reason=f'有{cable_count}组线缆但清单中无电缆头',
                confidence=0.9,
                suggestion='补充电缆头（每根电缆配2个）'
            ))

        # 有设备但无接线端子
        if has_devices and '接线端子' not in accessory_names:
            device_count = sum(d.get('quantity', 1) for d in device_items)
            result.corrections.append(AuditItem(
                item_type='missing',
                category='accessory',
                original_name='',
                suggested_name='接线端子',
                suggested_quantity=device_count * 4,  # 每个设备约4个端子
                suggested_unit='个',
                reason=f'有{device_count}台设备但清单中无接线端子',
                confidence=0.8,
                suggestion='补充接线端子'
            ))

        # 有桥架但无桥架连接件
        if has_trunking and '桥架连接件' not in accessory_names:
            result.warnings.append(AuditItem(
                item_type='warning',
                category='accessory',
                original_name='',
                reason='有桥架但清单中无桥架连接件',
                confidence=0.6,
                suggestion='补充桥架连接件、托臂、吊挂件等'
            ))

    def _calculate_confidence(self, result: AuditResult) -> float:
        """计算审核置信度"""

        # 基础分数
        base_score = 0.8

        # 根据问题数量扣分
        corrections = len(result.corrections)
        warnings = len(result.warnings)

        if corrections > 5:
            base_score -= 0.3
        elif corrections > 3:
            base_score -= 0.2
        elif corrections > 1:
            base_score -= 0.1

        if warnings > 10:
            base_score -= 0.2
        elif warnings > 5:
            base_score -= 0.1
        elif warnings > 2:
            base_score -= 0.05

        return max(0.0, min(1.0, base_score))

    def _generate_summary(self, result: AuditResult) -> str:
        """生成审核摘要"""

        parts = []

        corrections = len(result.corrections)
        warnings = len(result.warnings)

        if corrections == 0 and warnings == 0:
            return "清单基本完整，未发现明显问题"
        else:
            if corrections > 0:
                parts.append(f"建议修正{corrections}项")
            if warnings > 0:
                parts.append(f"注意{warnings}项")

        return "，".join(parts)
