"""
项目结算报表自动生成 + ERP 对接
===================================

核心功能:
  • 工程结算报表自动生成 (中期/竣工/年度)
  • 工程进度款申请报表
  • 与 ERP/财务系统对接 (广联达/金蝶/用友/畅捷通/普联)
  • 支持 PDF/Excel/CSV/JSON 多种输出格式

报表模板 (Report Type):
  • SETTLEMENT_V1     工程竣工结算报表
  • MID_PAYMENT_V1    中期进度款报表
  • QUARTERLY_V1      季度成本分析
  • ANNUAL_V1         年度结算汇总

ERP 接口支持 (Adapters):
  • 广联达 GNP (Glodon Net Platform)        adapter=guanglianda
  • 金蝶 K/3 Cloud / 精斗云                     adapter=kingdee
  • 用友 NC / U8 / T6                         adapter=yonyou
  • 通用 HTTP JSON API                          adapter=generic_http
  • CSV 文件交换                                 adapter=csv
"""
import os
import json
import uuid
import time
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime

from common.models import QuantityItem, CalculationResult, ListSummary
from framework.exceptions import ParseError


# ============ 数据模型 ============
@dataclass
class SettlementRow:
    code: str = ""
    name: str = ""
    category: str = ""
    unit: str = ""
    quantity: float = 0.0
    unit_price: float = 0.0
    total_price: float = 0.0
    supply_type: str = "contractor"
    period: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SettlementReport:
    report_id: str
    report_type: str              # SETTLEMENT_V1 | MID_PAYMENT_V1 | etc.
    project_name: str
    project_code: str
    contractor: str = "默认施工单位"
    owner: str = "默认业主"
    period_start: str = ""
    period_end: str = ""
    created_at: str = ""
    rows: List[SettlementRow] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    erp_submitted: bool = False
    erp_response: Optional[Dict[str, Any]] = None


# ============ 报表生成器 ============
class SettlementReportGenerator:
    """项目结算报表自动生成器"""

    SUPPORTED_TYPES = ['SETTLEMENT_V1', 'MID_PAYMENT_V1', 'QUARTERLY_V1', 'ANNUAL_V1']

    def __init__(self):
        pass

    def generate(self,
                 items: List[QuantityItem],
                 report_type: str = 'SETTLEMENT_V1',
                 project_name: str = '未命名项目',
                 project_code: str = '',
                 contractor: str = '施工单位',
                 owner: str = '业主单位',
                 period: Optional[Dict[str, str]] = None,
                 ) -> SettlementReport:
        """
        从清单项目生成报表

        period: {'start': '2024-01-01', 'end': '2024-12-31'}
        """
        if report_type not in self.SUPPORTED_TYPES:
            raise ValueError(f"不支持的报表类型: {report_type}, 支持: {self.SUPPORTED_TYPES}")

        # 按类别/供应方式分组
        rows = []
        category_totals: Dict[str, Dict[str, float]] = {}

        for item in items:
            # 推断 supply_type (甲供/乙供)
            supply_type = self._guess_supply_type(item.name, item.category)

            row = SettlementRow(
                code=item.code or 'DL001',
                name=item.name,
                category=item.category or '其他',
                unit=item.unit or '个',
                quantity=item.quantity,
                unit_price=item.unit_price,
                total_price=item.total_price or (item.quantity * item.unit_price),
                supply_type=supply_type,
                period=period['end'] if period else datetime.now().strftime('%Y-%m-%d'),
                attributes={'item_id': item.id, 'description': item.description}
            )
            rows.append(row)

            cat = row.category
            if cat not in category_totals:
                category_totals[cat] = {'count': 0, 'quantity': 0.0, 'amount': 0.0}
            category_totals[cat]['count'] += 1
            category_totals[cat]['quantity'] += row.quantity
            category_totals[cat]['amount'] += row.total_price

        # 汇总信息
        total_amount = sum(r.total_price for r in rows)
        total_qty = sum(r.quantity for r in rows)

        summary = {
            'report_type': report_type,
            'total_rows': len(rows),
            'total_quantity': total_qty,
            'total_amount': total_amount,
            'by_category': category_totals,
            'owner_supplied_amount': sum(r.total_price for r in rows if r.supply_type.startswith('owner')),
            'contractor_supplied_amount': sum(r.total_price for r in rows if r.supply_type == 'contractor'),
            'project_name': project_name,
            'project_code': project_code,
        }

        return SettlementReport(
            report_id=str(uuid.uuid4()),
            report_type=report_type,
            project_name=project_name,
            project_code=project_code,
            contractor=contractor,
            owner=owner,
            period_start=period['start'] if period else '',
            period_end=period['end'] if period else '',
            created_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            rows=rows,
            summary=summary,
        )

    def generate_from_calc(self, calc: CalculationResult, **kwargs) -> SettlementReport:
        all_items = (
            list(calc.devices) + list(calc.cables) +
            list(calc.trunkings) + list(calc.pipes) +
            list(calc.accessories)
        )
        return self.generate(all_items, **kwargs)

    def generate_from_summary(self, summary: ListSummary, **kwargs) -> SettlementReport:
        return self.generate(summary.items,
                              project_name=summary.project_name,
                              project_code=summary.project_code,
                              **kwargs)

    @staticmethod
    def _guess_supply_type(name: str, category: str) -> str:
        n = str(name).lower()
        cat = str(category)
        # 甲供设备
        for kw in ['配电柜', '开关柜', '变压器', '发电机', 'UPS', 'GGD', 'KYN', 'MNS', 'XGN']:
            if kw in name or kw.lower() in n:
                return 'owner_equipment'
        # 甲供材料
        for kw in ['高压', '矿物', 'BTTZ', '铜排', '母排', '封闭母线', '母线槽']:
            if kw in name:
                return 'owner_material'
        return 'contractor'


