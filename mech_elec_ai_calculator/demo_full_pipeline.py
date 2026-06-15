"""
机电 BIM 自动算量完整流程 DEMO
================================

📐 图纸解析 (DXF / PDF)
  ↓
📊 本地规则算量 (ElectricalCalculator)
  ↓
🤖 AgnesAI AI 智能审核 (漏项 / 分类 / 数量)
  ↓
🏗️ 3D BIM 建模 (立方体 / 圆柱体 / 矩形条)
  ↓
🔗 量模双向绑定 (ModelManager)
  ↓
📄 IFC4 导出 (可导入 Revit / ArchiCAD)
  ↓
🌐 交互式 3D 查看器 (Three.js HTML)

使用方式:
    # DXF 图纸
    python demo_full_pipeline.py --dxf drawing_data/test_electrical_complex.dxf

    # PDF 图纸
    python demo_full_pipeline.py --pdf test_data/electrical_test.pdf

    # 新建测试PDF
    python demo_full_pipeline.py --create-test
"""

import os
import sys
import json
import argparse
from typing import Optional, List, Dict, Any

sys.path.insert(0, os.path.dirname(__file__))

from drawing_parser.dxf_parser import DXFParser
from drawing_parser.pdf_parser import PDFParser
from drawing_parser.drawing_processor import DrawingProcessor
from electrical_calculator.calculator import ElectricalCalculator
from list_summary.summary_generator import SummaryGenerator
from list_summary.excel_exporter import ExcelExporter
from openhuman_audit import OpenHumanClient
from bim_modeling import (
    BIMGenerator, Geometry3D,
    ModelManager, IFCExporter, Viewer3D
)
from common.models import QuantityItem


# ============================================================
# 1. 图纸解析
# ============================================================
def step_parse_drawing(file_path: str):
    ext = os.path.splitext(file_path)[1].lower()

    if ext == '.dxf':
        print("\n" + "=" * 70)
        print("📐 [步骤 1/6] 解析 DXF 图纸")
        print("=" * 70)
        parser = DXFParser()
    elif ext == '.pdf':
        print("\n" + "=" * 70)
        print("📐 [步骤 1/6] 解析 PDF 矢量图纸")
        print("=" * 70)
        parser = PDFParser()
    else:
        raise ValueError(f"不支持的文件格式: {ext}")

    drawing_data = parser.parse(file_path)

    print(f"  ✅ 文件: {os.path.basename(file_path)}")
    print(f"  ✅ 设备: {len(drawing_data.devices)} 个")
    print(f"  ✅ 线缆: {len(drawing_data.cables)} 组")
    print(f"  ✅ 桥架: {len(drawing_data.trunkings)} 个")
    print(f"  ✅ 图元: {len(drawing_data.lines)} lines / {len(drawing_data.texts)} texts")

    # 显示前5个识别到的设备
    if drawing_data.devices:
        print(f"\n  📋 设备清单 (前5个):")
        for dev in drawing_data.devices[:5]:
            conf = dev.attributes.get('confidence', 0) if isinstance(dev.attributes, dict) else 0
            print(f"     • {dev.name} [{dev.type.value}] (confidence={conf:.2f})")

    return drawing_data


# ============================================================
# 2. 本地规则算量
# ============================================================
def step_calculate(drawing_data):
    print("\n" + "=" * 70)
    print("📊 [步骤 2/6] 执行本地规则算量")
    print("=" * 70)

    calc = ElectricalCalculator()
    result = calc.calculate(drawing_data)

    print(f"  ✅ 设备工程量: {len(result.devices)} 项")
    print(f"  ✅ 线缆工程量: {len(result.cables)} 项")
    print(f"  ✅ 桥架工程量: {len(result.trunkings)} 项")
    print(f"  ✅ 配管工程量: {len(result.pipes)} 项")
    print(f"  ✅ 辅材工程量: {len(result.accessories)} 项")
    print(f"  ✅ 算量总造价: ¥{result.total_cost:,.2f}")

    print(f"\n  📋 主要工程量 (前8项):")
    all_items = list(result.devices) + list(result.cables) + list(result.trunkings) + list(result.pipes)
    for item in all_items[:8]:
        print(f"     • {item.name}: {item.quantity:.2f} {item.unit} (¥{item.total_price:,.0f})")

    return result


