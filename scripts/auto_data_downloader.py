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
        self.data_source = get_multi_data_source(use_cache=True)
        self.cache = get_data_cache()
        
        # 下载状态
        self.last_download_time = None
        self.download_status = {}
        
        logger.info("自动数据下载器初始化完成")
    
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
                results['stocks'] = {
                    'success': True,
                    'count': len(stocks_df),
                    'source': source
                }
                logger.info(f"成功下载 {len(stocks_df)} 只股票数据，来源: {source}")
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
                        df, source = self.data_source.get_stock_daily_data(
                            code=code,
                            days=30,
                            use_cache=not force
                        )
                        if not df.empty:
                            historical_count += 1
                    except Exception as e:
                        logger.warning(f"下载股票 {code} 历史数据失败: {e}")
                
                results['historical'] = {
                    'success': historical_count > 0,
                    'count': historical_count
                }
                logger.info(f"成功下载 {historical_count} 只股票历史数据")
            
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