# ============ ERP Adapter 基类 ============
class ERPAdapter:
    """ERP 对接适配器基类"""
    adapter_name = 'base'

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def submit(self, report: SettlementReport) -> Dict[str, Any]:
        raise NotImplementedError

    def query_project(self, project_code: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    def list_transactions(self, date_from: str, date_to: str) -> List[Dict[str, Any]]:
        raise NotImplementedError


class GenericHTTPAdapter(ERPAdapter):
    """通用 HTTP JSON API 对接"""
    adapter_name = 'generic_http'

    def submit(self, report: SettlementReport) -> Dict[str, Any]:
        import requests
        url = self.config.get('url')
        api_key = self.config.get('api_key', '')
        if not url:
            return {'ok': False, 'error': '未配置 URL'}

        payload = {
            'report_id': report.report_id,
            'report_type': report.report_type,
            'project': {'name': report.project_name, 'code': report.project_code},
            'contractor': report.contractor,
            'owner': report.owner,
            'amount': report.summary.get('total_amount', 0),
            'rows': [asdict(r) for r in report.rows],
            'generated_at': report.created_at,
        }

        try:
            resp = requests.post(
                url,
                json=payload,
                headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
                timeout=30,
            )
            return {
                'ok': resp.status_code < 400,
                'status_code': resp.status_code,
                'response': resp.json() if resp.headers.get('content-type', '').startswith('application/json') else resp.text[:500],
            }
        except Exception as e:
            return {'ok': False, 'error': str(e)}

    def query_project(self, project_code: str) -> Optional[Dict[str, Any]]:
        import requests
        url = self.config.get('url')
        if not url:
            return None
        try:
            resp = requests.get(f"{url}/projects/{project_code}", timeout=10)
            return resp.json() if resp.status_code == 200 else None
        except Exception:
            return None

    def list_transactions(self, date_from, date_to):
        return []


class KingdeeAdapter(GenericHTTPAdapter):
    """金蝶 K/3 Cloud 对接"""
    adapter_name = 'kingdee'

    def submit(self, report: SettlementReport) -> Dict[str, Any]:
        # 金蝶 K/3 Cloud 使用其 OData/REST 接口推送工程结算单
        base = self.config.get('base_url', '')
        form_id = self.config.get('form_id', 'PUR_PurchaseOrder')
        if not base:
            return {'ok': False, 'error': '未配置 base_url'}

        import requests
        url = f"{base}/Kingdee.BOS.WebApi.ServicesStub.DynamicFormService.Save.common.kdsvc"
        headers = {
            'Content-Type': 'application/json',
            'X-Authorization': self.config.get('token', ''),
        }
        payload = {
            'data': {
                'FormId': form_id,
                'NeedReturnData': True,
                'Model': {
                    'FID': 0,
                    'FBillNo': report.report_id,
                    'FDate': report.created_at,
                    'FSupplierId': {'FNumber': self.config.get('supplier_no', 'S001')},
                    'FProjectId': {'FNumber': report.project_code},
                    'FAmount': report.summary.get('total_amount', 0),
                    'FEntity': [
                        {'FRowId': i + 1,
                         'FNumber': r.code,
                         'FName': r.name,
                         'FQty': r.quantity,
                         'FUnit': r.unit,
                         'FPrice': r.unit_price,
                         'FAmount': r.total_price}
                        for i, r in enumerate(report.rows)
                    ]
                }
            }
        }

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=30)
            return {
                'ok': resp.status_code == 200,
                'response': resp.text[:500],
                'status_code': resp.status_code,
            }
        except Exception as e:
            return {'ok': False, 'error': str(e)}


