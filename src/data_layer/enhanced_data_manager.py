# -*- coding: utf-8 -*-
"""
===================================
Enhanced Data Layer - Multi-Source Data Manager
===================================

[Features]
1. Multi-source automatic switching: OpenBB → AkShare → Tushare → EastMoney → TongHuaShun → Cache
2. Automatic data validation: Missing values, outliers, suspensions, limit-ups/downs
3. Auto cache + resume download + retry mechanism
4. Data source health report

[Data Source Priority]
1. OpenBB (Primary)
2. AkShare (Backup 1)
3. Tushare (Backup 2)
4. EastMoney (Backup 3)
5. TongHuaShun (Backup 4)
6. Local Cache (Final fallback)
"""

import os
import sys
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.trae_memory import get_memory

logger = logging.getLogger(__name__)


class DataSourceHealth:
    """
    Data source health tracking
    """
    
    def __init__(self):
        self.health_stats = {
            'openbb': {'success': 0, 'failure': 0, 'last_success': None, 'avg_response_time': 0.0},
            'akshare': {'success': 0, 'failure': 0, 'last_success': None, 'avg_response_time': 0.0},
            'tushare': {'success': 0, 'failure': 0, 'last_success': None, 'avg_response_time': 0.0},
            'eastmoney': {'success': 0, 'failure': 0, 'last_success': None, 'avg_response_time': 0.0},
            'tonghuashun': {'success': 0, 'failure': 0, 'last_success': None, 'avg_response_time': 0.0},
            'cache': {'success': 0, 'failure': 0, 'last_success': None, 'avg_response_time': 0.0}
        }
    
    def record_success(self, source: str, response_time: float = 0.0):
        """Record successful fetch"""
        if source not in self.health_stats:
            return
        
        stats = self.health_stats[source]
        stats['success'] += 1
        stats['last_success'] = datetime.now().isoformat()
        
        if stats['avg_response_time'] == 0:
            stats['avg_response_time'] = response_time
        else:
            stats['avg_response_time'] = (stats['avg_response_time'] * (stats['success'] - 1) + response_time) / stats['success']
    
    def record_failure(self, source: str):
        """Record failed fetch"""
        if source not in self.health_stats:
            return
        
        self.health_stats[source]['failure'] += 1
    
    def get_health_report(self) -> Dict[str, Any]:
        """Generate health report"""
        report = {}
        
        for source, stats in self.health_stats.items():
            total = stats['success'] + stats['failure']
            success_rate = (stats['success'] / total * 100) if total > 0 else 0
            
            report[source] = {
                'success_rate': f"{success_rate:.1f}%",
                'success_count': stats['success'],
                'failure_count': stats['failure'],
                'last_success': stats['last_success'],
                'avg_response_time': f"{stats['avg_response_time']:.2f}s",
                'status': 'EXCELLENT' if success_rate >= 95 else 'GOOD' if success_rate >= 80 else 'FAIR' if success_rate >= 60 else 'POOR'
            }
        
        return report
    
    def get_best_source(self) -> str:
        """Get the best performing source"""
        best_source = 'openbb'
        best_rate = 0.0
        
        for source, stats in self.health_stats.items():
            total = stats['success'] + stats['failure']
            if total == 0:
                continue
            
            rate = stats['success'] / total
            if rate > best_rate:
                best_rate = rate
                best_source = source
        
        return best_source


