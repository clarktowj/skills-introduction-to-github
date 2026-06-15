#!/usr/bin/env python3
"""创建真实设计院风格的测试DXF - 包含多种命名混乱的设备、图层"""
import ezdxf
import os


def create_complex_test_dxf(output_path: str):
    """创建一个包含多种电气元素的复杂DXF"""

    doc = ezdxf.new(dxfversion='R2010')
    msp = doc.modelspace()

    # ===== 1. 创建真实设计院风格的图层（混乱命名） =====
    doc.layers.add('E-设备', color=7)
    doc.layers.add('E-电缆', color=1)  # 红色 = 电力电缆
    doc.layers.add('E-桥架', color=3)  # 绿色 = 桥架
    doc.layers.add('E-照明', color=4)  # 青色 = 照明
    doc.layers.add('E-插座', color=5)  # 蓝色 = 插座
    doc.layers.add('E-控制', color=2)  # 黄色 = 控制
    doc.layers.add('E-标注', color=6)
    doc.layers.add('建筑-墙体', color=8)  # 非电气图层，应被过滤
    doc.layers.add('建筑-柱', color=9)  # 非电气图层，应被过滤
    doc.layers.add('轴线', color=7)  # 非电气图层，应被过滤

    # ===== 2. 创建图块定义 =====

    # 配电柜（多种命名）
    doc.blocks.new('配电柜')
    for block_name in ['P1', 'AP1', 'MCC-1', 'GCS-1', 'XL-21', '低压柜']:
        doc.blocks.new(block_name)

    # 配电箱
    for block_name in ['AL1', 'ALE1', 'AL-E1', 'AT1']:
        doc.blocks.new(block_name)

    # 开关
    for block_name in ['单极开关', '双极开关', 'MCB-1P', 'QF1']:
        doc.blocks.new(block_name)

    # 插座
    for block_name in ['插座', '单相插座', '五孔插座']:
        doc.blocks.new(block_name)

    # 照明
    for block_name in ['灯具', '吸顶灯', '应急灯']:
        doc.blocks.new(block_name)

    # 电机
    for block_name in ['电机-1', 'M-1', '水泵', '风机']:
        doc.blocks.new(block_name)

    # ===== 3. 放置图块到模型空间 =====
    positions = [
        # 配电柜系列
        ('P1', (0, 0), 'E-设备'),
        ('AP1', (1500, 0), 'E-设备'),
        ('MCC-1', (3000, 0), 'E-设备'),
        ('GCS-1', (4500, 0), 'E-设备'),
        ('XL-21', (6000, 0), 'E-设备'),
        ('低压柜', (7500, 0), 'E-设备'),

        # 配电箱系列
        ('AL1', (1000, 1500), 'E-设备'),
        ('ALE1', (2500, 1500), 'E-设备'),
        ('AL-E1', (4000, 1500), 'E-设备'),
        ('AT1', (5500, 1500), 'E-设备'),

        # 开关系列
        ('单极开关', (800, 3000), 'E-设备'),
        ('双极开关', (1800, 3000), 'E-设备'),
        ('MCB-1P', (2800, 3000), 'E-设备'),
        ('QF1', (3800, 3000), 'E-设备'),

        # 插座系列
        ('插座', (600, 4000), 'E-插座'),
        ('单相插座', (1600, 4000), 'E-插座'),
        ('五孔插座', (2600, 4000), 'E-插座'),
        ('插座', (3600, 4000), 'E-插座'),

        # 照明系列
        ('灯具', (1000, 5000), 'E-照明'),
        ('吸顶灯', (2500, 5000), 'E-照明'),
        ('应急灯', (4000, 5000), 'E-照明'),
        ('灯具', (5500, 5000), 'E-照明'),

        # 电机/设备系列
        ('电机-1', (2000, 6000), 'E-设备'),
        ('M-1', (3500, 6000), 'E-设备'),
        ('水泵', (5000, 6000), 'E-设备'),
        ('风机', (6500, 6000), 'E-设备'),
    ]

    for block_name, (x, y), layer in positions:
        msp.add_blockref(block_name, insert=(x, y), dxfattribs={'layer': layer})

    # ===== 4. 绘制电力电缆（红色连续线） =====
    cable_lines = [
        # 主干电缆
        ((0, 500), (8000, 500), 'E-电缆'),
        # 配电柜之间的连接
        ((0, 0), (0, 500), 'E-电缆'),
        ((1500, 0), (1500, 500), 'E-电缆'),
        ((3000, 0), (3000, 500), 'E-电缆'),
        ((4500, 0), (4500, 500), 'E-电缆'),
        ((6000, 0), (6000, 500), 'E-电缆'),
        ((7500, 0), (7500, 500), 'E-电缆'),
        # 到配电箱的支线
        ((1000, 500), (1000, 1500), 'E-电缆'),
        ((2500, 500), (2500, 1500), 'E-电缆'),
        ((4000, 500), (4000, 1500), 'E-电缆'),
        ((5500, 500), (5500, 1500), 'E-电缆'),
        # 到开关区
        ((800, 500), (800, 3000), 'E-电缆'),
        ((1800, 500), (1800, 3000), 'E-电缆'),
        ((2800, 500), (2800, 3000), 'E-电缆'),
        ((3800, 500), (3800, 3000), 'E-电缆'),
        # 到设备区
        ((2000, 500), (2000, 6000), 'E-电缆'),
        ((3500, 500), (3500, 6000), 'E-电缆'),
        ((5000, 500), (5000, 6000), 'E-电缆'),
        ((6500, 500), (6500, 6000), 'E-电缆'),
    ]

    for (x1, y1), (x2, y2), layer in cable_lines:
        msp.add_line((x1, y1), (x2, y2), dxfattribs={'layer': layer, 'color': 1})

    # ===== 5. 绘制桥架（绿色连续线） =====
    trunking_lines = [
        # 主桥架 - 水平
        ((-500, -500), (8500, -500), 'E-桥架'),
        ((-500, -300), (8500, -300), 'E-桥架'),
        # 垂直连接
        ((-500, -500), (-500, -300), 'E-桥架'),
        ((8500, -500), (8500, -300), 'E-桥架'),
        # 分支桥架
        ((2000, -500), (2000, -200), 'E-桥架'),
        ((4000, -500), (4000, -200), 'E-桥架'),
        ((6000, -500), (6000, -200), 'E-桥架'),
    ]

    for (x1, y1), (x2, y2), layer in trunking_lines:
        msp.add_line((x1, y1), (x2, y2), dxfattribs={'layer': layer, 'color': 3})

    # ===== 6. 绘制控制电缆（黄色虚线） =====
    control_lines = [
        ((0, 500), (0, 6000), 'E-控制'),
        ((4000, 500), (4000, 6000), 'E-控制'),
    ]

    for (x1, y1), (x2, y2), layer in control_lines:
        msp.add_line((x1, y1), (x2, y2), dxfattribs={'layer': layer, 'color': 2})

    # ===== 7. 绘制照明线路（青色） =====
    lighting_lines = [
        # 照明主线
        ((500, 4500), (6000, 4500), 'E-照明'),
        # 灯具连接
        ((1000, 4500), (1000, 5000), 'E-照明'),
        ((2500, 4500), (2500, 5000), 'E-照明'),
        ((4000, 4500), (4000, 5000), 'E-照明'),
        ((5500, 4500), (5500, 5000), 'E-照明'),
    ]

    for (x1, y1), (x2, y2), layer in lighting_lines:
        msp.add_line((x1, y1), (x2, y2), dxfattribs={'layer': layer, 'color': 4})

    # ===== 8. 插座线路（蓝色） =====
    socket_lines = [
        ((500, 3500), (4500, 3500), 'E-插座'),
        ((600, 3500), (600, 4000), 'E-插座'),
        ((1600, 3500), (1600, 4000), 'E-插座'),
        ((2600, 3500), (2600, 4000), 'E-插座'),
        ((3600, 3500), (3600, 4000), 'E-插座'),
    ]

    for (x1, y1), (x2, y2), layer in socket_lines:
        msp.add_line((x1, y1), (x2, y2), dxfattribs={'layer': layer, 'color': 5})

    # ===== 9. 添加文字标注 =====
    texts = [
        ('配电柜P1', (0, -200), 'E-标注', 100),
        ('动力配电柜AP1', (1500, -200), 'E-标注', 100),
        ('MCC柜', (3000, -200), 'E-标注', 100),
        ('GCS开关柜', (4500, -200), 'E-标注', 100),
        ('XL-21配电柜', (6000, -200), 'E-标注', 100),
        ('照明配电箱AL1', (1000, 1300), 'E-标注', 80),
        ('应急配电箱ALE1', (2500, 1300), 'E-标注', 80),
        ('双电源切换箱AT1', (5500, 1300), 'E-标注', 80),
        ('桥架CT-300x150', (4000, -600), 'E-标注', 80),
        ('YJV-4x25+1x16', (4000, 700), 'E-标注', 70),
        ('SC25', (4000, 3200), 'E-标注', 70),
    ]

    for content, (x, y), layer, size in texts:
        msp.add_text(content, dxfattribs={'height': size, 'insert': (x, y), 'layer': layer})

    # ===== 10. 添加一些建筑线条（测试过滤功能） =====
    wall_lines = [
        ((-1000, -1000), (-1000, 7000), '建筑-墙体'),
        ((9000, -1000), (9000, 7000), '建筑-墙体'),
        ((-1000, -1000), (9000, -1000), '建筑-墙体'),
        ((-1000, 7000), (9000, 7000), '建筑-墙体'),
    ]

    for (x1, y1), (x2, y2), layer in wall_lines:
        msp.add_line((x1, y1), (x2, y2), dxfattribs={'layer': layer, 'color': 8})

    # 保存文件
    doc.saveas(output_path)
    print(f"复杂测试DXF已创建: {output_path}")

    # 打印统计信息
    print(f"  - 图层: {len(list(doc.layers))} 个")
    print(f"  - 图块: {len(positions)} 个")
    print(f"  - 电缆线条: {len(cable_lines)} 条")
    print(f"  - 桥架线条: {len(trunking_lines)} 条")
    print(f"  - 控制线路: {len(control_lines)} 条")
    print(f"  - 照明线路: {len(lighting_lines)} 条")
    print(f"  - 插座线路: {len(socket_lines)} 条")
    print(f"  - 建筑线条: {len(wall_lines)} 条 (应被过滤)")
    print(f"  - 文字标注: {len(texts)} 个")

    return output_path


if __name__ == '__main__':
    output_dir = os.path.dirname(os.path.abspath(__file__))
    dxf_path = os.path.join(output_dir, 'test_electrical_complex.dxf')
    create_complex_test_dxf(dxf_path)