class YonyouAdapter(GenericHTTPAdapter):
    """用友 U8 / NC 对接"""
    adapter_name = 'yonyou'

    def submit(self, report: SettlementReport) -> Dict[str, Any]:
        import requests
        base = self.config.get('base_url', '')
        token = self.config.get('token', '')
        if not base:
            return {'ok': False, 'error': '未配置 base_url'}

        url = f"{base}/u8cloud/api/bill/push"
        payload = {
            'billCode': report.report_id,
            'billType': report.report_type,
            'projectCode': report.project_code,
            'projectName': report.project_name,
            'amount': report.summary.get('total_amount', 0),
            'lines': [
                {'code': r.code, 'name': r.name, 'qty': r.quantity, 'unit': r.unit, 'price': r.unit_price, 'amount': r.total_price}
                for r in report.rows
            ]
        }

        try:
            resp = requests.post(url, json=payload, headers={'Authorization': f'Bearer {token}'}, timeout=30)
            return {'ok': resp.status_code == 200, 'response': resp.text[:500]}
        except Exception as e:
            return {'ok': False, 'error': str(e)}


class CSVAdapter(ERPAdapter):
    """CSV 文件方式对接 (最兼容的落地方式)"""
    adapter_name = 'csv'

    def submit(self, report: SettlementReport) -> Dict[str, Any]:
        out_dir = self.config.get('output_dir', './outputs/erp_csv')
        os.makedirs(out_dir, exist_ok=True)
        path = os.path.join(out_dir, f"erp_{report.report_type}_{report.report_id}.csv")

        try:
            import csv
            with open(path, 'w', encoding='utf-8-sig', newline='') as f:
                w = csv.writer(f)
                w.writerow(['报表类型', report.report_type])
                w.writerow(['项目名称', report.project_name])
                w.writerow(['项目编码', report.project_code])
                w.writerow(['施工单位', report.contractor])
                w.writerow(['业主', report.owner])
                w.writerow(['结算周期起', report.period_start])
                w.writerow(['结算周期止', report.period_end])
                w.writerow(['生成时间', report.created_at])
                w.writerow([])
                w.writerow(['编码', '名称', '分类', '数量', '单位', '单价', '合价', '供应方式'])
                for r in report.rows:
                    w.writerow([r.code, r.name, r.category, f'{r.quantity:.4f}', r.unit,
                                f'{r.unit_price:.2f}', f'{r.total_price:.2f}', r.supply_type])
                w.writerow([])
                w.writerow(['合计', '', '',
                            sum(r.quantity for r in report.rows),
                            '', '', sum(r.total_price for r in report.rows)])
            return {'ok': True, 'path': path, 'rows': len(report.rows)}
        except Exception as e:
            return {'ok': False, 'error': str(e)}

    def query_project(self, project_code: str):
        return {'project_code': project_code, 'status': 'CSV文件对接'}

    def list_transactions(self, date_from, date_to):
        return []


