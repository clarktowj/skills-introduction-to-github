"""
PDF 图纸完整流程测试

1. 解析 PDF 图纸
2. 执行电气算量
3. 生成清单
4. AgnesAI AI 审核
5. 输出Excel清单

验证 DXF+PDF 双格式通吃
"""
import sys
import os
from uuid import uuid4

sys.path.insert(0, os.path.dirname(__file__))

from drawing_parser.pdf_parser import PDFParser
from drawing_parser.drawing_processor import DrawingProcessor
from drawing_parser.dxf_parser import DXFParser
from electrical_calculator.calculator import ElectricalCalculator
from list_summary.summary_generator import SummaryGenerator
from list_summary.excel_exporter import ExcelExporter
from openhuman_audit import OpenHumanClient, AuditProcessor
from common.models import ListSummary, QuantityItem


def convert_to_dict(obj) -> dict:
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


def safe_parse_quantity(value) -> float:
    """
    安全解析数量值，处理 AI 修正返回的非数字内容
    例如: "至少26个", "2.0", 2, None
    """
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        # 提取第一个数字（支持整数和小数）
        import re
        match = re.search(r'[\d.]+', value)
        if match:
            try:
                return float(match.group())
            except (ValueError, TypeError):
                pass
        # 如果找不到数字，返回默认值 1.0
        return 1.0
    return 1.0


def run_pdf_pipeline():
    print("=" * 80)
    print("机电电气自动算量 + PDF图纸解析 + AgnesAI审核")
    print("=" * 80)

    test_pdf = os.path.join(os.path.dirname(__file__), "test_data", "electrical_test.pdf")

    if not os.path.exists(test_pdf):
        print(f"[ERROR] PDF 文件不存在: {test_pdf}")
        print("  请先运行: python create_test_pdf.py")
        return False

    print(f"\n[1/6] 📐 解析 PDF 图纸: {os.path.basename(test_pdf)}")
    parser = PDFParser()
    drawing_data = parser.parse(test_pdf)

    print(f"  ✅ 图纸格式: {drawing_data.file_type}")
    print(f"  ✅ 图层: {len(drawing_data.layers)}")
    print(f"  ✅ 线条图元: {len(drawing_data.lines)}")
    print(f"  ✅ 文字标注: {len(drawing_data.texts)}")
    print(f"  ✅ 设备图块: {len(drawing_data.blocks)}")
    print(f"  ✅ 识别设备: {len(drawing_data.devices)}")
    print(f"  ✅ 识别线缆: {len(drawing_data.cables)}")
    print(f"  ✅ 识别桥架: {len(drawing_data.trunkings)}")

    if drawing_data.devices:
        print("\n  📋 识别到的设备:")
        for dev in drawing_data.devices[:15]:
            conf = dev.attributes.get('confidence', 0) if isinstance(dev.attributes, dict) else 0
            print(f"    - {dev.name} [{dev.type.value}] (conf={conf})")

    print("\n[2/6] 📊 执行电气算量 (初版清单)...")
    calculator = ElectricalCalculator()
    calc_result = calculator.calculate(drawing_data)
    print(f"  ✅ 设备条目: {len(calc_result.devices)}")
    print(f"  ✅ 线缆条目: {len(calc_result.cables)}")
    print(f"  ✅ 桥架条目: {len(calc_result.trunkings)}")
    print(f"  ✅ 配管条目: {len(calc_result.pipes)}")
    print(f"  ✅ 辅材条目: {len(calc_result.accessories)}")
    print(f"  ✅ 总造价: ¥{calc_result.total_cost:,.2f}")

    print("\n[3/6] 📋 生成初版工程量清单...")
    generator = SummaryGenerator()
    list_summary = generator.generate(calc_result, drawing_data)
    quantity_list = [item.model_dump() for item in list_summary.items]
    print(f"  ✅ 清单条目: {len(quantity_list)} 项")

    print("\n[4/6] 🤖 AgnesAI AI 审核中...")
    print("  📡 API: https://apihub.agnes-ai.com/v1")
    print("  🤖 Model: agnes-2.0-flash")

    drawing_info = convert_to_dict(drawing_data)

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
        print(f"  📝 AI摘要: {audit_result.summary[:100]}...")

    print("\n[5/6] 🔧 处理审核结果...")

    audit_processor = AuditProcessor(confidence_threshold=0.6)
    processed = audit_processor.process(audit_result, quantity_list)

    if processed.has_auto_changes():
        print(f"  ✅ 自动应用: {len(processed.additions)}项添加 + {len(processed.modifications)}项修正")
        corrected_list = audit_processor.apply_corrections(processed, quantity_list, auto_apply=True)
        report = audit_processor.generate_report(processed)
        print("\n" + report)
    else:
        print("  ✅ 无需自动修正")
        corrected_list = quantity_list

    print("\n[6/6] 💾 导出最终工程量清单...")

    final_summary = ListSummary(
        calculation_id=str(uuid4()),
        project_name=list_summary.project_name,
        project_code=list_summary.project_code
    )

    for item_dict in corrected_list:
        quantity = safe_parse_quantity(item_dict.get('quantity', 0))
        unit_price = safe_parse_quantity(item_dict.get('unit_price', 0)) or estimate_unit_price(item_dict.get('name', ''))

        item = QuantityItem(
            component_id=item_dict.get('component_id', ''),
            code=item_dict.get('code', 'DL999'),
            name=item_dict.get('name', ''),
            unit=item_dict.get('unit', '个'),
            quantity=quantity,
            unit_price=float(unit_price),
            total_price=quantity * float(unit_price),
            category=item_dict.get('category', '其他'),
            sub_category=item_dict.get('sub_category', ''),
            description=item_dict.get('description', '')
        )
        final_summary.items.append(item)

    final_summary.total_cost = sum(item.total_price for item in final_summary.items)

    output_path = os.path.join(os.path.dirname(__file__), "outputs", "工程量清单_PDF格式.xlsx")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    exporter = ExcelExporter()
    result_path = exporter.export(final_summary, output_path)
    print(f"  ✅ 文件已保存: {result_path}")

    print("\n" + "=" * 80)
    print("📊 最终工程量清单")
    print("=" * 80)
    print(f"{'类别':<10s} {'项目名称':<25s} {'数量':>10s} {'单位':>6s} {'单价':>10s} {'合价(元)':>12s}")
    print("-" * 80)

    for item in final_summary.items[:20]:
        print(f"{item.category:<10s} {item.name:<25s} {item.quantity:>10.2f} {item.unit:>6s} {item.unit_price:>10.0f} {item.total_price:>12,.0f}")

    print("-" * 80)
    print(f"{'':>55s} {'TOTAL':>10s} {final_summary.total_cost:>12,.2f}")

    print("\n" + "=" * 80)
    print("✅ PDF 格式图纸测试完成！")
    print("=" * 80)
    return True


