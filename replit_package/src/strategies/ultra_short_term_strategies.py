# -*- coding: utf-8 -*-
"""
===================================
Ultra-Short-Term Strategies (5 Master Strategies)
===================================

[Strategies]
1. Volume Breakout Strategy
2. Strong Pullback Buy Strategy
3. First Board Weak-to-Strong Strategy
4. MA Trend Strategy
5. MACD/KDJ Resonance Strategy

[Trading Wisdom Quantified]
- Cut losses short, let profits run
- Trade with the trend
- Only trade high certainty setups
- Don't chase highs, don't catch falling knives
- Strict stop loss
"""

import pandas as pd
import numpy as np
from typing import Dict, Any
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.backtest_layer.enhanced_backtester import (
    UltraShortTermStrategy,
    get_enhanced_backtester,
    BacktestResult
)

logger = logging.getLogger(__name__)


class VolumeBreakoutStrategy(UltraShortTermStrategy):
    """
    Strategy 1: Volume Breakout Strategy
    
    [Rules]
    - Buy: Price breaks resistance with >2x volume
    - Sell: Take profit 8-10%, Stop loss 3-5% or max 5 days
    """
    
    def __init__(
        self,
        lookback: int = 20,
        volume_threshold: float = 2.0,
        max_holding_days: int = 5,
        stop_loss_pct: float = -0.05,
        take_profit_pct: float = 0.10
    ):
        super().__init__(
            name="VolumeBreakout",
            max_holding_days=max_holding_days,
            stop_loss_pct=stop_loss_pct,
            take_profit_pct=take_profit_pct
        )
        self.lookback = lookback
        self.volume_threshold = volume_threshold
    
    def should_buy(self, df: pd.DataFrame, idx: int) -> bool:
        if idx < self.lookback + 5:
            return False
        
        high = df['high'].iloc[idx - self.lookback:idx].max()
        current_high = df['high'].iloc[idx]
        current_close = df['close'].iloc[idx]
        
        volume = df['volume'].iloc[idx]
        avg_volume = df['volume'].iloc[idx - 20:idx].mean()
        
        breakout = current_close > high * 0.99
        volume_spike = volume > avg_volume * self.volume_threshold
        
        return breakout and volume_spike
    
    def should_sell(self, df: pd.DataFrame, idx: int, entry_idx: int) -> bool:
        return False


class StrongPullbackStrategy(UltraShortTermStrategy):
    """
    Strategy 2: Strong Pullback Buy Strategy
    
    [Rules]
    - Buy: Strong stock pulls back to MA5/MA10/MA20
    - Sell: Take profit 8-10%, Stop loss 3-5% or max 5 days
    """
    
    def __init__(
        self,
        ma_period: int = 10,
        pullback_threshold: float = 0.98,
        max_holding_days: int = 5,
        stop_loss_pct: float = -0.05,
        take_profit_pct: float = 0.10
    ):
        super().__init__(
            name="StrongPullback",
            max_holding_days=max_holding_days,
            stop_loss_pct=stop_loss_pct,
            take_profit_pct=take_profit_pct
        )
        self.ma_period = ma_period
        self.pullback_threshold = pullback_threshold
    
    def should_buy(self, df: pd.DataFrame, idx: int) -> bool:
        if idx < 30:
            return False
        
        ma = df['close'].rolling(self.ma_period).mean().iloc[idx]
        current_close = df['close'].iloc[idx]
        current_low = df['low'].iloc[idx]
        
        ma20_prev = df['close'].rolling(20).mean().iloc[idx - 5]
        ma20_curr = df['close'].rolling(20).mean().iloc[idx]
        uptrend = ma20_curr > ma20_prev
        
        touches_ma = current_low <= ma * 1.01 and current_close >= ma * 0.99
        
        return uptrend and touches_ma
    
    def should_sell(self, df: pd.DataFrame, idx: int, entry_idx: int) -> bool:
        return False


