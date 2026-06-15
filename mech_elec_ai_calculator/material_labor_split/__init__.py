"""
甲供材 / 劳务量 自动拆分模块
==================================

概念:
  • 甲供材 (Owner Supplied Material) - 业主/甲方采购的材料，不纳入工程造价
      例: 开关柜、变压器、高压电缆、灯具品牌、配电柜本体

  • 乙供材 / 乙供设备 (Contractor Supplied) - 施工单位采购
      例: 桥架、配管、普通电缆、辅材

  • 劳务量 (Labor Quantity) - 安装工时、安装人工单价、工日统计

本模块实现内容:
  1. 材料分类引擎 (关键词 + 规则字典)
  2. 工程量项自动标记 (owner/contractor/labor)
  3. 四类拆分: 甲供设备 / 甲供材料 / 乙供 / 劳务
  4. 输出: 拆分结果 (SplitResult)

示例结构:
  {
    'owner_equipment': [...],   # 甲供设备
    'owner_materials': [...],   # 甲供材料
    'contractor': [...],        # 乙供 (含辅材/设备)
    'labor': [...],             # 劳务工日
    'summary': { ... }
  }
"""

import os
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from uuid import uuid4

from common.models import QuantityItem, CalculationResult
from framework.exceptions import ParseError


# ============ 规则字典：甲供材关键词 ============
OWNER_EQUIPMENT_KEYWORDS = [
    # 电气设备（通常由业主采购）
    '配电柜', '开关柜', '配电柜', 'GGD', 'GCK', 'GCS', 'MNS', 'KYN', 'XGN',
    '变压器', '干式变压器', '油浸变压器', '干式', '变压器',
    '发电机', 'UPS', '不间断电源', 'EPS',
    '高压电缆', '高压电缆', '电力变压器', '发电机',
    '柴油发电机', '直流屏', '直流屏',
    '电容器柜',
    '软启动器', 'VFD', '变频器',
    '母线', '封闭母线', '母线槽',
    '柴油发电机组', '变压器房',
]

OWNER_MATERIAL_KEYWORDS = [
    # 甲方直接供应材料（非主材）
    '高压', '高压电缆', '矿物绝缘电缆', '矿物质电缆', 'BTTZ', 'BTLY',
    '防火电缆', 'NG-A', 'NG-A(BTLY)', '耐火',
    '铜排', '母排', '母线', '密集母线',
    '配电箱', 'PZ30', 'XM', '照明箱', '照明配电箱', '动力配电箱',
    '电缆桥架', '桥架', '镀锌桥架', '不锈钢桥架', '铝合金桥架',
]

LABOR_RULES = {
    # 劳务拆分系数 (人工费 / 材料费 %):
    # 参考: GB50500-2013 建设工程工程量清单计价规范
    # 及各地方定额
    '配电柜': {'labor_ratio': 0.08, 'material_ratio': 0.72, 'equipment_ratio': 0.20, 'machine_ratio': 0.0},
    '配电箱': {'labor_ratio': 0.10, 'material_ratio': 0.65, 'equipment_ratio': 0.25, 'machine_ratio': 0.0},
    '电缆': {'labor_ratio': 0.15, 'material_ratio': 0.80, 'equipment_ratio': 0.0, 'machine_ratio': 0.05},
    '桥架': {'labor_ratio': 0.25, 'material_ratio': 0.70, 'equipment_ratio': 0.0, 'machine_ratio': 0.05},
    '配管': {'labor_ratio': 0.30, 'material_ratio': 0.65, 'equipment_ratio': 0.0, 'machine_ratio': 0.05},
    '开关': {'labor_ratio': 0.40, 'material_ratio': 0.60, 'equipment_ratio': 0.0, 'machine_ratio': 0.0},
    '插座': {'labor_ratio': 0.35, 'material_ratio': 0.65, 'equipment_ratio': 0.0, 'machine_ratio': 0.0},
    '灯具': {'labor_ratio': 0.25, 'material_ratio': 0.75, 'equipment_ratio': 0.0, 'machine_ratio': 0.0},
    'default': {'labor_ratio': 0.20, 'material_ratio': 0.60, 'equipment_ratio': 0.15, 'machine_ratio': 0.05},
}


