# -*- coding: utf-8 -*-
"""
===================================
OpenBB数据获取模块
===================================

功能：
1. 封装OpenBB统一调用接口
2. 实现多源兜底逻辑（OpenBB→Tushare→AkShare→本地缓存）
3. 实现数据完整性校验
4. 异常处理和自动切换
"""

import logging
import os
import time
import pandas as pd
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class DataSourceType(Enum):
    """数据源类型枚举"""
    OPENBB = "openbb"
    TUSHARE = "tushare"
    AKSHARE = "akshare"
    CACHE = "cache"


@dataclass
class DataSourceResult:
    """数据源结果"""
    success: bool
    data: Optional[pd.DataFrame]
    source: DataSourceType
    message: str
    duration: float


class OpenBBFetcher:
    """
    OpenBB数据获取器
    
    实现多源兜底逻辑，确保数据稳定获取
    """
    
    def __init__(self):
        """初始化OpenBB获取器"""
        self.obb = None
        self.openbb_available = False
        self._init_openbb()
        
        # 数据源优先级
        self.source_priority = [
            DataSourceType.OPENBB,
            DataSourceType.TUSHARE,
            DataSourceType.AKSHARE,
            DataSourceType.CACHE
        ]
        
        # 重试配置
        self.retry_config = {
            'max_retries': 3,
            'retry_intervals': [3, 8, 15],  # 秒
            'timeout': 20  # 秒
        }
        
        logger.info("OpenBB数据获取器初始化完成")
    
    def _init_openbb(self) -> bool:
        """
        初始化OpenBB
        
        Returns:
            bool: 是否初始化成功
        """
        try:
            from openbb import obb
            self.obb = obb
            self.openbb_available = True
            logger.info("✅ OpenBB初始化成功")
            return True
        except ImportError as e:
            logger.warning(f"⚠️ OpenBB导入失败: {e}")
            return False
        except Exception as e:
            logger.warning(f"⚠️ OpenBB初始化失败: {e}")
            return False
    
    def get_stock_data(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        interval: str = "1d"
    ) -> DataSourceResult:
        """
        获取股票数据（带多源兜底）
        
        Args:
            symbol: 股票代码（如：000001.SZ）
            start_date: 开始日期（YYYY-MM-DD）
            end_date: 结束日期（YYYY-MM-DD）
            interval: 数据间隔（1d=日线, 1h=小时线）
            
        Returns:
            DataSourceResult: 数据获取结果
        """
        # 设置默认日期
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        
        # 按优先级尝试各数据源
        for source in self.source_priority:
            result = self._try_source(
                source, symbol, start_date, end_date, interval
            )
            
            if result.success:
                # 数据完整性校验
                if self._validate_data(result.data):
                    logger.info(f"✅ 从{source.value}获取数据成功，共{len(result.data)}条")
                    return result
                else:
                    logger.warning(f"⚠️ {source.value}数据校验失败，尝试下一个数据源")
            else:
                logger.warning(f"⚠️ {source.value}获取失败: {result.message}")
        
        # 所有数据源都失败
        return DataSourceResult(
            success=False,
            data=None,
            source=DataSourceType.CACHE,
            message="所有数据源均不可用",
            duration=0
        )
    
    def _try_source(
        self,
        source: DataSourceType,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str
    ) -> DataSourceResult:
        """
        尝试从指定数据源获取数据
        
        Args:
            source: 数据源类型
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            interval: 数据间隔
            
        Returns:
            DataSourceResult: 获取结果
        """
        start_time = time.time()
        
        for attempt in range(self.retry_config['max_retries']):
            try:
                if source == DataSourceType.OPENBB:
                    data = self._fetch_from_openbb(symbol, start_date, end_date, interval)
                elif source == DataSourceType.TUSHARE:
                    data = self._fetch_from_tushare(symbol, start_date, end_date)
                elif source == DataSourceType.AKSHARE:
                    data = self._fetch_from_akshare(symbol, start_date, end_date)
                else:
                    data = self._fetch_from_cache(symbol, start_date, end_date)
                
                duration = time.time() - start_time
                
                if data is not None and not data.empty:
                    return DataSourceResult(
                        success=True,
                        data=data,
                        source=source,
                        message=f"成功获取{len(data)}条数据",
                        duration=duration
                    )
                else:
                    raise ValueError("返回数据为空")
                    
            except Exception as e:
                logger.warning(f"⚠️ {source.value}第{attempt+1}次尝试失败: {e}")
                
                if attempt < self.retry_config['max_retries'] - 1:
                    wait_time = self.retry_config['retry_intervals'][attempt]
                    logger.info(f"⏳ 等待{wait_time}秒后重试...")
                    time.sleep(wait_time)
        
        duration = time.time() - start_time
        return DataSourceResult(
            success=False,
            data=None,
            source=source,
            message=f"{self.retry_config['max_retries']}次重试后仍失败",
            duration=duration
        )
    
    def _fetch_from_openbb(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str
    ) -> Optional[pd.DataFrame]:
        """
        从OpenBB获取数据
        
        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            interval: 数据间隔
            
        Returns:
            Optional[pd.DataFrame]: 股票数据
        """
        if not self.openbb_available:
            raise RuntimeError("OpenBB未初始化")
        
        # 转换股票代码格式
        openbb_symbol = self._convert_to_openbb_symbol(symbol)
        
        # 获取数据
        output = self.obb.equity.price.historical(
            symbol=openbb_symbol,
            start_date=start_date,
            end_date=end_date,
            interval=interval
        )
        
        df = output.to_dataframe()
        
        # 标准化列名
        df = self._standardize_columns(df, 'openbb')
        
        return df
    
    def _fetch_from_tushare(
        self,
        symbol: str,
        start_date: str,
        end_date: str
    ) -> Optional[pd.DataFrame]:
        """
        从Tushare获取数据（非复权日K）
        
        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            Optional[pd.DataFrame]: 股票数据
        """
        try:
            import tushare as ts
            from dotenv import load_dotenv
            
            # 加载环境变量
            load_dotenv()
            
            # 获取token
            token = os.getenv('TUSHARE_TOKEN')
            if not token:
                logger.error("TUSHARE_TOKEN未配置")
                return None
            
            # 转换代码格式
            ts_symbol = self._convert_to_tushare_symbol(symbol)
            
            # 获取数据（非复权日K）
            pro = ts.pro_api(token=token)
            df = pro.daily(
                ts_code=ts_symbol,
                start_date=start_date.replace('-', ''),
                end_date=end_date.replace('-', '')
            )
            
            if df is not None and not df.empty:
                df = self._standardize_columns(df, 'tushare')
                return df
            else:
                return None
                
        except Exception as e:
            logger.error(f"Tushare获取失败: {e}")
            return None
    
    def _fetch_from_akshare(
        self,
        symbol: str,
        start_date: str,
        end_date: str
    ) -> Optional[pd.DataFrame]:
        """
        从AkShare获取数据
        
        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            Optional[pd.DataFrame]: 股票数据
        """
        try:
            import akshare as ak
            
            # 转换代码格式
            ak_symbol = self._convert_to_akshare_symbol(symbol)
            
            # 获取数据
            df = ak.stock_zh_a_hist(
                symbol=ak_symbol,
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"
            )
            
            if df is not None and not df.empty:
                df = self._standardize_columns(df, 'akshare')
                return df
            else:
                return None
                
        except Exception as e:
            logger.error(f"AkShare获取失败: {e}")
            return None
    
    def _fetch_from_cache(
        self,
        symbol: str,
        start_date: str,
        end_date: str
    ) -> Optional[pd.DataFrame]:
        """
        从本地缓存获取数据
        
        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            Optional[pd.DataFrame]: 股票数据
        """
        try:
            from data_provider.data_cache import get_data_cache
            cache = get_data_cache()
            
            # 尝试从缓存加载
            df = cache.load_stock_data(symbol)
            
            if df is not None and not df.empty:
                # 过滤日期范围
                df = df[(df['trade_date'] >= start_date) & (df['trade_date'] <= end_date)]
                logger.info(f"从缓存加载{symbol}数据，共{len(df)}条")
                return df
            else:
                return None
                
        except Exception as e:
            logger.error(f"缓存获取失败: {e}")
            return None
    
    def _convert_to_openbb_symbol(self, symbol: str) -> str:
        """转换为OpenBB格式的股票代码"""
        # 000001.SZ -> 000001.SZ (OpenBB使用标准格式)
        return symbol
    
    def _convert_to_tushare_symbol(self, symbol: str) -> str:
        """转换为Tushare格式的股票代码"""
        # 000001.SZ -> 000001.SZ (Tushare使用标准格式)
        return symbol
    
    def _convert_to_akshare_symbol(self, symbol: str) -> str:
        """转换为AkShare格式的股票代码"""
        # 000001.SZ -> 000001
        return symbol.split('.')[0]
    
    def _standardize_columns(self, df: pd.DataFrame, source: str) -> pd.DataFrame:
        """
        标准化列名
        
        Args:
            df: 原始数据
            source: 数据源名称
            
        Returns:
            pd.DataFrame: 标准化后的数据
        """
        df = df.copy()
        
        # 列名映射
        column_mapping = {
            'openbb': {
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume',
                'date': 'trade_date'
            },
            'tushare': {
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'vol': 'volume',
                'trade_date': 'trade_date'
            },
            'akshare': {
                '开盘': 'open',
                '最高': 'high',
                '最低': 'low',
                '收盘': 'close',
                '成交量': 'volume',
                '日期': 'trade_date'
            }
        }
        
        if source in column_mapping:
            df = df.rename(columns=column_mapping[source])
        
        # 确保日期格式正确
        if 'trade_date' in df.columns:
            df['trade_date'] = pd.to_datetime(df['trade_date']).dt.strftime('%Y-%m-%d')
        
        return df
    
    def _validate_data(self, df: pd.DataFrame) -> bool:
        """
        数据完整性校验
        
        Args:
            df: 数据DataFrame
            
        Returns:
            bool: 校验是否通过
        """
        if df is None or df.empty:
            logger.warning("数据为空")
            return False
        
        # 检查核心字段
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in required_columns:
            if col not in df.columns:
                logger.warning(f"缺少核心字段: {col}")
                return False
        
        # 检查数值合理性
        # 1. 成交量必须>=0
        if (df['volume'] < 0).any():
            logger.warning("成交量存在负值")
            return False
        
        # 2. A股涨跌幅检查（±10%）
        if 'pct_change' in df.columns:
            max_change = df['pct_change'].abs().max()
            if max_change > 0.11:  # 允许一定误差
                logger.warning(f"涨跌幅异常: {max_change:.2%}")
                return False
        
        # 3. 价格逻辑检查
        if not ((df['low'] <= df['close']) & (df['close'] <= df['high'])).all():
            logger.warning("价格逻辑错误")
            return False
        
        logger.info(f"✅ 数据校验通过，共{len(df)}条记录")
        return True


# 全局实例
_openbb_fetcher: Optional[OpenBBFetcher] = None


def get_openbb_fetcher() -> OpenBBFetcher:
    """获取OpenBB获取器实例"""
    global _openbb_fetcher
    if _openbb_fetcher is None:
        _openbb_fetcher = OpenBBFetcher()
    return _openbb_fetcher


def get_openbb_stock_data(
    symbol: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    interval: str = "1d"
) -> Tuple[Optional[pd.DataFrame], str]:
    """
    获取股票数据（统一接口）
    
    Args:
        symbol: 股票代码
        start_date: 开始日期
        end_date: 结束日期
        interval: 数据间隔
        
    Returns:
        Tuple[Optional[pd.DataFrame], str]: (数据, 数据源名称)
    """
    fetcher = get_openbb_fetcher()
    result = fetcher.get_stock_data(symbol, start_date, end_date, interval)
    
    if result.success:
        return result.data, result.source.value
    else:
        return None, result.message