# ============================================================
# 3. AgnesAI AI 审核
# ============================================================
def step_ai_audit(drawing_data, quantity_list):
    print("\n" + "=" * 70)
    print("🤖 [步骤 3/6] AgnesAI AI 智能审核")
    print("=" * 70)

    try:
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

        drawing_info = {
            'id': getattr(drawing_data, 'id', 'demo'),
            'file_type': drawing_data.file_type,
            'total_devices': len(drawing_data.devices),
            'total_cables': len(drawing_data.cables),
            'total_trunkings': len(drawing_data.trunkings),
        }

        audit_result = audit_client.audit(
            drawing_info=drawing_info,
            quantity_list=quantity_list,
            rules_summary=None
        )

        print(f"  ✅ 审核服务: {audit_result.service_used}")
        print(f"  ✅ 置信度: {audit_result.confidence_score:.0%}")
        print(f"  ✅ 修正项: {len(audit_result.corrections)} 个")
        print(f"  ✅ 警告项: {len(audit_result.warnings)} 个")

        if audit_result and audit_result.corrections:
            print(f"\n  🛠️ AI 修正建议 (前5项):")
            for cor in audit_result.corrections[:5]:
                try:
                    cat = getattr(cor, 'category', '?')
                    name = getattr(cor, 'suggested_name', None) or getattr(cor, 'original_name', '未命名')
                    orig = getattr(cor, 'original_quantity', '?')
                    suggested = getattr(cor, 'suggested_quantity', '?')
                    print(f"     • [{cat}] {name}: {orig} → {suggested}")
                except Exception:
                    print(f"     • {cor}")

        if audit_result.summary:
            print(f"\n  📝 AI 审核摘要: {audit_result.summary[:150]}...")

        return audit_result

    except Exception as e:
        print(f"  ⚠️  AI 审核失败: {e}")
        print(f"     → 跳过AI审核，继续执行本地流程")
        return None


# ============================================================
# 4. 3D BIM 建模 + 量模绑定
# ============================================================
def step_bim_modeling(drawing_data, calculation_result):
    print("\n" + "=" * 70)
    print("🏗️ [步骤 4/6] 3D BIM 建模 + 量模双向绑定")
    print("=" * 70)

    # 1) 从图纸生成构件（有真实坐标）
    bim_gen = BIMGenerator(scale_factor=1.0)
    components, geometries = bim_gen.generate_from_drawing(drawing_data)

    # 2) 管理量模绑定 —— 新版 ModelManager 会自动按分类匹配
    manager = ModelManager()
    manager.add_components(components)
    bound_count = manager.bind_from_calculation(calculation_result)

    # 3) 汇总统计 (从 manager 读取已绑定的工程量信息)
    by_type: Dict[str, int] = {}
    for comp in components:
        t = comp.type.value if hasattr(comp.type, 'value') else str(comp.type)
        by_type[t] = by_type.get(t, 0) + 1

    print(f"  ✅ 构件总数: {len(components)} 个")
    print(f"  ✅ 按类型分布: {json.dumps(by_type, ensure_ascii=False)}")
    print(f"  ✅ 量模绑定数: {bound_count} / {len(components)}")
    print(f"  ✅ 绑定覆盖率: {manager.get_binding_report()['coverage']:.0%}")

    # 4) 为未绑定的构件自动补充工程量信息 (从计算结果中匹配)
    all_calc_items_by_category: Dict[str, List[Any]] = {}
    for item in (list(calculation_result.devices) + list(calculation_result.cables) +
                  list(calculation_result.trunkings) + list(calculation_result.pipes)):
        key = item.category or "其他"
        if key not in all_calc_items_by_category:
            all_calc_items_by_category[key] = []
        all_calc_items_by_category[key].append(item)

    # 按构件类型的中文名映射到算量项 category
    type_mapping = {
        'cabinet': ['配电柜', '开关柜', 'cabinet', '设备'],
        'distribution_box': ['配电箱', '配电盘', 'cabinet', '设备'],
        'equipment': ['电气设备', '设备', 'cabinet', 'equipment'],
        'fixture': ['开关', '插座', '灯具', 'fixture'],
        'cable': ['电缆', '线缆', 'cable'],
        'cable_tray': ['桥架', '线槽', 'trunking'],
        'pipe': ['配管', 'pipe'],
    }

    for comp in components:
        t = comp.type.value if hasattr(comp.type, 'value') else str(comp.type)
        matched_keywords = type_mapping.get(t, [])

        # 在分类对应的算量项中查找
        for cat, items in all_calc_items_by_category.items():
            if any(kw in cat.lower() or kw in (item.name or '').lower() for kw in matched_keywords for item in items):
                # 取第一个匹配项填充属性
                if items and isinstance(comp.attributes, dict) and 'quantity' not in comp.attributes:
                    item = items[0]
                    comp.attributes['quantity'] = item.quantity
                    comp.attributes['unit'] = item.unit
                    comp.attributes['unit_price'] = item.unit_price
                    comp.attributes['total_price'] = item.total_price
                    comp.attributes['category'] = item.category
                    comp.attributes['code'] = item.code
                break

    return components, geometries, manager