class FirstBoardWeakToStrongStrategy(UltraShortTermStrategy):
    """
    Strategy 3: First Board Weak-to-Strong Strategy
    
    [Rules]
    - Buy: First limit-up board, then weak-to-strong next day
    - Sell: Take profit 10-15%, Stop loss 3-5% or max 5 days
    """
    
    def __init__(
        self,
        max_holding_days: int = 5,
        stop_loss_pct: float = -0.05,
        take_profit_pct: float = 0.15
    ):
        super().__init__(
            name="FirstBoardWeakToStrong",
            max_holding_days=max_holding_days,
            stop_loss_pct=stop_loss_pct,
            take_profit_pct=take_profit_pct
        )
    
    def should_buy(self, df: pd.DataFrame, idx: int) -> bool:
        if idx < 2:
            return False
        
        prev_close = df['close'].iloc[idx - 1]
        prev_prev_close = df['close'].iloc[idx - 2]
        
        prev_pct = (prev_close - prev_prev_close) / prev_prev_close * 100
        first_board = prev_pct >= 9.8
        
        current_open = df['open'].iloc[idx]
        current_pct_open = (current_open - prev_close) / prev_close * 100
        weak_open = current_pct_open < 2.0
        
        current_close = df['close'].iloc[idx]
        strong_close = current_close > current_open
        
        return first_board and weak_open and strong_close
    
    def should_sell(self, df: pd.DataFrame, idx: int, entry_idx: int) -> bool:
        return False


class MATrendStrategy(UltraShortTermStrategy):
    """
    Strategy 4: MA Trend Strategy
    
    [Rules]
    - Buy: MA5 > MA10 > MA20, price above MA5
    - Sell: Price below MA10 or max 5 days
    """
    
    def __init__(
        self,
        max_holding_days: int = 5,
        stop_loss_pct: float = -0.05,
        take_profit_pct: float = 0.10
    ):
        super().__init__(
            name="MATrend",
            max_holding_days=max_holding_days,
            stop_loss_pct=stop_loss_pct,
            take_profit_pct=take_profit_pct
        )
    
    def should_buy(self, df: pd.DataFrame, idx: int) -> bool:
        if idx < 30:
            return False
        
        ma5 = df['close'].rolling(5).mean().iloc[idx]
        ma10 = df['close'].rolling(10).mean().iloc[idx]
        ma20 = df['close'].rolling(20).mean().iloc[idx]
        current_close = df['close'].iloc[idx]
        
        ma_arrangement = ma5 > ma10 > ma20
        price_above_ma5 = current_close > ma5
        
        return ma_arrangement and price_above_ma5
    
    def should_sell(self, df: pd.DataFrame, idx: int, entry_idx: int) -> bool:
        if idx < 10:
            return False
        
        ma10 = df['close'].rolling(10).mean().iloc[idx]
        current_close = df['close'].iloc[idx]
        
        return current_close < ma10


class MACDKDJResonanceStrategy(UltraShortTermStrategy):
    """
    Strategy 5: MACD/KDJ Resonance Strategy
    
    [Rules]
    - Buy: MACD golden cross + KDJ golden cross (both below 50)
    - Sell: MACD death cross or max 5 days
    """
    
    def __init__(
        self,
        max_holding_days: int = 5,
        stop_loss_pct: float = -0.05,
        take_profit_pct: float = 0.10
    ):
        super().__init__(
            name="MACDKDJResonance",
            max_holding_days=max_holding_days,
            stop_loss_pct=stop_loss_pct,
            take_profit_pct=take_profit_pct
        )
    
    def _calculate_macd(self, df: pd.DataFrame) -> tuple:
        ema12 = df['close'].ewm(span=12, adjust=False).mean()
        ema26 = df['close'].ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9, adjust=False).mean()
        return macd, signal
    
    def _calculate_kdj(self, df: pd.DataFrame) -> tuple:
        low_min = df['low'].rolling(9).min()
        high_max = df['high'].rolling(9).max()
        rsv = (df['close'] - low_min) / (high_max - low_min + 1e-8) * 100
        rsv = rsv.fillna(50)
        k = rsv.ewm(com=2, adjust=False).mean()
        d = k.ewm(com=2, adjust=False).mean()
        return k, d
    
    def should_buy(self, df: pd.DataFrame, idx: int) -> bool:
        if idx < 30:
            return False
        
        macd, signal = self._calculate_macd(df)
        k, d = self._calculate_kdj(df)
        
        macd_golden = (macd.iloc[idx] > signal.iloc[idx] and 
                      macd.iloc[idx - 1] <= signal.iloc[idx - 1])
        
        kdj_golden = (k.iloc[idx] > d.iloc[idx] and 
                     k.iloc[idx - 1] <= d.iloc[idx - 1])
        
        kdj_low = k.iloc[idx] < 50
        
        return macd_golden and kdj_golden and kdj_low
    
    def should_sell(self, df: pd.DataFrame, idx: int, entry_idx: int) -> bool:
        if idx < 30:
            return False
        
        macd, signal = self._calculate_macd(df)
        
        macd_death = (macd.iloc[idx] < signal.iloc[idx] and 
                     macd.iloc[idx - 1] >= signal.iloc[idx - 1])
        
        return macd_death


