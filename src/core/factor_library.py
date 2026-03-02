# -*- coding: utf-8 -*-
"""
===================================
统一因子库 (Factor Library)
===================================

【优化说明】
1. 整合所有因子计算逻辑，提供统一接口
2. 支持缓存机制，避免重复计算
3. 完善的异常处理和容错机制
4. 优化性能，减少资源浪费

【调用方式】
```python
from src.core.factor_library import FactorLibrary, FactorType

# 创建因子库实例
factor_lib = FactorLibrary()

# 计算单个因子
result = factor_lib.calculate_factor(
    stock_code='600000',
    data=df,
    factor_type=FactorType.VOLUME_PRICE
)

# 批量计算多个因子
results = factor_lib.calculate_factors_batch(
    stock_codes=['600000', '000001'],
    factor_types=[FactorType.VOLUME_PRICE, FactorType.EMOTION]
)
```
"""

import logging
import functools
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Dict, List, Any, Optional, Callable, Union, Tuple
from functools import lru_cache

import pandas as pd
import numpy as np
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import get_config
from data_provider.base import DataFetcherManager

logger = logging.getLogger(__name__)


class FactorType(Enum):
    """因子类型枚举"""
    VOLUME_PRICE = auto()      # 量价因子
    EMOTION = auto()           # 情绪因子
    RISK = auto()              # 风险因子
    LIQUIDITY = auto()         # 流动性因子
    TECHNICAL = auto()         # 技术面因子
    FUNDAMENTAL = auto()       # 基本面因子
    ALL = auto()               # 所有因子


class FactorError(Exception):
    """因子计算异常基类"""
    pass


class FactorDataError(FactorError):
    """因子数据异常"""
    pass


class FactorCalculationError(FactorError):
    """因子计算异常"""
    pass


@dataclass
class FactorResult:
    """因子计算结果"""
    stock_code: str
    factor_type: FactorType
    score: float                    # 因子得分 (0-100)
    raw_value: Any                  # 原始值
    normalized_value: float         # 归一化值 (0-1)
    weight: float = 1.0             # 权重
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """验证结果有效性"""
        if not (0 <= self.score <= 100):
            logger.warning(f"因子得分 {self.score} 超出范围 [0, 100]，将截断")
            self.score = max(0, min(100, self.score))
        
        if not (0 <= self.normalized_value <= 1):
            logger.warning(f"归一化值 {self.normalized_value} 超出范围 [0, 1]，将截断")
            self.normalized_value = max(0, min(1, self.normalized_value))


@dataclass
class FactorConfig:
    """因子配置"""
    # 量价因子阈值
    volume_price_threshold: float = 1.5      # 量比阈值
    turnover_min: float = 3.0                # 最小换手率
    turnover_max: float = 10.0               # 最大换手率
    volume_ma_days: int = 5                  # 成交量均线天数
    
    # 情绪因子阈值
    emotion_lookback_days: int = 30          # 情绪回看天数
    speed_window: int = 5                    # 涨速计算窗口（分钟）
    
    # 风险因子阈值
    stop_loss_pct: float = -3.0              # 止损阈值
    support_ma_days: int = 5                 # 支撑位均线天数
    
    # 流动性因子阈值
    min_amount: float = 50_000_000           # 最小成交额（5000万）
    max_market_cap: float = 10_000_000_000   # 最大流通市值（100亿）
    
    # 价格范围
    price_min: float = 5.0                   # 最低价格
    price_max: float = 35.0                  # 最高价格
    
    # 缓存配置
    cache_enabled: bool = True
    cache_ttl_seconds: int = 3600            # 缓存有效期1小时