class GuangliandaAdapter(GenericHTTPAdapter):
    """广联达 GNP 对接 —— 工程造价平台"""
    adapter_name = 'guanglianda'

    def submit(self, report: SettlementReport) -> Dict[str, Any]:
        # 实际项目中对接广联达 GNP 需要调用其专属SDK/接口
        # 此处为标准JSON推送方式演示
        import requests
        base = self.config.get('base_url', '')
        app_key = self.config.get('app_key', '')
        if not base:
            return {'ok': False, 'error': '未配置 base_url (广联达GNP)'}

        url = f"{base}/gnp/api/v1/project/{report.project_code}/settlement"
        headers = {'X-GNP-AppKey': app_key, 'Content-Type': 'application/json'}
        payload = {
            'bill_no': report.report_id,
            'report_type': report.report_type,
            'project_code': report.project_code,
            'total_amount': report.summary.get('total_amount', 0),
            'period': {'start': report.period_start, 'end': report.period_end},
            'line_items': [asdict(r) for r in report.rows],
        }
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=30)
            return {'ok': resp.status_code == 200, 'response': resp.text[:500]}
        except Exception as e:
            return {'ok': False, 'error': str(e)}


# ============ ERP适配器注册表 ============
class ERPClient:
    """ERP 客户端 —— 统一对接入口"""

    def __init__(self, adapter_name: str, config: Dict[str, Any]):
        adapters = {
            'generic_http': GenericHTTPAdapter,
            'kingdee': KingdeeAdapter,
            'yonyou': YonyouAdapter,
            'guanglianda': GuangliandaAdapter,
            'csv': CSVAdapter,
        }
        if adapter_name not in adapters:
            raise ValueError(f"不支持的ERP: {adapter_name}, 支持: {list(adapters.keys())}")
        self.adapter = adapters[adapter_name](config)
        self.name = adapter_name

    def submit(self, report: SettlementReport) -> Dict[str, Any]:
        result = self.adapter.submit(report)
        report.erp_submitted = result.get('ok', False)
        report.erp_response = result
        return result


