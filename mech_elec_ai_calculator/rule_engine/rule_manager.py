from typing import Dict, Any, Optional, List, Tuple
from .rule_loader import RuleLoader
from .rule_validator import RuleValidator
from framework.exceptions import RuleEngineError
import re


class RuleManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._rules = {}
            cls._instance._rule_loader = RuleLoader()
            cls._instance._rule_validator = RuleValidator()
            cls._instance._compiled_patterns = {}
        return cls._instance

    def load_rules(self, version: str = 'latest') -> None:
        self._rules = self._rule_loader.load_rules(version)
        self._rule_validator.validate(self._rules)
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """预编译正则表达式以提高性能"""
        device_classification = self.get_rule('device_classification', {})
        for device_type, config in device_classification.items():
            patterns = config.get('name_patterns', [])
            if patterns:
                compiled = [re.compile(p, re.IGNORECASE) for p in patterns]
                self._compiled_patterns[f'device_{device_type}'] = compiled

        cable_config = self.get_rule('cable_identification', {})
        for cable_type, config in cable_config.items():
            patterns = config.get('model_patterns', [])
            if patterns:
                compiled = [re.compile(p, re.IGNORECASE) for p in patterns]
                self._compiled_patterns[f'cable_{cable_type}'] = compiled

    def get_rule(self, key: str, default: Any = None) -> Any:
        keys = key.split('.')
        value = self._rules
        try:
            for k in keys:
                value = value[k]
            return value
        except KeyError:
            return default

    def get_reserve_length(self, reserve_type: str) -> float:
        return self.get_rule(f'reserve_lengths.{reserve_type}', 0.0)

    def get_correction_factor(self, factor_name: str) -> float:
        return self.get_rule(f'correction_factors.{factor_name}', 1.0)

    # ==================== 文本规范化 ====================

    def normalize_text(self, text: str) -> str:
        """对文本进行规范化处理 - 去掉空格、特殊字符、转小写等"""
        if not text:
            return ""

        fuzzy_config = self.get_rule('fuzzy_matching', {})
        normalization = fuzzy_config.get('text_normalization', {})

        normalized = str(text).strip()

        if normalization.get('remove_parentheses_content', True):
            # 去掉括号及括号内的内容
            normalized = re.sub(r'[（(][^)）]*[)）]', '', normalized)

        if normalization.get('remove_spaces', True):
            normalized = normalized.replace(' ', '').replace('\t', '')

        if normalization.get('remove_special_chars', True):
            special_chars = normalization.get(
                'special_chars_to_remove',
                '()[]{}<>【】（）『』「」『』、\\|.,;:!！？?#@*&^%$'
            )
            for char in special_chars:
                normalized = normalized.replace(char, '')

        if normalization.get('to_lowercase', True):
            normalized = normalized.lower()

        return normalized.strip()

    def expand_abbreviations(self, text: str) -> str:
        """展开常见的电气缩写"""
        fuzzy_config = self.get_rule('fuzzy_matching', {})
        expansion = fuzzy_config.get('abbreviation_expansion', {})

        if not expansion.get('enabled', True):
            return text

        mappings = expansion.get('mappings', {})
        normalized = self.normalize_text(text)

        # 精确匹配缩写
        if normalized in mappings:
            return mappings[normalized]

        # 前缀匹配
        for abbr, full in mappings.items():
            if normalized.startswith(abbr.lower()):
                return full

        return text

    # ==================== 其他辅助 ====================

    def normalize_device_type(self, raw_type: str) -> str:
        """将规则库中的设备类型映射为DeviceType枚举支持的值"""
        type_mapping = {
            'cabinet': 'cabinet',
            'equipment': 'equipment',
            'distribution_box': 'distribution_box',
            'switch': 'switch',
            'socket': 'socket',
            'lighting': 'lighting',
            'meter': 'other',        # 电表归为其他
            'junction_box': 'other', # 接线盒归为其他
            'panel': 'cabinet',      # 面板柜归为配电柜
            'other': 'other'
        }
        return type_mapping.get(raw_type, 'other')

    def classify_device(self, block_name: str) -> Optional[str]:
        """基于关键词的简单设备分类 - 返回归一化后的设备类型"""
        result = self.classify_device_with_confidence(block_name)
        raw_type = result.get('device_type', 'other')
        return self.normalize_device_type(raw_type)

    def classify_device_with_confidence(self, block_name: str) -> Optional[Dict[str, Any]]:
        """
        设备分类并计算置信度
        返回: {device_type, confidence, matched_keywords, match_method}
        """
        if not block_name:
            return {'device_type': 'other', 'confidence': 0.0, 'matched_keywords': [], 'match_method': 'none'}

        device_classification = self.get_rule('device_classification', {})

        # 按优先级排序
        sorted_configs = sorted(
            device_classification.items(),
            key=lambda x: x[1].get('priority', 99)
        )

        normalized_name = self.normalize_text(block_name)

        best_match = None
        best_confidence = 0.0

        for device_type, config in sorted_configs:
            confidence = 0.0
            matched_keywords = []

            # 1. 精确关键词匹配 (最高权重)
            keywords = config.get('keywords', [])
            for keyword in keywords:
                normalized_keyword = self.normalize_text(keyword)
                if not normalized_keyword or len(normalized_keyword) < 2:
                    continue

                if normalized_keyword == normalized_name:
                    confidence += 1.0
                    matched_keywords.append(keyword)
                    break
                elif normalized_keyword in normalized_name:
                    confidence += 0.8
                    matched_keywords.append(keyword)

            # 2. 图块关键词匹配
            block_keywords = config.get('block_keywords', [])
            for bk in block_keywords:
                normalized_bk = self.normalize_text(bk)
                if normalized_bk and normalized_bk in normalized_name:
                    confidence += 0.6
                    matched_keywords.append(bk)

            # 3. 正则表达式模式匹配
            patterns = self._compiled_patterns.get(f'device_{device_type}', [])
            for pattern in patterns:
                if pattern.search(block_name):
                    confidence += 0.7
                    matched_keywords.append(pattern.pattern)
                    break

            # 4. 多关键词增强
            if len(matched_keywords) >= 2:
                fuzzy_config = self.get_rule('fuzzy_matching', {})
                boost_config = fuzzy_config.get('multi_keyword_boost', {})
                boost_factor = boost_config.get('boost_factor', 1.3)
                max_boost = boost_config.get('max_boost', 2.0)
                confidence = min(confidence * boost_factor, max_boost)

            # 5. 缩写展开后的二次匹配
            expanded_name = self.expand_abbreviations(block_name)
            if expanded_name != block_name:
                for keyword in keywords:
                    if self.normalize_text(keyword) in self.normalize_text(expanded_name):
                        confidence += 0.5
                        matched_keywords.append(f'[缩写] {keyword}')
                        break

            # 限制置信度在0-1范围
            confidence = min(confidence, 1.0)

            # 检查是否超过该设备类型的阈值
            threshold = config.get('confidence_threshold', 0.3)

            if confidence > best_confidence and confidence >= threshold:
                best_confidence = confidence
                best_match = {
                    'device_type': device_type,
                    'confidence': confidence,
                    'matched_keywords': matched_keywords,
                    'match_method': 'keyword' if matched_keywords else 'fallback'
                }

        if best_match:
            return best_match

        return {'device_type': 'other', 'confidence': 0.1, 'matched_keywords': [], 'match_method': 'default'}

    # ==================== 线缆识别 ====================

    def identify_cable_type(self, text: str, layer: str = '', color: str = '', line_type: str = '') -> Dict[str, Any]:
        """
        综合识别线缆类型
        返回: {cable_type, confidence, cable_name, laying_method}
        """
        cable_config = self.get_rule('cable_identification', {})

        if not cable_config:
            return {'cable_type': 'power', 'confidence': 0.3, 'cable_name': '电力电缆', 'laying_method': 'cable_tray'}

        normalized_text = self.normalize_text(text) if text else ''
        normalized_layer = self.normalize_text(layer) if layer else ''

        best_type = 'power'
        best_confidence = 0.0
        best_name = '电力电缆'

        # 按优先级排序线缆类型
        sorted_cables = sorted(
            cable_config.items(),
            key=lambda x: x[1].get('priority', 99)
        )

        for cable_type, config in sorted_cables:
            confidence = 0.0
            matched_items = []

            # 1. 关键词匹配 (文本内容)
            keywords = config.get('keywords', [])
            for kw in keywords:
                normalized_kw = self.normalize_text(kw)
                if normalized_kw and normalized_kw in normalized_text:
                    confidence += 0.8
                    matched_items.append(kw)
                elif normalized_kw and normalized_kw in normalized_layer:
                    confidence += 0.6
                    matched_items.append(f'[图层] {kw}')

            # 2. 颜色匹配
            colors = config.get('colors', [])
            if color and color in colors:
                confidence += 0.5
                matched_items.append(f'[颜色] {color}')

            # 3. 线型匹配
            line_types = config.get('line_types', [])
            if line_type and line_type.upper() in [lt.upper() for lt in line_types]:
                confidence += 0.3
                matched_items.append(f'[线型] {line_type}')

            # 4. 正则模式匹配 (电缆型号)
            patterns = self._compiled_patterns.get(f'cable_{cable_type}', [])
            for pattern in patterns:
                if text and pattern.search(text):
                    confidence += 0.9
                    matched_items.append(f'[型号] {pattern.pattern}')
                    break

            confidence = min(confidence, 1.0)

            if confidence > best_confidence:
                best_confidence = confidence
                best_type = cable_type
                best_name = keywords[0] if keywords else cable_type

        # 确定敷设方式
        laying_method = self._detect_laying_method(layer, line_type)

        return {
            'cable_type': best_type,
            'confidence': max(best_confidence, 0.3),
            'cable_name': best_name,
            'laying_method': laying_method
        }

    def _detect_laying_method(self, layer: str, line_type: str) -> str:
        """根据图层和线型判断敷设方式"""
        normalized_layer = self.normalize_text(layer) if layer else ''

        # 桥架
        if any(kw in normalized_layer for kw in ['桥架', 'ct', 'tray', 'trunking', '线槽']):
            return 'cable_tray'

        # 穿管
        if any(kw in normalized_layer for kw in ['配管', 'sc', 'pc', 'mt', 'pipe', 'conduit', '线管']):
            return 'pipe'

        # 吊顶/沿墙
        if '吊顶' in layer or '天棚' in layer or 'ceiling' in normalized_layer:
            return 'ceiling'
        if '墙' in layer or 'wall' in normalized_layer:
            return 'wall'

        # 直埋
        if any(kw in normalized_layer for kw in ['埋', '地', 'buried', 'ground']):
            return 'direct_burial'

        # 通过线型判断
        if line_type:
            lt = line_type.upper()
            if 'DASHED' in lt:
                return 'pipe'
            elif 'PHANTOM' in lt:
                return 'ceiling'

        return 'cable_tray'

    # ==================== 桥架/配管识别 ====================

    def identify_trunking(self, layer: str, color: str = '', line_type: str = '') -> Optional[str]:
        """识别是否为桥架或配管"""
        trunking_config = self.get_rule('trunking_identification', {})
        normalized_layer = self.normalize_text(layer) if layer else ''

        for item_type, config in trunking_config.items():
            layer_keywords = config.get('layer_keywords', [])
            keywords = config.get('keywords', [])

            for kw in layer_keywords + keywords:
                normalized_kw = self.normalize_text(kw)
                if normalized_kw and normalized_kw in normalized_layer:
                    return item_type

        return None

    # ==================== 图层过滤 ====================

    def is_electrical_layer(self, layer_name: str) -> bool:
        """判断是否为电气专业相关图层"""
        if not layer_name:
            return False

        layer_filter = self.get_rule('layer_filter', {})
        if not layer_filter.get('enabled', True):
            return True

        normalized_layer = self.normalize_text(layer_name)

        # 检查排除图层
        exclude_config = layer_filter.get('exclude_layers', {})
        exclude_keywords = exclude_config.get('keywords', [])
        exclude_prefixes = exclude_config.get('layer_prefixes', [])

        for kw in exclude_keywords:
            if self.normalize_text(kw) in normalized_layer:
                return False

        for prefix in exclude_prefixes:
            if normalized_layer.startswith(self.normalize_text(prefix)):
                return False

        # 检查电气相关图层
        electrical_configs = [
            'electrical_layers',
            'equipment_layers',
            'cable_layers',
            'trunking_layers',
            'pipe_layers',
            'lighting_layers',
            'annotation_layers'
        ]

        for config_key in electrical_configs:
            config = layer_filter.get(config_key, {})
            keywords = config.get('keywords', [])
            prefixes = config.get('layer_prefixes', [])

            for kw in keywords:
                if self.normalize_text(kw) in normalized_layer:
                    return True

            for prefix in prefixes:
                if normalized_layer.startswith(self.normalize_text(prefix)):
                    return True

        # 默认: 未明确排除的图层都当作电气相关
        return True

    def get_layer_category(self, layer_name: str) -> str:
        """获取图层分类: equipment, cable, trunking, pipe, lighting, annotation, other"""
        if not layer_name:
            return 'other'

        layer_filter = self.get_rule('layer_filter', {})
        normalized_layer = self.normalize_text(layer_name)

        category_mapping = {
            'equipment_layers': 'equipment',
            'cable_layers': 'cable',
            'trunking_layers': 'trunking',
            'pipe_layers': 'pipe',
            'lighting_layers': 'lighting',
            'annotation_layers': 'annotation',
            'electrical_layers': 'electrical'
        }

        for config_key, category in category_mapping.items():
            config = layer_filter.get(config_key, {})
            keywords = config.get('keywords', [])
            prefixes = config.get('layer_prefixes', [])

            for kw in keywords:
                if self.normalize_text(kw) in normalized_layer:
                    return category

            for prefix in prefixes:
                if normalized_layer.startswith(self.normalize_text(prefix)):
                    return category

        return 'other'

    def filter_layers(self, layer_names: List[str]) -> Dict[str, str]:
        """
        过滤图层，返回 {图层名: 分类} 字典
        只包含电气相关图层
        """
        result = {}
        for name in layer_names:
            if self.is_electrical_layer(name):
                result[name] = self.get_layer_category(name)
        return result

    # ==================== 其他辅助 ====================

    def match_block(self, block_name: str) -> Optional[Dict[str, Any]]:
        block_matching = self.get_rule('block_matching', {})

        for pattern, config in block_matching.items():
            match_type = config.get('match_type', 'contains')

            if match_type == 'exact' and block_name == pattern:
                return config
            elif match_type == 'contains' and pattern.lower() in block_name.lower():
                return config

        return None

    def get_quantity_rule(self, rule_name: str) -> Optional[Dict[str, Any]]:
        return self.get_rule(f'quantity_rules.{rule_name}')

    def get_validation_threshold(self, threshold_name: str) -> float:
        return self.get_rule(f'validation_thresholds.{threshold_name}', 0.0)

    def get_unit_price(self, price_key: str) -> float:
        return self.get_rule(f'unit_prices.{price_key}', 100.0)

    def list_rules(self) -> List[str]:
        def _flatten_rules(prefix: str, rules: Dict[str, Any]) -> List[str]:
            result = []
            for key, value in rules.items():
                new_prefix = f"{prefix}.{key}" if prefix else key
                if isinstance(value, dict):
                    result.extend(_flatten_rules(new_prefix, value))
                else:
                    result.append(new_prefix)
            return result

        return _flatten_rules('', self._rules)