class BaseFactorCalculator(ABC):
    """因子计算器基类"""
    
    def __init__(self, config: FactorConfig):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def calculate(self, stock_code: str, data: pd.DataFrame) -> FactorResult:
        """
        计算因子
        
        Args:
            stock_code: 股票代码
            data: 股票数据DataFrame
            
        Returns:
            FactorResult: 因子计算结果
        """
        pass
    
    def validate_data(self, data: pd.DataFrame, required_columns: List[str]) -> bool:
        """
        验证数据完整性
        
        Args:
            data: 数据DataFrame
            required_columns: 必需的列名列表
            
        Returns:
            bool: 数据是否有效
        """
        if data is None or data.empty:
            self.logger.warning("数据为空")
            return False
        
        missing_cols = [col for col in required_columns if col not in data.columns]
        if missing_cols:
            self.logger.warning(f"缺少必需列: {missing_cols}")
            return False
        
        return True
    
    def normalize(self, value: float, min_val: float, max_val: float) -> float:
        """
        归一化值到 [0, 1] 范围
        
        Args:
            value: 原始值
            min_val: 最小值
            max_val: 最大值
            
        Returns:
            float: 归一化值
        """
        if max_val == min_val:
            return 0.5
        return max(0, min(1, (value - min_val) / (max_val - min_val)))
    
    def safe_divide(self, numerator: float, denominator: float, default: float = 0.0) -> float:
        """
        安全除法
        
        Args:
            numerator: 分子
            denominator: 分母
            default: 默认值
            
        Returns:
            float: 除法结果或默认值
        """
        try:
            if denominator == 0 or pd.isna(denominator):
                return default
            return numerator / denominator
        except Exception as e:
            self.logger.debug(f"除法错误: {e}")
            return default


class VolumePriceFactorCalculator(BaseFactorCalculator):
    """量价因子计算器"""
    
    REQUIRED_COLUMNS = ['收盘', '成交量', '成交额', '换手率']
    
    def calculate(self, stock_code: str, data: pd.DataFrame) -> FactorResult:
        """
        计算量价因子
        
        因子包括：
        1. 尾盘成交额异动（对比近5日均值）
        2. 换手率（3%-10%）
        3. 量比（>1.5）
        """
        if not self.validate_data(data, self.REQUIRED_COLUMNS):
            return self._create_empty_result(stock_code, FactorType.VOLUME_PRICE)
        
        try:
            # 获取最新数据
            latest = data.iloc[-1]
            
            # 1. 计算尾盘成交额异动
            if len(data) >= self.config.volume_ma_days:
                recent_volume = data['成交额'].tail(self.config.volume_ma_days).mean()
                prev_volume = data['成交额'].tail(self.config.volume_ma_days * 2).head(self.config.volume_ma_days).mean()
                volume_anomaly = self.safe_divide(recent_volume - prev_volume, prev_volume, 0) * 100
            else:
                volume_anomaly = 0
            
            # 2. 换手率评分
            turnover = latest.get('换手率', 0)
            if self.config.turnover_min <= turnover <= self.config.turnover_max:
                turnover_score = 100 - abs(turnover - 6.5) * 10  # 6.5%为最优
            else:
                turnover_score = max(0, 100 - min(
                    abs(turnover - self.config.turnover_min),
                    abs(turnover - self.config.turnover_max)
                ) * 20)
            
            # 3. 量比评分
            volume_ratio = latest.get('量比', 1.0)
            if volume_ratio >= self.config.volume_price_threshold:
                volume_ratio_score = min(100, 50 + (volume_ratio - 1.5) * 25)
            else:
                volume_ratio_score = max(0, volume_ratio / self.config.volume_price_threshold * 50)
            
            # 综合评分
            total_score = (turnover_score * 0.4 + volume_ratio_score * 0.4 + 
                          min(100, max(0, volume_anomaly * 5 + 50)) * 0.2)
            
            # 归一化
            normalized = self.normalize(total_score, 0, 100)
            
            return FactorResult(
                stock_code=stock_code,
                factor_type=FactorType.VOLUME_PRICE,
                score=total_score,
                raw_value={
                    'turnover': turnover,
                    'volume_ratio': volume_ratio,
                    'volume_anomaly': volume_anomaly
                },
                normalized_value=normalized,
                metadata={
                    'turnover_score': turnover_score,
                    'volume_ratio_score': volume_ratio_score,
                    'volume_anomaly_pct': volume_anomaly
                }
            )
            
        except Exception as e:
            self.logger.error(f"计算量价因子失败: {e}")
            return self._create_empty_result(stock_code, FactorType.VOLUME_PRICE)
    
    def _create_empty_result(self, stock_code: str, factor_type: FactorType) -> FactorResult:
        """创建空结果"""
        return FactorResult(
            stock_code=stock_code,
            factor_type=factor_type,
            score=50,
            raw_value=None,
            normalized_value=0.5,
            metadata={'error': '数据不足'}
        )


