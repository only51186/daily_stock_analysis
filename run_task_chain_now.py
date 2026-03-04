
# -*- coding: utf-8 -*-
"""
立即运行完整的自动化任务链
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.scheduler.auto_scheduler import AutoScheduler

def main():
    print("\n" + "=" * 80)
    print("立即运行完整的自动化任务链")
    print("=" * 80)
    
    scheduler = AutoScheduler()
    
    try:
        print("\n🚀 开始执行任务链...")
        success = scheduler.run_task_chain()
        
        if success:
            print("\n✅ 任务链执行完成！")
        else:
            print("\n❌ 任务链执行失败！")
            
    except Exception as e:
        print(f"\n❌ 任务链执行异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return success

if __name__ == '__main__':
    main()

