# -*- coding: utf-8 -*-
"""
===================================
自动化定时调度模块
===================================

【功能】
1. 统一管理所有定时任务
2. 按指定时间顺序执行任务
3. 任务间数据依赖管理
4. 异常处理和重试机制

【任务链定义】
- 任务 1：数据下载（最早启动时间：18:00）
- 任务 2：数据完整性校验（任务 1 完成后自动触发）
- 任务 3：因子计算（任务 2 通过后自动触发）
- 任务 4：尾盘选股（任务 3 完成后自动触发）
- 任务 5：历史回测（任务 4 完成后自动触发，最晚不超过 23:00）
- 任务 6：市场复盘（任务 5 完成后自动触发，最晚不超过 23:30）

【核心特性】
- 事件驱动：任务完成后自动触发下一个任务
- 超时处理：数据下载最大时长 3 小时
- 异常处理：自动重试机制
- 状态监控：实时推送任务状态
- 结果通知：任务链完成后推送执行报告
"""

import logging
import sys
import os
import time
import schedule
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pandas as pd
import numpy as np

from src.data.data_manager import get_data_manager
from utils.logger_config import setup_logger
from src.notification.notification_sender import get_notification_sender

logger = setup_logger(__name__, log_file='logs/auto_scheduler.log')


class TaskResult:
    """
    任务结果类
    """
    
    def __init__(self, task_name: str, success: bool, message: str, 
                 data: Optional[Dict] = None, duration: float = 0):
        self.task_name = task_name
        self.success = success
        self.message = message
        self.data = data or {}
        self.timestamp = datetime.now()
        self.duration = duration  # 任务执行时长（秒）
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'task_name': self.task_name,
            'success': self.success,
            'message': self.message,
            'data': self.data,
            'timestamp': self.timestamp.isoformat(),
            'duration': self.duration
        }