class EmotionFactorCalculator(BaseFactorCalculator):
    """情绪因子计算器"""
    
    REQUIRED_COLUMNS = ['收盘', '涨跌幅', '成交量']
    
    def calculate(self, stock_code: str, data: pd.DataFrame) -> FactorResult:
        """
        计算情绪因子
        
        因子包括：
        1. 板块涨跌幅排名
        2. 个股涨速（5分钟）
        3. 近30天涨停次数
        """
        if not self.validate_data(data, self.REQUIRED_COLUMNS):
            return self._create_empty_result(stock_code, FactorType.EMOTION)
        
        try:
            # 1. 计算近期涨跌幅趋势
            if len(data) >= 5:
                recent_changes = data['涨跌幅'].tail(5)
                avg_change = recent_changes.mean()
                change_score = min(100, max(0, 50 + avg_change * 10))
            else:
                change_score = 50
            
            # 2. 计算涨停次数（近30天）
            if len(data) >= self.config.emotion_lookback_days:
                lookback_data = data.tail(self.config.emotion_lookback_days)
                limit_up_count = (lookback_data['涨跌幅'] >= 9.9).sum()
                limit_up_score = min(100, limit_up_count * 20)
            else:
                limit_up_count = 0
                limit_up_score = 0
            
            # 3. 计算动量（近期表现）
            if len(data) >= 10:
                momentum = data['涨跌幅'].tail(5).mean() - data['涨跌幅'].tail(10).head(5).mean()
                momentum_score = min(100, max(0, 50 + momentum * 10))
            else:
                momentum_score = 50
            
            # 综合评分
            total_score = change_score * 0.4 + limit_up_score * 0.3 + momentum_score * 0.3
            normalized = self.normalize(total_score, 0, 100)
            
            return FactorResult(
                stock_code=stock_code,
                factor_type=FactorType.EMOTION,
                score=total_score,
                raw_value={
                    'avg_change_5d': avg_change if len(data) >= 5 else 0,
                    'limit_up_count': limit_up_count,
                    'momentum': momentum if len(data) >= 10 else 0
                },
                normalized_value=normalized,
                metadata={
                    'change_score': change_score,
                    'limit_up_score': limit_up_score,
                    'momentum_score': momentum_score
                }
            )
            
        except Exception as e:
            self.logger.error(f"计算情绪因子失败: {e}")
            return self._create_empty_result(stock_code, FactorType.EMOTION)
    
    def _create_empty_result(self, stock_code: str, factor_type: FactorType) -> FactorResult:
        """创建空结果"""
        return FactorResult(
            stock_code=stock_code,
            factor_type=factor_type,
            score=50,
            raw_value=None,
            normalized_value=0.5,
            metadata={'error': '数据不足'}
        )


class RiskFactorCalculator(BaseFactorCalculator):
    """风险因子计算器"""
    
    REQUIRED_COLUMNS = ['收盘', '最高', '最低', '涨跌幅']
    
    def calculate(self, stock_code: str, data: pd.DataFrame) -> FactorResult:
        """
        计算风险因子
        
        因子包括：
        1. 5日线支撑验证
        2. 止损阈值（买入价-3%）
        3. 波动率控制
        """
        if not self.validate_data(data, self.REQUIRED_COLUMNS):
            return self._create_empty_result(stock_code, FactorType.RISK)
        
        try:
            # 1. 计算5日均线
            if len(data) >= 5:
                ma5 = data['收盘'].tail(5).mean()
                current_price = data['收盘'].iloc[-1]
                support_score = 100 if current_price >= ma5 else max(0, 100 - (ma5 - current_price) / ma5 * 1000)
            else:
                support_score = 50
            
            # 2. 计算波动率
            if len(data) >= 10:
                volatility = data['涨跌幅'].tail(10).std()
                volatility_score = max(0, 100 - volatility * 10)  # 波动率越低越好
            else:
                volatility_score = 50
            
            # 3. 计算近期最大回撤
            if len(data) >= 20:
                recent_high = data['最高'].tail(20).max()
                recent_low = data['最低'].tail(20).min()
                drawdown = self.safe_divide(recent_high - recent_low, recent_high, 0) * 100
                drawdown_score = max(0, 100 - drawdown * 2)
            else:
                drawdown_score = 50
            
            # 综合评分（风险越低，得分越高）
            total_score = support_score * 0.4 + volatility_score * 0.3 + drawdown_score * 0.3
            normalized = self.normalize(total_score, 0, 100)
            
            return FactorResult(
                stock_code=stock_code,
                factor_type=FactorType.RISK,
                score=total_score,
                raw_value={
                    'ma5': ma5 if len(data) >= 5 else 0,
                    'volatility': volatility if len(data) >= 10 else 0,
                    'drawdown': drawdown if len(data) >= 20 else 0
                },
                normalized_value=normalized,
                metadata={
                    'support_score': support_score,
                    'volatility_score': volatility_score,
                    'drawdown_score': drawdown_score
                }
            )
            
        except Exception as e:
            self.logger.error(f"计算风险因子失败: {e}")
            return self._create_empty_result(stock_code, FactorType.RISK)
    
    def _create_empty_result(self, stock_code: str, factor_type: FactorType) -> FactorResult:
        """创建空结果"""
        return FactorResult(
            stock_code=stock_code,
            factor_type=factor_type,
            score=50,
            raw_value=None,
            normalized_value=0.5,
            metadata={'error': '数据不足'}
        )