class StrategyOptimizer:
    """
    Strategy Optimizer
    
    [Features]
    - Test multiple strategies
    - Optimize parameters
    - Select top 3 strategies
    """
    
    def __init__(self):
        self.strategies = [
            VolumeBreakoutStrategy(),
            StrongPullbackStrategy(),
            FirstBoardWeakToStrongStrategy(),
            MATrendStrategy(),
            MACDKDJResonanceStrategy()
        ]
        self.results = {}
    
    def test_all_strategies(
        self,
        df: pd.DataFrame,
        initial_capital: float = 100000.0
    ) -> Dict[str, BacktestResult]:
        """
        Test all strategies on given data
        
        Args:
            df: OHLCV DataFrame
            initial_capital: Initial capital
            
        Returns:
            Dict of strategy name to BacktestResult
        """
        backtester = get_enhanced_backtester(initial_capital=initial_capital)
        
        for strategy in self.strategies:
            try:
                logger.info(f"Testing strategy: {strategy.name}")
                result = backtester.run(df, strategy)
                self.results[strategy.name] = result
                logger.info(f"Strategy {strategy.name} - Win Rate: {result.win_rate:.2%}, Total Return: {result.total_return:.2%}")
            except Exception as e:
                logger.error(f"Strategy {strategy.name} failed: {e}")
        
        return self.results
    
    def get_top_strategies(
        self,
        n: int = 3,
        sort_by: str = 'sharpe_ratio'
    ) -> list:
        """
        Get top N strategies
        
        Args:
            n: Number of strategies to return
            sort_by: Metric to sort by
            
        Returns:
            List of (strategy_name, result) tuples
        """
        if not self.results:
            return []
        
        sorted_strategies = sorted(
            self.results.items(),
            key=lambda x: getattr(x[1], sort_by, 0),
            reverse=True
        )
        
        return sorted_strategies[:n]
    
    def print_strategy_comparison(self):
        """Print strategy comparison table"""
        if not self.results:
            print("No results to compare")
            return
        
        print("\n" + "=" * 120)
        print("STRATEGY COMPARISON")
        print("=" * 120)
        print(f"{'Strategy':<25} {'Win Rate':<10} {'Total Return':<15} {'Sharpe':<10} {'Max DD':<10} {'Trades':<10}")
        print("-" * 120)
        
        for name, result in self.results.items():
            print(f"{name:<25} "
                  f"{result.win_rate:<10.2%} "
                  f"{result.total_return:<15.2%} "
                  f"{result.sharpe_ratio:<10.2f} "
                  f"{result.max_drawdown:<10.2%} "
                  f"{result.total_trades:<10}")
        
        print("=" * 120)


def get_all_strategies() -> list:
    """Get all 5 master strategies"""
    return [
        VolumeBreakoutStrategy(),
        StrongPullbackStrategy(),
        FirstBoardWeakToStrongStrategy(),
        MATrendStrategy(),
        MACDKDJResonanceStrategy()
    ]


def get_strategy_optimizer() -> StrategyOptimizer:
    """Get strategy optimizer instance"""
    return StrategyOptimizer()


if __name__ == '__main__':
    print("Ultra-Short-Term Strategies module loaded")
    strategies = get_all_strategies()
    print(f"Available strategies: {[s.name for s in strategies]}")
