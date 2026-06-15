#!/usr/bin/env python3
"""
使用 AgnesAI API 进行电气工程量审核
完整示例：DXF解析 -> 本地算量 -> AgnesAI审核 -> 自动修正 -> 输出清单
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from drawing_parser.dxf_parser import DXFParser
from electrical_calculator.calculator import ElectricalCalculator
from list_summary.summary_generator import SummaryGenerator
from list_summary.excel_exporter import ExcelExporter
from openhuman_audit import OpenHumanClient, AuditProcessor


def convert_to_dict(obj) -> dict:
    """将Pydantic模型转换为字典"""
    if hasattr(obj, 'model_dump'):
        return obj.model_dump()
    elif hasattr(obj, '__dict__'):
        result = {}
        for key, value in obj.__dict__.items():
            if not key.startswith('_'):
                if isinstance(value, list):
                    result[key] = [convert_to_dict(v) for v in value]
                elif hasattr(value, '__dict__'):
                    result[key] = convert_to_dict(value)
                else:
                    result[key] = value
        return result
    return obj


def estimate_unit_price(name: str) -> float:
    """根据名称估算单价"""
    if '配电柜' in name or '开关柜' in name:
        return 5000.0
    elif '配电箱' in name or '配电盘' in name:
        return 800.0
    elif '开关' in name or '断路器' in name:
        return 50.0
    elif '插座' in name:
        return 30.0
    elif '灯' in name or '照明' in name:
        return 150.0
    elif '电缆' in name:
        return 100.0
    elif '桥架' in name:
        return 300.0
    elif '电缆头' in name:
        return 50.0
    elif '端子' in name:
        return 5.0
    else:
        return 100.0


def main():
    print("=" * 80)
    print("机电电气自动算量 + AgnesAI AI审核系统")
    print("=" * 80)

    dxf_file = 'test_data/test_electrical_complex.dxf'

    # ===== 第1步：DXF图纸解析 =====
    print("\n[1/6] 📐 解析DXF图纸...")
    parser = DXFParser()
    drawing_data = parser.parse(dxf_file)
    print(f"  ✅ 设备: {len(drawing_data.devices)} 个")
    print(f"  ✅ 线缆: {len(drawing_data.cables)} 组")
    print(f"  ✅ 桥架: {len(drawing_data.trunkings)} 组")

    # ===== 第2步：电气自动算量 =====
    print("\n[2/6] 📊 执行电气算量 (初版清单)...")
    calculator = ElectricalCalculator()
    calc_result = calculator.calculate(drawing_data)
    print(f"  ✅ 设备条目: {len(calc_result.devices)}")
    print(f"  ✅ 线缆条目: {len(calc_result.cables)}")
    print(f"  ✅ 桥架条目: {len(calc_result.trunkings)}")

    # ===== 第3步：生成清单 =====
    print("\n[3/6] 📋 生成初版工程量清单...")
    generator = SummaryGenerator()
    list_summary = generator.generate(calc_result, drawing_data)
    quantity_list = [item.model_dump() for item in list_summary.items]
    print(f"  ✅ 清单条目: {len(quantity_list)} 项")

    # ===== 第4步：AgnesAI 审核 =====
    print("\n[4/6] 🤖 AgnesAI AI 审核中...")
    print("  📡 API: https://apihub.agnes-ai.com/v1")
    print("  🤖 Model: agnes-2.0-flash")

    drawing_info = convert_to_dict(drawing_data)

    # AgnesAI 配置
    audit_client = OpenHumanClient({
        'service_type': 'openai',
        'api_key': 'sk-o9HJZWD6ImlQzMcTUtll8AKghTl7ioDYlPQLwVHGuiJp6TMu',
        'api_base': 'https://apihub.agnes-ai.com/v1',
        'model': 'agnes-2.0-flash',
        'temperature': 0.1,
        'max_tokens': 4000,
        'timeout': 120,
        'local_rules_enabled': True
    })

    audit_result = audit_client.audit(
        drawing_info=drawing_info,
        quantity_list=quantity_list,
        rules_summary=None
    )

    print(f"\n  ✅ 审核服务: {audit_result.service_used}")
    print(f"  ✅ 审核置信度: {audit_result.confidence_score:.1%}")
    print(f"  ✅ 修正项: {len(audit_result.corrections)} | 警告项: {len(audit_result.warnings)}")

    if audit_result.summary:
        print(f"  📝 AI摘要: {audit_result.summary[:80]}...")

    # ===== 第5步：处理审核结果 =====
    print("\n[5/6] 🔧 处理审核结果...")

    processor = AuditProcessor(confidence_threshold=0.6)
    processed = processor.process(audit_result, quantity_list)

    if processed.has_auto_changes():
        print(f"  ✅ 自动应用: {len(processed.additions)}项添加 + {len(processed.modifications)}项修正")
        corrected_list = processor.apply_corrections(processed, quantity_list, auto_apply=True)
        report = processor.generate_report(processed)
        print("\n" + report)
    else:
        print("  ✅ 无需自动修正")
        corrected_list = quantity_list

    # ===== 第6步：导出最终清单 =====
    print("\n[6/6] 💾 导出最终工程量清单...")

    from common.models import ListSummary, QuantityItem
    from uuid import uuid4

    final_summary = ListSummary(
        calculation_id=str(uuid4()),
        project_name=list_summary.project_name,
        project_code=list_summary.project_code
    )

    for item_dict in corrected_list:
        quantity = item_dict.get('quantity', 0)
        unit_price = item_dict.get('unit_price', 0) or estimate_unit_price(item_dict.get('name', ''))

        item = QuantityItem(
            component_id=item_dict.get('component_id', ''),
            code=item_dict.get('code', 'DL999'),
            name=item_dict.get('name', ''),
            unit=item_dict.get('unit', '个'),
            quantity=float(quantity),
            unit_price=float(unit_price),
            total_price=float(quantity) * float(unit_price),
            category=item_dict.get('category', '其他'),
            sub_category=item_dict.get('sub_category', ''),
            description=item_dict.get('description', '')
        )
        final_summary.items.append(item)

    final_summary.total_cost = sum(item.total_price for item in final_summary.items)

    output_file = 'outputs/工程量清单_agnesai.xlsx'
    exporter = ExcelExporter()
    result_path = exporter.export(final_summary, output_file)
    print(f"  ✅ 文件已保存: {result_path}")

    # ===== 结果汇总 =====
    print("\n" + "=" * 80)
    print("📊 最终工程量清单")
    print("=" * 80)
    print(f"{'类别':<10s} {'项目名称':<25s} {'数量':>10s} {'单位':>6s} {'单价':>10s} {'合价(元)':>12s}")
    print("-" * 80)

    for item in final_summary.items:
        print(f"{item.category:<10s} {item.name:<25s} {item.quantity:>10.1f} {item.unit:>6s} {item.unit_price:>10.0f} {item.total_price:>12,.0f}")

    print("-" * 80)
    print(f"{'TOTAL':<70s} ¥{final_summary.total_cost:>12,.2f}")

    print("\n" + "=" * 80)
    print("✅ 计算完成！")
    print("=" * 80)


if __name__ == '__main__':
    main()