class LiquidityFactorCalculator(BaseFactorCalculator):
    """流动性因子计算器"""
    
    REQUIRED_COLUMNS = ['成交额', '流通市值']
    
    def calculate(self, stock_code: str, data: pd.DataFrame) -> FactorResult:
        """
        计算流动性因子
        
        因子包括：
        1. 日成交额 > 5000万
        2. 流通市值 < 100亿
        """
        if not self.validate_data(data, self.REQUIRED_COLUMNS):
            return self._create_empty_result(stock_code, FactorType.LIQUIDITY)
        
        try:
            latest = data.iloc[-1]
            
            # 1. 成交额评分
            amount = latest.get('成交额', 0)
            if amount >= self.config.min_amount:
                amount_score = min(100, 50 + (amount - self.config.min_amount) / self.config.min_amount * 25)
            else:
                amount_score = max(0, amount / self.config.min_amount * 50)
            
            # 2. 流通市值评分（越小越好，但不能太小）
            market_cap = latest.get('流通市值', 0)
            if market_cap <= self.config.max_market_cap:
                market_cap_score = min(100, 100 - market_cap / self.config.max_market_cap * 50)
            else:
                market_cap_score = max(0, 100 - (market_cap - self.config.max_market_cap) / self.config.max_market_cap * 50)
            
            # 综合评分
            total_score = amount_score * 0.6 + market_cap_score * 0.4
            normalized = self.normalize(total_score, 0, 100)
            
            return FactorResult(
                stock_code=stock_code,
                factor_type=FactorType.LIQUIDITY,
                score=total_score,
                raw_value={
                    'amount': amount,
                    'market_cap': market_cap
                },
                normalized_value=normalized,
                metadata={
                    'amount_score': amount_score,
                    'market_cap_score': market_cap_score
                }
            )
            
        except Exception as e:
            self.logger.error(f"计算流动性因子失败: {e}")
            return self._create_empty_result(stock_code, FactorType.LIQUIDITY)
    
    def _create_empty_result(self, stock_code: str, factor_type: FactorType) -> FactorResult:
        """创建空结果"""
        return FactorResult(
            stock_code=stock_code,
            factor_type=factor_type,
            score=50,
            raw_value=None,
            normalized_value=0.5,
            metadata={'error': '数据不足'}
        )


