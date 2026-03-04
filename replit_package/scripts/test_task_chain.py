# -*- coding: utf-8 -*-
"""
===================================
任务链测试脚本
===================================

【功能】
1. 测试完整的任务链执行
2. 输出执行时长和各环节耗时
3. 验证任务链是否正常工作

【使用方法】
直接运行此脚本：
    python test_task_chain.py
"""

import os
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.scheduler.auto_scheduler import AutoScheduler
from utils.logger_config import setup_logger

logger = setup_logger(__name__, log_file='logs/test_task_chain.log')


def print_banner():
    """
    打印测试横幅
    """
    banner = """
╔══════════════════════════════════════════════════════════════════╗
║                                                                      ║
║          🧪 任务链测试脚本 v1.0 🧪                                  ║
║                                                                      ║
║  功能：测试完整任务链执行，验证系统可靠性                       ║
║  任务：数据下载 → 数据校验 → 因子计算 → 尾盘选股 → 历史回测 → 市场复盘 ║
║                                                                      ║
╚════════════════════════════════════════════════════════════════════╝
"""
    print(banner)


def test_task_chain():
    """
    测试任务链执行
    """
    print_banner()
    
    print(f"\n开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print("开始执行任务链测试")
    print("=" * 80)
    
    try:
        # 创建调度器实例
        scheduler = AutoScheduler()
        
        # 执行任务链
        start_time = time.time()
        
        print("\n🚀 启动任务链...")
        print("任务顺序：数据下载 → 数据校验 → 因子计算 → 尾盘选股 → 历史回测 → 市场复盘")
        
        # 执行任务链
        scheduler.run_task_chain()
        
        # 计算总耗时
        total_duration = time.time() - start_time
        
        print("\n" + "=" * 80)
        print("任务链测试完成")
        print("=" * 80)
        
        # 输出执行结果
        print(f"\n总执行时长: {total_duration:.2f}秒")
        print(f"完成任务数: {len(scheduler.chain_status['completed_tasks'])}/{len(scheduler.task_chain)}")
        print(f"失败任务数: {len(scheduler.chain_status['failed_tasks'])}")
        
        # 输出各任务耗时
        print("\n各任务执行时长:")
        print("-" * 80)
        
        for task_config in scheduler.task_chain:
            task_name = task_config['name']
            display_name = task_config['display_name']
            
            if task_name in scheduler.task_durations:
                duration = scheduler.task_durations[task_name]
                print(f"{display_name:12s}: {duration:.2f}秒")
            else:
                print(f"{display_name:12s}: 未执行")
        
        # 输出任务链状态
        print("\n任务链执行状态:")
        print("-" * 80)
        
        for task_config in scheduler.task_chain:
            task_name = task_config['name']
            display_name = task_config['display_name']
            
            if task_name in scheduler.task_results:
                result = scheduler.task_results[task_name]
                status = "✅ 成功" if result.success else "❌ 失败"
                print(f"{display_name:12s}: {status}")
            else:
                print(f"{display_name:12s}: ⚠️ 未执行")
        
        # 检查是否成功
        if len(scheduler.chain_status['failed_tasks']) == 0:
            print("\n" + "=" * 80)
            print("🎉 任务链测试成功！")
            print("=" * 80)
            print("\n系统已准备就绪，可以开始使用！")
            print("\n启动命令：")
            print("  python main.py --mode schedule")
            return True
        else:
            print("\n" + "=" * 80)
            print("❌ 任务链测试失败")
            print("=" * 80)
            print(f"失败任务: {scheduler.chain_status['failed_tasks']}")
            return False
            
    except Exception as e:
        print(f"\n" + "=" * 80)
        print("❌ 测试异常")
        print("=" * 80)
        print(f"错误信息: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """
    主函数
    """
    success = test_task_chain()
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