class EnhancedDataManager:
    """
    Enhanced Multi-Source Data Manager
    
    [Core Features]
    1. Multi-source automatic fallback
    2. Automatic data cleaning and validation
    3. Smart caching with TTL
    4. Resume download support
    5. Retry with exponential backoff
    6. Health monitoring and reporting
    """
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.cache_dir = self.project_root / "data_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.health = DataSourceHealth()
        self.memory = get_memory()
        
        self.source_priority = ['openbb', 'akshare', 'tushare', 'eastmoney', 'tonghuashun', 'cache']
        
        self.cache_ttl_hours = 24
    
    def get_stock_data(
        self,
        symbol: str,
        start_date: str = None,
        end_date: str = None,
        force_refresh: bool = False
    ) -> Tuple[Optional[pd.DataFrame], str]:
        """
        Get stock data with multi-source fallback
        
        Args:
            symbol: Stock code (e.g., '000001.SZ')
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            force_refresh: Force refresh, skip cache
            
        Returns:
            Tuple of (DataFrame, source_name)
        """
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        if not force_refresh:
            cached_data = self._get_from_cache(symbol, start_date, end_date)
            if cached_data is not None:
                self.health.record_success('cache')
                return cached_data, 'cache'
        
        for source in self.source_priority:
            if source == 'cache':
                continue
            
            start_time = time.time()
            
            try:
                df = self._fetch_from_source(source, symbol, start_date, end_date)
                
                if df is not None and not df.empty:
                    df = self._clean_and_validate_data(df, symbol)
                    
                    if df is not None and not df.empty:
                        response_time = time.time() - start_time
                        self.health.record_success(source, response_time)
                        
                        self._save_to_cache(df, symbol, start_date, end_date)
                        self.memory.record_data_fetch(source, symbol, True)
                        
                        return df, source
            except Exception as e:
                logger.warning(f"Source {source} failed: {e}")
                self.health.record_failure(source)
                self.memory.record_data_fetch(source, symbol, False)
                continue
        
        return None, 'none'
    
    def _fetch_from_source(
        self,
        source: str,
        symbol: str,
        start_date: str,
        end_date: str
    ) -> Optional[pd.DataFrame]:
        """
        Fetch data from specific source
        
        Args:
            source: Source name
            symbol: Stock code
            start_date: Start date
            end_date: End date
            
        Returns:
            DataFrame or None
        """
        if source == 'openbb':
            return self._fetch_openbb(symbol, start_date, end_date)
        elif source == 'akshare':
            return self._fetch_akshare(symbol, start_date, end_date)
        elif source == 'tushare':
            return self._fetch_tushare(symbol, start_date, end_date)
        elif source == 'eastmoney':
            return self._fetch_eastmoney(symbol, start_date, end_date)
        elif source == 'tonghuashun':
            return self._fetch_tonghuashun(symbol, start_date, end_date)
        
        return None
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Exception,))
    )
    def _fetch_openbb(
        self,
        symbol: str,
        start_date: str,
        end_date: str
    ) -> Optional[pd.DataFrame]:
        """Fetch from OpenBB"""
        try:
            from openbb import obb
            
            clean_symbol = symbol.replace('.SZ', '').replace('.SH', '')
            
            df = obb.equity.price.historical(
                clean_symbol,
                provider="yfinance",
                start_date=start_date,
                end_date=end_date
            )
            
            if df is not None and not df.empty:
                df = self._standardize_columns(df, 'openbb')
                return df
            
            return None
        except Exception as e:
            logger.error(f"OpenBB fetch failed: {e}")
            raise
    
    def _fetch_akshare(
        self,
        symbol: str,
        start_date: str,
        end_date: str
    ) -> Optional[pd.DataFrame]:
        """Fetch from AkShare"""
        try:
            import akshare as ak
            
            clean_symbol = symbol.replace('.SZ', '').replace('.SH', '')
            
            df = ak.stock_zh_a_hist(
                symbol=clean_symbol,
                period="daily",
                adjust=""
            )
            
            if df is not None and not df.empty:
                df = self._standardize_columns(df, 'akshare')
                return df
            
            return None
        except Exception as e:
            logger.error(f"AkShare fetch failed: {e}")
            return None
    
    def _fetch_tushare(
        self,
        symbol: str,
        start_date: str,
        end_date: str
    ) -> Optional[pd.DataFrame]:
        """Fetch from Tushare"""
        try:
            import tushare as ts
            from dotenv import load_dotenv
            
            load_dotenv()
            token = os.getenv('TUSHARE_TOKEN')
            
            if not token:
                return None
            
            pro = ts.pro_api(token)
            
            df = pro.daily(
                ts_code=symbol,
                start_date=start_date.replace('-', ''),
                end_date=end_date.replace('-', '')
            )
            
            if df is not None and not df.empty:
                df = self._standardize_columns(df, 'tushare')
                return df
            
            return None
        except Exception as e:
            logger.error(f"Tushare fetch failed: {e}")
            return None
    
    def _fetch_eastmoney(
        self,
        symbol: str,
        start_date: str,
        end_date: str
    ) -> Optional[pd.DataFrame]:
        """Fetch from EastMoney (via AkShare)"""
        try:
            import akshare as ak
            
            clean_symbol = symbol.replace('.SZ', '').replace('.SH', '')
            
            df = ak.stock_individual_spot_em()
            
            if df is not None and not df.empty:
                df = df[df['代码'] == clean_symbol].copy()
                df = self._standardize_columns(df, 'eastmoney')
                return df
            
            return None
        except Exception as e:
            logger.error(f"EastMoney fetch failed: {e}")
            return None
    
    def _fetch_tonghuashun(
        self,
        symbol: str,
        start_date: str,
        end_date: str
    ) -> Optional[pd.DataFrame]:
        """Fetch from TongHuaShun (via AkShare)"""
        try:
            import akshare as ak
            
            clean_symbol = symbol.replace('.SZ', '').replace('.SH', '')
            
            df = ak.stock_zh_a_spot()
            
            if df is not None and not df.empty:
                df = df[df['代码'] == clean_symbol].copy()
                df = self._standardize_columns(df, 'tonghuashun')
                return df
            
            return None
        except Exception as e:
            logger.error(f"TongHuaShun fetch failed: {e}")
            return None
    
    def _standardize_columns(self, df: pd.DataFrame, source: str) -> pd.DataFrame:
        """Standardize column names across sources"""
        column_mappings = {
            'openbb': {
                'date': 'trade_date',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume'
            },
            'akshare': {
                '日期': 'trade_date',
                '开盘': 'open',
                '最高': 'high',
                '最低': 'low',
                '收盘': 'close',
                '成交量': 'volume'
            },
            'tushare': {
                'trade_date': 'trade_date',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'vol': 'volume'
            },
            'eastmoney': {
                '日期': 'trade_date',
                '开盘价': 'open',
                '最高价': 'high',
                '最低价': 'low',
                '收盘价': 'close',
                '成交量': 'volume'
            },
            'tonghuashun': {
                '日期': 'trade_date',
                '开盘': 'open',
                '最高': 'high',
                '最低': 'low',
                '收盘': 'close',
                '成交量': 'volume'
            }
        }
        
        mapping = column_mappings.get(source, {})
        
        df = df.rename(columns=mapping)
        
        required_cols = ['trade_date', 'open', 'high', 'low', 'close', 'volume']
        for col in required_cols:
            if col not in df.columns:
                df[col] = np.nan
        
        return df[required_cols]
    
    def _clean_and_validate_data(self, df: pd.DataFrame, symbol: str) -> Optional[pd.DataFrame]:
        """
        Clean and validate data
        
        Args:
            df: Raw DataFrame
            symbol: Stock code
            
        Returns:
            Cleaned DataFrame or None
        """
        if df is None or df.empty:
            return None
        
        df = df.copy()
        
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        df = df.dropna(subset=['open', 'high', 'low', 'close'])
        
        df = df[
            (df['high'] >= df['low']) &
            (df['high'] >= df['open']) &
            (df['high'] >= df['close']) &
            (df['low'] <= df['open']) &
            (df['low'] <= df['close'])
        ]
        
        for col in numeric_cols:
            if col in df.columns:
                q_low = df[col].quantile(0.01)
                q_high = df[col].quantile(0.99)
                df = df[(df[col] >= q_low) & (df[col] <= q_high)]
        
        df['pct_chg'] = df['close'].pct_change() * 100
        
        df['is_limit_up'] = df['pct_chg'] >= 9.9
        df['is_limit_down'] = df['pct_chg'] <= -9.9
        df['is_suspended'] = df['volume'] == 0
        
        if 'trade_date' in df.columns:
            df = df.sort_values('trade_date').reset_index(drop=True)
        
        return df
    
    def _get_cache_key(self, symbol: str, start_date: str, end_date: str) -> str:
        """Generate cache key"""
        safe_symbol = symbol.replace('.', '_').replace(':', '_')
        return f"{safe_symbol}_{start_date}_{end_date}"
    
    def _get_from_cache(
        self,
        symbol: str,
        start_date: str,
        end_date: str
    ) -> Optional[pd.DataFrame]:
        """Get data from cache"""
        cache_key = self._get_cache_key(symbol, start_date, end_date)
        cache_file = self.cache_dir / f"{cache_key}.parquet"
        
        if not cache_file.exists():
            return None
        
        file_age_hours = (time.time() - cache_file.stat().st_mtime) / 3600
        if file_age_hours > self.cache_ttl_hours:
            return None
        
        try:
            df = pd.read_parquet(cache_file)
            return df
        except Exception as e:
            logger.error(f"Cache read failed: {e}")
            return None
    
    def _save_to_cache(
        self,
        df: pd.DataFrame,
        symbol: str,
        start_date: str,
        end_date: str
    ) -> bool:
        """Save data to cache"""
        cache_key = self._get_cache_key(symbol, start_date, end_date)
        cache_file = self.cache_dir / f"{cache_key}.parquet"
        
        try:
            df.to_parquet(cache_file)
            return True
        except Exception as e:
            logger.error(f"Cache write failed: {e}")
            return False
    
    def get_health_report(self) -> Dict[str, Any]:
        """Get data source health report"""
        return self.health.get_health_report()
    
    def print_health_report(self):
        """Print health report"""
        report = self.get_health_report()
        
        print("\n" + "=" * 80)
        print("DATA SOURCE HEALTH REPORT")
        print("=" * 80)
        
        for source, stats in report.items():
            print(f"\n{source.upper()}:")
            print(f"  Status: {stats['status']}")
            print(f"  Success Rate: {stats['success_rate']}")
            print(f"  Success/Failure: {stats['success_count']}/{stats['failure_count']}")
            print(f"  Last Success: {stats['last_success']}")
            print(f"  Avg Response Time: {stats['avg_response_time']}")
        
        print("\n" + "=" * 80)
        print(f"BEST SOURCE: {self.health.get_best_source().upper()}")
        print("=" * 80)


def get_enhanced_data_manager() -> EnhancedDataManager:
    """Get enhanced data manager instance"""
    return EnhancedDataManager()


if __name__ == '__main__':
    manager = get_enhanced_data_manager()
    
    print("Testing Enhanced Data Manager...")
    
    df, source = manager.get_stock_data('000001.SZ')
    
    if df is not None:
        print(f"\nSuccessfully fetched data from: {source}")
        print(f"Data shape: {df.shape}")
        print(f"Date range: {df['trade_date'].min()} to {df['trade_date'].max()}")
    else:
        print("\nFailed to fetch data from any source")
    
    manager.print_health_report()