class FactorLibrary:
    """
    统一因子库
    
    【优化说明】
    1. 整合所有因子计算逻辑
    2. 支持缓存机制
    3. 完善的异常处理
    4. 批量计算优化
    """
    
    def __init__(self, config: Optional[FactorConfig] = None):
        """
        初始化因子库
        
        Args:
            config: 因子配置，默认使用全局配置
        """
        self.config = config or FactorConfig()
        self.data_manager = DataFetcherManager()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 初始化因子计算器
        self._calculators: Dict[FactorType, BaseFactorCalculator] = {
            FactorType.VOLUME_PRICE: VolumePriceFactorCalculator(self.config),
            FactorType.EMOTION: EmotionFactorCalculator(self.config),
            FactorType.RISK: RiskFactorCalculator(self.config),
            FactorType.LIQUIDITY: LiquidityFactorCalculator(self.config),
        }
        
        # 缓存
        self._cache: Dict[str, Tuple[FactorResult, datetime]] = {}
        
        self.logger.info("因子库初始化完成")
    
    def calculate_factor(
        self,
        stock_code: str,
        data: pd.DataFrame,
        factor_type: FactorType,
        use_cache: bool = True
    ) -> FactorResult:
        """
        计算单个因子
        
        Args:
            stock_code: 股票代码
            data: 股票数据
            factor_type: 因子类型
            use_cache: 是否使用缓存
            
        Returns:
            FactorResult: 因子计算结果
        """
        cache_key = f"{stock_code}_{factor_type.name}_{datetime.now().strftime('%Y%m%d')}"
        
        # 检查缓存
        if use_cache and self.config.cache_enabled and cache_key in self._cache:
            result, timestamp = self._cache[cache_key]
            if (datetime.now() - timestamp).seconds < self.config.cache_ttl_seconds:
                self.logger.debug(f"使用缓存: {cache_key}")
                return result
        
        # 计算因子
        calculator = self._calculators.get(factor_type)
        if calculator is None:
            self.logger.error(f"未知的因子类型: {factor_type}")
            return FactorResult(
                stock_code=stock_code,
                factor_type=factor_type,
                score=50,
                raw_value=None,
                normalized_value=0.5,
                metadata={'error': '未知的因子类型'}
            )
        
        result = calculator.calculate(stock_code, data)
        
        # 更新缓存
        if use_cache and self.config.cache_enabled:
            self._cache[cache_key] = (result, datetime.now())
        
        return result
    
    def calculate_factors_batch(
        self,
        stock_codes: List[str],
        factor_types: List[FactorType],
        days: int = 30
    ) -> Dict[str, Dict[FactorType, FactorResult]]:
        """
        批量计算因子
        
        Args:
            stock_codes: 股票代码列表
            factor_types: 因子类型列表
            days: 数据天数
            
        Returns:
            Dict: {stock_code: {factor_type: FactorResult}}
        """
        results = {}
        
        for stock_code in stock_codes:
            results[stock_code] = {}
            
            # 获取数据
            try:
                data, _ = self.data_manager.get_stock_daily_data(stock_code, days=days)
                if data.empty:
                    self.logger.warning(f"股票 {stock_code} 数据为空")
                    continue
            except Exception as e:
                self.logger.error(f"获取股票 {stock_code} 数据失败: {e}")
                continue
            
            # 计算因子
            for factor_type in factor_types:
                try:
                    result = self.calculate_factor(stock_code, data, factor_type)
                    results[stock_code][factor_type] = result
                except Exception as e:
                    self.logger.error(f"计算 {stock_code} 的 {factor_type.name} 因子失败: {e}")
                    results[stock_code][factor_type] = FactorResult(
                        stock_code=stock_code,
                        factor_type=factor_type,
                        score=50,
                        raw_value=None,
                        normalized_value=0.5,
                        metadata={'error': str(e)}
                    )
        
        return results
    
    def calculate_composite_score(
        self,
        factor_results: Dict[FactorType, FactorResult],
        weights: Optional[Dict[FactorType, float]] = None
    ) -> float:
        """
        计算综合得分
        
        Args:
            factor_results: 因子结果字典
            weights: 权重字典，默认等权重
            
        Returns:
            float: 综合得分 (0-100)
        """
        if not factor_results:
            return 50.0
        
        if weights is None:
            weights = {ft: 1.0 for ft in factor_results.keys()}
        
        total_score = 0.0
        total_weight = 0.0
        
        for factor_type, result in factor_results.items():
            weight = weights.get(factor_type, 1.0)
            total_score += result.score * weight
            total_weight += weight
        
        if total_weight == 0:
            return 50.0
        
        return total_score / total_weight
    
    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()
        self.logger.info("因子缓存已清空")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return {
            'cache_size': len(self._cache),
            'cache_enabled': self.config.cache_enabled,
            'cache_ttl_seconds': self.config.cache_ttl_seconds
        }


# 单例模式
_factor_library_instance: Optional[FactorLibrary] = None


def get_factor_library(config: Optional[FactorConfig] = None) -> FactorLibrary:
    """
    获取因子库实例（单例）
    
    Args:
        config: 因子配置
        
    Returns:
        FactorLibrary: 因子库实例
    """
    global _factor_library_instance
    
    if _factor_library_instance is None:
        _factor_library_instance = FactorLibrary(config)
    
    return _factor_library_instance


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    factor_lib = get_factor_library()
    
    # 测试获取缓存统计
    print("缓存统计:", factor_lib.get_cache_stats())
    
    print("因子库测试完成")
