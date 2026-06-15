#!/usr/bin/env python3
"""
创建测试用DXF图纸文件
包含配电柜、设备、线缆等典型电气元素
"""
import ezdxf
import os

def create_test_dxf(output_path: str):
    """创建测试用DXF文件"""
    
    # 创建新DXF文档
    doc = ezdxf.new(dxfversion='R2010')
    msp = doc.modelspace()
    
    # 创建图层
    doc.layers.add('设备层', color=7)
    doc.layers.add('电缆层', color=1)
    doc.layers.add('桥架层', color=3)
    doc.layers.add('文字标注', color=2)
    doc.layers.add('配电柜', color=5)
    
    # 1. 添加配电柜图块
    cabinet_block = doc.blocks.new('配电柜')
    cabinet_block.add_lwpolyline([(0, 0), (800, 0), (800, 2000), (0, 2000)], close=True)
    
    # 在模型空间插入配电柜
    msp.add_blockref('配电柜', insert=(0, 0), dxfattribs={'layer': '配电柜'})
    msp.add_blockref('配电柜', insert=(5000, 0), dxfattribs={'layer': '配电柜'})
    
    # 2. 添加配电箱图块
    box_block = doc.blocks.new('配电箱')
    box_block.add_lwpolyline([(0, 0), (400, 0), (400, 600), (0, 600)], close=True)
    
    msp.add_blockref('配电箱', insert=(2000, 0), dxfattribs={'layer': '设备层'})
    msp.add_blockref('配电箱', insert=(3500, 0), dxfattribs={'layer': '设备层'})
    
    # 3. 添加开关图块
    switch_block = doc.blocks.new('开关')
    switch_block.add_circle((0, 0), radius=50)
    
    msp.add_blockref('开关', insert=(1500, 1500), dxfattribs={'layer': '设备层'})
    msp.add_blockref('开关', insert=(2500, 1500), dxfattribs={'layer': '设备层'})
    msp.add_blockref('开关', insert=(4500, 1500), dxfattribs={'layer': '设备层'})
    
    # 4. 添加线缆（电缆层）
    # 主电缆：从配电柜到配电箱
    msp.add_line((0, 1000), (5000, 1000), dxfattribs={'layer': '电缆层'})
    
    # 垂直段
    msp.add_line((0, 1000), (0, 0), dxfattribs={'layer': '电缆层'})
    msp.add_line((5000, 1000), (5000, 0), dxfattribs={'layer': '电缆层'})
    
    # 分支电缆
    msp.add_line((2000, 0), (2000, -500), dxfattribs={'layer': '电缆层'})
    msp.add_line((3500, 0), (3500, -500), dxfattribs={'layer': '电缆层'})
    msp.add_line((1500, 1500), (1500, 1000), dxfattribs={'layer': '电缆层'})
    msp.add_line((2500, 1500), (2500, 1000), dxfattribs={'layer': '电缆层'})
    msp.add_line((4500, 1500), (4500, 1000), dxfattribs={'layer': '电缆层'})
    
    # 水平连接
    msp.add_line((1500, 1500), (2500, 1500), dxfattribs={'layer': '电缆层'})
    msp.add_line((2500, 1500), (4500, 1500), dxfattribs={'layer': '电缆层'})
    
    # 5. 添加桥架
    msp.add_line((0, -1000), (5000, -1000), dxfattribs={'layer': '桥架层'})
    msp.add_line((0, -800), (5000, -800), dxfattribs={'layer': '桥架层'})
    
    # 桥架立柱
    for x in [0, 1000, 2000, 3000, 4000, 5000]:
        msp.add_line((x, -1000), (x, -800), dxfattribs={'layer': '桥架层'})
    
    # 6. 添加文字标注
    msp.add_text('主配电柜', dxfattribs={'height': 150, 'insert': (2500, 2500), 'layer': '文字标注'})
    msp.add_text('分配电箱', dxfattribs={'height': 100, 'insert': (2750, 500), 'layer': '文字标注'})
    msp.add_text('照明开关', dxfattribs={'height': 80, 'insert': (3000, 1500), 'layer': '文字标注'})
    
    # 7. 添加设备标注
    msp.add_circle((0, 0), radius=100, dxfattribs={'layer': '设备层'})
    msp.add_circle((5000, 0), radius=100, dxfattribs={'layer': '设备层'})
    
    # 保存文件
    doc.saveas(output_path)
    print(f"测试DXF文件已创建: {output_path}")
    return output_path

if __name__ == '__main__':
    # 创建测试DXF文件
    output_dir = os.path.dirname(__file__)
    dxf_path = os.path.join(output_dir, 'test_electrical.dxf')
    create_test_dxf(dxf_path)
