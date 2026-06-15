"""
四合一 DEMO: BIM 插件 + 甲供材拆分 + 结算报表 + 移动端
==================================================================
运行: python -m mech_elec_ai_calculator.demo_4in1
"""
import os
import sys
import json
from datetime import datetime


def section(title: str):
    print("\n" + "=" * 80)
    print(f"📦 {title}")
    print("=" * 80)


def main():
    print("🏗️ 机电 BIM 自动算量系统 - 四合一 DEMO")
    print(f"    时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # ---- 初始化算量结果（构造测试数据） ----
    from common.models import CalculationResult, QuantityItem
    from uuid import uuid4

    drawing_id = str(uuid4())

    devices = [
        QuantityItem(id=str(uuid4()), component_id='C001', code='SB001', name='配电柜 低压配电柜 GGD', category='设备', unit='个', quantity=3.0, unit_price=15000.0, total_price=45000.0),
        QuantityItem(id=str(uuid4()), component_id='C002', code='SB002', name='配电箱 AL-1F', category='设备', unit='个', quantity=5.0, unit_price=5000.0, total_price=25000.0),
        QuantityItem(id=str(uuid4()), component_id='C003', code='SB003', name='变压器 SCB14-800kVA', category='设备', unit='台', quantity=1.0, unit_price=120000.0, total_price=120000.0),
        QuantityItem(id=str(uuid4()), component_id='C004', code='SB004', name='电动机控制中心 MCC', category='设备', unit='个', quantity=2.0, unit_price=80000.0, total_price=160000.0),
        QuantityItem(id=str(uuid4()), component_id='C005', code='DL001', name='开关 2P 16A', category='电气', unit='个', quantity=40.0, unit_price=80.0, total_price=3200.0),
    ]

    cables = [
        QuantityItem(id=str(uuid4()), component_id='K001', code='DL101', name='电力电缆 YJV-4x95', category='线缆', unit='米', quantity=520.0, unit_price=280.0, total_price=145600.0),
        QuantityItem(id=str(uuid4()), component_id='K002', code='DL102', name='控制电缆 KVV-4x2.5', category='线缆', unit='米', quantity=820.0, unit_price=22.0, total_price=18040.0),
        QuantityItem(id=str(uuid4()), component_id='K003', code='DL103', name='矿物绝缘电缆 BTTZ-1x25', category='线缆', unit='米', quantity=160.0, unit_price=180.0, total_price=28800.0),
    ]

    trunkings = [
        QuantityItem(id=str(uuid4()), component_id='T001', code='DL201', name='桥架 200x100 镀锌', category='桥架', unit='米', quantity=180.0, unit_price=180.0, total_price=32400.0),
        QuantityItem(id=str(uuid4()), component_id='T002', code='DL202', name='桥架 100x100 镀锌', category='桥架', unit='米', quantity=120.0, unit_price=120.0, total_price=14400.0),
    ]

    pipes = [
        QuantityItem(id=str(uuid4()), component_id='P001', code='DL301', name='配管 SC40 镀锌钢管', category='配管', unit='米', quantity=220.0, unit_price=28.0, total_price=6160.0),
        QuantityItem(id=str(uuid4()), component_id='P002', code='DL302', name='配管 SC25 镀锌钢管', category='配管', unit='米', quantity=460.0, unit_price=18.0, total_price=8280.0),
    ]

    accessories = [
        QuantityItem(id=str(uuid4()), component_id='A001', code='DL401', name='接线盒', category='辅材', unit='个', quantity=160.0, unit_price=3.5, total_price=560.0),
        QuantityItem(id=str(uuid4()), component_id='A002', code='DL402', name='电缆头', category='辅材', unit='个', quantity=80.0, unit_price=45.0, total_price=3600.0),
    ]

    total_cost = sum(i.total_price for i in devices + cables + trunkings + pipes + accessories)

    calc = CalculationResult(
        id=str(uuid4()),
        drawing_id=drawing_id,
        devices=devices, cables=cables, trunkings=trunkings,
        pipes=pipes, accessories=accessories, total_cost=total_cost
    )

    # ---- 1) BIM 3D 构件 ----
    section("1) BIM 三维建模 (自动生成几何构件)")

    from bim_modeling.bim_generator import BIMGenerator
    from bim_modeling.model_manager import ModelManager

    bim_gen = BIMGenerator(scale_factor=1.0)
    components, geometries = bim_gen.generate_from_calculation(calc, drawing_data=None)

    # 从算量结果把 quantity/total_price 注入 BIM 构件（用于联动显示）
    all_items = devices + cables + trunkings + pipes + accessories
    for comp in components:
        for item in all_items:
            if comp.name and item.name and comp.name.split(' ')[0] in item.name[:12]:
                if isinstance(comp.attributes, dict):
                    comp.attributes['quantity'] = item.quantity
                    comp.attributes['unit'] = item.unit
                    comp.attributes['unit_price'] = item.unit_price
                    comp.attributes['total_price'] = item.total_price
                    comp.attributes['code'] = item.code
                break
        else:
            if isinstance(comp.attributes, dict) and 'quantity' not in comp.attributes:
                comp.attributes['quantity'] = 1.0
                comp.attributes['total_price'] = comp.attributes.get('unit_price', 0)

    mm = ModelManager()
    mm.add_components(components)
    bound = mm.bind_from_calculation(calc)

    print(f"    构件总数: {len(components)}")
    print(f"    已绑定工程量: {bound}")
    print(f"    绑定覆盖率: {mm.get_binding_report()['coverage'] * 100:.0f}%")
    print(f"    构件类型: {list({(c.type.value if hasattr(c.type, 'value') else str(c.type)) for c in components})}")

    # 导出 HTML 3D 查看器
    from bim_modeling.viewer3d import Viewer3D
    output_dir = "./outputs/four_in_one"
    os.makedirs(output_dir, exist_ok=True)
    html_path = os.path.join(output_dir, "bim_viewer_3d.html")
    Viewer3D().generate(mm, html_path)
    print(f"    3D 查看器: {os.path.abspath(html_path)}")

    # 导出 IFC
    from bim_modeling import IFCExporter
    ifc_path = os.path.join(output_dir, "bim_model.ifc")
    IFCExporter().export(components, ifc_path, project_name="四合一 DEMO 项目")
    print(f"    IFC 文件: {os.path.abspath(ifc_path)}")

    # ---- 2) 甲供材/劳务拆分 ----
    section("2) 甲供材 / 劳务 自动拆分")

    from material_labor_split import MaterialLaborSplitter, split_calculation
    splitter = MaterialLaborSplitter()
    split_result = splitter.split(calc)
    summary = split_result.summary

    print(f"    甲供设备: {len(split_result.owner_equipment)} 项, 金额 ¥{summary['owner_equipment_total']:,.0f}")
    print(f"    甲供材料: {len(split_result.owner_materials)} 项, 金额 ¥{summary['owner_materials_total']:,.0f}")
    print(f"    乙供    : {len(split_result.contractor)} 项, 金额 ¥{summary['contractor_total']:,.0f}")
    print(f"    劳务    : {len(split_result.labor)} 项, 金额 ¥{summary['labor_total']:,.0f}")
    print(f"    工程总造价: ¥{summary['grand_total']:,.0f}")

    # 导出 Excel
    excel_path = os.path.join(output_dir, "甲供材劳务拆分.xlsx")
    splitter.export_excel(split_result, excel_path)
    print(f"    拆分报表 Excel: {os.path.abspath(excel_path)}")

    # ---- 3) 结算报表 + ERP 对接 ----
    section("3) 项目结算报表自动生成 + ERP 对接")

    from settlement_report import SettlementReportGenerator, ERPClient, ReportExporter

    rgen = SettlementReportGenerator()
    report = rgen.generate_from_calc(
        calc,
        report_type='SETTLEMENT_V1',
        project_name="四合一 DEMO 项目 - 机电工程",
        project_code="DEMO-001",
        contractor="示例施工单位",
        owner="示例业主单位",
        period={'start': datetime.now().strftime('%Y-01-01'),
                'end': datetime.now().strftime('%Y-%m-%d')}
    )

    print(f"    报表 ID: {report.report_id}")
    print(f"    项目编码: {report.project_code}")
    print(f"    总金额: ¥{report.summary['total_amount']:,.0f}")
    print(f"    明细项数: {len(report.rows)}")

    report_excel = os.path.join(output_dir, "项目结算报表_DEMO001.xlsx")
    ReportExporter.to_excel(report, report_excel)
    print(f"    Excel 报表: {os.path.abspath(report_excel)}")

    # ERP 对接 (CSV 方式，简单可靠)
    erp_client = ERPClient('csv', {'output_dir': output_dir})
    erp_response = erp_client.submit(report)
    print(f"    ERP 推送 (CSV): {'OK' if erp_response.get('ok') else '失败'}")
    if 'path' in erp_response:
        print(f"    CSV 文件: {erp_response['path']}")

    # ---- 4) 移动端轻量化模型 + REST API ----
    section("4) 移动端轻量化模型 + REST API")

    from mobile_viewer.server import ProjectRepository, LightweightModelGenerator, create_app

    repository = ProjectRepository()
    pid = repository.add_project("四合一 DEMO 项目", code="DEMO-001")
    repository.set_components(pid, components)
    repository.set_calculation(pid, calc)

    print(f"    项目 ID: {pid}")
    print(f"    构件数: {len(components)}")

    # 生成轻量化 3D JSON
    lightweight_path = os.path.join(output_dir, "model_lightweight.json")
    LightweightModelGenerator().generate_simplified_json(components, lightweight_path)
    print(f"    轻量化模型文件: {os.path.abspath(lightweight_path)}")

    # 生成移动端 HTML (PWA-ready)
    mobile_html_path = os.path.join(output_dir, "mobile_viewer.html")
    html = generate_mobile_index()
    with open(mobile_html_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"    移动端网页主页: {os.path.abspath(mobile_html_path)}")

    # 生成 3D 查看器 HTML
    viewer_3d_path = os.path.join(output_dir, "viewer_3d.html")
    from mobile_viewer.server import generate_mobile_html
    html_3d = generate_mobile_html(pid, "四合一 DEMO 项目")
    with open(viewer_3d_path, 'w', encoding='utf-8') as f:
        f.write(html_3d)
    print(f"    3D 查看器网页: {os.path.abspath(viewer_3d_path)}")

    # ---- 汇总 ----
    section("✅ DEMO 完成 —— 输出文件汇总")
    files = [
        ("🏗️ BIM 3D 查看器 (HTML)", html_path),
        ("🏗️ IFC 模型 (.ifc)", ifc_path),
        ("📊 甲供材/劳务拆分 Excel", excel_path),
        ("📄 项目结算报表 Excel", report_excel),
        ("📦 轻量化模型 JSON", lightweight_path),
        ("📱 移动端项目主页 HTML", mobile_html_path),
        ("📱 移动端 3D 查看器 HTML", viewer_3d_path),
    ]

    for label, path in files:
        exists = "✅" if os.path.exists(path) else "❌"
        size = os.path.getsize(path) if os.path.exists(path) else 0
        print(f"    {exists} {label}")
        print(f"       → {path}  ({size / 1024:.1f} KB)")

    print("\n" + "=" * 80)
    print("🚀 启动 REST API 服务器 (访问 http://localhost:8000 查看网页端)")
    print("=" * 80)
    print("    指令: python -m mech_elec_ai_calculator.mobile_viewer.server")

    return {
        'output_dir': os.path.abspath(output_dir),
        'report': report,
        'split_result': split_result,
        'components': components,
        'project_id': pid,
    }


def generate_mobile_index():
    return """<!DOCTYPE html><html lang="zh-CN"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>BIM 移动端轻量化查看器</title>
<style>
body { font-family: -apple-system, sans-serif; margin: 0; background: #f5f5f5; color: #333; }
header { background: linear-gradient(135deg, #667eea, #764ba2); color: #fff; padding: 20px 15px;
  box-shadow: 0 3px 8px rgba(0,0,0,0.15); }
h1 { margin: 0 0 8px 0; font-size: 22px; } .subtitle { font-size: 12px; opacity: 0.9; }
.container { padding: 16px; max-width: 768px; margin: 0 auto; }
.card { background: #fff; border-radius: 12px; padding: 14px; margin-bottom: 12px;
  box-shadow: 0 2px 6px rgba(0,0,0,0.1); }
.card h2 { margin: 0 0 8px 0; font-size: 16px; }
.card .meta { color: #888; font-size: 12px; margin-bottom: 10px; }
.actions { display: flex; gap: 8px; flex-wrap: wrap; }
.btn { background: #667eea; color: #fff; padding: 10px 18px; border-radius: 8px;
  text-decoration: none; font-size: 13px; font-weight: 500; text-align: center; flex: 1; min-width: 80px; }
.btn.btn-secondary { background: #333; }
.btn.btn-gray { background: #888; }
</style></head>
<body><header>
<h1>🏗️ BIM 移动端查看器</h1><div class="subtitle">工程量查询 / 3D 模型 / 结算报表</div>
</header>
<div class="container">
<div class="card"><h2>四合一 DEMO 项目</h2><div class="meta">项目编码: DEMO-001</div>
<div class="actions">
<a class="btn" href="./viewer_3d.html">3D 查看</a>
<a class="btn btn-secondary" href="./甲供材劳务拆分.xlsx">甲供材拆分</a>
<a class="btn btn-gray" href="./项目结算报表_DEMO001.xlsx">结算报表</a>
</div></div>
</div></body></html>"""


if __name__ == "__main__":
    try:
        result = main()
        print(f"\n🎉 所有模块已正确运行！")
        print(f"   查看: open {result['output_dir']}/mobile_viewer.html")
        sys.exit(0)
    except Exception as exc:
        import traceback
        print(f"\n❌ 运行失败: {exc}")
        traceback.print_exc()
        sys.exit(1)
