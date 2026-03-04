# -*- coding: utf-8 -*-
"""
===================================
数据下载自动化模块
===================================

【功能】
1. 定时自动下载数据（每日9:30/14:00）
2. 本地CSV缓存（有效期1小时），避免重复请求
3. 合并重复的"数据请求-解析"逻辑
4. 复用原有Windows任务计划程序适配逻辑

【开发状态】新增模块
"""

import logging
import sys
import os
import time
import schedule
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from data_provider.multi_data_source import get_multi_data_source
from data_provider.data_cache import get_data_cache
from config.settings import get_settings
from utils.logger_config import setup_logger, log_execution_time
from src.data.tushare_processor import get_tushare_processor

# 配置日志
logger = setup_logger(__name__, log_file='logs/data.log')


class AutoDataDownloader:
    """
    自动数据下载器
    
    【新增类】
    功能：
    1. 定时下载板块和个股数据
    2. 管理本地缓存
    3. 提供统一的数据获取接口
    """
    
    def __init__(self):
        """
        初始化自动数据下载器
        """
        self.settings = get_settings()
        self.data_source = get_multi_data_source()
        self.cache = get_data_cache()
        self.tushare_processor = get_tushare_processor()
        
        # 下载状态
        self.last_download_time = None
        self.download_status = {}
        
        logger.info("自动数据下载器初始化完成")
        logger.info("已集成 Tushare 数据处理器（遵循120积分权限规则）")
    
    @log_execution_time
    def download_all_data(self, force: bool = False) -> Dict[str, Any]:
        """
        下载所有数据
        
        【新增方法】
        功能：下载板块排名、所有股票数据、热门股票历史数据
        
        Args:
            force: 是否强制下载（忽略缓存）
            
        Returns:
            下载结果统计
        """
        logger.info("开始下载所有数据...")
        
        results = {
            'sectors': {'success': False, 'count': 0, 'source': ''},
            'stocks': {'success': False, 'count': 0, 'source': ''},
            'historical': {'success': False, 'count': 0},
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            # 1. 下载板块数据
            logger.info("下载板块数据...")
            sectors, source = self.data_source.get_sector_rankings(
                n=self.settings.strategy.top_sectors_count,
                use_cache=not force
            )
            
            if sectors:
                results['sectors'] = {
                    'success': True,
                    'count': len(sectors),
                    'source': source
                }
                logger.info(f"成功下载 {len(sectors)} 个板块数据，来源: {source}")
            else:
                logger.warning("板块数据下载失败")
            
            # 2. 下载所有股票数据
            logger.info("下载股票数据...")
            stocks_df, source = self.data_source.get_all_stocks(use_cache=not force)
            
            if not stocks_df.empty:
                # 标准化列名，确保数据可以直接用于计算指标
                print("📊 标准化数据格式，确保可用于指标计算...")
                
                column_mapping = {
                    '代码': 'code',
                    '名称': 'name',
                    '最新价': 'close',
                    '昨收': 'pre_close',
                    '涨跌幅': 'pct_chg',
                    '涨跌额': 'change',
                    '成交量': 'volume',
                    '成交额': 'amount',
                    '换手率': 'turnover',
                    '量比': 'volume_ratio',
                    '流通市值': 'circ_mv',
                    '总市值': 'total_mv',
                    '振幅': 'amplitude',
                    '最高': 'high',
                    '最低': 'low',
                    '今开': 'open',
                }
                
                for old_col, new_col in column_mapping.items():
                    if old_col in stocks_df.columns:
                        stocks_df[new_col] = stocks_df[old_col]
                
                # 添加日期列
                stocks_df['date'] = datetime.now().strftime('%Y-%m-%d')
                
                # 确保数值类型正确
                numeric_columns = ['open', 'high', 'low', 'close', 'pre_close', 
                                 'change', 'pct_chg', 'volume', 'amount', 
                                 'turnover', 'volume_ratio', 'circ_mv', 
                                 'total_mv', 'amplitude']
                
                for col in numeric_columns:
                    if col in stocks_df.columns:
                        stocks_df[col] = pd.to_numeric(stocks_df[col], errors='coerce')
                
                # 保存到CSV缓存（当天可重复使用）
                print("💾 保存数据到本地CSV缓存...")
                self.cache.save_stock_data(stocks_df)
                
                # 直接保存股票数据到数据库
                print("💾 保存数据到SQLite数据库...")
                try:
                    import sqlite3
                    from pathlib import Path
                    
                    project_root = Path(__file__).parent.parent
                    db_path = project_root / 'data' / 'stock_data.db'
                    
                    conn = sqlite3.connect(str(db_path), check_same_thread=False)
                    
                    cursor = conn.cursor()
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS stock_daily (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            code TEXT NOT NULL,
                            name TEXT,
                            date TEXT NOT NULL,
                            open REAL,
                            high REAL,
                            low REAL,
                            close REAL,
                            volume REAL,
                            amount REAL,
                            pct_chg REAL,
                            turnover REAL,
                            volume_ratio REAL,
                            circ_mv REAL,
                            total_mv REAL,
                            amplitude REAL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            UNIQUE(code, date)
                        )
                    ''')
                    conn.commit()
                    
                    # 处理缺失列，确保所有必要的列都存在
                    save_columns = ['code', 'name', 'date', 'open', 'high', 'low', 'close', 
                                  'volume', 'amount', 'pct_chg', 'turnover', 
                                  'volume_ratio', 'circ_mv', 'total_mv', 'amplitude']
                    
                    df_to_save = pd.DataFrame()
                    for col in save_columns:
                        if col in stocks_df.columns:
                            df_to_save[col] = stocks_df[col]
                        else:
                            df_to_save[col] = None
                    
                    df_to_save.to_sql('stock_daily', conn, if_exists='append', index=False, 
                                   method='multi', chunksize=100)
                    conn.commit()
                    conn.close()
                    
                    results['stocks'] = {
                        'success': True,
                        'count': len(stocks_df),
                        'source': source
                    }
                    logger.info(f"成功下载并保存 {len(stocks_df)} 只股票数据，来源: {source}")
                    print(f"✅ 数据处理完成：已标准化格式、保存到缓存和数据库")
                except Exception as e:
                    results['stocks'] = {
                        'success': False,
                        'count': 0,
                        'source': source
                    }
                    logger.warning(f"股票数据保存失败: {str(e)}")
                    import traceback
                    traceback.print_exc()
            else:
                logger.warning("股票数据下载失败")
            
            # 3. 下载热门股票历史数据（前50只）
            if not stocks_df.empty:
                logger.info("下载热门股票历史数据...")
                
                # 筛选主板股票
                main_board_codes = self._get_main_board_codes(stocks_df)
                
                # 下载历史数据
                historical_count = 0
                for code in main_board_codes[:50]:  # 只下载前50只
                    try:
                        # 使用 Tushare 数据处理器（遵循120积分权限规则）
                        ts_code = self._convert_to_tushare_code(code)
                        end_date = datetime.now().strftime('%Y%m%d')
                        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
                        
                        logger.info(f"处理股票历史数据: {ts_code}")
                        
                        # 使用 tushare_processor 处理数据（自动完成复权计算）
                        result = self.tushare_processor.process_stock_data(
                            ts_code, start_date, end_date
                        )
                        
                        if result['success']:
                            historical_count += 1
                            logger.info(f"✅ {ts_code}: 非复权{result['raw_count']}条, 前复权{result['qfq_count']}条, 后复权{result['hqf_count']}条")
                        else:
                            logger.warning(f"⚠️ {ts_code}: {result.get('error', '处理失败')}")
                            
                    except Exception as e:
                        logger.warning(f"处理股票 {code} 历史数据失败: {e}")
                
                results['historical'] = {
                    'success': historical_count > 0,
                    'count': historical_count
                }
                logger.info(f"成功处理 {historical_count} 只股票历史数据（含复权计算）")
            
            # 更新下载状态
            self.last_download_time = datetime.now()
            self.download_status = results
            
            logger.info("数据下载完成")
            return results
            
        except Exception as e:
            logger.error(f"数据下载过程中发生错误: {e}", exc_info=True)
            return results
    
    def _get_main_board_codes(self, stocks_df: pd.DataFrame) -> List[str]:
        """
        获取主板股票代码列表
        
        【新增方法】
        
        Args:
            stocks_df: 股票数据DataFrame
            
        Returns:
            主板股票代码列表
        """
        codes = []
        
        for _, row in stocks_df.iterrows():
            code = str(row.get('代码', ''))
            
            # 处理不同格式的股票代码
            if '.' in code:
                code = code.split('.')[0]
            
            code = code.strip()
            
            # 主板股票代码规则
            if code.startswith(('600', '601', '603', '000')):
                codes.append(code)
        
        return codes
    
    def _convert_to_tushare_code(self, code: str) -> str:
        """
        转换为 Tushare 代码格式
        
        【新增方法】
        
        Args:
            code: 股票代码（如 600000）
            
        Returns:
            Tushare 格式代码（如 600000.SH）
        """
        code = code.strip()
        
        # 处理不同格式的股票代码
        if '.' in code:
            code = code.split('.')[0]
        
        # 添加交易所后缀
        if code.startswith('6'):
            return f"{code}.SH"
        elif code.startswith(('0', '3')):
            return f"{code}.SZ"
        else:
            return code
    
    def get_cached_data(self, data_type: str) -> Optional[Any]:
        """
        获取缓存数据
        
        【新增方法】
        功能：从缓存获取数据，如果过期则自动下载
        
        Args:
            data_type: 数据类型（sectors, stocks, historical）
            
        Returns:
            缓存数据
        """
        cache_ttl = self.settings.data_source.cache_ttl_hours
        
        if data_type == 'sectors':
            data = self.cache.load_sector_data(max_age_hours=cache_ttl)
            if data is None:
                logger.info("板块数据缓存过期，自动下载...")
                self.download_all_data()
                data = self.cache.load_sector_data(max_age_hours=cache_ttl)
            return data
            
        elif data_type == 'stocks':
            data = self.cache.load_stock_data(max_age_hours=cache_ttl)
            if data is None:
                logger.info("股票数据缓存过期，自动下载...")
                self.download_all_data()
                data = self.cache.load_stock_data(max_age_hours=cache_ttl)
            return data
            
        else:
            logger.warning(f"未知的数据类型: {data_type}")
            return None
    
    def schedule_downloads(self):
        """
        配置定时下载任务
        
        【新增方法】
        功能：设置每日9:30和14:00自动下载数据
        """
        download_times = self.settings.data_source.download_times
        
        for time_str in download_times:
            schedule.every().day.at(time_str).do(self.download_all_data)
            logger.info(f"已配置定时下载任务: {time_str}")
    
    def run_scheduler(self):
        """
        运行调度器
        
        【新增方法】
        功能：持续运行定时任务
        """
        logger.info("启动数据下载调度器...")
        
        # 配置定时任务
        self.schedule_downloads()
        
        # 立即执行一次
        self.download_all_data()
        
        # 持续运行
        while True:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次
    
    def get_download_status(self) -> Dict[str, Any]:
        """
        获取下载状态
        
        【新增方法】
        
        Returns:
            下载状态信息
        """
        return {
            'last_download_time': self.last_download_time.isoformat() if self.last_download_time else None,
            'download_status': self.download_status,
            'cache_stats': self.cache.get_cache_stats()
        }


def main():
    """
    主函数
    
    【新增函数】
    """
    logger.info("启动数据下载自动化...")
    
    # 创建下载器
    downloader = AutoDataDownloader()
    
    # 立即下载一次
    results = downloader.download_all_data()
    
    # 输出结果
    print("\n=== 数据下载结果 ===")
    print(f"板块数据: {results['sectors']['count']} 个")
    print(f"股票数据: {results['stocks']['count']} 只")
    print(f"历史数据: {results['historical']['count']} 只")
    
    # 启动定时调度（可选）
    # downloader.run_scheduler()


if __name__ == "__main__":
    main()
