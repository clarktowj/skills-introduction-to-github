#!/usr/bin/env python3
"""
使用 AgnesAI API 进行 OpenHuman AI 审核测试
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from openhuman_audit import OpenHumanClient, AuditProcessor


def test_aginesai_connection():
    """测试 AgnesAI API 连接"""

    print("=" * 80)
    print("AgnesAI API 连接测试")
    print("=" * 80)

    # 配置
    config = {
        'service_type': 'openai',
        'api_key': 'sk-o9HJZWD6ImlQzMcTUtll8AKghTl7ioDYlPQLwVHGuiJp6TMu',
        'api_base': 'https://apihub.agnes-ai.com/v1',
        'model': 'agnes-2.0-flash',
        'temperature': 0.1,
        'max_tokens': 4000,
        'timeout': 120,
        'local_rules_enabled': True  # 启用fallback
    }

    # 创建客户端
    client = OpenHumanClient(config)

    # 准备测试数据
    drawing_info = {
        'devices': [
            {'name': 'P1', 'type': 'cabinet', 'quantity': 2},
            {'name': 'AL1', 'type': 'distribution_box', 'quantity': 4},
            {'name': '开关', 'type': 'switch', 'quantity': 8},
        ],
        'cables': [
            {'model': '电力电缆', 'type': 'power', 'length': 500, 'laying_method': 'cable_tray'},
            {'model': '控制电缆', 'type': 'control', 'length': 200, 'laying_method': 'pipe'},
        ],
        'layers': [
            {'name': 'E-设备', 'category': 'equipment'},
            {'name': 'E-电缆', 'category': 'cable'},
        ]
    }

    quantity_list = [
        {'name': '配电柜', 'quantity': 2, 'unit': '个', 'category': '设备'},
        {'name': '配电箱', 'quantity': 4, 'unit': '个', 'category': '设备'},
        {'name': '开关', 'quantity': 8, 'unit': '个', 'category': '设备'},
        {'name': '电力电缆', 'quantity': 500, 'unit': '米', 'category': '线缆'},
        {'name': '控制电缆', 'quantity': 200, 'unit': '米', 'category': '线缆'},
    ]

    print("\n📋 测试数据:")
    print(f"   设备: {len(drawing_info['devices'])} 种")
    print(f"   线缆: {len(drawing_info['cables'])} 种")
    print(f"   清单项: {len(quantity_list)} 项")

    print("\n🤖 正在调用 AgnesAI API...")

    try:
        # 执行审核
        result = client.audit(
            drawing_info=drawing_info,
            quantity_list=quantity_list,
            rules_summary=None
        )

        print(f"\n✅ 审核完成!")
        print(f"   服务: {result.service_used}")
        print(f"   置信度: {result.confidence_score:.1%}")
        print(f"   处理时间: {result.processing_time:.2f}秒")

        if result.has_issues:
            print(f"\n⚠️  发现问题:")
            print(f"   修正项: {len(result.corrections)}")
            print(f"   警告项: {len(result.warnings)}")
        else:
            print(f"\n✅ 未发现问题")

        if result.summary:
            print(f"\n📝 摘要: {result.summary}")

        # 显示原始响应（如果有）
        if result.raw_response:
            print(f"\n📄 AI 响应预览:")
            preview = result.raw_response[:500]
            if len(result.raw_response) > 500:
                preview += "..."
            print(preview)

        if result.error_message:
            print(f"\n❌ 错误: {result.error_message}")

        print("\n" + "=" * 80)
        return True

    except Exception as e:
        print(f"\n❌ 调用失败: {str(e)}")
        print("\n" + "=" * 80)
        return False


def main():
    success = test_aginesai_connection()

    if success:
        print("✅ AgnesAI API 配置成功!")
    else:
        print("❌ 请检查 API Key 和端点配置")

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
