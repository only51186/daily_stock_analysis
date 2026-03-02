# -*- coding: utf-8 -*-
"""
===================================
多数据源整合模块
===================================

功能：
1. 优先使用 akshare 获取实时板块热度、个股数据
2. 备用源：efinance（补充尾盘数据）、东方财富网爬虫（补充热度排名）
3. 数据缺失时自动切换数据源，避免脚本中断
"""

import logging
import time
import pandas as pd
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime

from data_provider.data_cache import get_data_cache

logger = logging.getLogger(__name__)


class MultiDataSource:
    """
    多数据源整合类
    
    实现数据源的优先级管理和自动切换，集成数据缓存功能
    """
    
    def __init__(self, use_cache: bool = True):
        """
        初始化多数据源
        
        Args:
            use_cache: 是否使用缓存
        """
        self.data_sources = {
            'akshare': {'priority': 1, 'name': 'Akshare'},
            'efinance': {'priority': 2, 'name': 'Efinance'},
            'eastmoney': {'priority': 3, 'name': 'Eastmoney'},
        }
        
        # 初始化缓存
        self.use_cache = use_cache
        self.cache = get_data_cache() if use_cache else None
        
        logger.info(f"多数据源整合模块初始化完成，缓存功能: {'启用' if use_cache else '禁用'}")
    
    def get_sector_rankings(self, n: int = 10, use_cache: bool = True) -> Tuple[List[Dict[str, Any]], str]:
        """
        获取板块热度排名
        
        优先级：缓存 -> akshare -> efinance -> eastmoney
        
        Args:
            n: 返回前N个板块
            use_cache: 是否使用缓存
            
        Returns:
            (板块列表, 数据源名称)
        """
        # 尝试从缓存加载
        if use_cache and self.cache:
            cached_df = self.cache.load_sector_data(max_age_hours=2)
            if cached_df is not None and not cached_df.empty:
                sectors = []
                for _, row in cached_df.head(n).iterrows():
                    sectors.append({
                        'name': row.get('name', ''),
                        'code': row.get('code', ''),
                        'change_pct': float(row.get('change_pct', 0)),
                        'net_inflow': float(row.get('net_inflow', 0)),
                    })
                logger.info(f"从缓存加载 {len(sectors)} 个板块")
                return sectors, 'cache'
        
        # 尝试 akshare
        try:
            logger.info("尝试使用 akshare 获取板块热度...")
            import akshare as ak
            
            # 获取行业板块资金流向
            df = ak.stock_sector_fund_flow_rank()
            if df is not None and not df.empty:
                # 按净流入额排序
                df = df.sort_values('净流入额', ascending=False)
                
                sectors = []
                for _, row in df.head(n).iterrows():
                    sectors.append({
                        'name': row.get('名称', ''),
                        'code': row.get('代码', ''),
                        'change_pct': float(row.get('涨跌幅', 0)),
                        'net_inflow': float(row.get('净流入额', 0)),
                    })
                
                # 保存到缓存
                if self.cache:
                    cache_df = pd.DataFrame(sectors)
                    self.cache.save_sector_data(cache_df)
                
                logger.info(f"akshare 成功获取 {len(sectors)} 个板块")
                return sectors, 'akshare'
        except Exception as e:
            logger.warning(f"akshare 获取板块热度失败: {e}")
        
        # 尝试 efinance
        try:
            logger.info("尝试使用 efinance 获取板块热度...")
            import efinance as ef
            
            # 获取板块行情
            df = ef.stock.get_sector_quote()
            if df is not None and not df.empty:
                # 按涨跌幅排序
                df = df.sort_values('涨跌幅', ascending=False)
                
                sectors = []
                for _, row in df.head(n).iterrows():
                    sectors.append({
                        'name': row.get('板块名称', ''),
                        'code': row.get('板块代码', ''),
                        'change_pct': float(row.get('涨跌幅', 0)),
                        'net_inflow': float(row.get('净流入额', 0)) if '净流入额' in row else 0,
                    })
                
                # 保存到缓存
                if self.cache:
                    cache_df = pd.DataFrame(sectors)
                    self.cache.save_sector_data(cache_df)
                
                logger.info(f"efinance 成功获取 {len(sectors)} 个板块")
                return sectors, 'efinance'
        except Exception as e:
            logger.warning(f"efinance 获取板块热度失败: {e}")
        
        # 尝试东方财富网爬虫
        try:
            logger.info("尝试使用东方财富网爬虫获取板块热度...")
            sectors = self._get_eastmoney_sector_rankings(n)
            if sectors:
                # 保存到缓存
                if self.cache:
                    cache_df = pd.DataFrame(sectors)
                    self.cache.save_sector_data(cache_df)
                
                logger.info(f"东方财富网爬虫成功获取 {len(sectors)} 个板块")
                return sectors, 'eastmoney'
        except Exception as e:
            logger.warning(f"东方财富网爬虫获取板块热度失败: {e}")
        
        logger.error("所有数据源获取板块热度均失败")
        return [], 'none'
    
    def _get_eastmoney_sector_rankings(self, n: int = 10) -> List[Dict[str, Any]]:
        """
        东方财富网爬虫获取板块热度
        
        Args:
            n: 返回前N个板块
            
        Returns:
            板块列表
        """
        import requests
        import json
        
        url = "http://push2.eastmoney.com/api/qt/clist/get"
        params = {
            "pn": 1,
            "pz": n,
            "po": 1,
            "np": 1,
            "fltt": 2,
            "invt": 2,
            "fid": "f20",
            "fs": "m:90",
            "fields": "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21,f22,f23,f24,f25,f26,f33,f34,f35,f36,f37,f38,f39,f40,f41,f42,f43,f44,f45,f46,f47,f48,f49,f50,f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65,f66,f67,f68,f69,f70,f71,f72,f73,f74,f75,f76,f77,f78,f79,f80,f81,f82,f83,f84,f85,f86,f87,f88,f89,f90,f91,f92,f93,f94,f95,f96,f97,f98,f99,f100",
            "_": int(time.time() * 1000)
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        data = response.json()
        
        sectors = []
        if 'data' in data and 'diff' in data['data']:
            for item in data['data']['diff']:
                sectors.append({
                    'name': item.get('f14', ''),
                    'code': item.get('f12', ''),
                    'change_pct': float(item.get('f3', 0)),
                    'net_inflow': float(item.get('f20', 0)),
                })
        
        return sectors
    
    def get_all_stocks(self, use_cache: bool = True) -> Tuple[pd.DataFrame, str]:
        """
        获取所有A股股票数据
        
        优先级：缓存 -> akshare -> efinance
        
        Args:
            use_cache: 是否使用缓存
            
        Returns:
            (股票数据DataFrame, 数据源名称)
        """
        # 尝试从缓存加载
        if use_cache and self.cache:
            cached_df = self.cache.load_stock_data(max_age_hours=2)
            if cached_df is not None and not cached_df.empty:
                logger.info(f"从缓存加载 {len(cached_df)} 只股票")
                return cached_df, 'cache'
        
        # 尝试 akshare
        try:
            logger.info("尝试使用 akshare 获取股票数据...")
            import akshare as ak
            
            df = ak.stock_zh_a_spot()
            if df is not None and not df.empty:
                # 保存到缓存
                if self.cache:
                    self.cache.save_stock_data(df)
                
                logger.info(f"akshare 成功获取 {len(df)} 只股票")
                return df, 'akshare'
        except Exception as e:
            logger.warning(f"akshare 获取股票数据失败: {e}")
        
        # 尝试 efinance
        try:
            logger.info("尝试使用 efinance 获取股票数据...")
            import efinance as ef
            
            # 防封禁策略：随机休眠
            time.sleep(2)
            
            df = ef.stock.get_realtime_quotes()
            if df is not None and not df.empty:
                # 保存到缓存
                if self.cache:
                    self.cache.save_stock_data(df)
                
                logger.info(f"efinance 成功获取 {len(df)} 只股票")
                return df, 'efinance'
        except Exception as e:
            logger.warning(f"efinance 获取股票数据失败: {e}")
        
        logger.error("所有数据源获取股票数据均失败")
        return pd.DataFrame(), 'none'
    
    def get_stock_daily_data(self, code: str, days: int = 30, use_cache: bool = True) -> Tuple[pd.DataFrame, str]:
        """
        获取个股历史数据
        
        优先级：缓存 -> akshare -> efinance
        
        Args:
            code: 股票代码
            days: 获取天数
            use_cache: 是否使用缓存
            
        Returns:
            (历史数据DataFrame, 数据源名称)
        """
        # 尝试从缓存加载
        if use_cache and self.cache:
            cached_df = self.cache.load_historical_data(code, max_age_hours=24)
            if cached_df is not None and not cached_df.empty:
                # 只取最近days天
                cached_df = cached_df.tail(days).reset_index(drop=True)
                logger.info(f"从缓存加载 {code} 历史数据，共 {len(cached_df)} 条")
                return cached_df, 'cache'
        
        # 尝试 akshare
        try:
            logger.info(f"尝试使用 akshare 获取 {code} 历史数据...")
            import akshare as ak
            
            # 判断股票类型
            if code.startswith('6'):
                stock_code = f"{code}.SH"
            else:
                stock_code = f"{code}.SZ"
            
            df = ak.stock_zh_a_hist(symbol=code, period="daily", start_date="20200101", adjust="qfq")
            if df is not None and not df.empty:
                # 保存到缓存
                if self.cache:
                    self.cache.save_historical_data(code, df)
                
                # 只取最近days天
                df = df.tail(days).reset_index(drop=True)
                logger.info(f"akshare 成功获取 {code} 历史数据，共 {len(df)} 条")
                return df, 'akshare'
        except Exception as e:
            logger.warning(f"akshare 获取 {code} 历史数据失败: {e}")
        
        # 尝试 efinance
        try:
            logger.info(f"尝试使用 efinance 获取 {code} 历史数据...")
            import efinance as ef
            
            # 防封禁策略：随机休眠
            time.sleep(1)
            
            df = ef.stock.get_quote_history(code)
            if df is not None and not df.empty:
                # 保存到缓存
                if self.cache:
                    self.cache.save_historical_data(code, df)
                
                # 只取最近days天
                df = df.tail(days).reset_index(drop=True)
                logger.info(f"efinance 成功获取 {code} 历史数据，共 {len(df)} 条")
                return df, 'efinance'
        except Exception as e:
            logger.warning(f"efinance 获取 {code} 历史数据失败: {e}")
        
        logger.error(f"所有数据源获取 {code} 历史数据均失败")
        return pd.DataFrame(), 'none'
    
    def get_realtime_data(self, codes: List[str]) -> Tuple[pd.DataFrame, str]:
        """
        获取实时行情数据
        
        优先级：akshare -> efinance
        
        Args:
            codes: 股票代码列表
            
        Returns:
            (实时数据DataFrame, 数据源名称)
        """
        # 尝试 akshare
        try:
            logger.info("尝试使用 akshare 获取实时行情...")
            import akshare as ak
            
            # 获取所有A股实时行情
            df = ak.stock_zh_a_spot()
            if df is not None and not df.empty:
                # 筛选指定股票
                # 处理不同格式的股票代码
                filtered_df = df[df['代码'].isin(codes)]
                logger.info(f"akshare 成功获取 {len(filtered_df)} 只股票实时行情")
                return filtered_df, 'akshare'
        except Exception as e:
            logger.warning(f"akshare 获取实时行情失败: {e}")
        
        # 尝试 efinance
        try:
            logger.info("尝试使用 efinance 获取实时行情...")
            import efinance as ef
            
            # 防封禁策略：随机休眠
            time.sleep(1)
            
            df = ef.stock.get_realtime_quotes()
            if df is not None and not df.empty:
                # 筛选指定股票
                code_col = '股票代码'
                if code_col in df.columns:
                    filtered_df = df[df[code_col].isin(codes)]
                    logger.info(f"efinance 成功获取 {len(filtered_df)} 只股票实时行情")
                    return filtered_df, 'efinance'
        except Exception as e:
            logger.warning(f"efinance 获取实时行情失败: {e}")
        
        logger.error("所有数据源获取实时行情均失败")
        return pd.DataFrame(), 'none'
    
    def get_end_of_day_data(self, code: str) -> Tuple[Dict[str, Any], str]:
        """
        获取尾盘数据
        
        优先级：efinance -> akshare
        
        Args:
            code: 股票代码
            
        Returns:
            (尾盘数据字典, 数据源名称)
        """
        # 尝试 efinance（尾盘数据更详细）
        try:
            logger.info(f"尝试使用 efinance 获取 {code} 尾盘数据...")
            import efinance as ef
            
            # 防封禁策略：随机休眠
            time.sleep(1)
            
            df = ef.stock.get_quote_history(code)
            if df is not None and not df.empty:
                # 获取最新一天的数据
                latest = df.iloc[-1]
                
                eod_data = {
                    'code': code,
                    'date': latest.get('日期', ''),
                    'open': float(latest.get('开盘', 0)),
                    'close': float(latest.get('收盘', 0)),
                    'high': float(latest.get('最高', 0)),
                    'low': float(latest.get('最低', 0)),
                    'volume': float(latest.get('成交量', 0)),
                    'amount': float(latest.get('成交额', 0)),
                    'turnover_rate': float(latest.get('换手率', 0)),
                    'change_pct': float(latest.get('涨跌幅', 0)),
                }
                
                logger.info(f"efinance 成功获取 {code} 尾盘数据")
                return eod_data, 'efinance'
        except Exception as e:
            logger.warning(f"efinance 获取 {code} 尾盘数据失败: {e}")
        
        # 尝试 akshare
        try:
            logger.info(f"尝试使用 akshare 获取 {code} 尾盘数据...")
            import akshare as ak
            
            df = ak.stock_zh_a_hist(symbol=code, period="daily", start_date="20200101", adjust="qfq")
            if df is not None and not df.empty:
                # 获取最新一天的数据
                latest = df.iloc[-1]
                
                eod_data = {
                    'code': code,
                    'date': latest.get('日期', ''),
                    'open': float(latest.get('开盘', 0)),
                    'close': float(latest.get('收盘', 0)),
                    'high': float(latest.get('最高', 0)),
                    'low': float(latest.get('最低', 0)),
                    'volume': float(latest.get('成交量', 0)),
                    'amount': float(latest.get('成交额', 0)),
                    'turnover_rate': float(latest.get('换手率', 0)),
                    'change_pct': float(latest.get('涨跌幅', 0)),
                }
                
                logger.info(f"akshare 成功获取 {code} 尾盘数据")
                return eod_data, 'akshare'
        except Exception as e:
            logger.warning(f"akshare 获取 {code} 尾盘数据失败: {e}")
        
        logger.error(f"所有数据源获取 {code} 尾盘数据均失败")
        return {}, 'none'
    
    def get_data_with_fallback(self, data_type: str, **kwargs) -> Tuple[Any, str]:
        """
        通用数据获取方法，带自动切换数据源
        
        Args:
            data_type: 数据类型（sector_rankings, all_stocks, stock_daily, realtime, end_of_day）
            **kwargs: 其他参数
            
        Returns:
            (数据, 数据源名称)
        """
        if data_type == 'sector_rankings':
            return self.get_sector_rankings(kwargs.get('n', 10))
        elif data_type == 'all_stocks':
            return self.get_all_stocks()
        elif data_type == 'stock_daily':
            return self.get_stock_daily_data(kwargs.get('code'), kwargs.get('days', 30))
        elif data_type == 'realtime':
            return self.get_realtime_data(kwargs.get('codes', []))
        elif data_type == 'end_of_day':
            return self.get_end_of_day_data(kwargs.get('code'))
        else:
            logger.error(f"未知的数据类型: {data_type}")
            return None, 'none'


# 单例模式
_multi_data_source = None


def get_multi_data_source() -> MultiDataSource:
    """
    获取多数据源实例（单例）
    
    Returns:
        MultiDataSource实例
    """
    global _multi_data_source
    if _multi_data_source is None:
        _multi_data_source = MultiDataSource()
    return _multi_data_source


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    mds = get_multi_data_source()
    
    # 测试获取板块热度
    print("\n测试获取板块热度:")
    sectors, source = mds.get_sector_rankings(5)
    print(f"数据源: {source}")
    for sector in sectors:
        print(f"  {sector['name']}: {sector['change_pct']:.2f}%")
    
    # 测试获取股票数据
    print("\n测试获取股票数据:")
    df, source = mds.get_all_stocks()
    print(f"数据源: {source}, 共 {len(df)} 只股票")
    
    # 测试获取个股历史数据
    print("\n测试获取个股历史数据:")
    df, source = mds.get_stock_daily_data('600000', 10)
    print(f"数据源: {source}, 共 {len(df)} 条数据")
    
    # 测试获取尾盘数据
    print("\n测试获取尾盘数据:")
    data, source = mds.get_end_of_day_data('600000')
    print(f"数据源: {source}")
    if data:
        print(f"  收盘价: {data['close']}")
        print(f"  涨跌幅: {data['change_pct']:.2f}%")
