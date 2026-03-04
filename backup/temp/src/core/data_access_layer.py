# -*- coding: utf-8 -*-
"""
===================================
统一数据访问层 (Data Access Layer)
===================================

【优化说明】
1. 统一所有数据访问接口，提供一致的API
2. 实现多级缓存机制（内存缓存 + 本地文件缓存）
3. 完善的数据校验和异常处理
4. 数据源自动切换和故障转移
5. 批量查询优化，减少重复调用

【调用方式】
```python
from src.core.data_access_layer import DataAccessLayer, DataType

# 创建数据访问层实例
dal = DataAccessLayer()

# 获取股票日线数据
data = dal.get_data(
    data_type=DataType.STOCK_DAILY,
    stock_code='600000',
    days=30
)

# 批量获取数据
batch_data = dal.get_batch_data(
    data_type=DataType.STOCK_DAILY,
    stock_codes=['600000', '000001'],
    days=30
)
```
"""

import logging
import json
import pickle
import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple, Callable
from functools import wraps

import pandas as pd
import numpy as np
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

from src.config import get_config
from data_provider.base import DataFetcherManager, DataFetchError

logger = logging.getLogger(__name__)


class DataType(Enum):
    """数据类型枚举"""
    STOCK_DAILY = auto()           # 股票日线数据
    STOCK_REALTIME = auto()        # 股票实时数据
    SECTOR_RANKING = auto()        # 板块排名
    STOCK_LIST = auto()            # 股票列表
    INDEX_DATA = auto()            # 指数数据
    FINANCIAL_DATA = auto()        # 财务数据


class DataAccessError(Exception):
    """数据访问异常基类"""
    pass


class DataValidationError(DataAccessError):
    """数据验证异常"""
    pass


class DataSourceError(DataAccessError):
    """数据源异常"""
    pass


@dataclass
class DataCacheConfig:
    """数据缓存配置"""
    memory_cache_enabled: bool = True
    file_cache_enabled: bool = True
    memory_cache_ttl: int = 300          # 内存缓存5分钟
    file_cache_ttl: int = 3600           # 文件缓存1小时
    cache_dir: str = "data_cache"
    max_memory_cache_size: int = 1000    # 最大内存缓存条目数


@dataclass
class DataRequest:
    """数据请求对象"""
    data_type: DataType
    stock_code: Optional[str] = None
    params: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def get_cache_key(self) -> str:
        """生成缓存键"""
        key_parts = [self.data_type.name]
        if self.stock_code:
            key_parts.append(self.stock_code)
        key_parts.append(json.dumps(self.params, sort_keys=True))
        key_str = "|".join(key_parts)
        return hashlib.md5(key_str.encode()).hexdigest()


@dataclass
class DataResponse:
    """数据响应对象"""
    data: Any
    data_type: DataType
    stock_code: Optional[str] = None
    source: str = "unknown"
    timestamp: datetime = field(default_factory=datetime.now)
    from_cache: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_empty(self) -> bool:
        """检查数据是否为空"""
        if self.data is None:
            return True
        if isinstance(self.data, pd.DataFrame):
            return self.data.empty
        if isinstance(self.data, (list, dict)):
            return len(self.data) == 0
        return False
    
    def validate(self, required_columns: Optional[List[str]] = None) -> bool:
        """
        验证数据有效性
        
        Args:
            required_columns: 必需的列名列表
            
        Returns:
            bool: 数据是否有效
        """
        if self.is_empty():
            return False
        
        if required_columns and isinstance(self.data, pd.DataFrame):
            missing = [col for col in required_columns if col not in self.data.columns]
            if missing:
                logger.warning(f"缺少必需列: {missing}")
                return False
        
        return True