# ============================================================
# 5. IFC4 导出
# ============================================================
def step_export_ifc(components, output_path: str):
    print("\n" + "=" * 70)
    print("📄 [步骤 5/6] 导出 IFC4 BIM 文件")
    print("=" * 70)

    exporter = IFCExporter()
    exporter.export(
        components=components,
        output_path=output_path,
        project_name="机电 BIM 自动算量项目"
    )

    size_kb = os.path.getsize(output_path) / 1024
    print(f"  ✅ 文件已保存: {output_path}")
    print(f"  ✅ 文件大小: {size_kb:.1f} KB")
    print(f"  ✅ 标准: IFC4 / Coordination View")
    print(f"  ✅ 可导入: Revit / ArchiCAD / Tekla / Solibri")
    print(f"\n  💡 在 Revit 中使用: 插入 → 链接 IFC / 导入 IFC")

    return output_path


# ============================================================
# 6. 3D 交互式查看器导出
# ============================================================
def step_export_viewer(manager, output_path: str, extra: Optional[Dict] = None):
    print("\n" + "=" * 70)
    print("🌐 [步骤 6/6] 导出交互式 3D 查看器")
    print("=" * 70)

    viewer = Viewer3D()
    viewer.generate(
        model_manager=manager,
        output_path=output_path,
        extra_data=extra or {}
    )

    print(f"  ✅ HTML 文件: {output_path}")
    print(f"  ✅ 框架: Three.js r160 + OrbitControls")
    print(f"\n  💡 操作指南:")
    print(f"     • 左键拖动: 旋转视角")
    print(f"     • 右键拖动: 平移画面")
    print(f"     • 鼠标滚轮: 缩放视图")
    print(f"     • 点击构件: 查看工程量信息 / 修改数据")

    # 在浏览器中打开提示
    abs_path = os.path.abspath(output_path)
    print(f"\n  🖥️ 在浏览器中打开: file://{abs_path}")
    return output_path


# ============================================================
# 7. Excel 清单导出
# ============================================================
def export_excel(calculation_result, output_path: str):
    print("\n" + "=" * 70)
    print("📊 导出工程量清单 Excel")
    print("=" * 70)

    # 构建汇总清单
    from uuid import uuid4
    from common.models import ListSummary

    all_items = (
        list(calculation_result.devices) +
        list(calculation_result.cables) +
        list(calculation_result.trunkings) +
        list(calculation_result.pipes) +
        list(calculation_result.accessories)
    )

    summary = ListSummary(
        calculation_id=str(uuid4()),
        project_name="机电BIM自动算量项目",
        project_code="MECH-ELEC-001"
    )
    for item in all_items:
        summary.items.append(item)

    exporter = ExcelExporter()
    exporter.export(summary, output_path)

    print(f"  ✅ 清单条目: {len(summary.items)} 项")
    print(f"  ✅ 总造价: ¥{calculation_result.total_cost:,.2f}")
    print(f"  ✅ 文件已保存: {output_path}")


