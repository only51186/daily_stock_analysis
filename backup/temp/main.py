# -*- coding: utf-8 -*-
"""
===================================
股票量化自动化系统 - 主入口
===================================

【系统功能】
1. 自动化数据下载和管理
2. 定时任务调度（15:30/16:00/18:00/20:00/21:00）
3. 尾盘选股、历史回测、市场复盘
4. 结果自动通知（豆包API）

【定时任务】
- 15:30: 下载/更新当日沪深主板股票数据
- 16:00: 基于公用数据进行因子计算
- 18:00: 执行尾盘选股程序
- 20:00: 对当日选出的标的进行历史回测验证
- 21:00: 完成当日市场复盘

【核心特性】
- 数据统一管理：SQLite数据库，增量更新
- 任务依赖管理：确保前置任务完成
- 自动通知：任务完成后通过豆包API推送
- 错误重试：自动重试机制
- 日志记录：完整记录执行过程
"""

import logging
import sys
import os
import argparse
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.scheduler.auto_scheduler import AutoScheduler
from src.data.data_manager import get_data_manager
from src.notification.notification_sender import get_notification_sender
from utils.logger_config import setup_logger

logger = setup_logger(__name__, log_file='logs/main.log')


def print_banner():
    """
    打印系统启动横幅
    """
    banner = """
╔══════════════════════════════════════════════════════════════════╗
║                                                                      ║
║          📊 股票量化自动化系统 v1.0 📊                              ║
║                                                                      ║
║  功能：自动选股 | 历史回测 | 市场复盘 | 数据管理               ║
║  时间：15:30/16:00/18:00/20:00/21:00                          ║
║  通知：豆包API自动推送                                              ║
║                                                                      ║
╚════════════════════════════════════════════════════════════════════╝
"""
    print(banner)


def print_system_info():
    """
    打印系统信息
    """
    print("\n" + "=" * 80)
    print("系统信息")
    print("=" * 80)
    
    # 数据管理器
    data_manager = get_data_manager()
    stats = data_manager.get_data_statistics()
    
    print(f"数据库路径: {data_manager.db_path}")
    print(f"股票日线数据: {stats.get('daily_count', 0)}条")
    print(f"股票数量: {stats.get('stock_count', 0)}只")
    print(f"数据日期范围: {stats.get('date_range', 'N/A')}")
    print(f"选股结果: {stats.get('selection_count', 0)}条")
    print(f"回测结果: {stats.get('backtest_count', 0)}条")
    print(f"复盘数据: {stats.get('review_count', 0)}条")
    
    # 通知发送器
    notification_sender = get_notification_sender()
    print(f"\n通知推送: {'启用' if notification_sender.enabled else '禁用'}")
    print(f"豆包API: {notification_sender.api_url}")
    print(f"模型: {notification_sender.model}")


def print_schedule_info(scheduler: AutoScheduler):
    """
    打印定时任务信息
    """
    print("\n" + "=" * 80)
    print("定时任务配置")
    print("=" * 80)
    
    for task_key, task_config in scheduler.tasks.items():
        status = "✅ 启用" if task_config['enabled'] else "❌ 禁用"
        print(f"{task_config['time']} - {task_config['name']:12s} [{status}]")


def run_scheduler():
    """
    运行调度器
    """
    print("\n" + "=" * 80)
    print("启动调度器")
    print("=" * 80)
    print("\n系统将按以下时间顺序执行任务：")
    print("  15:30 - 数据下载")
    print("  16:00 - 因子计算")
    print("  18:00 - 尾盘选股")
    print("  20:00 - 历史回测")
    print("  21:00 - 市场复盘")
    print("\n按 Ctrl+C 停止系统\n")
    
    scheduler = AutoScheduler()
    scheduler.run()


def run_manual_tasks(args):
    """
    手动执行任务
    """
    print("\n" + "=" * 80)
    print("手动执行模式")
    print("=" * 80)
    
    scheduler = AutoScheduler()
    
    if args.task == 'all':
        print("执行所有任务...\n")
        scheduler.run_all_tasks()
    elif args.task == 'data':
        print("执行数据下载任务...\n")
        result = scheduler.execute_task('data_download')
        print(f"\n结果: {result.message}")
    elif args.task == 'factor':
        print("执行因子计算任务...\n")
        result = scheduler.execute_task('factor_calculation')
        print(f"\n结果: {result.message}")
    elif args.task == 'selection':
        print("执行尾盘选股任务...\n")
        result = scheduler.execute_task('stock_selection')
        print(f"\n结果: {result.message}")
    elif args.task == 'backtest':
        print("执行历史回测任务...\n")
        result = scheduler.execute_task('backtest')
        print(f"\n结果: {result.message}")
    elif args.task == 'review':
        print("执行市场复盘任务...\n")
        result = scheduler.execute_task('market_review')
        print(f"\n结果: {result.message}")
    else:
        print(f"未知任务: {args.task}")
        print("可用任务: all, data, factor, selection, backtest, review")


def cleanup_old_data(days: int = 365):
    """
    清理旧数据
    
    Args:
        days: 保留天数
    """
    print("\n" + "=" * 80)
    print(f"清理{days}天前的旧数据")
    print("=" * 80)
    
    data_manager = get_data_manager()
    data_manager.cleanup_old_data(days)
    
    print(f"✅ 清理完成")


def main():
    """
    主函数
    """
    print_banner()
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='股票量化自动化系统')
    parser.add_argument('--mode', '-m', type=str, default='schedule',
                      choices=['schedule', 'manual', 'info', 'cleanup'],
                      help='运行模式: schedule(调度), manual(手动), info(信息), cleanup(清理)')
    parser.add_argument('--task', '-t', type=str, default='all',
                      choices=['all', 'data', 'factor', 'selection', 'backtest', 'review'],
                      help='手动模式任务: all(全部), data(数据), factor(因子), selection(选股), backtest(回测), review(复盘)')
    parser.add_argument('--cleanup-days', '-d', type=int, default=365,
                      help='清理数据保留天数')
    
    args = parser.parse_args()
    
    # 打印系统信息
    print_system_info()
    
    # 根据模式执行
    if args.mode == 'schedule':
        scheduler = AutoScheduler()
        print_schedule_info(scheduler)
        run_scheduler()
    elif args.mode == 'manual':
        run_manual_tasks(args)
    elif args.mode == 'info':
        print("\n系统信息已显示")
    elif args.mode == 'cleanup':
        cleanup_old_data(args.cleanup_days)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n" + "=" * 80)
        print("系统已停止")
        print("=" * 80)
    except Exception as e:
        logger.error(f"系统异常: {e}", exc_info=True)
        print(f"\n❌ 系统异常: {e}")
        print("=" * 80)
