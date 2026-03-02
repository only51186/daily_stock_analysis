# -*- coding: utf-8 -*-
"""
===================================
数据缓存模块
===================================

功能：
1. 把每日获取的板块 / 个股数据保存到本地 CSV
2. 避免重复请求，提升脚本运行速度
3. 每日新增数据优先下载，下载后立马保存为共用的数据库
4. 供后面每个功能重复使用数据
"""

import os
import json
import logging
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)


class DataCache:
    """
    数据缓存类
    
    管理每日数据的本地缓存，避免重复请求
    """
    
    def __init__(self, cache_dir: str = None):
        """
        初始化数据缓存
        
        Args:
            cache_dir: 缓存目录路径，默认为项目根目录下的 data_cache 文件夹
        """
        if cache_dir is None:
            # 获取项目根目录
            project_root = Path(__file__).parent.parent
            self.cache_dir = project_root / "data_cache"
        else:
            self.cache_dir = Path(cache_dir)
        
        # 创建缓存目录
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建子目录
        self.sector_dir = self.cache_dir / "sectors"
        self.stock_dir = self.cache_dir / "stocks"
        self.historical_dir = self.cache_dir / "historical"
        
        self.sector_dir.mkdir(exist_ok=True)
        self.stock_dir.mkdir(exist_ok=True)
        self.historical_dir.mkdir(exist_ok=True)
        
        # 缓存元数据文件
        self.metadata_file = self.cache_dir / "cache_metadata.json"
        self.metadata = self._load_metadata()
        
        logger.info(f"数据缓存模块初始化完成，缓存目录: {self.cache_dir}")
    
    def _load_metadata(self) -> Dict[str, Any]:
        """
        加载缓存元数据
        
        Returns:
            元数据字典
        """
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"加载缓存元数据失败: {e}")
        
        return {
            'last_update': {},
            'data_sources': {},
            'version': '1.0'
        }
    
    def _save_metadata(self):
        """
        保存缓存元数据
        """
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存缓存元数据失败: {e}")
    
    def _get_today_str(self) -> str:
        """
        获取今日日期字符串
        
        Returns:
            日期字符串，格式：YYYY-MM-DD
        """
        return datetime.now().strftime('%Y-%m-%d')
    
    def _is_cache_valid(self, cache_key: str, max_age_hours: int = 24) -> bool:
        """
        检查缓存是否有效
        
        Args:
            cache_key: 缓存键
            max_age_hours: 最大缓存时间（小时）
            
        Returns:
            缓存是否有效
        """
        if cache_key not in self.metadata['last_update']:
            return False
        
        last_update = datetime.fromisoformat(self.metadata['last_update'][cache_key])
        age = datetime.now() - last_update
        
        return age < timedelta(hours=max_age_hours)
    
    def save_sector_data(self, data: pd.DataFrame, date: str = None) -> str:
        """
        保存板块数据到缓存
        
        Args:
            data: 板块数据DataFrame
            date: 日期字符串，默认为今日
            
        Returns:
            缓存文件路径
        """
        if date is None:
            date = self._get_today_str()
        
        cache_file = self.sector_dir / f"sectors_{date}.csv"
        
        try:
            data.to_csv(cache_file, index=False, encoding='utf-8-sig')
            
            # 更新元数据
            cache_key = f"sectors_{date}"
            self.metadata['last_update'][cache_key] = datetime.now().isoformat()
            self.metadata['data_sources'][cache_key] = 'local_cache'
            self._save_metadata()
            
            logger.info(f"板块数据已保存到缓存: {cache_file}")
            return str(cache_file)
        except Exception as e:
            logger.error(f"保存板块数据到缓存失败: {e}")
            return None
    
    def load_sector_data(self, date: str = None, max_age_hours: int = 24) -> Optional[pd.DataFrame]:
        """
        从缓存加载板块数据
        
        Args:
            date: 日期字符串，默认为今日
            max_age_hours: 最大缓存时间（小时）
            
        Returns:
            板块数据DataFrame，如果缓存无效则返回None
        """
        if date is None:
            date = self._get_today_str()
        
        cache_key = f"sectors_{date}"
        cache_file = self.sector_dir / f"sectors_{date}.csv"
        
        # 检查缓存是否有效
        if not self._is_cache_valid(cache_key, max_age_hours):
            logger.info(f"板块数据缓存无效或已过期: {cache_file}")
            return None
        
        if not cache_file.exists():
            logger.info(f"板块数据缓存文件不存在: {cache_file}")
            return None
        
        try:
            df = pd.read_csv(cache_file, encoding='utf-8-sig')
            logger.info(f"从缓存加载板块数据成功: {len(df)} 条记录")
            return df
        except Exception as e:
            logger.error(f"从缓存加载板块数据失败: {e}")
            return None
    
    def save_stock_data(self, data: pd.DataFrame, date: str = None) -> str:
        """
        保存个股数据到缓存
        
        Args:
            data: 个股数据DataFrame
            date: 日期字符串，默认为今日
            
        Returns:
            缓存文件路径
        """
        if date is None:
            date = self._get_today_str()
        
        cache_file = self.stock_dir / f"stocks_{date}.csv"
        
        try:
            data.to_csv(cache_file, index=False, encoding='utf-8-sig')
            
            # 更新元数据
            cache_key = f"stocks_{date}"
            self.metadata['last_update'][cache_key] = datetime.now().isoformat()
            self.metadata['data_sources'][cache_key] = 'local_cache'
            self._save_metadata()
            
            logger.info(f"个股数据已保存到缓存: {cache_file}")
            return str(cache_file)
        except Exception as e:
            logger.error(f"保存个股数据到缓存失败: {e}")
            return None
    
    def load_stock_data(self, date: str = None, max_age_hours: int = 24) -> Optional[pd.DataFrame]:
        """
        从缓存加载个股数据
        
        Args:
            date: 日期字符串，默认为今日
            max_age_hours: 最大缓存时间（小时）
            
        Returns:
            个股数据DataFrame，如果缓存无效则返回None
        """
        if date is None:
            date = self._get_today_str()
        
        cache_key = f"stocks_{date}"
        cache_file = self.stock_dir / f"stocks_{date}.csv"
        
        # 检查缓存是否有效
        if not self._is_cache_valid(cache_key, max_age_hours):
            logger.info(f"个股数据缓存无效或已过期: {cache_file}")
            return None
        
        if not cache_file.exists():
            logger.info(f"个股数据缓存文件不存在: {cache_file}")
            return None
        
        try:
            df = pd.read_csv(cache_file, encoding='utf-8-sig')
            logger.info(f"从缓存加载个股数据成功: {len(df)} 条记录")
            return df
        except Exception as e:
            logger.error(f"从缓存加载个股数据失败: {e}")
            return None
    
    def save_historical_data(self, code: str, data: pd.DataFrame) -> str:
        """
        保存个股历史数据到缓存
        
        Args:
            code: 股票代码
            data: 历史数据DataFrame
            
        Returns:
            缓存文件路径
        """
        cache_file = self.historical_dir / f"{code}_historical.csv"
        
        try:
            data.to_csv(cache_file, index=False, encoding='utf-8-sig')
            
            # 更新元数据
            cache_key = f"historical_{code}"
            self.metadata['last_update'][cache_key] = datetime.now().isoformat()
            self.metadata['data_sources'][cache_key] = 'local_cache'
            self._save_metadata()
            
            logger.info(f"股票 {code} 历史数据已保存到缓存: {cache_file}")
            return str(cache_file)
        except Exception as e:
            logger.error(f"保存股票 {code} 历史数据到缓存失败: {e}")
            return None
    
    def load_historical_data(self, code: str, max_age_hours: int = 24) -> Optional[pd.DataFrame]:
        """
        从缓存加载个股历史数据
        
        Args:
            code: 股票代码
            max_age_hours: 最大缓存时间（小时）
            
        Returns:
            历史数据DataFrame，如果缓存无效则返回None
        """
        cache_key = f"historical_{code}"
        cache_file = self.historical_dir / f"{code}_historical.csv"
        
        # 检查缓存是否有效
        if not self._is_cache_valid(cache_key, max_age_hours):
            logger.info(f"股票 {code} 历史数据缓存无效或已过期")
            return None
        
        if not cache_file.exists():
            logger.info(f"股票 {code} 历史数据缓存文件不存在")
            return None
        
        try:
            df = pd.read_csv(cache_file, encoding='utf-8-sig')
            logger.info(f"从缓存加载股票 {code} 历史数据成功: {len(df)} 条记录")
            return df
        except Exception as e:
            logger.error(f"从缓存加载股票 {code} 历史数据失败: {e}")
            return None
    
    def clear_expired_cache(self, max_age_days: int = 7):
        """
        清理过期缓存
        
        Args:
            max_age_days: 最大缓存天数
        """
        expired_time = datetime.now() - timedelta(days=max_age_days)
        
        # 清理板块数据缓存
        for cache_file in self.sector_dir.glob("sectors_*.csv"):
            try:
                file_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
                if file_time < expired_time:
                    cache_file.unlink()
                    logger.info(f"删除过期板块缓存: {cache_file}")
            except Exception as e:
                logger.warning(f"删除过期缓存失败: {cache_file}, {e}")
        
        # 清理个股数据缓存
        for cache_file in self.stock_dir.glob("stocks_*.csv"):
            try:
                file_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
                if file_time < expired_time:
                    cache_file.unlink()
                    logger.info(f"删除过期个股缓存: {cache_file}")
            except Exception as e:
                logger.warning(f"删除过期缓存失败: {cache_file}, {e}")
        
        logger.info("过期缓存清理完成")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            统计信息字典
        """
        stats = {
            'total_cache_files': 0,
            'sector_files': 0,
            'stock_files': 0,
            'historical_files': 0,
            'total_size_mb': 0
        }
        
        # 统计板块数据
        for cache_file in self.sector_dir.glob("*.csv"):
            stats['sector_files'] += 1
            stats['total_cache_files'] += 1
            stats['total_size_mb'] += cache_file.stat().st_size / (1024 * 1024)
        
        # 统计个股数据
        for cache_file in self.stock_dir.glob("*.csv"):
            stats['stock_files'] += 1
            stats['total_cache_files'] += 1
            stats['total_size_mb'] += cache_file.stat().st_size / (1024 * 1024)
        
        # 统计历史数据
        for cache_file in self.historical_dir.glob("*.csv"):
            stats['historical_files'] += 1
            stats['total_cache_files'] += 1
            stats['total_size_mb'] += cache_file.stat().st_size / (1024 * 1024)
        
        stats['total_size_mb'] = round(stats['total_size_mb'], 2)
        
        return stats


# 单例模式
_data_cache = None


def get_data_cache(cache_dir: str = None) -> DataCache:
    """
    获取数据缓存实例（单例）
    
    Args:
        cache_dir: 缓存目录路径
        
    Returns:
        DataCache实例
    """
    global _data_cache
    if _data_cache is None:
        _data_cache = DataCache(cache_dir)
    return _data_cache


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    cache = get_data_cache()
    
    # 测试保存和加载板块数据
    print("\n测试板块数据缓存:")
    test_sectors = pd.DataFrame({
        'name': ['半导体', '新能源', '医药'],
        'change_pct': [5.2, 3.8, 2.1]
    })
    cache.save_sector_data(test_sectors)
    loaded_sectors = cache.load_sector_data()
    if loaded_sectors is not None:
        print(f"成功加载板块数据: {len(loaded_sectors)} 条")
        print(loaded_sectors)
    
    # 测试保存和加载个股数据
    print("\n测试个股数据缓存:")
    test_stocks = pd.DataFrame({
        'code': ['600000', '600519', '000001'],
        'name': ['浦发银行', '贵州茅台', '平安银行'],
        'price': [10.5, 1500.0, 12.3]
    })
    cache.save_stock_data(test_stocks)
    loaded_stocks = cache.load_stock_data()
    if loaded_stocks is not None:
        print(f"成功加载个股数据: {len(loaded_stocks)} 条")
        print(loaded_stocks)
    
    # 测试缓存统计
    print("\n缓存统计:")
    stats = cache.get_cache_stats()
    print(stats)