# ============================================================
# 主流程
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="机电 BIM 自动算量完整流程 DEMO")
    parser.add_argument('--dxf', type=str, default=None, help='DXF 图纸路径')
    parser.add_argument('--pdf', type=str, default=None, help='PDF 图纸路径')
    parser.add_argument('--output', type=str, default='outputs', help='输出目录')
    parser.add_argument('--create-test', action='store_true', help='创建测试PDF后运行')
    args = parser.parse_args()

    # 输出目录
    output_dir = os.path.join(os.path.dirname(__file__), args.output)
    os.makedirs(output_dir, exist_ok=True)

    # 确定输入文件
    file_path = None
    if args.create_test:
        print("🖨️ 创建测试矢量 PDF 图纸...")
        from create_test_pdf import create_electrical_pdf
        pdf_path = os.path.join(os.path.dirname(__file__), "test_data", "electrical_test.pdf")
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
        create_electrical_pdf(pdf_path)
        file_path = pdf_path
        print(f"  ✅ 已创建: {file_path}")
    elif args.pdf:
        file_path = args.pdf
    elif args.dxf:
        file_path = args.dxf
    else:
        # 默认使用 DXF
        default_dxf = os.path.join(os.path.dirname(__file__), "test_data", "complex_electrical.dxf")
        if os.path.exists(default_dxf):
            file_path = default_dxf
        else:
            print("❌ 请提供 --dxf 或 --pdf 参数，或使用 --create-test")
            sys.exit(1)

    if not os.path.exists(file_path):
        print(f"❌ 文件不存在: {file_path}")
        sys.exit(1)

    # ========== 主流程 ==========
    print("\n" + "=" * 70)
    print("🏗️  机电 BIM 自动算量系统 DEMO  | DX F/PDF → 算量 → AI 审核 → BIM 建模 → IFC/3D 查看器")
    print("=" * 70)

    try:
        # Step 1: 图纸解析
        drawing_data = step_parse_drawing(file_path)

        # Step 2: 本地算量
        calc_result = step_calculate(drawing_data)

        # Step 3: AI 审核
        items_for_audit = [
            {'id': item.id, 'name': item.name, 'quantity': item.quantity,
             'unit': item.unit, 'unit_price': item.unit_price,
             'total_price': item.total_price, 'category': item.category}
            for item in list(calc_result.devices) + list(calc_result.cables)
            + list(calc_result.trunkings) + list(calc_result.pipes)
        ]

        audit_result = step_ai_audit(drawing_data, items_for_audit)

        # Step 4: 3D BIM 建模 + 量模绑定
        components, geometries, manager = step_bim_modeling(drawing_data, calc_result)

        # Step 5: 导出 IFC
        ifc_path = os.path.join(output_dir, f"bim_model_{os.path.splitext(os.path.basename(file_path))[0]}.ifc")
        step_export_ifc(components, ifc_path)

        # Step 6: 导出 3D 查看器
        viewer_path = os.path.join(output_dir, f"bim_viewer_{os.path.splitext(os.path.basename(file_path))[0]}.html")
        step_export_viewer(manager, viewer_path, {
            'total_cost': calc_result.total_cost,
            'audit_confidence': audit_result.confidence_score if audit_result else 0.0,
        })

        # Step 7: 导出 Excel
        excel_path = os.path.join(output_dir, f"工程量清单_{os.path.splitext(os.path.basename(file_path))[0]}.xlsx")
        export_excel(calc_result, excel_path)

        # ===== 最终汇总 =====
        print("\n" + "=" * 70)
        print("🎉 DEMO 执行完成！输出文件汇总:")
        print("=" * 70)

        files = [
            ('📄 IFC4 BIM 文件', ifc_path, "可导入 Revit/ArchiCAD"),
            ('🌐 3D 交互式查看器', viewer_path, "浏览器中打开，点击构件查看工程量"),
            ('📊 Excel 工程量清单', excel_path, "标准工程量清单"),
        ]

        for label, path, desc in files:
            size = os.path.getsize(path) / 1024
            print(f"\n  {label}")
            print(f"    路径: {path}")
            print(f"    大小: {size:.1f} KB")
            print(f"    说明: {desc}")

        print("\n" + "=" * 70)
        print("✅ 量模一体化 DEMO 完成")
        print("=" * 70)
        print(f"   构件总数: {len(components)}")
        print(f"   造价合计: ¥{calc_result.total_cost:,.2f}")
        print(f"   图纸格式: {drawing_data.file_type}")
        print(f"   AI 审核: {'已通过' if (audit_result and audit_result.confidence_score > 0.5) else '跳过/失败'}")
        print("\n" + "📌 对标广联达/算王/Sketchup:")
        print("   • 自动识别设备/线缆/桥架 (CAD → 构件)")
        print("   • 按国标规则自动算量 (与算王同逻辑)")
        print("   • BIM 构件与工程量双向绑定 (Revit 可导入)")
        print("   • 三维可视化检查与交互修改")
        print("   • AI 审核补充漏项/错项")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ DEMO 执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
