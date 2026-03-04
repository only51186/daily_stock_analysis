# -*- coding: utf-8 -*-
"""
===================================
Market Analysis Module
===================================

[Features]
1. Technical indicators: MA, MACD, KDJ, RSI, BOLL
2. Trend identification: uptrend, downtrend, sideways
3. Support/resistance detection
4. Breakout/pullback recognition
5. Anomaly detection
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class TechnicalIndicators:
    """
    Technical Indicators Calculator
    
    [Supported Indicators]
    - Moving Averages (MA, EMA, SMA)
    - MACD
    - KDJ
    - RSI
    - BOLL (Bollinger Bands)
    - Volume indicators
    """
    
    @staticmethod
    def sma(df: pd.DataFrame, period: int = 20, price_col: str = 'close') -> pd.Series:
        """Simple Moving Average"""
        return df[price_col].rolling(window=period).mean()
    
    @staticmethod
    def ema(df: pd.DataFrame, period: int = 20, price_col: str = 'close') -> pd.Series:
        """Exponential Moving Average"""
        return df[price_col].ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def macd(
        df: pd.DataFrame,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
        price_col: str = 'close'
    ) -> Dict[str, pd.Series]:
        """MACD indicator"""
        ema_fast = df[price_col].ewm(span=fast, adjust=False).mean()
        ema_slow = df[price_col].ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        
        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }
    
    @staticmethod
    def kdj(
        df: pd.DataFrame,
        n: int = 9,
        m1: int = 3,
        m2: int = 3,
        price_cols: Dict[str, str] = None
    ) -> Dict[str, pd.Series]:
        """KDJ indicator"""
        if price_cols is None:
            price_cols = {'high': 'high', 'low': 'low', 'close': 'close'}
        
        low_min = df[price_cols['low']].rolling(window=n).min()
        high_max = df[price_cols['high']].rolling(window=n).max()
        
        rsv = (df[price_cols['close']] - low_min) / (high_max - low_min) * 100
        rsv = rsv.fillna(50)
        
        k = rsv.ewm(com=m1 - 1, adjust=False).mean()
        d = k.ewm(com=m2 - 1, adjust=False).mean()
        j = 3 * k - 2 * d
        
        return {'k': k, 'd': d, 'j': j}
    
    @staticmethod
    def rsi(df: pd.DataFrame, period: int = 14, price_col: str = 'close') -> pd.Series:
        """RSI indicator"""
        delta = df[price_col].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    @staticmethod
    def boll(
        df: pd.DataFrame,
        period: int = 20,
        std_dev: int = 2,
        price_col: str = 'close'
    ) -> Dict[str, pd.Series]:
        """Bollinger Bands"""
        sma = df[price_col].rolling(window=period).mean()
        std = df[price_col].rolling(window=period).std()
        
        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)
        width = (upper - lower) / sma * 100
        
        return {
            'middle': sma,
            'upper': upper,
            'lower': lower,
            'width': width
        }
    
    @staticmethod
    def volume_ma(df: pd.DataFrame, period: int = 20, volume_col: str = 'volume') -> pd.Series:
        """Volume Moving Average"""
        return df[volume_col].rolling(window=period).mean()


class TrendAnalyzer:
    """
    Trend Analyzer
    
    [Features]
    - Trend direction identification
    - Support/resistance levels
    - Breakout/pullback detection
    - Anomaly detection
    """
    
    @staticmethod
    def identify_trend(
        df: pd.DataFrame,
        short_period: int = 5,
        long_period: int = 20,
        price_col: str = 'close'
    ) -> Dict[str, Any]:
        """
        Identify trend direction
        
        Returns:
            Dict with trend info:
                - direction: 'uptrend' | 'downtrend' | 'sideways'
                - strength: 0-100
                - slope: trend slope
        """
        if len(df) < long_period:
            return {'direction': 'unknown', 'strength': 0, 'slope': 0}
        
        short_ma = df[price_col].rolling(window=short_period).mean()
        long_ma = df[price_col].rolling(window=long_period).mean()
        
        current_short = short_ma.iloc[-1]
        current_long = long_ma.iloc[-1]
        prev_short = short_ma.iloc[-2]
        prev_long = long_ma.iloc[-2]
        
        if current_short > current_long and prev_short > prev_long:
            direction = 'uptrend'
            strength = min(100, (current_short - current_long) / current_long * 100 + 50)
        elif current_short < current_long and prev_short < prev_long:
            direction = 'downtrend'
            strength = min(100, (current_long - current_short) / current_long * 100 + 50)
        else:
            direction = 'sideways'
            strength = max(0, 50 - abs(current_short - current_long) / current_long * 100)
        
        x = np.arange(long_period)
        y = df[price_col].tail(long_period).values
        slope = np.polyfit(x, y, 1)[0]
        
        return {
            'direction': direction,
            'strength': strength,
            'slope': slope
        }
    
    @staticmethod
    def find_support_resistance(
        df: pd.DataFrame,
        lookback: int = 60,
        sensitivity: float = 0.02,
        price_col: str = 'close'
    ) -> Dict[str, List[float]]:
        """
        Find support and resistance levels
        
        Args:
            df: DataFrame
            lookback: Lookback period
            sensitivity: Price sensitivity (percentage)
            price_col: Price column
            
        Returns:
            Dict with 'support' and 'resistance' lists
        """
        if len(df) < lookback:
            return {'support': [], 'resistance': []}
        
        data = df[price_col].tail(lookback).values
        highs = []
        lows = []
        
        for i in range(2, len(data) - 2):
            if data[i] > data[i-1] and data[i] > data[i-2] and data[i] > data[i+1] and data[i] > data[i+2]:
                highs.append(data[i])
            
            if data[i] < data[i-1] and data[i] < data[i-2] and data[i] < data[i+1] and data[i] < data[i+2]:
                lows.append(data[i])
        
        def cluster_levels(levels: List[float], sensitivity: float) -> List[float]:
            if not levels:
                return []
            
            levels_sorted = sorted(levels)
            clusters = []
            current_cluster = [levels_sorted[0]]
            
            for level in levels_sorted[1:]:
                last_in_cluster = current_cluster[-1]
                if (level - last_in_cluster) / last_in_cluster <= sensitivity:
                    current_cluster.append(level)
                else:
                    clusters.append(np.mean(current_cluster))
                    current_cluster = [level]
            
            if current_cluster:
                clusters.append(np.mean(current_cluster))
            
            return sorted(clusters, reverse=True)
        
        return {
            'support': cluster_levels(lows, sensitivity),
            'resistance': cluster_levels(highs, sensitivity)
        }
    
    @staticmethod
    def detect_breakout(
        df: pd.DataFrame,
        resistance_levels: List[float],
        volume_col: str = 'volume',
        price_col: str = 'close'
    ) -> Dict[str, Any]:
        """
        Detect breakout above resistance
        
        Returns:
            Dict with breakout info
        """
        if len(df) < 2 or not resistance_levels:
            return {'is_breakout': False, 'level': None, 'strength': 0}
        
        current_price = df[price_col].iloc[-1]
        prev_price = df[price_col].iloc[-2]
        current_volume = df[volume_col].iloc[-1]
        avg_volume = df[volume_col].tail(20).mean()
        
        for level in resistance_levels:
            if current_price > level and prev_price <= level:
                volume_factor = current_volume / avg_volume if avg_volume > 0 else 1
                strength = min(100, (current_price - level) / level * 100 + volume_factor * 20)
                
                return {
                    'is_breakout': True,
                    'level': level,
                    'strength': strength,
                    'volume_factor': volume_factor
                }
        
        return {'is_breakout': False, 'level': None, 'strength': 0}
    
    @staticmethod
    def detect_pullback(
        df: pd.DataFrame,
        support_levels: List[float],
        price_col: str = 'close'
    ) -> Dict[str, Any]:
        """
        Detect pullback to support
        
        Returns:
            Dict with pullback info
        """
        if len(df) < 2 or not support_levels:
            return {'is_pullback': False, 'level': None, 'strength': 0}
        
        current_price = df[price_col].iloc[-1]
        prev_price = df[price_col].iloc[-2]
        
        for level in support_levels:
            if current_price >= level and prev_price < level:
                strength = min(100, 100 - (current_price - level) / level * 100)
                
                return {
                    'is_pullback': True,
                    'level': level,
                    'strength': strength
                }
        
        return {'is_pullback': False, 'level': None, 'strength': 0}
    
    @staticmethod
    def detect_anomaly(
        df: pd.DataFrame,
        price_col: str = 'close',
        volume_col: str = 'volume'
    ) -> Dict[str, Any]:
        """
        Detect anomalies (price/volume spikes)
        
        Returns:
            Dict with anomaly info
        """
        if len(df) < 5:
            return {'has_anomaly': False, 'type': None}
        
        price_changes = df[price_col].pct_change().abs()
        volume_changes = df[volume_col].pct_change().abs()
        
        avg_price_change = price_changes.tail(20).mean()
        avg_volume_change = volume_changes.tail(20).mean()
        
        current_price_change = price_changes.iloc[-1]
        current_volume_change = volume_changes.iloc[-1]
        
        price_spike = current_price_change > avg_price_change * 3
        volume_spike = current_volume_change > avg_volume_change * 3
        
        anomaly_type = None
        if price_spike and volume_spike:
            anomaly_type = 'price_volume_spike'
        elif price_spike:
            anomaly_type = 'price_spike'
        elif volume_spike:
            anomaly_type = 'volume_spike'
        
        return {
            'has_anomaly': anomaly_type is not None,
            'type': anomaly_type,
            'price_change': current_price_change,
            'volume_change': current_volume_change
        }


class MarketAnalyzer:
    """
    Comprehensive Market Analyzer
    
    Combines technical indicators and trend analysis
    """
    
    def __init__(self):
        self.indicators = TechnicalIndicators()
        self.trend = TrendAnalyzer()
    
    def analyze(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Perform comprehensive market analysis
        
        Args:
            df: OHLCV DataFrame
            
        Returns:
            Analysis result dict
        """
        if df is None or len(df) < 30:
            return {'error': 'Insufficient data'}
        
        df = df.copy()
        
        ma5 = self.indicators.sma(df, 5)
        ma10 = self.indicators.sma(df, 10)
        ma20 = self.indicators.sma(df, 20)
        ma60 = self.indicators.sma(df, 60)
        
        ema12 = self.indicators.ema(df, 12)
        ema26 = self.indicators.ema(df, 26)
        
        macd = self.indicators.macd(df)
        kdj = self.indicators.kdj(df)
        rsi = self.indicators.rsi(df)
        boll = self.indicators.boll(df)
        vol_ma = self.indicators.volume_ma(df)
        
        trend_info = self.trend.identify_trend(df)
        levels = self.trend.find_support_resistance(df)
        breakout = self.trend.detect_breakout(df, levels['resistance'])
        pullback = self.trend.detect_pullback(df, levels['support'])
        anomaly = self.trend.detect_anomaly(df)
        
        latest_idx = df.index[-1]
        
        signals = []
        
        if macd['macd'].iloc[-1] > macd['signal'].iloc[-1] and macd['macd'].iloc[-2] <= macd['signal'].iloc[-2]:
            signals.append('MACD_GOLDEN_CROSS')
        
        if kdj['k'].iloc[-1] > kdj['d'].iloc[-1] and kdj['k'].iloc[-2] <= kdj['d'].iloc[-2] and kdj['k'].iloc[-1] < 30:
            signals.append('KDJ_OVERSOLD_BUY')
        
        if rsi.iloc[-1] < 30:
            signals.append('RSI_OVERSOLD')
        elif rsi.iloc[-1] > 70:
            signals.append('RSI_OVERBOUGHT')
        
        if df['close'].iloc[-1] > boll['upper'].iloc[-1]:
            signals.append('BOLL_BREAKOUT_UPPER')
        elif df['close'].iloc[-1] < boll['lower'].iloc[-1]:
            signals.append('BOLL_BREAKOUT_LOWER')
        
        if breakout['is_breakout']:
            signals.append('PRICE_BREAKOUT')
        
        if pullback['is_pullback']:
            signals.append('PRICE_PULLBACK')
        
        if anomaly['has_anomaly']:
            signals.append(f'ANOMALY_{anomaly["type"].upper()}')
        
        bullish_count = sum(1 for s in signals if any(x in s for x in ['GOLDEN', 'OVERSOLD', 'BREAKOUT', 'PULLBACK']))
        bearish_count = sum(1 for s in signals if any(x in s for x in ['DEATH', 'OVERBOUGHT', 'LOWER']))
        
        overall_sentiment = 'NEUTRAL'
        if bullish_count > bearish_count + 1:
            overall_sentiment = 'BULLISH'
        elif bearish_count > bullish_count + 1:
            overall_sentiment = 'BEARISH'
        
        return {
            'trend': trend_info,
            'support_resistance': levels,
            'breakout': breakout,
            'pullback': pullback,
            'anomaly': anomaly,
            'signals': signals,
            'sentiment': overall_sentiment,
            'bullish_count': bullish_count,
            'bearish_count': bearish_count,
            'indicators': {
                'MA5': ma5.iloc[-1],
                'MA10': ma10.iloc[-1],
                'MA20': ma20.iloc[-1],
                'MA60': ma60.iloc[-1],
                'MACD': macd['macd'].iloc[-1],
                'MACD_Signal': macd['signal'].iloc[-1],
                'KDJ_K': kdj['k'].iloc[-1],
                'KDJ_D': kdj['d'].iloc[-1],
                'RSI': rsi.iloc[-1],
                'BOLL_Upper': boll['upper'].iloc[-1],
                'BOLL_Lower': boll['lower'].iloc[-1],
                'BOLL_Width': boll['width'].iloc[-1],
                'Current_Price': df['close'].iloc[-1],
                'Volume_MA20': vol_ma.iloc[-1]
            }
        }
    
    def print_analysis(self, analysis: Dict[str, Any]):
        """Print formatted analysis report"""
        if 'error' in analysis:
            print(f"Error: {analysis['error']}")
            return
        
        print("\n" + "=" * 80)
        print("MARKET ANALYSIS REPORT")
        print("=" * 80)
        
        print(f"\nOverall Sentiment: {analysis['sentiment']}")
        print(f"Trend: {analysis['trend']['direction']} (Strength: {analysis['trend']['strength']:.1f}%)")
        
        print(f"\nKey Indicators:")
        for key, value in analysis['indicators'].items():
            if isinstance(value, float):
                print(f"  {key}: {value:.4f}")
            else:
                print(f"  {key}: {value}")
        
        print(f"\nSupport Levels: {analysis['support_resistance']['support']}")
        print(f"Resistance Levels: {analysis['support_resistance']['resistance']}")
        
        if analysis['signals']:
            print(f"\nTrading Signals:")
            for signal in analysis['signals']:
                print(f"  - {signal}")
        
        print(f"\nBullish: {analysis['bullish_count']} | Bearish: {analysis['bearish_count']}")
        print("=" * 80)


def get_market_analyzer() -> MarketAnalyzer:
    """Get market analyzer instance"""
    return MarketAnalyzer()


if __name__ == '__main__':
    analyzer = get_market_analyzer()
    print("Market Analyzer module loaded")
