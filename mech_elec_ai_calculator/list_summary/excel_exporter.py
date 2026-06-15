import os
from typing import List
from common.models import ListSummary, QuantityItem
from framework.exceptions import FileError

class ExcelExporter:
    def __init__(self):
        pass
    
    def export(self, summary: ListSummary, output_path: str) -> str:
        try:
            try:
                import openpyxl
                from openpyxl.styles import Font, Alignment, Border, Side
                from openpyxl.utils import get_column_letter
            except ImportError:
                return self._export_csv(summary, output_path)
            
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "工程量清单"
            
            # 写入表头
            headers = ['序号', '定额编号', '项目名称', '规格型号', '计量单位', '工程量', '单价(元)', '合价(元)', '分类', '子分类', '备注']
            for col, header in enumerate(headers, 1):
                ws.cell(row=1, column=col, value=header)
                ws.cell(row=1, column=col).font = Font(bold=True)
            
            # 写入数据
            for row_idx, item in enumerate(summary.items, 2):
                ws.cell(row=row_idx, column=1, value=row_idx-1)
                ws.cell(row=row_idx, column=2, value=item.code)
                ws.cell(row=row_idx, column=3, value=item.name)
                ws.cell(row=row_idx, column=4, value='')
                ws.cell(row=row_idx, column=5, value=item.unit)
                ws.cell(row=row_idx, column=6, value=item.quantity)
                ws.cell(row=row_idx, column=7, value=item.unit_price)
                ws.cell(row=row_idx, column=8, value=item.total_price)
                ws.cell(row=row_idx, column=9, value=item.category)
                ws.cell(row=row_idx, column=10, value=item.sub_category)
                ws.cell(row=row_idx, column=11, value=item.description)
            
            # 写入合计
            last_row = len(summary.items) + 2
            ws.cell(row=last_row, column=1, value='合计')
            ws.cell(row=last_row, column=8, value=summary.total_cost)
            
            # 写入项目信息
            ws.cell(row=last_row+1, column=1, value='项目名称')
            ws.cell(row=last_row+1, column=2, value=summary.project_name)
            ws.cell(row=last_row+2, column=1, value='项目编号')
            ws.cell(row=last_row+2, column=2, value=summary.project_code)
            
            # 调整列宽
            for col in range(1, 12):
                ws.column_dimensions[get_column_letter(col)].width = 15
            
            directory = os.path.dirname(output_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
            
            wb.save(output_path)
            return output_path
        
        except ImportError:
            return self._export_csv(summary, output_path)
        except Exception as e:
            raise FileError(f"Failed to export Excel file: {str(e)}")
    
    def _export_csv(self, summary: ListSummary, output_path: str) -> str:
        try:
            directory = os.path.dirname(output_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
            
            csv_path = output_path.replace('.xlsx', '.csv')
            
            with open(csv_path, 'w', encoding='utf-8-sig') as f:
                f.write("序号,编号,项目名称,规格型号,单位,数量,单价,合价,分类,子分类\n")
                
                for i, item in enumerate(summary.items, 1):
                    f.write(f"{i},{item.code},{item.name},,{item.unit},{item.quantity},{item.unit_price},{item.total_price},{item.category},{item.sub_category}\n")
                
                f.write(f",,,,,,,{summary.total_cost},合计,\n")
            
            return csv_path
        except Exception as e:
            raise FileError(f"Failed to export CSV file: {str(e)}")
