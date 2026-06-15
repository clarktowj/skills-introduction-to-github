"""
创建测试用矢量PDF电气图纸

使用 reportlab 创建包含以下内容的PDF：
- 设备矩形（配电柜、配电箱、开关、插座）
- 线缆（红色=电力，绿色=控制）
- 桥架（粗线）
- 文字标注（设备名称、型号）
"""
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.colors import red, green, blue, black, gray, yellow
from reportlab.lib.units import mm


def create_electrical_pdf(output_path: str):
    """创建电气系统PDF图纸"""
    c = canvas.Canvas(output_path, pagesize=landscape(A3))
    width, height = landscape(A3)

    c.setFont("Helvetica-Bold", 24)
    c.drawString(50, height - 50, "Electrical System Schematic - Floor 1")

    c.setFont("Helvetica", 12)
    c.drawString(50, height - 70, "Project: Building A - Mechanical/Electrical")
    c.drawString(50, height - 85, "DWG: E-001 - Single Line Diagram")

    device_specs = [
        {"name": "配电柜 AP1", "type": "switchboard", "x": 100, "y": height - 200, "w": 120, "h": 80, "fill": None},
        {"name": "配电箱 AL1", "type": "panel", "x": 280, "y": height - 200, "w": 100, "h": 80, "fill": None},
        {"name": "配电箱 AL2", "type": "panel", "x": 430, "y": height - 200, "w": 100, "h": 80, "fill": None},
        {"name": "MCC-1 电机控制中心", "type": "mcc", "x": 580, "y": height - 200, "w": 140, "h": 80, "fill": None},
        {"name": "配电柜 AP2", "type": "switchboard", "x": 100, "y": height - 400, "w": 120, "h": 80, "fill": None},
        {"name": "开关 SB-1", "type": "switch", "x": 280, "y": height - 400, "w": 60, "h": 60, "fill": None},
        {"name": "开关 SB-2", "type": "switch", "x": 380, "y": height - 400, "w": 60, "h": 60, "fill": None},
        {"name": "插座 SW-1", "type": "socket", "x": 480, "y": height - 400, "w": 60, "h": 60, "fill": None},
        {"name": "照明 LT-1", "type": "lighting", "x": 580, "y": height - 400, "w": 60, "h": 60, "fill": None},
        {"name": "电机 M-1", "type": "motor", "x": 680, "y": height - 200, "w": 80, "h": 60, "fill": None},
        {"name": "水泵 P-1", "type": "pump", "x": 680, "y": height - 400, "w": 80, "h": 60, "fill": None},
        {"name": "风机 F-1", "type": "fan", "x": 820, "y": height - 300, "w": 80, "h": 60, "fill": None},
    ]

    for dev in device_specs:
        c.setStrokeColor(black)
        c.setLineWidth(2)
        c.rect(dev["x"], dev["y"], dev["w"], dev["h"], stroke=1, fill=0)

        c.setFillColor(black)
        c.setFont("Helvetica-Bold", 10)
        text_x = dev["x"] + dev["w"] / 2
        text_y = dev["y"] - 15
        c.drawCentredString(text_x, text_y, dev["name"])

        c.setFont("Helvetica", 8)
        c.drawCentredString(text_x, text_y - 12, f"Type: {dev['type'].upper()}")

    c.setStrokeColor(red)
    c.setLineWidth(1.5)
    # AP1 -> AL1
    c.line(220, height - 160, 280, height - 160)
    # AL1 -> AL2
    c.line(380, height - 160, 430, height - 160)
    # AL2 -> MCC-1
    c.line(530, height - 160, 580, height - 160)
    # AP1 -> AP2 (vertical connection)
    c.line(160, height - 200, 160, height - 320)
    c.line(160, height - 320, 160, height - 400)

    c.setStrokeColor(green)
    c.setLineWidth(1.2)
    # AP2 -> SB-1
    c.line(220, height - 370, 280, height - 370)
    # SB-1 -> SB-2
    c.line(340, height - 370, 380, height - 370)
    # SB-2 -> SW-1
    c.line(440, height - 370, 480, height - 370)
    # SW-1 -> LT-1
    c.line(540, height - 370, 580, height - 370)

    c.setStrokeColor(red)
    c.setLineWidth(1.5)
    # MCC-1 -> M-1
    c.line(720, height - 200, 680 + 40, height - 200)
    c.line(720, height - 180, 680 + 40, height - 170)
    # M-1 -> P-1
    c.line(720, height - 260, 720, height - 340)
    # P-1 -> F-1
    c.line(760, height - 370, 820, height - 330)

    c.setStrokeColor(gray)
    c.setLineWidth(3)
    # Main cable tray - horizontal
    c.line(80, height - 280, width - 80, height - 280)
    c.line(80, height - 290, width - 80, height - 290)

    # Vertical cable tray
    c.line(300, height - 290, 300, height - 480)
    c.line(310, height - 290, 310, height - 480)

    c.setFillColor(gray)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(120, height - 270, "Main Cable Tray 200x100")
    c.drawString(320, height - 390, "Vertical Tray")

    # Cable labels
    c.setFillColor(red)
    c.setFont("Helvetica", 7)
    c.drawCentredString(250, height - 145, "YJV-4x25")
    c.drawCentredString(405, height - 145, "YJV-4x16")
    c.drawCentredString(555, height - 145, "YJV-3x70")

    c.setFillColor(green)
    c.drawCentredString(250, height - 355, "ZR-BV-2x4")
    c.drawCentredString(410, height - 355, "ZR-BV-2x4")
    c.drawCentredString(510, height - 355, "ZR-BV-3x2.5")

    # Title block
    c.setStrokeColor(black)
    c.setLineWidth(1)
    tb_x = width - 300
    tb_y = 30
    tb_w = 270
    tb_h = 100
    c.rect(tb_x, tb_y, tb_w, tb_h)

    c.setFillColor(black)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(tb_x + 10, tb_y + tb_h - 15, "Drawing Title Block")
    c.setFont("Helvetica", 9)
    c.drawString(tb_x + 10, tb_y + tb_h - 30, "Drawing: E-001 Single Line Diagram")
    c.drawString(tb_x + 10, tb_y + tb_h - 45, "Scale: 1:100")
    c.drawString(tb_x + 10, tb_y + tb_h - 60, "Rev: A | Date: 2024-01-15")
    c.drawString(tb_x + 10, tb_y + tb_h - 75, "Engineer: Zhang Wei")

    # Notes
    c.setFont("Helvetica", 9)
    c.setFillColor(black)
    c.drawString(50, 100, "Notes:")
    c.drawString(70, 85, "1. All power cables use YJV copper conductors")
    c.drawString(70, 70, "2. Control cables use ZR-BV flame retardant type")
    c.drawString(70, 55, "3. Cable tray specification: 200x100 hot-dip galvanized steel")

    c.showPage()
    c.save()
    print(f"  Created: {output_path}")
    print(f"  Size: {os.path.getsize(output_path)} bytes")


if __name__ == "__main__":
    test_dir = os.path.join(os.path.dirname(__file__), "test_data")
    os.makedirs(test_dir, exist_ok=True)

    pdf_path = os.path.join(test_dir, "electrical_test.pdf")
    create_electrical_pdf(pdf_path)
