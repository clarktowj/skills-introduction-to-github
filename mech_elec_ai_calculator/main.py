import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from framework.app import Application
from common.models import TaskConfig
from routing.scheduler import TaskScheduler

def main():
    parser = argparse.ArgumentParser(description='机电AI自动算量系统')
    parser.add_argument('-i', '--input', nargs='+', required=True, help='输入图纸文件路径')
    parser.add_argument('-o', '--output', default='./outputs', help='输出目录')
    parser.add_argument('-r', '--rule-version', default='latest', help='规则版本')
    parser.add_argument('--no-audit', action='store_true', help='禁用AI审核')
    parser.add_argument('--no-modeling', action='store_true', help='禁用BIM建模')
    
    args = parser.parse_args()
    
    app = Application()
    
    try:
        app.initialize()
        
        task_config = TaskConfig(
            task_name='电气算量任务',
            input_files=args.input,
            output_path=args.output,
            rule_version=args.rule_version,
            enable_audit=not args.no_audit,
            enable_modeling=not args.no_modeling
        )
        
        scheduler = TaskScheduler()
        result = scheduler.execute(task_config)
        
        if result.status == 'completed':
            app.logger.info(f"任务完成")
            app.logger.info(f"输出文件: {result.output_files}")
        else:
            app.logger.error(f"任务失败: {result.error_message}")
        
        return 0
    
    except Exception as e:
        print(f"执行失败: {str(e)}")
        return 1

if __name__ == '__main__':
    sys.exit(main())