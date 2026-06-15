#!/usr/bin/env python3
"""验证DXF识别结果"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from drawing_parser.dxf_parser import DXFParser
from rule_engine.rule_manager import RuleManager

def main():
    dxf_file = 'test_data/test_electrical_complex.dxf'
    print("=" * 80)
    print("DXF 识别结果验证")
    print("=" * 80)

    parser = DXFParser()
    result = parser.parse(dxf_file)

    # 1. 图层统计
    print("\n📋 图层过滤结果 (应该过滤掉建筑相关图层):")
    print("-" * 80)

    layer_stats = {}
    for layer in result.layers:
        category = layer.category or 'unknown'
        if category not in layer_stats:
            layer_stats[category] = []
        layer_stats[category].append(layer.name)

    for category, layers in sorted(layer_stats.items()):
        print(f"  {category:12s}: {len(layers):3d} 个 - {', '.join(layers[:5])}")

    # 2. 图块识别统计
    print("\n🔧 设备识别统计 (按类型分组):")
    print("-" * 80)

    device_by_type = {}
    for device in result.devices:
        t = device.type.value
        if t not in device_by_type:
            device_by_type[t] = []
        device_by_type[t].append(device.name)

    expected_distribution = {
        'cabinet': ['P1', 'AP1', 'MCC-1', 'GCS-1', 'XL-21', '低压柜'],
        'distribution_box': ['AL1', 'ALE1', 'AL-E1', 'AT1'],
        'switch': ['单极开关', '双极开关', 'MCB-1P', 'QF1'],
        'socket': ['插座', '插座', '单相插座', '五孔插座'],
        'lighting': ['灯具', '灯具', '吸顶灯', '应急灯'],
        'equipment': ['电机-1', 'M-1', '水泵', '风机'],
        'other': []
    }

    total_correct = 0
    total_devices = len(result.devices)

    for device_type, expected_names in expected_distribution.items():
        actual_names = device_by_type.get(device_type, [])
        if actual_names:
            print(f"  {device_type:18s}: {len(actual_names):3d} 个 - {', '.join(actual_names[:6])}")
        else:
            print(f"  {device_type:18s}:   0 个")

        # 检查期望的设备是否被正确识别
        for name in expected_names:
            if name in actual_names:
                total_correct += 1

    total_expected = sum(len(v) for v in expected_distribution.values())
    print(f"\n  ✅ 正确识别: {total_correct}/{total_expected} ({100*total_correct/total_expected:.0f}%)")

    # 3. 线条识别统计
    print("\n📏 线条识别统计 (按图层和颜色):")
    print("-" * 80)

    cable_lines = [l for l in result.lines if '电缆' in l.layer or l.color in ['1', '3', '5']]
    trunking_lines = [l for l in result.lines if '桥架' in l.layer or 'TR' in l.layer.upper()]
    lighting_lines = [l for l in result.lines if '照明' in l.layer]
    socket_lines = [l for l in result.lines if '插座' in l.layer]
    control_lines = [l for l in result.lines if '控制' in l.layer]

    print(f"  电力电缆   : {len(cable_lines)} 条")
    print(f"  桥架       : {len(trunking_lines)} 条")
    print(f"  控制线路   : {len(control_lines)} 条")
    print(f"  照明线路   : {len(lighting_lines)} 条")
    print(f"  插座线路   : {len(socket_lines)} 条")

    # 4. 线缆统计
    print("\n🔌 线缆识别结果 (按敷设方式和类型):")
    print("-" * 80)

    for cable in result.cables:
        cable_type = cable.type.value if hasattr(cable.type, 'value') else str(cable.type)
        laying = cable.laying_method.value if hasattr(cable.laying_method, 'value') else str(cable.laying_method)
        print(f"  {cable_type:15s} | {laying:12s} | 长度: {cable.length:.1f}m | 模型: {cable.model}")

    # 5. 桥架统计
    print("\n🏗️  桥架识别结果:")
    print("-" * 80)

    if result.trunkings:
        for t in result.trunkings:
            print(f"  {t.get('name', '桥架'):15s} | {t.get('type', ''):12s} | 长度: {t.get('length', 0):.1f}m")
    else:
        print("  ⚠️  未识别到独立的桥架对象 (桥架线段已作为线缆处理)")

    # 6. 文字标注统计
    print("\n📝 文字标注识别:")
    print("-" * 80)
    print(f"  识别到文字标注: {len(result.texts)} 条")
    if result.texts:
        for text in result.texts[:8]:
            print(f"    - {text.content}")

    # 7. 总体摘要
    summary = result.attributes if isinstance(result.attributes, dict) else {}
    print("\n📊 识别摘要:")
    print("-" * 80)
    for key, value in summary.items():
        print(f"  {key:25s}: {value}")

    print("\n" + "=" * 80)
    print("✅ DXF识别完成")
    print("=" * 80)


if __name__ == '__main__':
    main()
