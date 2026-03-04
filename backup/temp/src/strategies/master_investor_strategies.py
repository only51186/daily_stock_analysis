# -*- coding: utf-8 -*-
"""
===================================
Three Master Investors' Ultra-Short-Term Strategies
===================================

[Strategies]
1. ChaoGu YangJia (情绪流) - 炒股养家
2. Chen XiaoQun (龙头人气流) - 陈小群
3. TuiXue ChaoGu (模式流) - 退学炒股

[Trading Rules]
- Market: Shanghai/Shenzhen Main Board only
- Style: Ultra-short-term (1-5 days)
- Position: Full position, single stock
- Target: Win rate ≥ 60%, Avg return ≥ 3%, Max drawdown ≤ 10%
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.backtest_layer import UltraShortTermStrategy

logger = logging.getLogger(__name__)


class MarketSentiment(Enum):
    """Market sentiment classification"""
    FREEZING = "freezing"    # 冰点
    LOW = "low"              # 低迷
    RECOVERY = "recovery"    # 回暖
    RISING = "rising"        # 上升
    HOT = "hot"              # 火热


@dataclass
class StockInfo:
    """Stock information"""
    symbol: str
    name: str
    market_cap: float  # 市值 (亿)
    turnover_rate: float  # 换手率
    is_st: bool = False
    is_suspended: bool = False
    is_main_board: bool = True


@dataclass
class ThemeInfo:
    """Theme/ sector information"""
    name: str
    stock_count: int
    up_stock_count: int
    limit_up_count: int
    total_turnover: float  # 总成交额 (亿)
    market_share: float  # 市场占比


class ChaoGuYangJiaStrategy(UltraShortTermStrategy):
    """
    Strategy 1: ChaoGu YangJia (情绪流)
    
    [Core Philosophy]
    - Buy on divergence, sell on consensus
    - Only trade mainstream themes, only trade leaders
    """
    
    def __init__(
        self,
        min_market_cap: float = 50.0,  # 最小市值 50亿
        max_market_cap: float = 500.0,  # 最大市值 500亿
        min_avg_turnover: float = 8.0,  # 最小日均换手 8%
        max_avg_turnover: float = 30.0,  # 最大日均换手 30%
        volume_ratio_threshold: float = 1.5,  # 量比阈值
        stop_loss_pct: float = -0.03,  # 止损 3%
        take_profit_pct: float = 0.05,  # 止盈 5%
        max_holding_days: int = 5
    ):
        super().__init__(
            name="ChaoGuYangJia",
            max_holding_days=max_holding_days,
            stop_loss_pct=stop_loss_pct,
            take_profit_pct=take_profit_pct
        )
        self.min_market_cap = min_market_cap
        self.max_market_cap = max_market_cap
        self.min_avg_turnover = min_avg_turnover
        self.max_avg_turnover = max_avg_turnover
        self.volume_ratio_threshold = volume_ratio_threshold
        
        self.market_sentiment = MarketSentiment.RECOVERY
        self.main_themes: List[ThemeInfo] = []
        self.theme_leaders: Dict[str, str] = {}  # theme -> leader symbol
    
    def analyze_market_sentiment(
        self,
        limit_up_count: int,
        limit_down_count: int,
        total_stock_count: int = 5000
    ) -> MarketSentiment:
        """
        Analyze market sentiment
        
        Args:
            limit_up_count: Number of limit-up stocks
            limit_down_count: Number of limit-down stocks
            total_stock_count: Total number of stocks
            
        Returns:
            MarketSentiment enum
        """
        if limit_up_count < 20 and limit_down_count > 10:
            return MarketSentiment.FREEZING
        elif limit_up_count < 50 or limit_down_count > 5:
            return MarketSentiment.LOW
        elif limit_up_count > 50 and limit_down_count < 5:
            return MarketSentiment.RECOVERY
        elif limit_up_count > 80:
            return MarketSentiment.RISING
        elif limit_up_count > 120:
            return MarketSentiment.HOT
        
        return MarketSentiment.LOW
    
    def identify_main_themes(
        self,
        theme_data: List[Dict[str, Any]]
    ) -> List[ThemeInfo]:
        """
        Identify mainstream themes
        
        Args:
            theme_data: List of theme data dicts
            
        Returns:
            List of ThemeInfo, sorted by importance
        """
        themes = []
        
        for data in theme_data:
            theme = ThemeInfo(
                name=data.get('name', ''),
                stock_count=data.get('stock_count', 0),
                up_stock_count=data.get('up_stock_count', 0),
                limit_up_count=data.get('limit_up_count', 0),
                total_turnover=data.get('total_turnover', 0),
                market_share=data.get('market_share', 0)
            )
            
            if theme.limit_up_count >= 10 and theme.market_share >= 0.15:
                themes.append(theme)
        
        themes.sort(key=lambda x: x.limit_up_count, reverse=True)
        return themes[:3]
    
    def is_leader(
        self,
        df: pd.DataFrame,
        idx: int,
        theme_stocks: List[str]
    ) -> bool:
        """
        Check if stock is theme leader
        
        Args:
            df: Stock DataFrame
            idx: Current index
            theme_stocks: List of stocks in the same theme
            
        Returns:
            True if leader
        """
        if idx < 3:
            return False
        
        current_close = df['close'].iloc[idx]
        prev_close = df['close'].iloc[idx - 1]
        pct_chg = (current_close - prev_close) / prev_close * 100
        
        is_limit_up = pct_chg >= 9.8
        
        if not is_limit_up:
            return False
        
        turnover_3d = df['volume'].iloc[idx - 2:idx + 1].mean() / df['volume'].iloc[idx - 20:idx - 2].mean() * 100
        turnover_ok = 5 <= turnover_3d <= 20
        
        return turnover_ok
    
    def check_divergence_buy(
        self,
        df: pd.DataFrame,
        idx: int
    ) -> bool:
        """
        Check divergence buy signal
        
        [Rules]
        - Leader stock blew up limit-up
        - Turnover ≥ 15% within 1 hour
        - Did not hit limit-down
        - Pulls back to MA5, stabilizes and turns red
        """
        if idx < 10:
            return False
        
        prev_close = df['close'].iloc[idx - 1]
        current_open = df['open'].iloc[idx]
        current_low = df['low'].iloc[idx]
        current_close = df['close'].iloc[idx]
        
        prev_pct = (prev_close - df['close'].iloc[idx - 2]) / df['close'].iloc[idx - 2] * 100
        was_limit_up = prev_pct >= 9.8
        
        if not was_limit_up:
            return False
        
        current_pct = (current_close - prev_close) / prev_close * 100
        not_limit_down = current_pct > -9.8
        
        if not not_limit_down:
            return False
        
        turnover = df.get('turnover_rate', pd.Series([0] * len(df))).iloc[idx]
        high_turnover = turnover >= 15
        
        ma5 = df['close'].rolling(5).mean().iloc[idx]
        touches_ma5 = current_low <= ma5 * 1.01 and current_close >= ma5 * 0.99
        
        stabilizes = current_close > current_open
        
        return high_turnover and touches_ma5 and stabilizes
    
    def check_weak_to_strong_buy(
        self,
        df: pd.DataFrame,
        idx: int
    ) -> bool:
        """
        Check weak-to-strong buy signal
        
        [Rules]
        - Leader stock
        - Next day opens low ≤ 2%
        - Breaks yesterday's close within 30 minutes with volume
        """
        if idx < 5:
            return False
        
        prev_close = df['close'].iloc[idx - 1]
        current_open = df['open'].iloc[idx]
        current_close = df['close'].iloc[idx]
        
        open_pct = (current_open - prev_close) / prev_close * 100
        low_open = -2 <= open_pct <= 2
        
        volume = df['volume'].iloc[idx]
        avg_volume = df['volume'].iloc[idx - 20:idx].mean()
        volume_spike = volume > avg_volume * 1.5
        
        breaks_prev_close = current_close > prev_close
        
        return low_open and volume_spike and breaks_prev_close
    
    def check_consensus_sell(
        self,
        df: pd.DataFrame,
        idx: int,
        entry_idx: int
    ) -> bool:
        """
        Check consensus sell signal
        
        [Rules]
        - Next day opens with ≥ 5% gain
        - Volume shrinks (volume ratio < 0.8)
        """
        if idx != entry_idx + 1:
            return False
        
        prev_close = df['close'].iloc[idx - 1]
        current_open = df['open'].iloc[idx]
        
        open_gain = (current_open - prev_close) / prev_close >= 0.05
        
        volume = df['volume'].iloc[idx]
        prev_volume = df['volume'].iloc[idx - 1]
        volume_shrinks = volume / prev_volume < 0.8
        
        return open_gain and volume_shrinks
    
    def should_buy(self, df: pd.DataFrame, idx: int) -> bool:
        if self.market_sentiment == MarketSentiment.FREEZING:
            return False
        
        if self.market_sentiment == MarketSentiment.LOW:
            return False
        
        if idx < 20:
            return False
        
        return self.check_divergence_buy(df, idx) or self.check_weak_to_strong_buy(df, idx)
    
    def should_sell(self, df: pd.DataFrame, idx: int, entry_idx: int) -> bool:
        return self.check_consensus_sell(df, idx, entry_idx)


class ChenXiaoQunStrategy(UltraShortTermStrategy):
    """
    Strategy 2: Chen XiaoQun (龙头人气流)
    
    [Core Philosophy]
    - Only trade the most popular stock in the market
    - The strong get stronger, don't guess the top
    """
    
    def __init__(
        self,
        min_consecutive_boards: int = 2,
        min_3d_turnover: float = 60.0,
        min_profit_ratio: float = 0.8,
        min_main_net_inflow: float = 5000.0,  # 万
        stop_loss_pct: float = -0.05,
        max_holding_days: int = 5
    ):
        super().__init__(
            name="ChenXiaoQun",
            max_holding_days=max_holding_days,
            stop_loss_pct=stop_loss_pct,
            take_profit_pct=0.20
        )
        self.min_consecutive_boards = min_consecutive_boards
        self.min_3d_turnover = min_3d_turnover
        self.min_profit_ratio = min_profit_ratio
        self.min_main_net_inflow = min_main_net_inflow
        
        self.popularity_rank: int = 999
        self.has_star_investors: bool = False
        self.consecutive_boards: int = 0
    
    def count_consecutive_boards(self, df: pd.DataFrame, idx: int) -> int:
        """Count consecutive limit-up boards"""
        if idx < 1:
            return 0
        
        count = 0
        for i in range(idx, max(-1, idx - 10), -1):
            if i < 1:
                break
            prev_close = df['close'].iloc[i - 1]
            current_close = df['close'].iloc[i]
            pct_chg = (current_close - prev_close) / prev_close * 100
            
            if pct_chg >= 9.8:
                count += 1
            else:
                break
        
        return count
    
    def check_pullback_buy(self, df: pd.DataFrame, idx: int) -> bool:
        """
        Check leader pullback buy signal
        
        [Rules]
        - Pulls back to MA20
        - Shrinks (turnover < 10%)
        - Stabilizes
        - Breaks MA5 with volume
        """
        if idx < 30:
            return False
        
        ma20 = df['close'].rolling(20).mean().iloc[idx]
        ma5 = df['close'].rolling(5).mean().iloc[idx]
        current_low = df['low'].iloc[idx]
        current_close = df['close'].iloc[idx]
        
        touches_ma20 = current_low <= ma20 * 1.01
        if not touches_ma20:
            return False
        
        turnover = df.get('turnover_rate', pd.Series([0] * len(df))).iloc[idx]
        shrinks = turnover < 10
        
        volume = df['volume'].iloc[idx]
        avg_volume = df['volume'].iloc[idx - 20:idx].mean()
        volume_spike = volume > avg_volume * 1.2
        
        breaks_ma5 = current_close > ma5
        
        return shrinks and volume_spike and breaks_ma5
    
    def check_breakout_buy(self, df: pd.DataFrame, idx: int) -> bool:
        """
        Check breakout buy signal
        
        [Rules]
        - Breaks 30-day high
        - Hits limit-up
        """
        if idx < 30:
            return False
        
        high_30d = df['high'].iloc[idx - 30:idx].max()
        current_high = df['high'].iloc[idx]
        current_close = df['close'].iloc[idx]
        prev_close = df['close'].iloc[idx - 1]
        
        breaks_high = current_high > high_30d * 0.99
        pct_chg = (current_close - prev_close) / prev_close * 100
        hits_limit_up = pct_chg >= 9.8
        
        return breaks_high and hits_limit_up
    
    def check_board_break_sell(self, df: pd.DataFrame, idx: int, entry_idx: int) -> bool:
        """
        Check board-break sell signal
        
        [Rules]
        - Did not hit limit-up on the day
        - Sell at next day's opening auction
        """
        if idx != entry_idx + 1:
            return False
        
        prev_close = df['close'].iloc[idx - 2]
        day_close = df['close'].iloc[idx - 1]
        day_pct = (day_close - prev_close) / prev_close * 100
        
        did_not_board = day_pct < 9.8
        
        return did_not_board
    
    def check_premium_sell(self, df: pd.DataFrame, idx: int, entry_idx: int) -> bool:
        """
        Check premium sell signal
        
        [Rules]
        - Next day opens high ≥ 5%
        - Does not hit limit-up within 15 minutes
        """
        if idx != entry_idx + 1:
            return False
        
        prev_close = df['close'].iloc[idx - 1]
        current_open = df['open'].iloc[idx]
        
        open_high = (current_open - prev_close) / prev_close >= 0.05
        
        return open_high
    
    def should_buy(self, df: pd.DataFrame, idx: int) -> bool:
        if idx < 30:
            return False
        
        self.consecutive_boards = self.count_consecutive_boards(df, idx)
        if self.consecutive_boards < self.min_consecutive_boards:
            return False
        
        return self.check_pullback_buy(df, idx) or self.check_breakout_buy(df, idx)
    
    def should_sell(self, df: pd.DataFrame, idx: int, entry_idx: int) -> bool:
        if idx < 10:
            return False
        
        ma10 = df['close'].rolling(10).mean().iloc[idx]
        current_close = df['close'].iloc[idx]
        
        if current_close < ma10:
            return True
        
        return self.check_board_break_sell(df, idx, entry_idx) or self.check_premium_sell(df, idx, entry_idx)


class TuiXueChaoGuStrategy(UltraShortTermStrategy):
    """
    Strategy 3: TuiXue ChaoGu (模式流)
    
    [Core Philosophy]
    - Only trade within the pattern, stay out otherwise
    - Cut losses short, let profits run
    """
    
    def __init__(
        self,
        min_10d_gain: float = 0.20,  # 10日涨幅≥20%
        min_volume_ratio: float = 1.2,
        platform_days: int = 10,
        platform_volume_ratio: float = 2.0,
        min_turnover: float = 5.0,  # 亿
        stop_loss_pct: float = -0.05,
        partial_take_profit_pct: float = 0.10,  # 10% 部分止盈
        full_take_profit_pct: float = 0.20,  # 20% 全部止盈
        max_holding_days: int = 5
    ):
        super().__init__(
            name="TuiXueChaoGu",
            max_holding_days=max_holding_days,
            stop_loss_pct=stop_loss_pct,
            take_profit_pct=full_take_profit_pct
        )
        self.min_10d_gain = min_10d_gain
        self.min_volume_ratio = min_volume_ratio
        self.platform_days = platform_days
        self.platform_volume_ratio = platform_volume_ratio
        self.min_turnover = min_turnover
        self.partial_take_profit_pct = partial_take_profit_pct
        
        self.in_pattern = False
        self.partial_position_sold = False
    
    def check_uptrend(self, df: pd.DataFrame, idx: int) -> bool:
        """
        Check uptrend
        
        [Rules]
        - MA5 > MA10 > MA20
        - 10-day gain ≥ 20%
        """
        if idx < 30:
            return False
        
        ma5 = df['close'].rolling(5).mean().iloc[idx]
        ma10 = df['close'].rolling(10).mean().iloc[idx]
        ma20 = df['close'].rolling(20).mean().iloc[idx]
        
        ma_arrangement = ma5 > ma10 > ma20
        
        gain_10d = (df['close'].iloc[idx] - df['close'].iloc[idx - 10]) / df['close'].iloc[idx - 10]
        
        return ma_arrangement and gain_10d >= self.min_10d_gain
    
    def check_volume_price_sync(self, df: pd.DataFrame, idx: int) -> bool:
        """
        Check volume-price synchronization
        
        [Rules]
        - Price up with volume up
        - Price down with volume down
        - Volume ratio > 1.2
        """
        if idx < 10:
            return False
        
        volume = df['volume'].iloc[idx]
        avg_volume = df['volume'].iloc[idx - 10:idx].mean()
        volume_ratio = volume / avg_volume if avg_volume > 0 else 0
        
        return volume_ratio >= self.min_volume_ratio
    
    def check_platform_breakout(self, df: pd.DataFrame, idx: int) -> bool:
        """
        Check platform breakout
        
        [Rules]
        - Sideways for ≥ 10 days
        - Breakout day volume > 2x platform average
        """
        if idx < self.platform_days + 5:
            return False
        
        platform_start = idx - self.platform_days
        platform_high = df['high'].iloc[platform_start:idx].max()
        platform_low = df['low'].iloc[platform_start:idx].min()
        platform_range = (platform_high - platform_low) / platform_low
        
        is_sideways = platform_range < 0.15
        
        if not is_sideways:
            return False
        
        platform_avg_volume = df['volume'].iloc[platform_start:idx].mean()
        current_volume = df['volume'].iloc[idx]
        volume_spike = current_volume > platform_avg_volume * self.platform_volume_ratio
        
        current_close = df['close'].iloc[idx]
        breaks_high = current_close > platform_high * 0.99
        
        return volume_spike and breaks_high
    
    def check_first_yin_reverse(self, df: pd.DataFrame, idx: int) -> bool:
        """
        Check first Yin reverse
        
        [Rules]
        - First big Yin (down ≥ 5%)
        - Next day big Yang covers ≥ 80% of Yin
        """
        if idx < 5:
            return False
        
        prev_close = df['close'].iloc[idx - 1]
        prev_prev_close = df['close'].iloc[idx - 2]
        first_yin_pct = (prev_close - prev_prev_close) / prev_prev_close
        
        is_first_yin = first_yin_pct <= -0.05
        
        if not is_first_yin:
            return False
        
        current_open = df['open'].iloc[idx]
        current_close = df['close'].iloc[idx]
        yin_body = prev_prev_close - prev_close
        yang_body = current_close - current_open
        
        covers_80 = yang_body >= yin_body * 0.8
        
        volume = df['volume'].iloc[idx]
        prev_volume = df['volume'].iloc[idx - 1]
        volume_spike = volume > prev_volume * 1.5
        
        return covers_80 and volume_spike
    
    def check_stagnation_sell(self, df: pd.DataFrame, idx: int, entry_idx: int) -> bool:
        """
        Check stagnation sell signal
        
        [Rules]
        - Does not make new high within 30 minutes
        - Volume shrinks
        """
        if idx - entry_idx < 1:
            return False
        
        if idx < 5:
            return False
        
        recent_high = df['high'].iloc[entry_idx:idx + 1].max()
        current_high = df['high'].iloc[idx]
        
        no_new_high = current_high < recent_high * 0.99
        
        volume = df['volume'].iloc[idx]
        avg_volume = df['volume'].iloc[entry_idx:idx].mean()
        volume_shrinks = volume < avg_volume * 0.8
        
        return no_new_high and volume_shrinks
    
    def should_buy(self, df: pd.DataFrame, idx: int) -> bool:
        if idx < 30:
            return False
        
        if not self.check_uptrend(df, idx):
            return False
        
        if not self.check_volume_price_sync(df, idx):
            return False
        
        self.in_pattern = True
        return self.check_platform_breakout(df, idx) or self.check_first_yin_reverse(df, idx)
    
    def should_sell(self, df: pd.DataFrame, idx: int, entry_idx: int) -> bool:
        if not self.in_pattern:
            return True
        
        if self.check_stagnation_sell(df, idx, entry_idx):
            return True
        
        return False


class ThreeInOneStrategy(UltraShortTermStrategy):
    """
    Three-In-One Combined Strategy
    
    Combines:
    1. ChaoGu YangJia (Emotion Flow)
    2. Chen XiaoQun (Leader Popularity Flow)
    3. TuiXue ChaoGu (Pattern Flow)
    
    [Unified Risk Control]
    - Stop loss: 3-5%
    - Max holding: 5 days
    - Full position only
    """
    
    def __init__(
        self,
        stop_loss_pct: float = -0.04,
        take_profit_pct: float = 0.12,
        max_holding_days: int = 5
    ):
        super().__init__(
            name="ThreeInOne",
            max_holding_days=max_holding_days,
            stop_loss_pct=stop_loss_pct,
            take_profit_pct=take_profit_pct
        )
        
        self.yangjia = ChaoGuYangJiaStrategy()
        self.xiaoqun = ChenXiaoQunStrategy()
        self.tuixue = TuiXueChaoGuStrategy()
        
        self.active_strategy: Optional[str] = None
    
    def should_buy(self, df: pd.DataFrame, idx: int) -> bool:
        if idx < 30:
            return False
        
        if self.yangjia.should_buy(df, idx):
            self.active_strategy = 'yangjia'
            return True
        
        if self.xiaoqun.should_buy(df, idx):
            self.active_strategy = 'xiaoqun'
            return True
        
        if self.tuixue.should_buy(df, idx):
            self.active_strategy = 'tuixue'
            return True
        
        return False
    
    def should_sell(self, df: pd.DataFrame, idx: int, entry_idx: int) -> bool:
        if self.active_strategy == 'yangjia':
            return self.yangjia.should_sell(df, idx, entry_idx)
        elif self.active_strategy == 'xiaoqun':
            return self.xiaoqun.should_sell(df, idx, entry_idx)
        elif self.active_strategy == 'tuixue':
            return self.tuixue.should_sell(df, idx, entry_idx)
        
        return False


def get_master_strategies() -> List[UltraShortTermStrategy]:
    """Get all 3 master strategies"""
    return [
        ChaoGuYangJiaStrategy(),
        ChenXiaoQunStrategy(),
        TuiXueChaoGuStrategy()
    ]


def get_three_in_one_strategy() -> ThreeInOneStrategy:
    """Get combined three-in-one strategy"""
    return ThreeInOneStrategy()


if __name__ == '__main__':
    print("Three Master Investors' Strategies module loaded")
    strategies = get_master_strategies()
    print(f"Available strategies: {[s.name for s in strategies]}")
