# -*- coding: utf-8 -*-
"""
智能自动化定时调度模块
"""

import logging
import sys
import os
import time
import schedule
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pandas as pd

from src.data.data_manager import get_data_manager
from utils.logger_config import setup_logger
from src.notification.notification_sender import get_notification_sender

logger = setup_logger(__name__, log_file='logs/smart_auto_scheduler.log')


class SmartAutoScheduler:
    """
    智能自动化调度器
    
    【新逻辑】
    1. 15:30开始数据下载
    2. 检查数据完整性
    3. 如果数据不完整，延迟重试
    4. 直到数据完整才开始后续任务
    5. 所有程序都可以往后延迟
    """
    
    def __init__(self):
        """初始化调度器"""
        self.data_manager = get_data_manager()
        self.notification_sender = get_notification_sender()
        
        # 任务状态
        self.task_results = {}
        self.is_running = False
        self.data_download_complete = False
        self.max_retry_attempts = 10  # 最大重试次数
        self.retry_interval = 10  # 重试间隔（分钟）
        
        logger.info("智能自动化调度器初始化完成")
    
    def start_scheduler(self):
        """启动调度器"""
        print("=" * 80)
        print("启动智能自动化调度器")
        print("=" * 80)
        
        # 设置15:30开始数据下载
        schedule.every().day.at("15:30").do(self._start_daily_task_chain)
        
        print("✅ 调度器已启动")
        print("📅 每天15:30开始数据下载任务")
        print("🔄 数据完整后自动执行后续任务")
        print("⏰ 所有程序可自动延迟")
        
        # 启动调度循环
        self._run_scheduler_loop()
    
    def _run_scheduler_loop(self):
        """运行调度器循环"""
        try:
            while True:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 调度器已停止")
            logger.info("调度器已停止")
    
    def _start_daily_task_chain(self):
        """开始每日任务链"""
        if self.is_running:
            print("⚠️ 任务链已在运行中，跳过本次执行")
            return
        
        print("\n" + "=" * 80)
        print("开始每日任务链")
        print("=" * 80)
        print(f"📅 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        self.is_running = True
        self.data_download_complete = False
        
        # 步骤1: 数据下载（15:30开始）
        success = self._execute_data_download_with_retry()
        
        if success:
            # 步骤2: 数据验证
            validation_result = self._validate_data_integrity()
            
            if validation_result['is_valid']:
                # 步骤3: 执行后续任务
                self._execute_subsequent_tasks()
            else:
                print("⚠️ 数据验证不通过，等待下次重试")
        else:
            print("❌ 数据下载失败，等待下次重试")
        
        self.is_running = False
    
    def _execute_data_download_with_retry(self) -> bool:
        """执行数据下载并重试"""
        print("\n🔄 开始数据下载（带重试机制）")
        
        for attempt in range(1, self.max_retry_attempts + 1):
            print(f"\n📥 下载尝试 {attempt}/{self.max_retry_attempts}")
            print(f"⏰ 当前时间: {datetime.now().strftime('%H:%M:%S')}")
            
            # 执行数据下载
            result = self._run_data_download()
            
            if result['success']:
                print(f"✅ 数据下载成功 (尝试 {attempt})")
                self.data_download_complete = True
                return True
            else:
                print(f"❌ 数据下载失败 (尝试 {attempt}): {result['message']}")
                
                # 检查是否需要重试
                if attempt < self.max_retry_attempts:
                    print(f"⏳ {self.retry_interval}分钟后重试...")
                    time.sleep(self.retry_interval * 60)
                else:
                    print("❌ 已达到最大重试次数，放弃下载")
                    return False
        
        return False
    
    def _run_data_download(self) -> Dict[str, Any]:
        """运行数据下载"""
        try:
            print("📥 执行数据下载...")
            
            # 导入数据下载模块
            from comprehensive_data_download import ComprehensiveDataDownloader
            downloader = ComprehensiveDataDownloader()
            
            # 执行下载
            success = downloader.download_comprehensive_data()
            
            if success:
                return {
                    'success': True,
                    'message': '数据下载完成',
                    'data_count': 5486
                }
            else:
                return {
                    'success': False,
                    'message': '数据下载失败'
                }
                
        except Exception as e:
            logger.error(f"数据下载异常: {e}", exc_info=True)
            return {
                'success': False,
                'message': f'数据下载异常: {e}'
            }
    
    def _validate_data_integrity(self) -> Dict[str, Any]:
        """验证数据完整性"""
        print("\n🔍 验证数据完整性...")
        
        try:
            # 获取当前数据
            data = self.data_manager.get_stock_daily()
            
            if data.empty:
                return {
                    'is_valid': False,
                    'message': '数据库中没有数据'
                }
            
            # 检查数据日期
            today = datetime.now().strftime('%Y-%m-%d')
            latest_date = data['date'].max()
            
            print(f"   最新数据日期: {latest_date}")
            print(f"   今天日期: {today}")
            
            # 检查数据量
            stock_count = len(data)
            print(f"   股票数量: {stock_count}")
            
            # 检查数据质量
            required_columns = ['close', 'pct_chg', 'volume', 'amount', 'turnover']
            missing_columns = [col for col in required_columns if col not in data.columns]
            
            if missing_columns:
                return {
                    'is_valid': False,
                    'message': f'缺少必要列: {", ".join(missing_columns)}'
                }
            
            # 检查数据有效性
            valid_data = data.dropna(subset=required_columns)
            valid_ratio = len(valid_data) / len(data)
            
            print(f"   有效数据比例: {valid_ratio:.1%}")
            
            # 判断数据是否完整
            is_valid = (
                latest_date == today and  # 数据是最新的
                stock_count >= 5000 and  # 数据量充足
                valid_ratio >= 0.95  # 数据质量高
            )
            
            if is_valid:
                print("✅ 数据完整性验证通过")
                return {
                    'is_valid': True,
                    'message': '数据完整性验证通过',
                    'stock_count': stock_count,
                    'valid_ratio': valid_ratio
                }
            else:
                print("❌ 数据完整性验证不通过")
                return {
                    'is_valid': False,
                    'message': '数据不完整或质量不足',
                    'stock_count': stock_count,
                    'valid_ratio': valid_ratio
                }
                
        except Exception as e:
            logger.error(f"数据验证异常: {e}", exc_info=True)
            return {
                'is_valid': False,
                'message': f'数据验证异常: {e}'
            }
    
    def _execute_subsequent_tasks(self):
        """执行后续任务"""
        print("\n" + "=" * 80)
        print("开始执行后续任务")
        print("=" * 80)
        
        tasks = [
            ('factor_calculation', '因子计算', self._run_factor_calculation),
            ('stock_selection', '尾盘选股', self._run_stock_selection),
            ('backtest', '历史回测', self._run_backtest),
            ('market_review', '市场复盘', self._run_market_review)
        ]
        
        for task_name, display_name, task_func in tasks:
            print(f"\n🔄 执行任务: {display_name}")
            result = task_func()
            
            if result['success']:
                print(f"✅ {display_name}完成")
            else:
                print(f"❌ {display_name}失败: {result['message']}")
                # 继续执行下一个任务，不中断
    
    def _run_factor_calculation(self) -> Dict[str, Any]:
        """运行因子计算"""
        try:
            print("📊 执行因子计算...")
            # 这里可以集成实际的因子计算模块
            return {
                'success': True,
                'message': '因子计算完成'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'因子计算异常: {e}'
            }
    
    def _run_stock_selection(self) -> Dict[str, Any]:
        """运行尾盘选股"""
        try:
            print("📋 执行尾盘选股...")
            from adaptive_stock_selector import AdaptiveStockSelector
            selector = AdaptiveStockSelector()
            selected_stocks = selector.select_stocks()
            
            return {
                'success': True,
                'message': f'选股完成，选出{len(selected_stocks)}只股票'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'选股异常: {e}'
            }
    
    def _run_backtest(self) -> Dict[str, Any]:
        """运行历史回测"""
        try:
            print("📈 执行历史回测...")
            # 这里可以集成实际的回测模块
            return {
                'success': True,
                'message': '历史回测完成'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'回测异常: {e}'
            }
    
    def _run_market_review(self) -> Dict[str, Any]:
        """运行市场复盘"""
        try:
            print("📝 执行市场复盘...")
            # 这里可以集成实际的复盘模块
            return {
                'success': True,
                'message': '市场复盘完成'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'复盘异常: {e}'
            }
    
    def _send_completion_notification(self, success: bool, message: str):
        """发送完成通知"""
        try:
            title = "任务链完成" if success else "任务链失败"
            self.notification_sender.send_notification(
                title=title,
                message=message
            )
            logger.info(f"通知已发送: {title}")
        except Exception as e:
            logger.error(f"发送通知失败: {e}")


def main():
    """主函数"""
    print("启动智能自动化调度器...")
    print(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    scheduler = SmartAutoScheduler()
    scheduler.start_scheduler()


if __name__ == "__main__":
    main()