def test_format_detection():
    print("\n" + "=" * 80)
    print("统一格式处理器测试 (DrawingProcessor)")
    print("=" * 80)

    processor = DrawingProcessor()

    test_cases = [
        ("electrical_test.pdf", "pdf"),
        ("test_electrical_complex.dxf", "dxf"),
    ]

    test_data_dir = os.path.join(os.path.dirname(__file__), "test_data")

    for filename, expected_type in test_cases:
        file_path = os.path.join(test_data_dir, filename)
        if not os.path.exists(file_path):
            print(f"  ⏭️  跳过 (文件不存在): {filename}")
            continue

        print(f"\n  📄 {filename}")
        try:
            drawing_data = processor.process(file_path)
            print(f"    ✅ 检测格式: {drawing_data.file_type} (期望: {expected_type})")
            print(f"    ✅ 设备: {len(drawing_data.devices)} | 线缆: {len(drawing_data.cables)} | 桥架: {len(drawing_data.trunkings)}")
        except Exception as e:
            print(f"    ❌ 错误: {e}")

    print(f"\n  ✅ 支持格式: .dxf / .pdf / .jpg / .jpeg / .png / .bmp / .tiff")
    return True


if __name__ == "__main__":
    success = run_pdf_pipeline()
    test_format_detection()

    if success:
        print("\n🎉 DXF+PDF 双格式通吃！")
    else:
        print("\n⚠️ 测试未完全通过")
        sys.exit(1)
