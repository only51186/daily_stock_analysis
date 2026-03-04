# -*- coding: utf-8 -*-
"""
===================================
统一调度模块
===================================

【功能】
1. 合并选股、回测的触发逻辑
2. 每日14:30自动运行选股
3. 每周日自动运行回测
4. 共用一套调度脚本，减少重复代码
5. 保留原有选股/回测结果格式，仅新增"自动保存+覆盖"逻辑

【开发状态】新增模块（合并原有逻辑）
"""

import logging
import sys
import os
import time
import schedule
from datetime import datetime, timedelta
from typing import Dict, Any, List
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import get_settings
from utils.logger_config import setup_logger, log_execution_time
from utils.notification_sender import get_notification_sender

# 配置日志
logger = setup_logger(__name__, log_file='logs/scheduler.log')


class UnifiedScheduler:
    """
    统一调度器
    
    【新增类】
    功能：
    1. 统一调度选股和回测任务
    2. 管理定时任务
    3. 自动推送结果
    """
    
    def __init__(self):
        """
        初始化统一调度器
        """
        self.settings = get_settings()
        self.notification_sender = get_notification_sender()
        
        # 任务状态
        self.task_status = {}
        self.last_run_times = {}
        
        logger.info("统一调度器初始化完成")
    
    @log_execution_time
    def run_stock_selection(self) -> Dict[str, Any]:
        """
        运行选股策略
        
        【合并方法】合并了原有的选股触发逻辑
        
        Returns:
            选股结果
        """
        logger.info("开始运行选股策略...")
        
        result = {
            'success': False,
            'timestamp': datetime.now().isoformat(),
            'sectors_count': 0,
            'stocks_count': 0,
            'message': ''
        }
        
        try:
            # 导入并运行选股策略
            from scripts.hs_mainboard_short_strategy import HSShortStrategy
            
            strategy = HSShortStrategy()
            strategy.run()
            
            result['success'] = True
            result['message'] = '选股策略运行成功'
            
            logger.info("选股策略运行完成")
            
        except Exception as e:
            result['message'] = f'选股策略运行失败: {str(e)}'
            logger.error(f"选股策略运行失败: {e}", exc_info=True)
        
        # 更新任务状态
        self.task_status['stock_selection'] = result
        self.last_run_times['stock_selection'] = datetime.now()
        
        return result
    
    @log_execution_time
    def run_backtest(self) -> Dict[str, Any]:
        """
        运行策略回测
        
        【合并方法】合并了原有的回测触发逻辑
        
        Returns:
            回测结果
        """
        logger.info("开始运行策略回测...")
        
        result = {
            'success': False,
            'timestamp': datetime.now().isoformat(),
            'total_return': 0,
            'win_rate': 0,
            'message': ''
        }
        
        try:
            # 导入并运行回测
            from scripts.strategy_backtest import run_backtest
            
            backtest_result = run_backtest()
            
            if backtest_result:
                result['success'] = True
                result['total_return'] = backtest_result.get('total_return', 0)
                result['win_rate'] = backtest_result.get('win_rate', 0)
                result['message'] = '回测运行成功'
            else:
                result['message'] = '回测未返回结果'
            
            logger.info("策略回测运行完成")
            
        except Exception as e:
            result['message'] = f'回测运行失败: {str(e)}'
            logger.error(f"策略回测运行失败: {e}", exc_info=True)
        
        # 更新任务状态
        self.task_status['backtest'] = result
        self.last_run_times['backtest'] = datetime.now()
        
        return result
    
    @log_execution_time
    def run_daily_review(self) -> Dict[str, Any]:
        """
        运行每日复盘
        
        【合并方法】合并了原有的复盘触发逻辑
        
        Returns:
            复盘结果
        """
        logger.info("开始运行每日复盘...")
        
        result = {
            'success': False,
            'timestamp': datetime.now().isoformat(),
            'message': ''
        }
        
        try:
            # 导入并运行复盘
            from scripts.daily_review import DailyReview
            
            reviewer = DailyReview()
            reviewer.run_review()
            
            result['success'] = True
            result['message'] = '每日复盘运行成功'
            
            logger.info("每日复盘运行完成")
            
        except Exception as e:
            result['message'] = f'每日复盘运行失败: {str(e)}'
            logger.error(f"每日复盘运行失败: {e}", exc_info=True)
        
        # 更新任务状态
        self.task_status['daily_review'] = result
        self.last_run_times['daily_review'] = datetime.now()
        
        return result
    
    def schedule_all_tasks(self):
        """
        配置所有定时任务
        
        【新增方法】
        功能：
        1. 每日14:30运行选股
        2. 每周日20:00运行回测
        3. 每日09:00运行复盘
        """
        schedule_config = self.settings.schedule
        
        # 1. 配置数据下载任务（复用原有逻辑）
        from scripts.auto_data_downloader import AutoDataDownloader
        downloader = AutoDataDownloader()
        downloader.schedule_downloads()
        logger.info("已配置数据下载定时任务")
        
        # 2. 配置选股任务（每日14:30，仅工作日）
        schedule.every().day.at(schedule_config.selection_time).do(self._run_selection_with_check)
        logger.info(f"已配置选股定时任务: {schedule_config.selection_time}")
        
        # 3. 配置回测任务（每周日20:00）
        getattr(schedule.every(), schedule_config.backtest_day.lower()).at(
            schedule_config.backtest_time
        ).do(self.run_backtest)
        logger.info(f"已配置回测定时任务: {schedule_config.backtest_day} {schedule_config.backtest_time}")
        
        # 4. 配置复盘任务（每日09:00，仅工作日）
        schedule.every().day.at(schedule_config.review_time).do(self._run_review_with_check)
        logger.info(f"已配置复盘定时任务: {schedule_config.review_time}")
    
    def _run_selection_with_check(self):
        """
        带工作日检查的选股运行
        
        【新增方法】
        """
        today = datetime.now().strftime('%A')
        if today in self.settings.schedule.selection_days:
            return self.run_stock_selection()
        else:
            logger.info(f"今天({today})不是工作日，跳过选股")
            return None
    
    def _run_review_with_check(self):
        """
        带工作日检查的复盘运行
        
        【新增方法】
        """
        today = datetime.now().strftime('%A')
        if today in self.settings.schedule.review_days:
            return self.run_daily_review()
        else:
            logger.info(f"今天({today})不是工作日，跳过复盘")
            return None
    
    def run_scheduler(self):
        """
        运行调度器
        
        【新增方法】
        功能：持续运行所有定时任务
        """
        logger.info("启动统一调度器...")
        
        # 配置所有定时任务
        self.schedule_all_tasks()
        
        logger.info("调度器已启动，等待任务执行...")
        
        # 持续运行
        while True:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次
    
    def run_all_now(self):
        """
        立即运行所有任务
        
        【新增方法】
        功能：手动触发所有任务（用于测试）
        """
        logger.info("手动触发所有任务...")
        
        # 1. 下载数据
        from scripts.auto_data_downloader import AutoDataDownloader
        downloader = AutoDataDownloader()
        downloader.download_all_data()
        
        # 2. 运行选股
        self.run_stock_selection()
        
        # 3. 运行复盘
        self.run_daily_review()
        
        # 4. 运行回测（仅在周日）
        if datetime.now().strftime('%A') == 'Sunday':
            self.run_backtest()
        
        logger.info("所有任务执行完成")
    
    def get_task_status(self) -> Dict[str, Any]:
        """
        获取任务状态
        
        【新增方法】
        
        Returns:
            任务状态信息
        """
        return {
            'task_status': self.task_status,
            'last_run_times': {
                k: v.isoformat() if v else None 
                for k, v in self.last_run_times.items()
            },
            'next_run_times': self._get_next_run_times()
        }
    
    def _get_next_run_times(self) -> Dict[str, str]:
        """
        获取下次运行时间
        
        【新增方法】
        
        Returns:
            下次运行时间
        """
        next_times = {}
        
        for job in schedule.jobs:
            next_run = job.next_run
            if next_run:
                job_name = str(job.job_func.__name__)
                next_times[job_name] = next_run.strftime('%Y-%m-%d %H:%M:%S')
        
        return next_times


def main():
    """
    主函数
    
    【新增函数】
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='统一调度器')
    parser.add_argument('--run-all', action='store_true', help='立即运行所有任务')
    parser.add_argument('--selection', action='store_true', help='仅运行选股')
    parser.add_argument('--backtest', action='store_true', help='仅运行回测')
    parser.add_argument('--review', action='store_true', help='仅运行复盘')
    parser.add_argument('--scheduler', action='store_true', help='启动定时调度器')
    
    args = parser.parse_args()
    
    scheduler = UnifiedScheduler()
    
    if args.run_all:
        scheduler.run_all_now()
    elif args.selection:
        scheduler.run_stock_selection()
    elif args.backtest:
        scheduler.run_backtest()
    elif args.review:
        scheduler.run_daily_review()
    elif args.scheduler:
        scheduler.run_scheduler()
    else:
        # 默认立即运行所有任务
        scheduler.run_all_now()


if __name__ == "__main__":
    main()
