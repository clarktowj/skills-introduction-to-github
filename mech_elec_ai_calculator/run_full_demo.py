#!/usr/bin/env python3
"""完整运行示例：演示DXF识别 + 自动算量 + Excel输出"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from drawing_parser.dxf_parser import DXFParser
from electrical_calculator.calculator import ElectricalCalculator
from list_summary.summary_generator import SummaryGenerator
from list_summary.excel_exporter import ExcelExporter

def main():
    print("=" * 80)
    print("机电电气自动算量系统 - 完整运行示例")
    print("=" * 80)

    # 测试DXF文件
    dxf_file = 'test_data/test_electrical_complex.dxf'

    # 第1步：DXF图纸解析
    print("\n[1/4] 📐 解析DXF图纸...")
    parser = DXFParser()
    drawing_data = parser.parse(dxf_file)

    summary = drawing_data.attributes if isinstance(drawing_data.attributes, dict) else {}
    print(f"  ✅ 图层: {len(drawing_data.layers)} 个")
    print(f"  ✅ 图块: {len(drawing_data.blocks)} 个")
    print(f"  ✅ 设备: {summary.get('total_devices', len(drawing_data.devices))} 个")
    print(f"  ✅ 线缆: {summary.get('total_cables', len(drawing_data.cables))} 组")
    print(f"  ✅ 桥架: {summary.get('total_trunkings', len(drawing_data.trunkings))} 组")

    # 第2步：电气自动算量
    print("\n[2/4] 📊 执行电气算量...")
    calculator = ElectricalCalculator()
    result = calculator.calculate(drawing_data)

    print(f"  ✅ 设备条目: {len(result.devices)}")
    print(f"  ✅ 线缆条目: {len(result.cables)}")
    print(f"  ✅ 桥架条目: {len(result.trunkings)}")
    print(f"  ✅ 辅材条目: {len(result.accessories)}")
    print(f"  ✅ 总造价: ¥{result.total_cost:,.2f}")

    # 第3步：清单汇总
    print("\n[3/4] 📋 生成工程量清单...")
    generator = SummaryGenerator()
    list_summary = generator.generate(result, drawing_data)
    print(f"  ✅ 清单条目: {len(list_summary.items)} 项")

    # 第4步：Excel导出
    print("\n[4/4] 💾 导出Excel文件...")
    output_file = 'outputs/工程量清单.xlsx'
    exporter = ExcelExporter()
    result_path = exporter.export(list_summary, output_file)
    print(f"  ✅ 文件已保存: {result_path}")

    # 结果汇总
    print("\n" + "=" * 80)
    print("📊 工程量清单汇总")
    print("=" * 80)
    print(f"{'类别':<15s} {'项目名称':<25s} {'数量':>10s} {'单位':>6s} {'单价':>10s} {'合价(元)':>12s}")
    print("-" * 80)

    total = 0
    for item in list_summary.items:
        print(f"{item.category:<15s} {item.name:<25s} {item.quantity:>10.1f} {item.unit:>6s} {item.unit_price:>10.0f} {item.total_price:>12,.0f}")
        total += item.total_price

    print("-" * 80)
    print(f"{'TOTAL':<59s} ¥{total:>12,.2f}")

    print("\n" + "=" * 80)
    print("✅ 计算完成！输出文件:", result_path)
    print("=" * 80)


if __name__ == '__main__':
    main()