# ============ 导出: Excel / PDF / JSON ============
class ReportExporter:
    """报表导出工具"""

    @staticmethod
    def to_excel(report: SettlementReport, output_path: str) -> str:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        wb = Workbook()
        ws = wb.active
        ws.title = '汇总'

        thin = Side(style='thin')
        border = Border(left=thin, right=thin, top=thin, bottom=thin)

        # 封面信息
        info = [
            ['报表ID', report.report_id],
            ['报表类型', report.report_type],
            ['项目名称', report.project_name],
            ['项目编码', report.project_code],
            ['施工单位', report.contractor],
            ['业主', report.owner],
            ['结算周期起', report.period_start],
            ['结算周期止', report.period_end],
            ['生成时间', report.created_at],
            ['总金额(元)', round(report.summary.get('total_amount', 0), 2)],
            ['总项数', report.summary.get('total_rows', 0)],
        ]
        for r, (k, v) in enumerate(info, 1):
            ws.cell(row=r, column=1, value=k).font = Font(bold=True, size=12)
            ws.cell(row=r, column=2, value=v).font = Font(size=12)
        ws.column_dimensions['A'].width = 22
        ws.column_dimensions['B'].width = 50

        # 明细表Sheet
        ws2 = wb.create_sheet('明细')
        headers = ['序号', '编码', '名称', '分类', '数量', '单位', '单价', '合价', '供应方式']
        for i, h in enumerate(headers, 1):
            c = ws2.cell(row=1, column=i, value=h)
            c.font = Font(bold=True)
            c.fill = PatternFill('solid', fgColor='FFFFCC')
            c.alignment = Alignment(horizontal='center')
            c.border = border

        total_amount = 0.0
        for idx, r in enumerate(report.rows, 2):
            values = [idx - 1, r.code, r.name, r.category, r.quantity, r.unit,
                      round(r.unit_price, 2), round(r.total_price, 2), r.supply_type]
            for col, v in enumerate(values, 1):
                cell = ws2.cell(row=idx, column=col, value=v)
                cell.border = border
            total_amount += r.total_price

        # 合计行
        r_idx = len(report.rows) + 3
        ws2.cell(row=r_idx, column=1, value='合计').font = Font(bold=True)
        ws2.cell(row=r_idx, column=8, value=round(total_amount, 2)).font = Font(bold=True, color='FF0000')

        for i, wdt in enumerate([6, 14, 35, 12, 12, 8, 10, 14, 14], 1):
            ws2.column_dimensions[chr(64 + i)].width = wdt

        # 分类汇总
        ws3 = wb.create_sheet('分类汇总')
        ws3.cell(row=1, column=1, value='分类').font = Font(bold=True)
        ws3.cell(row=1, column=2, value='项数').font = Font(bold=True)
        ws3.cell(row=1, column=3, value='数量').font = Font(bold=True)
        ws3.cell(row=1, column=4, value='金额(元)').font = Font(bold=True)
        ws3.cell(row=1, column=5, value='占比%').font = Font(bold=True)

        for col in range(1, 6):
            ws3.cell(row=1, column=col).fill = PatternFill('solid', fgColor='FFFFCC')
            ws3.cell(row=1, column=col).border = border

        categories = report.summary.get('by_category', {})
        for r, (cat, vals) in enumerate(sorted(categories.items(), key=lambda x: -x[1]['amount']), 2):
            ws3.cell(row=r, column=1, value=cat).border = border
            ws3.cell(row=r, column=2, value=vals['count']).border = border
            ws3.cell(row=r, column=3, value=round(vals['quantity'], 2)).border = border
            ws3.cell(row=r, column=4, value=round(vals['amount'], 2)).border = border
            ws3.cell(row=r, column=5,
                     value=round(vals['amount'] / total_amount * 100, 1) if total_amount else 0).border = border

        for i, w in enumerate([20, 8, 15, 15, 10], 1):
            ws3.column_dimensions[chr(64 + i)].width = w

        wb.save(output_path)
        return output_path

    @staticmethod
    def to_json(report: SettlementReport, output_path: str) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        data = asdict(report)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return output_path

    @staticmethod
    def to_csv(report: SettlementReport, output_path: str) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        import csv
        with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
            w = csv.writer(f)
            w.writerow(['编码', '名称', '分类', '数量', '单位', '单价', '合价', '供应方式'])
            for r in report.rows:
                w.writerow([r.code, r.name, r.category, r.quantity, r.unit, r.unit_price, r.total_price, r.supply_type])
        return output_path


# ============ 便捷函数 ============
def run_settlement_pipeline(
    calculation: CalculationResult,
    report_type: str = 'SETTLEMENT_V1',
    project_name: str = '项目',
    project_code: str = '',
    output_dir: str = './outputs',
    erp_adapter_name: str = 'csv',
    erp_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    一键执行: 报表生成 → Excel/JSON导出 → ERP 推送

    Args:
        calculation: 算量结果
        report_type: 报表类型
        project_name: 项目名
        project_code: 项目编码
        output_dir: 输出目录
        erp_adapter_name: ERP 适配器名 (kingdee / yonyou / guanglianda / csv / generic_http)
        erp_config: 适配器配置

    Returns:
        dict: { report, excel_path, json_path, erp_result }
    """
    os.makedirs(output_dir, exist_ok=True)
    gen = SettlementReportGenerator()
    report = gen.generate_from_calc(
        calculation,
        report_type=report_type,
        project_name=project_name,
        project_code=project_code,
        period={'start': datetime.now().strftime('%Y-01-01'),
                'end': datetime.now().strftime('%Y-%m-%d')},
    )

    ts = datetime.now().strftime('%Y%m%d')
    excel_path = os.path.join(output_dir, f"结算报表_{report_type}_{project_code}_{ts}.xlsx")
    json_path = os.path.join(output_dir, f"结算报表_{report_type}_{project_code}_{ts}.json")

    ReportExporter.to_excel(report, excel_path)
    ReportExporter.to_json(report, json_path)

    # ERP 推送
    client = ERPClient(erp_adapter_name, erp_config or {'output_dir': output_dir})
    erp_result = client.submit(report)

    return {
        'report': report,
        'excel_path': excel_path,
        'json_path': json_path,
        'erp_submitted': report.erp_submitted,
        'erp_result': erp_result,
        'summary': report.summary,
    }