# ============ 数据结构 ============
@dataclass
class SplitDetail:
    """单项拆分"""
    item_id: str
    name: str
    category: str
    quantity: float
    unit: str
    unit_price: float
    total_price: float
    supply_type: str          # 'owner_equipment' | 'owner_material' | 'contractor' | 'labor'
    labor_quantity: float = 0.0
    labor_amount: float = 0.0
    material_amount: float = 0.0
    equipment_amount: float = 0.0
    machine_amount: float = 0.0
    split_ratio: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SplitResult:
    """整体拆分结果"""
    calculation_id: str
    owner_equipment: List[SplitDetail]
    owner_materials: List[SplitDetail]
    contractor: List[SplitDetail]
    labor: List[SplitDetail]
    summary: Dict[str, Any]


# ============ 拆分引擎 ============
class MaterialLaborSplitter:
    """
    甲供材 / 劳务量 自动拆分引擎

    Usage:
        from mech_elec_ai_calculator.material_labor_split import MaterialLaborSplitter
        splitter = MaterialLaborSplitter()
        split_result = splitter.split(calculation_result)
        # 或从 JSON / 清单文件
        split_result = splitter.split_from_items(quantity_items)
        splitter.export_excel(split_result, 'outputs/甲供材拆分.xlsx')
        splitter.export_json(split_result, 'outputs/甲供材拆分.json')
    """

    def __init__(self, custom_rules: Optional[Dict[str, Any]] = None):
        self.owner_equipment_keywords = list(OWNER_EQUIPMENT_KEYWORDS)
        self.owner_material_keywords = list(OWNER_MATERIAL_KEYWORDS)
        self.labor_rules = {k: dict(v) for k, v in LABOR_RULES.items()}

        if custom_rules:
            if 'owner_equipment' in custom_rules:
                self.owner_equipment_keywords.extend(custom_rules['owner_equipment'])
            if 'owner_materials' in custom_rules:
                self.owner_material_keywords.extend(custom_rules['owner_materials'])
            if 'labor_ratios' in custom_rules:
                for k, v in custom_rules['labor_ratios'].items():
                    self.labor_rules[k] = v

    # ============ 判定逻辑 ============

    def classify(self, item_name: str, item_category: str) -> str:
        """判断一项工程量的供应类型"""
        name = str(item_name)
        cat = str(item_category).lower()

        # 优先匹配甲供设备 (优先级最高)
        for kw in self.owner_equipment_keywords:
            if kw in name:
                return 'owner_equipment'

        # 其次匹配甲供材料
        for kw in self.owner_material_keywords:
            if kw in name:
                return 'owner_material'

        # 按分类规则 (甲供材类别名 / 设备类判断)
        if '设备' in cat or 'cabinet' in cat or 'equipment' in cat:
            return 'owner_equipment'

        # 默认乙供
        return 'contractor'

    def _get_labor_rule(self, item_name: str) -> Dict[str, float]:
        """根据名称选择劳务拆分规则"""
        for key in ['配电柜', '配电箱', '电缆', '桥架', '配管', '开关', '插座', '灯具']:
            if key in item_name:
                return self.labor_rules[key]
        return self.labor_rules['default']

    # ============ 主入口 ============

    def split(self, calc: CalculationResult) -> SplitResult:
        """从算量结果拆分"""
        all_items = list(calc.devices) + list(calc.cables) + list(calc.trunkings) + list(calc.pipes) + list(calc.accessories)
        return self._split_items(all_items, calc.id)

    def split_from_items(self, items: List[QuantityItem], calc_id: Optional[str] = None) -> SplitResult:
        return self._split_items(items, calc_id or str(uuid4()))

    # ============ 实现 ============

    def _split_items(self, items: List[QuantityItem], calc_id: str) -> SplitResult:
        owner_equipment: List[SplitDetail] = []
        owner_materials: List[SplitDetail] = []
        contractor: List[SplitDetail] = []
        labor_list: List[SplitDetail] = []

        for item in items:
            supply_type = self.classify(item.name, item.category)
            rule = self._get_labor_rule(item.name)

            labor_qty = item.quantity
            total = item.total_price or (item.quantity * item.unit_price)

            labor_amount = total * rule['labor_ratio']
            material_amount = total * rule['material_ratio']
            equipment_amount = total * rule['equipment_ratio']
            machine_amount = total * rule['machine_ratio']

            detail = SplitDetail(
                item_id=item.id,
                name=item.name,
                category=item.category,
                quantity=item.quantity,
                unit=item.unit,
                unit_price=item.unit_price,
                total_price=total,
                supply_type=supply_type,
                labor_quantity=labor_qty,
                labor_amount=labor_amount,
                material_amount=material_amount,
                equipment_amount=equipment_amount,
                machine_amount=machine_amount,
                split_ratio="人{:.0f}% / 材{:.0f}% / 机{:.0f}%".format(
                    rule['labor_ratio'] * 100, rule['material_ratio'] * 100, rule['machine_ratio'] * 100
                ),
                attributes={
                    'rule': rule,
                    'code': item.code,
                    'description': item.description,
                }
            )

            if supply_type == 'owner_equipment':
                owner_equipment.append(detail)
            elif supply_type == 'owner_material':
                owner_materials.append(detail)
            elif supply_type == 'labor':
                labor_list.append(detail)
            else:
                contractor.append(detail)

        summary = self._make_summary(owner_equipment, owner_materials, contractor, labor_list)
        return SplitResult(
            calculation_id=calc_id,
            owner_equipment=owner_equipment,
            owner_materials=owner_materials,
            contractor=contractor,
            labor=labor_list,
            summary=summary,
        )

    def _make_summary(self,
                      owner_equipment, owner_materials, contractor, labor) -> Dict[str, Any]:
        def sum_list(lst):
            return sum(d.total_price for d in lst)

        total_owner = sum_list(owner_equipment) + sum_list(owner_materials)
        total_contractor = sum_list(contractor)
        total_labor = sum_list(labor)

        return {
            'owner_equipment_total': total_owner,
            'owner_materials_total': sum_list(owner_materials),
            'contractor_total': total_contractor,
            'labor_total': total_labor,
            'grand_total': total_owner + total_contractor + total_labor,
            'owner_equipment_count': len(owner_equipment),
            'owner_materials_count': len(owner_materials),
            'contractor_count': len(contractor),
            'labor_count': len(labor),
        }

    # ============ 导出 ============

    def export_json(self, result: SplitResult, output_path: str) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            data = {
                'calculation_id': result.calculation_id,
                'owner_equipment': [asdict(x) for x in result.owner_equipment],
                'owner_materials': [asdict(x) for x in result.owner_materials],
                'contractor': [asdict(x) for x in result.contractor],
                'labor': [asdict(x) for x in result.labor],
                'summary': result.summary,
            }
            json.dump(data, f, ensure_ascii=False, indent=2)
        return output_path

    def export_excel(self, result: SplitResult, output_path: str) -> str:
        """导出 Excel —— 四个工作簿: 甲供设备 / 甲供材料 / 乙供 / 劳务 + 汇总表"""
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        import os
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        wb = Workbook()
        wb.remove(wb.active)

        headers = ['项目编码', '项目名称', '分类', '数量', '单位', '单价', '合价', '人工费', '材料费', '设备费', '机械费', '供应方式']

        thin_border = Border(
            left=Side(style='thin'), right=Side(style='thin'),
            top=Side(style='thin'), bottom=Side(style='thin')
        )

        def write_sheet(ws_name: str, rows: List[SplitDetail]):
            ws = wb.create_sheet(ws_name)
            for col, h in enumerate(headers, 1):
                cell = ws.cell(row=1, column=col, value=h)
                cell.font = Font(bold=True)
                cell.fill = PatternFill("solid", fgColor="D9D9D9")
                cell.alignment = Alignment(horizontal='center')
                cell.border = thin_border

            total_qty = 0.0
            total_price = 0.0
            total_labor = 0.0
            total_material = 0.0
            total_equipment = 0.0
            total_machine = 0.0

            for r, d in enumerate(rows, 2):
                ws.cell(row=r, column=1, value=d.attributes.get('code', '')).border = thin_border
                ws.cell(row=r, column=2, value=d.name).border = thin_border
                ws.cell(row=r, column=3, value=d.category).border = thin_border
                ws.cell(row=r, column=4, value=round(d.quantity, 4)).border = thin_border
                ws.cell(row=r, column=5, value=d.unit).border = thin_border
                ws.cell(row=r, column=6, value=round(d.unit_price, 2)).border = thin_border
                ws.cell(row=r, column=7, value=round(d.total_price, 2)).border = thin_border
                ws.cell(row=r, column=8, value=round(d.labor_amount, 2)).border = thin_border
                ws.cell(row=r, column=9, value=round(d.material_amount, 2)).border = thin_border
                ws.cell(row=r, column=10, value=round(d.equipment_amount, 2)).border = thin_border
                ws.cell(row=r, column=11, value=round(d.machine_amount, 2)).border = thin_border
                ws.cell(row=r, column=12, value=self._translate_supply_type(d.supply_type)).border = thin_border
                total_qty += d.quantity
                total_price += d.total_price
                total_labor += d.labor_amount
                total_material += d.material_amount
                total_equipment += d.equipment_amount
                total_machine += d.machine_amount

            r = len(rows) + 3
            totals = {
                4: total_qty, 7: total_price, 8: total_labor,
                9: total_material, 10: total_equipment, 11: total_machine
            }
            ws.cell(row=r, column=1, value="合计").font = Font(bold=True)
            for c, v in totals.items():
                cell = ws.cell(row=r, column=c, value=round(v, 2))
                cell.font = Font(bold=True)
                cell.fill = PatternFill("solid", fgColor="FFFFCC")
                cell.border = thin_border

            ws.cell(row=r, column=12, value=f'共{len(rows)}项').font = Font(bold=True)

            for col_idx in range(1, 13):
                ws.column_dimensions[chr(64 + col_idx)].width = 8 if col_idx == 1 else (30 if col_idx == 2 else 12)

        # 写每个表
        write_sheet('甲供设备', result.owner_equipment)
        write_sheet('甲供材料', result.owner_materials)
        write_sheet('乙供材-设备', result.contractor)
        write_sheet('劳务用量', result.labor)

        # 汇总表
        s = result.summary
        ws = wb.create_sheet('汇总表')
        summary_rows = [
            ['甲供设备合计', s['owner_equipment_count'], s['owner_equipment_total']],
            ['甲供材料合计', s['owner_materials_count'], s['owner_materials_total']],
            ['乙供材/设备合计', s['contractor_count'], s['contractor_total']],
            ['劳务/工日', s['labor_count'], s['labor_total']],
        ]
        ws.cell(row=1, column=1, value='类别').font = Font(bold=True)
        ws.cell(row=1, column=2, value='项数').font = Font(bold=True)
        ws.cell(row=1, column=3, value='金额(元)').font = Font(bold=True)
        ws.cell(row=1, column=4, value='占比(%)').font = Font(bold=True)
        for i, (name, cnt, price) in enumerate(summary_rows, 2):
            ws.cell(row=i, column=1, value=name)
            ws.cell(row=i, column=2, value=cnt)
            ws.cell(row=i, column=3, value=round(price, 2))
            ws.cell(row=i, column=4,
                     value=round(price / s['grand_total'] * 100, 1) if s['grand_total'] else 0)
        ws.cell(row=6, column=1, value='总计').font = Font(bold=True)
        ws.cell(row=6, column=3, value=round(s['grand_total'], 2)).font = Font(bold=True)
        ws.column_dimensions['A'].width = 22
        ws.column_dimensions['B'].width = 10
        ws.column_dimensions['C'].width = 15
        ws.column_dimensions['D'].width = 12

        wb.save(output_path)
        return output_path

    @staticmethod
    def _translate_supply_type(st: str) -> str:
        return {
            'owner_equipment': '甲供设备',
            'owner_material': '甲供材料',
            'contractor': '乙供',
            'labor': '劳务',
        }.get(st, st)


# ============ 快速使用 ============
def split_calculation(calc: CalculationResult, output_dir: str, project_name: str = "项目") -> Dict[str, Any]:
    """便捷函数：对算量结果执行拆分并导出"""
    splitter = MaterialLaborSplitter()
    result = splitter.split(calc)

    os.makedirs(output_dir, exist_ok=True)
    xlsx_path = os.path.join(output_dir, f"甲供材劳务拆分_{project_name}.xlsx")
    json_path = os.path.join(output_dir, f"甲供材劳务拆分_{project_name}.json")

    splitter.export_excel(result, xlsx_path)
    splitter.export_json(result, json_path)

    return {
        'xlsx': xlsx_path,
        'json': json_path,
        'summary': result.summary,
        'result': result,
    }