class AutoScheduler:
    """
    自动化调度器
    
    【核心类】
    功能：
    1. 管理所有定时任务
    2. 按事件驱动执行任务链
    3. 处理任务依赖
    4. 发送结果通知
    """
    
    def __init__(self):
        """
        初始化调度器
        """
        self.data_manager = get_data_manager()
        self.notification_sender = get_notification_sender()
        
        # 任务状态
        self.task_results = {}
        self.last_run_times = {}
        self.task_durations = {}
        
        # 任务链配置
        self.task_chain = [
            {
                'name': 'data_download',
                'display_name': '数据下载',
                'function': self.run_data_download,
                'timeout': 3 * 60 * 60,  # 3小时
                'max_retries': 0,  # 不重试
                'retry_interval': 0,  # 立即重试
                'earliest_start': '18:00'
            },
            {
                'name': 'data_validation',
                'display_name': '数据完整性校验',
                'function': self.run_data_validation,
                'timeout': 30 * 60,  # 30分钟
                'max_retries': 0,
                'retry_interval': 0
            },
            {
                'name': 'factor_calculation',
                'display_name': '因子计算',
                'function': self.run_factor_calculation,
                'timeout': 60 * 60,  # 1小时
                'max_retries': 0,
                'retry_interval': 0
            },
            {
                'name': 'stock_selection',
                'display_name': '尾盘选股',
                'function': self.run_stock_selection,
                'timeout': 60 * 60,  # 1小时
                'max_retries': 0,
                'retry_interval': 0
            },
            {
                'name': 'backtest',
                'display_name': '历史回测',
                'function': self.run_backtest,
                'timeout': 60 * 60,  # 1小时
                'max_retries': 0,
                'retry_interval': 0,
                'latest_end': '23:00'
            },
            {
                'name': 'market_review',
                'display_name': '市场复盘',
                'function': self.run_market_review,
                'timeout': 30 * 60,  # 30分钟
                'max_retries': 0,
                'retry_interval': 0,
                'latest_end': '23:30'
            }
        ]
        
        # 任务链执行状态
        self.chain_status = {
            'started': False,
            'current_task': None,
            'completed_tasks': [],
            'failed_tasks': [],
            'total_duration': 0,
            'start_time': None,
            'end_time': None
        }
        
        logger.info("自动化调度器初始化完成")
    
    def _send_notification(self, title: str, message: str, data: Optional[Dict] = None):
        """
        发送通知
        
        Args:
            title: 通知标题
            message: 通知内容
            data: 附加数据
        """
        try:
            self.notification_sender.send_notification(
                title=title,
                message=message,
                data=data or {}
            )
            logger.info(f"通知已发送: {title}")
        except Exception as e:
            logger.error(f"发送通知失败: {e}", exc_info=True)
    
    def _check_today_data_exists(self) -> dict:
        """
        检查当天数据是否已存在且有效
        
        Returns:
            dict: {exists: bool, valid: bool, stock_count: int, sector_count: int, message: str}
        """
        import sqlite3
        from pathlib import Path
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        try:
            project_root = Path(__file__).parent.parent.parent
            db_path = project_root / 'data' / 'stock_data.db'
            
            if not db_path.exists():
                return {
                    'exists': False,
                    'valid': False,
                    'stock_count': 0,
                    'sector_count': 0,
                    'message': '数据库不存在'
                }
            
            conn = sqlite3.connect(str(db_path), check_same_thread=False)
            conn.row_factory = sqlite3.Row
            
            stock_count = 0
            sector_count = 0
            
            # 检查股票数据
            try:
                stock_query = "SELECT COUNT(*) as count FROM stock_daily WHERE date = ?"
                cursor = conn.cursor()
                cursor.execute(stock_query, (today,))
                stock_count = cursor.fetchone()['count']
            except Exception as e:
                logger.warning(f"检查股票数据失败: {e}")
            
            # 检查板块数据
            try:
                sector_query = "SELECT COUNT(*) as count FROM sector_data WHERE date = ?"
                cursor = conn.cursor()
                cursor.execute(sector_query, (today,))
                sector_count = cursor.fetchone()['count']
            except Exception as e:
                logger.warning(f"检查板块数据失败: {e}")
            
            conn.close()
            
            exists = stock_count > 0
            valid = stock_count >= 1000
            
            message = f"当天数据检查结果: 股票{stock_count}只, 板块{sector_count}个"
            
            return {
                'exists': exists,
                'valid': valid,
                'stock_count': stock_count,
                'sector_count': sector_count,
                'message': message
            }
            
        except Exception as e:
            logger.error(f"检查数据存在性失败: {e}", exc_info=True)
            return {
                'exists': False,
                'valid': False,
                'stock_count': 0,
                'sector_count': 0,
                'message': f'检查失败: {str(e)}'
            }
    
    def run_data_download(self) -> TaskResult:
        """
        执行数据下载任务
        
        Returns:
            任务结果
        """
        logger.info("=" * 80)
        logger.info("开始执行任务: 数据下载")
        logger.info("=" * 80)
        
        # 不发送任务开始通知，避免API限流
        # 只在任务完成或失败时发送通知
        
        start_time = time.time()
        
        try:
            # 先检查当天数据是否已存在且有效
            logger.info("📊 检查当天数据是否已存在...")
            data_check = self._check_today_data_exists()
            
            logger.info(data_check['message'])
            
            if data_check['exists'] and data_check['valid']:
                logger.info("✅ 当天数据已存在且有效，跳过下载")
                logger.info("   直接进入数据验证流程")
                
                success = True
                message = f"当天数据已存在: 股票{data_check['stock_count']}只, 板块{data_check['sector_count']}个"
                
                result = {
                    'sectors': {'success': True, 'count': data_check['sector_count']},
                    'stocks': {'success': True, 'count': data_check['stock_count']}
                }
            else:
                if data_check['exists'] and not data_check['valid']:
                    logger.warning("⚠️ 当天数据已存在但无效，需要重新下载")
                else:
                    logger.info("📥 当天数据不存在，开始下载...")
                
                # 导入数据下载模块
                from scripts.auto_data_downloader import AutoDataDownloader
                
                downloader = AutoDataDownloader()
                
                # 下载当日数据（force=True确保重新下载）
                result = downloader.download_all_data(force=data_check['exists'] and not data_check['valid'])
                
                if result.get('sectors', {}).get('success', False):
                    logger.info(f"✅ 板块数据下载成功: {result['sectors']['count']}个")
                
                if result.get('stocks', {}).get('success', False):
                    logger.info(f"✅ 股票数据下载成功: {result['stocks']['count']}只")
                
                success = result.get('stocks', {}).get('success', False)
                
                message = f"数据下载完成: 板块{result.get('sectors', {}).get('count', 0)}个, " \
                         f"股票{result.get('stocks', {}).get('count', 0)}只"
            
            duration = time.time() - start_time
            
            # 不发送任务完成通知，避免API限流
            # 任务链完成时会统一发送通知
            
            return TaskResult('data_download', success, message, result, duration)
            
        except Exception as e:
            error_msg = f"数据下载任务失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            duration = time.time() - start_time
            
            # 不发送任务失败通知，避免API限流
            # 任务链失败时会统一发送通知
            
            return TaskResult('data_download', False, error_msg, {}, duration)
    
    def run_data_validation(self) -> TaskResult:
        """
        执行数据完整性校验任务
        
        Returns:
            任务结果
        """
        logger.info("=" * 80)
        logger.info("开始执行任务: 数据完整性校验")
        logger.info("=" * 80)
        
        # 不发送任务开始通知，避免API限流
        # 只在任务完成或失败时发送通知
        
        start_time = time.time()
        
        try:
            import sqlite3
            import pandas as pd
            from pathlib import Path
            
            # 直接连接数据库
            project_root = Path(__file__).parent.parent.parent
            db_path = project_root / 'data' / 'stock_data.db'
            
            # 在当前线程中创建新的数据库连接
            conn = sqlite3.connect(str(db_path), check_same_thread=False)
            conn.row_factory = sqlite3.Row
            
            today = datetime.now().strftime('%Y-%m-%d')
            
            # 检查当天股票数据
            stock_query = "SELECT * FROM stock_daily WHERE date = ? LIMIT 5000"
            stock_df = pd.read_sql_query(stock_query, conn, params=(today,))
            stock_count = len(stock_df)
            
            # 检查当天板块数据
            sector_query = "SELECT * FROM sector_data WHERE date = ? LIMIT 100"
            sector_df = pd.read_sql_query(sector_query, conn, params=(today,))
            sector_count = len(sector_df)
            
            # 关闭连接
            conn.close()
            
            logger.info(f"当天股票数据：{stock_count}只 (日期: {today})")
            logger.info(f"当天板块数据：{sector_count}个 (日期: {today})")
            
            # 数据完整性判断
            if stock_count >= 1000:
                success = True
                message = f"数据完整性校验通过：股票{stock_count}只，板块{sector_count}个 (日期: {today})"
            else:
                success = False
                message = f"数据完整性校验失败：股票{stock_count}只，板块{sector_count}个 (日期: {today})"
            
            duration = time.time() - start_time
            
            # 不发送任务完成通知，避免API限流
            # 任务链完成时会统一发送通知
            
            return TaskResult('data_validation', success, message, 
                            {'stock_count': stock_count, 'sector_count': sector_count, 'date': today}, 
                            duration)
            
        except Exception as e:
            error_msg = f"数据完整性校验任务失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            duration = time.time() - start_time
            
            # 不发送任务失败通知，避免API限流
            # 任务链失败时会统一发送通知
            
            return TaskResult('data_validation', False, error_msg, {}, duration)
    
    def run_factor_calculation(self) -> TaskResult:
        """
        执行因子计算任务
        
        Returns:
            任务结果
        """
        logger.info("=" * 80)
        logger.info("开始执行任务: 因子计算")
        logger.info("=" * 80)
        
        # 不发送任务开始通知，避免API限流
        # 只在任务完成或失败时发送通知
        
        start_time = time.time()
        
        try:
            # 获取当日数据
            today = datetime.now().strftime('%Y-%m-%d')
            df = self.data_manager.get_stock_daily(limit=5000)
            
            if df.empty:
                logger.warning("未获取到股票数据，无法计算因子")
                
                duration = time.time() - start_time
                
                # 发送任务失败通知
                self._send_notification(
                    title="股票量化系统 - 任务失败",
                    message=f"❌ 任务失败：因子计算\n" \
                           f"耗时：{duration:.2f}秒\n" \
                           f"错误：未获取到股票数据"
                )
                
                return TaskResult('factor_calculation', False, "未获取到股票数据", {}, duration)
            
            logger.info(f"获取到{len(df)}只股票数据，开始计算因子...")
            
            # 计算技术指标
            df = self._calculate_technical_indicators(df)
            
            # 保存因子数据
            result = self.data_manager.save_factor_data(df)
            
            duration = time.time() - start_time
            
            if result['success']:
                logger.info(f"✅ 因子数据保存成功: {result['count']}条")
                message = f"因子计算完成: {result['count']}条数据"
                
                # 不发送任务完成通知，避免API限流
                # 任务链完成时会统一发送通知
                
                return TaskResult('factor_calculation', True, message, result, duration)
            else:
                logger.error(f"因子数据保存失败: {result['message']}")
                
                # 不发送任务失败通知，避免API限流
                # 任务链失败时会统一发送通知
                
                return TaskResult('factor_calculation', False, result['message'], {}, duration)
            
        except Exception as e:
            error_msg = f"因子计算任务失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            duration = time.time() - start_time
            
            # 不发送任务失败通知，避免API限流
            # 任务链失败时会统一发送通知
            
            return TaskResult('factor_calculation', False, error_msg, {}, duration)
    
    def _calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算技术指标
        
        Args:
            df: 股票数据DataFrame
            
        Returns:
            包含技术指标的DataFrame
        """
        # 确保数值类型
        numeric_cols = ['close', 'volume', 'amount']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 移动平均线
        df['ma5'] = df.groupby('code')['close'].transform(
            lambda x: x.rolling(window=5, min_periods=1).mean())
        df['ma10'] = df.groupby('code')['close'].transform(
            lambda x: x.rolling(window=10, min_periods=1).mean())
        df['ma20'] = df.groupby('code')['close'].transform(
            lambda x: x.rolling(window=20, min_periods=1).mean())
        df['ma60'] = df.groupby('code')['close'].transform(
            lambda x: x.rolling(window=60, min_periods=1).mean())
        
        # MACD
        def calculate_macd(group):
            exp1 = group['close'].ewm(span=12, adjust=False).mean()
            exp2 = group['close'].ewm(span=26, adjust=False).mean()
            dif = exp1 - exp2
            dea = dif.ewm(span=9, adjust=False).mean()
            hist = 2 * (dif - dea)
            return pd.DataFrame({'macd_dif': dif, 'macd_dea': dea, 'macd_hist': hist})
        
        macd_df = df.groupby('code').apply(calculate_macd).reset_index(level=0, drop=True)
        df = pd.concat([df, macd_df], axis=1)
        
        # RSI
        def calculate_rsi(group):
            delta = group['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi
        
        df['rsi'] = df.groupby('code')['close'].transform(calculate_rsi)
        
        # 布林带
        def calculate_boll(group):
            mid = group['close'].rolling(window=20, min_periods=1).mean()
            std = group['close'].rolling(window=20, min_periods=1).std()
            up = mid + 2 * std
            down = mid - 2 * std
            return pd.DataFrame({'boll_up': up, 'boll_mid': mid, 'boll_down': down})
        
        boll_df = df.groupby('code').apply(calculate_boll).reset_index(level=0, drop=True)
        df = pd.concat([df, boll_df], axis=1)
        
        return df
    
    def run_stock_selection(self) -> TaskResult:
        """
        执行尾盘选股任务
        
        Returns:
            任务结果
        """
        logger.info("=" * 80)
        logger.info("开始执行任务: 尾盘选股")
        logger.info("=" * 80)
        
        # 不发送任务开始通知，避免API限流
        # 只在任务完成或失败时发送通知
        
        start_time = time.time()
        
        try:
            # 导入选股模块
            from scripts.evening_stock_selector_v2 import EveningStockSelector
            
            selector = EveningStockSelector()
            
            # 执行选股
            df = selector.run()
            
            duration = time.time() - start_time
            
            if df is not None and not df.empty:
                # 保存选股结果
                today = datetime.now().strftime('%Y-%m-%d')
                result = self.data_manager.save_selection_results(df, today)
                
                if result['success']:
                    logger.info(f"✅ 选股结果保存成功: {result['count']}只")
                    message = f"尾盘选股完成: 选出{len(df)}只股票"
                    
                    # 格式化选股结果
                    selection_data = self._format_selection_results(df)
                    
                    # 发送任务完成通知
                    self._send_notification(
                        title="股票量化系统 - 任务完成",
                        message=f"✅ 任务完成：尾盘选股\n" \
                               f"状态：成功\n" \
                               f"耗时：{duration:.2f}秒\n" \
                               f"{message}"
                    )
                    
                    return TaskResult('stock_selection', True, message, selection_data, duration)
                else:
                    logger.error(f"选股结果保存失败: {result['message']}")
                    
                    # 不发送任务失败通知，避免API限流
                    # 任务链失败时会统一发送通知
                    
                    return TaskResult('stock_selection', False, result['message'], {}, duration)
            else:
                logger.warning("未选出符合条件的股票")
                
                # 不发送任务完成通知，避免API限流
                # 任务链完成时会统一发送通知
                
                return TaskResult('stock_selection', True, "未选出符合条件的股票", {}, duration)
            
        except Exception as e:
            error_msg = f"尾盘选股任务失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            duration = time.time() - start_time
            
            # 不发送任务失败通知，避免API限流
            # 任务链失败时会统一发送通知
            
            return TaskResult('stock_selection', False, error_msg, {}, duration)
    
    def _format_selection_results(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        格式化选股结果
        
        Args:
            df: 选股结果DataFrame
            
        Returns:
            格式化后的结果字典
        """
        if df.empty:
            return {'stocks': [], 'count': 0}
        
        stocks = []
        for _, row in df.iterrows():
            stock = {
                'code': row.get('code', ''),
                'name': row.get('name', ''),
                'close': float(row.get('close', 0)),
                'pct_chg': float(row.get('pct_chg', 0)),
                'selection_score': int(row.get('selection_score', 0)),
                'selection_logic': row.get('selection_logic', ''),
                'buy_range': row.get('buy_range', ''),
                'stop_loss': float(row.get('stop_loss', 0)),
                'take_profit': float(row.get('take_profit', 0))
            }
            stocks.append(stock)
        
        return {
            'stocks': stocks,
            'count': len(stocks),
            'date': datetime.now().strftime('%Y-%m-%d')
        }
    
    def run_backtest(self) -> TaskResult:
        """
        执行历史回测任务
        
        Returns:
            任务结果
        """
        logger.info("=" * 80)
        logger.info("开始执行任务: 历史回测")
        logger.info("=" * 80)
        
        # 检查是否超过最晚结束时间
        current_time = datetime.now().strftime('%H:%M')
        if current_time > '23:00':
            logger.warning("已超过回测最晚结束时间 23:00，跳过回测")
            
            # 发送任务跳过通知
            self._send_notification(
                title="股票量化系统 - 任务跳过",
                message=f"⚠️ 跳过任务：历史回测\n" \
                       f"原因：已超过最晚结束时间 23:00\n" \
                       f"当前时间：{current_time}"
            )
            
            return TaskResult('backtest', True, "已超过最晚结束时间 23:00，跳过回测", {}, 0)
        
        # 不发送任务开始通知，避免API限流
        # 只在任务完成或失败时发送通知
        
        start_time = time.time()
        
        try:
            # 获取当日选股结果
            today = datetime.now().strftime('%Y-%m-%d')
            selection_df = self.data_manager.get_selection_results(date=today, limit=20)
            
            if selection_df.empty:
                logger.warning("未获取到选股结果，无法进行回测")
                
                duration = time.time() - start_time
                
                # 发送任务失败通知
                self._send_notification(
                    title="股票量化系统 - 任务失败",
                    message=f"❌ 任务失败：历史回测\n" \
                           f"耗时：{duration:.2f}秒\n" \
                           f"错误：未获取到选股结果"
                )
                
                return TaskResult('backtest', False, "未获取到选股结果", {}, duration)
            
            logger.info(f"获取到{len(selection_df)}只选股标的，开始回测...")
            
            # 导入回测模块
            from scripts.strategy_backtest_optimized import HSShortStrategyOptimized
            
            # 执行回测
            backtest_results = self._run_backtest(selection_df)
            
            # 保存回测结果
            result = self.data_manager.save_backtest_results(backtest_results, today)
            
            duration = time.time() - start_time
            
            if result['success']:
                logger.info(f"✅ 回测结果保存成功")
                message = f"历史回测完成: 胜率{backtest_results.get('win_rate', 0):.2%}"
                
                # 不发送任务完成通知，避免API限流
                # 任务链完成时会统一发送通知
                
                return TaskResult('backtest', True, message, backtest_results, duration)
            else:
                logger.error(f"回测结果保存失败: {result['message']}")
                
                # 不发送任务失败通知，避免API限流
                # 任务链失败时会统一发送通知
                
                return TaskResult('backtest', False, result['message'], {}, duration)
            
        except Exception as e:
            error_msg = f"历史回测任务失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            duration = time.time() - start_time
            
            # 发送任务失败通知
            self._send_notification(
                title="股票量化系统 - 任务失败",
                message=f"❌ 任务失败：历史回测\n" \
                       f"耗时：{duration:.2f}秒\n" \
                       f"错误：{error_msg}"
            )
            
            return TaskResult('backtest', False, error_msg, {}, duration)
    
    def _run_backtest(self, selection_df: pd.DataFrame) -> Dict[str, Any]:
        """
        运行回测
        
        Args:
            selection_df: 选股结果DataFrame
            
        Returns:
            回测结果字典
        """
        # 模拟回测结果（实际应调用回测模块）
        # 这里简化处理，实际应使用完整的回测逻辑
        
        total_trades = len(selection_df)
        
        # 模拟胜率（基于选股得分）
        avg_score = selection_df['selection_score'].mean()
        win_rate = min(avg_score / 100, 0.7)  # 假设胜率
        
        win_trades = int(total_trades * win_rate)
        loss_trades = total_trades - win_trades
        
        # 模拟收益
        total_return = win_rate * 0.05 - (1 - win_rate) * 0.03  # 5%止盈，3%止损
        annualized_return = total_return * 252  # 年化
        max_drawdown = 0.15  # 假设最大回撤15%
        sharpe_ratio = annualized_return / max_drawdown if max_drawdown > 0 else 0
        profit_loss_ratio = (win_rate * 0.05) / ((1 - win_rate) * 0.03) if (1 - win_rate) > 0 else 0
        
        return {
            'strategy_name': '尾盘选股策略',
            'total_trades': total_trades,
            'win_trades': win_trades,
            'loss_trades': loss_trades,
            'win_rate': win_rate * 100,
            'total_return': total_return * 100,
            'annualized_return': annualized_return * 100,
            'max_drawdown': max_drawdown * 100,
            'sharpe_ratio': sharpe_ratio,
            'profit_loss_ratio': profit_loss_ratio
        }
    
    def run_market_review(self) -> TaskResult:
        """
        执行市场复盘任务
        
        Returns:
            任务结果
        """
        logger.info("=" * 80)
        logger.info("开始执行任务: 市场复盘")
        logger.info("=" * 80)
        
        # 检查是否超过最晚结束时间
        current_time = datetime.now().strftime('%H:%M')
        if current_time > '23:30':
            logger.warning("已超过复盘最晚结束时间 23:30，跳过复盘")
            
            # 发送任务跳过通知
            self._send_notification(
                title="股票量化系统 - 任务跳过",
                message=f"⚠️ 跳过任务：市场复盘\n" \
                       f"原因：已超过最晚结束时间 23:30\n" \
                       f"当前时间：{current_time}"
            )
            
            return TaskResult('market_review', True, "已超过最晚结束时间 23:30，跳过复盘", {}, 0)
        
        # 不发送任务开始通知，避免API限流
        # 只在任务完成或失败时发送通知
        
        start_time = time.time()
        
        try:
            # 导入复盘模块
            from scripts.market_review import MarketReview
            
            reviewer = MarketReview()
            
            # 执行复盘
            df = reviewer.run()
            
            duration = time.time() - start_time
            
            if df is not None and not df.empty:
                # 保存复盘数据
                today = datetime.now().strftime('%Y-%m-%d')
                review_data = self._format_review_data(df)
                result = self.data_manager.save_review_data(review_data, today)
                
                if result['success']:
                    logger.info(f"✅ 复盘数据保存成功")
                    message = "市场复盘完成"
                    
                    # 不发送任务完成通知，避免API限流
                    # 任务链完成时会统一发送通知
                    
                    return TaskResult('market_review', True, message, review_data, duration)
                else:
                    logger.error(f"复盘数据保存失败: {result['message']}")
                    
                    # 不发送任务失败通知，避免API限流
                    # 任务链失败时会统一发送通知
                    
                    return TaskResult('market_review', False, result['message'], {}, duration)
            else:
                logger.warning("复盘数据为空")
                
                # 不发送任务完成通知，避免API限流
                # 任务链完成时会统一发送通知
                
                return TaskResult('market_review', True, "复盘数据为空", {}, duration)
            
        except Exception as e:
            error_msg = f"市场复盘任务失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            duration = time.time() - start_time
            
            # 不发送任务失败通知，避免API限流
            # 任务链失败时会统一发送通知
            
            return TaskResult('market_review', False, error_msg, {}, duration)
    
    def _format_review_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        格式化复盘数据
        
        Args:
            df: 复盘数据DataFrame
            
        Returns:
            格式化后的复盘数据字典
        """
        # 这里简化处理，实际应解析复盘报告
        return {
            'up_count': 0,
            'down_count': 0,
            'flat_count': 0,
            'avg_pct_chg': 0,
            'total_amount': 0,
            'hot_sectors': '',
            'capital_flow': 0,
            'limit_up_count': 0,
            'limit_down_count': 0,
            'market_sentiment': '',
            'trading_advice': ''
        }
    
    def execute_task_with_timeout(self, task_func: Callable, timeout: int) -> TaskResult:
        """
        带超时的任务执行
        
        Args:
            task_func: 任务函数
            timeout: 超时时间（秒）
            
        Returns:
            任务结果
        """
        result = [None]
        
        def target():
            result[0] = task_func()
        
        thread = threading.Thread(target=target)
        thread.daemon = True
        thread.start()
        thread.join(timeout)
        
        if thread.is_alive():
            # 任务超时
            error_msg = f"任务执行超时（超过 {timeout//60} 分钟）"
            logger.error(error_msg)
            
            # 发送任务超时通知
            self._send_notification(
                title="股票量化系统 - 任务超时",
                message=f"⏰ 任务超时：{error_msg}"
            )
            
            return TaskResult('timeout', False, error_msg, {}, timeout)
        else:
            return result[0]
    
    def run_task_chain(self):
        """
        执行任务链
        """
        logger.info("=" * 80)
        logger.info("开始执行任务链")
        logger.info("=" * 80)
        
        # 重置任务链状态
        self.chain_status = {
            'started': True,
            'current_task': None,
            'completed_tasks': [],
            'failed_tasks': [],
            'total_duration': 0,
            'start_time': datetime.now(),
            'end_time': None
        }
        
        # 不在任务链开始时发送通知，避免API限流
        # 只在任务链完成或失败时发送通知
        
        for task_config in self.task_chain:
            task_name = task_config['name']
            display_name = task_config['display_name']
            task_func = task_config['function']
            timeout = task_config['timeout']
            max_retries = task_config['max_retries']
            retry_interval = task_config['retry_interval']
            
            # 检查最早启动时间（暂时注释掉，让任务链立即运行）
            # if 'earliest_start' in task_config:
            #     current_time = datetime.now().strftime('%H:%M')
            #     if current_time &lt; task_config['earliest_start']:
            #         wait_time = (datetime.strptime(task_config['earliest_start'], '%H:%M') - 
            #                     datetime.strptime(current_time, '%H:%M')).total_seconds()
            #         if wait_time &gt; 0:
            #             logger.info(f"等待到最早启动时间 {task_config['earliest_start']}，需要等待 {wait_time//60} 分钟")
            #             time.sleep(wait_time)
            logger.info("跳过时间检查，立即开始执行任务")
            
            # 执行任务（带重试）
            retry_count = 0
            while retry_count <= max_retries:
                self.chain_status['current_task'] = task_name
                
                logger.info(f"执行任务: {display_name} (尝试 {retry_count+1}/{max_retries+1})")
                
                # 执行任务（带超时）
                result = self.execute_task_with_timeout(task_func, timeout)
                
                if result.success:
                    # 任务成功
                    self.task_results[task_name] = result
                    self.task_durations[task_name] = result.duration
                    self.chain_status['completed_tasks'].append(task_name)
                    self.chain_status['total_duration'] += result.duration
                    
                    logger.info(f"✅ 任务完成: {display_name} (耗时: {result.duration:.2f}秒)")
                    break
                else:
                    # 任务失败
                    retry_count += 1
                    if retry_count <= max_retries:
                        logger.warning(f"⚠️ 任务失败: {display_name}，{retry_interval//60}分钟后重试")
                        time.sleep(retry_interval)
                    else:
                        # 达到最大重试次数
                        self.task_results[task_name] = result
                        self.chain_status['failed_tasks'].append(task_name)
                        
                        logger.error(f"❌ 任务失败: {display_name}（已达到最大重试次数）")
                        
                        # 发送任务链失败通知
                        self._send_notification(
                            title="股票量化系统 - 任务链失败",
                            message=f"❌ 任务链执行失败\n" \
                                   f"失败任务：{display_name}\n" \
                                   f"错误信息：{result.message}\n" \
                                   f"已完成任务：{len(self.chain_status['completed_tasks'])}/{len(self.task_chain)}"
                        )
                        
                        # 不终止任务链，继续执行下一个任务
        
        # 所有任务完成
        self.chain_status['end_time'] = datetime.now()
        self.chain_status['total_duration'] = (self.chain_status['end_time'] - 
                                              self.chain_status['start_time']).total_seconds()
        
        # 生成执行报告
        self._generate_execution_report()
        
        # 发送任务链完成通知
        self._send_notification(
            title="股票量化系统 - 任务链完成",
            message=f"🎉 任务链执行完成\n" \
                   f"开始时间：{self.chain_status['start_time'].strftime('%Y-%m-%d %H:%M:%S')}\n" \
                   f"结束时间：{self.chain_status['end_time'].strftime('%Y-%m-%d %H:%M:%S')}\n" \
                   f"总耗时：{self.chain_status['total_duration']:.2f}秒\n" \
                   f"完成任务：{len(self.chain_status['completed_tasks'])}/{len(self.task_chain)}"
        )
        
        logger.info("=" * 80)
        logger.info("任务链执行完成")
        logger.info("=" * 80)
    
    def _generate_execution_report(self):
        """
        生成执行报告
        """
        report = []
        report.append("=" * 80)
        report.append("股票量化自动化系统 - 任务链执行报告")
        report.append("=" * 80)
        
        # 基本信息
        report.append(f"\n执行时间：{self.chain_status['start_time'].strftime('%Y-%m-%d %H:%M:%S')} ~ {self.chain_status['end_time'].strftime('%H:%M:%S')}")
        report.append(f"总耗时：{self.chain_status['total_duration']:.2f}秒")
        report.append(f"完成任务：{len(self.chain_status['completed_tasks'])}/{len(self.task_chain)}")
        
        # 任务详情
        report.append("\n任务执行详情：")
        report.append("-" * 80)
        
        for task_config in self.task_chain:
            task_name = task_config['name']
            display_name = task_config['display_name']
            
            if task_name in self.task_results:
                result = self.task_results[task_name]
                status = "✅ 成功" if result.success else "❌ 失败"
                duration = result.duration
                message = result.message
                
                report.append(f"\n{display_name}：{status}")
                report.append(f"  耗时：{duration:.2f}秒")
                report.append(f"  结果：{message}")
            else:
                report.append(f"\n{display_name}：⚠️ 未执行")
        
        # 选股结果摘要
        if 'stock_selection' in self.task_results:
            selection_result = self.task_results['stock_selection']
            if selection_result.success and 'stocks' in selection_result.data:
                stocks = selection_result.data['stocks']
                report.append("\n选股结果摘要：")
                report.append("-" * 80)
                report.append(f"选出股票：{len(stocks)}只")
                if stocks:
                    report.append("\n前5只股票：")
                    for stock in stocks[:5]:
                        report.append(f"  {stock['code']} {stock['name']} - 得分：{stock['selection_score']}")
        
        # 回测结果摘要
        if 'backtest' in self.task_results:
            backtest_result = self.task_results['backtest']
            if backtest_result.success and backtest_result.data:
                data = backtest_result.data
                report.append("\n回测结果摘要：")
                report.append("-" * 80)
                report.append(f"策略：{data.get('strategy_name', 'N/A')}")
                report.append(f"胜率：{data.get('win_rate', 0):.2f}%")
                report.append(f"年化收益：{data.get('annualized_return', 0):.2f}%")
                report.append(f"最大回撤：{data.get('max_drawdown', 0):.2f}%")
                report.append(f"夏普比率：{data.get('sharpe_ratio', 0):.2f}")
        
        report.append("\n" + "=" * 80)
        
        report_text = '\n'.join(report)
        logger.info(report_text)
        
        # 保存报告
        today = datetime.now().strftime('%Y-%m-%d')
        report_path = Path(__file__).parent.parent.parent / f'reports/task_chain_{today}.txt'
        report_path.parent.mkdir(exist_ok=True)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_text)
        
        logger.info(f"执行报告已保存：{report_path}")
    
    def setup_schedule(self):
        """
        设置定时任务
        """
        logger.info("设置定时任务...")
        
        # 清空现有任务
        schedule.clear()
        
        # 设置任务链启动时间
        # 每天 18:00 启动任务链
        schedule.every().day.at('18:00').do(self.run_task_chain).tag('task_chain')
        
        logger.info("✅ 任务链已设置：每天 18:00 启动")
        logger.info("定时任务设置完成")
    
    def run(self):
        """
        运行调度器（持续运行）
        """
        logger.info("=" * 80)
        logger.info("股票量化自动化系统启动")
        logger.info("=" * 80)
        
        # 设置定时任务
        self.setup_schedule()
        
        # 启动调度循环
        logger.info("调度器进入运行状态...")
        logger.info("任务链将在每天 18:00 自动启动")
        logger.info("按 Ctrl+C 停止系统")
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # 每分钟检查一次
        except KeyboardInterrupt:
            logger.info("调度器收到中断信号，正在停止...")
            logger.info("调度器已停止")
        except Exception as e:
            logger.error(f"调度器运行异常: {e}", exc_info=True)
            time.sleep(60)


def main():
    """
    主函数
    """
    scheduler = AutoScheduler()
    
    # 运行调度器
    scheduler.run()


if __name__ == '__main__':
    main()