class CacheManager:
    """缓存管理器"""
    
    def __init__(self, config: DataCacheConfig):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 内存缓存
        self._memory_cache: Dict[str, Tuple[Any, datetime]] = {}
        
        # 缓存目录
        self._cache_dir = Path(config.cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存数据
        
        Args:
            key: 缓存键
            
        Returns:
            Optional[Any]: 缓存数据或None
        """
        # 先检查内存缓存
        if self.config.memory_cache_enabled and key in self._memory_cache:
            data, timestamp = self._memory_cache[key]
            if (datetime.now() - timestamp).seconds < self.config.memory_cache_ttl:
                self.logger.debug(f"内存缓存命中: {key[:8]}...")
                return data
            else:
                # 过期，删除
                del self._memory_cache[key]
        
        # 检查文件缓存
        if self.config.file_cache_enabled:
            cache_file = self._cache_dir / f"{key}.pkl"
            if cache_file.exists():
                try:
                    mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
                    if (datetime.now() - mtime).seconds < self.config.file_cache_ttl:
                        with open(cache_file, 'rb') as f:
                            data = pickle.load(f)
                        self.logger.debug(f"文件缓存命中: {key[:8]}...")
                        
                        # 更新内存缓存
                        if self.config.memory_cache_enabled:
                            self._set_memory_cache(key, data)
                        
                        return data
                    else:
                        # 过期，删除
                        cache_file.unlink()
                except Exception as e:
                    self.logger.warning(f"读取文件缓存失败: {e}")
        
        return None
    
    def set(self, key: str, data: Any):
        """
        设置缓存数据
        
        Args:
            key: 缓存键
            data: 缓存数据
        """
        # 更新内存缓存
        if self.config.memory_cache_enabled:
            self._set_memory_cache(key, data)
        
        # 更新文件缓存
        if self.config.file_cache_enabled:
            try:
                cache_file = self._cache_dir / f"{key}.pkl"
                with open(cache_file, 'wb') as f:
                    pickle.dump(data, f)
            except Exception as e:
                self.logger.warning(f"写入文件缓存失败: {e}")
    
    def _set_memory_cache(self, key: str, data: Any):
        """设置内存缓存"""
        # 清理过期缓存
        self._cleanup_memory_cache()
        
        # 如果缓存已满，删除最旧的条目
        if len(self._memory_cache) >= self.config.max_memory_cache_size:
            oldest_key = min(self._memory_cache.keys(), 
                           key=lambda k: self._memory_cache[k][1])
            del self._memory_cache[oldest_key]
        
        self._memory_cache[key] = (data, datetime.now())
    
    def _cleanup_memory_cache(self):
        """清理过期内存缓存"""
        now = datetime.now()
        expired_keys = [
            key for key, (_, timestamp) in self._memory_cache.items()
            if (now - timestamp).seconds > self.config.memory_cache_ttl
        ]
        for key in expired_keys:
            del self._memory_cache[key]
    
    def clear(self):
        """清空所有缓存"""
        self._memory_cache.clear()
        
        if self.config.file_cache_enabled:
            for cache_file in self._cache_dir.glob("*.pkl"):
                try:
                    cache_file.unlink()
                except Exception as e:
                    self.logger.warning(f"删除缓存文件失败: {e}")
        
        self.logger.info("缓存已清空")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return {
            'memory_cache_size': len(self._memory_cache),
            'file_cache_count': len(list(self._cache_dir.glob("*.pkl"))),
            'memory_cache_enabled': self.config.memory_cache_enabled,
            'file_cache_enabled': self.config.file_cache_enabled
        }


class DataAccessLayer:
    """
    统一数据访问层
    
    【优化说明】
    1. 统一数据访问接口
    2. 多级缓存机制
    3. 完善的异常处理
    4. 数据源自动切换
    """
    
    def __init__(self, cache_config: Optional[DataCacheConfig] = None):
        """
        初始化数据访问层
        
        Args:
            cache_config: 缓存配置
        """
        self.config = get_config()
        self.cache_config = cache_config or DataCacheConfig()
        self.cache_manager = CacheManager(self.cache_config)
        self.data_manager = DataFetcherManager()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 数据源优先级
        self._data_source_priority = ['akshare', 'efinance', 'tushare']
        
        self.logger.info("数据访问层初始化完成")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(DataSourceError),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    def get_data(
        self,
        data_type: DataType,
        stock_code: Optional[str] = None,
        use_cache: bool = True,
        **kwargs
    ) -> DataResponse:
        """
        获取数据（统一入口）
        
        Args:
            data_type: 数据类型
            stock_code: 股票代码
            use_cache: 是否使用缓存
            **kwargs: 其他参数
            
        Returns:
            DataResponse: 数据响应
        """
        request = DataRequest(
            data_type=data_type,
            stock_code=stock_code,
            params=kwargs
        )
        
        cache_key = request.get_cache_key()
        
        # 检查缓存
        if use_cache:
            cached_data = self.cache_manager.get(cache_key)
            if cached_data is not None:
                return DataResponse(
                    data=cached_data,
                    data_type=data_type,
                    stock_code=stock_code,
                    source="cache",
                    from_cache=True
                )
        
        # 获取数据
        try:
            data, source = self._fetch_data(data_type, stock_code, **kwargs)
            
            response = DataResponse(
                data=data,
                data_type=data_type,
                stock_code=stock_code,
                source=source
            )
            
            # 更新缓存
            if use_cache and not response.is_empty():
                self.cache_manager.set(cache_key, data)
            
            return response
            
        except Exception as e:
            self.logger.error(f"获取数据失败: {e}")
            raise DataSourceError(f"获取数据失败: {e}")
    
    def _fetch_data(
        self,
        data_type: DataType,
        stock_code: Optional[str],
        **kwargs
    ) -> Tuple[Any, str]:
        """
        从数据源获取数据
        
        Args:
            data_type: 数据类型
            stock_code: 股票代码
            **kwargs: 其他参数
            
        Returns:
            Tuple[Any, str]: (数据, 数据源)
        """
        if data_type == DataType.STOCK_DAILY:
            days = kwargs.get('days', 30)
            return self.data_manager.get_stock_daily_data(stock_code, days=days)
        
        elif data_type == DataType.STOCK_REALTIME:
            codes = kwargs.get('codes', [stock_code] if stock_code else [])
            return self.data_manager.get_realtime_data(codes)
        
        elif data_type == DataType.SECTOR_RANKING:
            n = kwargs.get('n', 10)
            return self.data_manager.get_sector_rankings(n)
        
        elif data_type == DataType.STOCK_LIST:
            return self.data_manager.get_all_stocks()
        
        elif data_type == DataType.INDEX_DATA:
            index_code = kwargs.get('index_code', '000001')
            days = kwargs.get('days', 30)
            return self.data_manager.get_index_data(index_code, days=days)
        
        else:
            raise DataAccessError(f"不支持的数据类型: {data_type}")
    
    def get_batch_data(
        self,
        data_type: DataType,
        stock_codes: List[str],
        max_workers: int = 5,
        **kwargs
    ) -> Dict[str, DataResponse]:
        """
        批量获取数据
        
        Args:
            data_type: 数据类型
            stock_codes: 股票代码列表
            max_workers: 最大并发数
            **kwargs: 其他参数
            
        Returns:
            Dict[str, DataResponse]: 股票代码到响应的映射
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        results = {}
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_code = {
                executor.submit(self.get_data, data_type, code, True, **kwargs): code
                for code in stock_codes
            }
            
            for future in as_completed(future_to_code):
                code = future_to_code[future]
                try:
                    response = future.result()
                    results[code] = response
                except Exception as e:
                    self.logger.error(f"批量获取 {code} 数据失败: {e}")
                    results[code] = DataResponse(
                        data=None,
                        data_type=data_type,
                        stock_code=code,
                        source="error",
                        metadata={'error': str(e)}
                    )
        
        return results
    
    def validate_stock_code(self, code: str) -> bool:
        """
        验证股票代码格式
        
        Args:
            code: 股票代码
            
        Returns:
            bool: 是否有效
        """
        if not code or not isinstance(code, str):
            return False
        
        code = code.strip()
        
        # 6位数字
        if not code.isdigit() or len(code) != 6:
            return False
        
        # 沪深主板
        if code.startswith(('600', '601', '603', '000')):
            return True
        
        # 创业板、科创板等
        if code.startswith(('300', '301', '688', '689')):
            return True
        
        return False
    
    def filter_main_board_stocks(self, df: pd.DataFrame, code_col: str = '股票代码') -> pd.DataFrame:
        """
        筛选沪深主板股票
        
        Args:
            df: 股票数据DataFrame
            code_col: 股票代码列名
            
        Returns:
            pd.DataFrame: 筛选后的DataFrame
        """
        if df.empty or code_col not in df.columns:
            return df
        
        # 确保代码是字符串
        df[code_col] = df[code_col].astype(str)
        
        # 筛选沪深主板
        mask = df[code_col].str.match(r'^60[013]\d{4}$|^000\d{4}$')
        return df[mask].copy()
    
    def filter_price_range(
        self,
        df: pd.DataFrame,
        price_col: str = '最新价',
        min_price: float = 5.0,
        max_price: float = 35.0
    ) -> pd.DataFrame:
        """
        筛选价格范围
        
        Args:
            df: 股票数据DataFrame
            price_col: 价格列名
            min_price: 最低价格
            max_price: 最高价格
            
        Returns:
            pd.DataFrame: 筛选后的DataFrame
        """
        if df.empty or price_col not in df.columns:
            return df
        
        # 转换价格为数值
        df[price_col] = pd.to_numeric(df[price_col], errors='coerce')
        
        # 筛选价格范围
        mask = (df[price_col] >= min_price) & (df[price_col] <= max_price)
        return df[mask].copy()
    
    def clear_cache(self):
        """清空缓存"""
        self.cache_manager.clear()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        return self.cache_manager.get_stats()


# 单例模式
_data_access_layer_instance: Optional[DataAccessLayer] = None


def get_data_access_layer(cache_config: Optional[DataCacheConfig] = None) -> DataAccessLayer:
    """
    获取数据访问层实例（单例）
    
    Args:
        cache_config: 缓存配置
        
    Returns:
        DataAccessLayer: 数据访问层实例
    """
    global _data_access_layer_instance
    
    if _data_access_layer_instance is None:
        _data_access_layer_instance = DataAccessLayer(cache_config)
    
    return _data_access_layer_instance


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    dal = get_data_access_layer()
    
    # 测试缓存统计
    print("缓存统计:", dal.get_cache_stats())
    
    print("数据访问层测试完成")
