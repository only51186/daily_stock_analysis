# -*- coding: utf-8 -*-
"""
===================================
Enhanced Factor Library
===================================

[Features]
1. Comprehensive factor categories: Value, Technical, Volume, Sentiment
2. Automatic factor calculation
3. Factor screening and effectiveness evaluation
4. Factor correlation analysis
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class FactorCalculator:
    """
    Factor Calculator
    
    [Factor Categories]
    1. Value Factors
    2. Technical Factors
    3. Volume Factors
    4. Sentiment Factors
    """
    
    @staticmethod
    def calculate_value_factors(df: pd.DataFrame) -> Dict[str, pd.Series]:
        """
        Calculate value-based factors
        
        Returns:
            Dict of factor series
        """
        factors = {}
        
        if 'close' in df.columns:
            close = df['close']
            
            factors['price_momentum_5d'] = close.pct_change(5)
            factors['price_momentum_20d'] = close.pct_change(20)
            factors['price_momentum_60d'] = close.pct_change(60)
            
            factors['price_to_ma5'] = close / close.rolling(5).mean() - 1
            factors['price_to_ma10'] = close / close.rolling(10).mean() - 1
            factors['price_to_ma20'] = close / close.rolling(20).mean() - 1
            factors['price_to_ma60'] = close / close.rolling(60).mean() - 1
            
            factors['volatility_5d'] = close.pct_change().rolling(5).std()
            factors['volatility_20d'] = close.pct_change().rolling(20).std()
        
        return factors
    
    @staticmethod
    def calculate_technical_factors(df: pd.DataFrame) -> Dict[str, pd.Series]:
        """
        Calculate technical factors
        
        Returns:
            Dict of factor series
        """
        factors = {}
        
        if all(col in df.columns for col in ['high', 'low', 'close']):
            high = df['high']
            low = df['low']
            close = df['close']
            
            factors['atr_14'] = FactorCalculator._atr(df, 14)
            factors['atr_20'] = FactorCalculator._atr(df, 20)
            
            factors['rsi_6'] = FactorCalculator._rsi(df, 6)
            factors['rsi_14'] = FactorCalculator._rsi(df, 14)
            factors['rsi_28'] = FactorCalculator._rsi(df, 28)
            
            factors['kdj_k'], factors['kdj_d'], factors['kdj_j'] = FactorCalculator._kdj(df)
            
            macd, macd_signal, macd_hist = FactorCalculator._macd(df)
            factors['macd'] = macd
            factors['macd_signal'] = macd_signal
            factors['macd_hist'] = macd_hist
            
            factors['upper_band'], factors['middle_band'], factors['lower_band'], factors['band_width'] = FactorCalculator._bollinger(df)
            
            factors['high_low_range'] = (high - low) / close
            factors['close_to_high'] = (close - low) / (high - low + 1e-8)
        
        return factors
    
    @staticmethod
    def calculate_volume_factors(df: pd.DataFrame) -> Dict[str, pd.Series]:
        """
        Calculate volume-based factors
        
        Returns:
            Dict of factor series
        """
        factors = {}
        
        if 'volume' in df.columns:
            volume = df['volume']
            
            factors['volume_ma5_ratio'] = volume / volume.rolling(5).mean()
            factors['volume_ma10_ratio'] = volume / volume.rolling(10).mean()
            factors['volume_ma20_ratio'] = volume / volume.rolling(20).mean()
            
            factors['volume_change_1d'] = volume.pct_change(1)
            factors['volume_change_5d'] = volume.pct_change(5)
            
            factors['obv'] = FactorCalculator._obv(df)
            factors['obv_ma10'] = factors['obv'].rolling(10).mean()
            
            factors['volume_volatility_5d'] = volume.pct_change().rolling(5).std()
        
        if all(col in df.columns for col in ['close', 'volume']):
            factors['vwap_5d'] = (df['close'] * df['volume']).rolling(5).sum() / df['volume'].rolling(5).sum()
            factors['vwap_10d'] = (df['close'] * df['volume']).rolling(10).sum() / df['volume'].rolling(10).sum()
            factors['price_to_vwap5'] = df['close'] / factors['vwap_5d'] - 1
        
        return factors
    
    @staticmethod
    def calculate_sentiment_factors(df: pd.DataFrame) -> Dict[str, pd.Series]:
        """
        Calculate sentiment factors
        
        Returns:
            Dict of factor series
        """
        factors = {}
        
        if all(col in df.columns for col in ['open', 'high', 'low', 'close']):
            close = df['close']
            open_ = df['open']
            high = df['high']
            low = df['low']
            
            factors['gap_up'] = (open_ > close.shift(1) * 1.02).astype(int)
            factors['gap_down'] = (open_ < close.shift(1) * 0.98).astype(int)
            
            factors['upper_shadow'] = (high - np.maximum(open_, close)) / (high - low + 1e-8)
            factors['lower_shadow'] = (np.minimum(open_, close) - low) / (high - low + 1e-8)
            factors['body_size'] = abs(close - open_) / (high - low + 1e-8)
            
            factors['bullish_engulfing'] = ((close.shift(1) < open_.shift(1)) & 
                                            (close > open_) & 
                                            (open_ < close.shift(1)) & 
                                            (close > open_.shift(1))).astype(int)
            
            factors['doji'] = (abs(close - open_) / (high - low + 1e-8) < 0.1).astype(int)
            
            factors['hammer'] = ((factors['lower_shadow'] > 0.6) & 
                                (factors['body_size'] < 0.3)).astype(int)
            
            factors['shooting_star'] = ((factors['upper_shadow'] > 0.6) & 
                                       (factors['body_size'] < 0.3)).astype(int)
        
        if all(col in df.columns for col in ['close', 'volume']):
            factors['price_volume_corr'] = df['close'].pct_change().rolling(20).corr(df['volume'].pct_change())
        
        return factors
    
    @staticmethod
    def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Average True Range"""
        high = df['high']
        low = df['low']
        close = df['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()
        
        return atr
    
    @staticmethod
    def _rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Relative Strength Index"""
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    @staticmethod
    def _kdj(df: pd.DataFrame, n: int = 9, m1: int = 3, m2: int = 3) -> tuple:
        """KDJ indicator"""
        low_min = df['low'].rolling(n).min()
        high_max = df['high'].rolling(n).max()
        
        rsv = (df['close'] - low_min) / (high_max - low_min + 1e-8) * 100
        rsv = rsv.fillna(50)
        
        k = rsv.ewm(com=m1 - 1, adjust=False).mean()
        d = k.ewm(com=m2 - 1, adjust=False).mean()
        j = 3 * k - 2 * d
        
        return k, d, j
    
    @staticmethod
    def _macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple:
        """MACD indicator"""
        ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
        ema_slow = df['close'].ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    @staticmethod
    def _bollinger(df: pd.DataFrame, period: int = 20, std_dev: int = 2) -> tuple:
        """Bollinger Bands"""
        sma = df['close'].rolling(window=period).mean()
        std = df['close'].rolling(window=period).std()
        
        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)
        width = (upper - lower) / sma * 100
        
        return upper, sma, lower, width
    
    @staticmethod
    def _obv(df: pd.DataFrame) -> pd.Series:
        """On Balance Volume"""
        obv = (np.sign(df['close'].diff()) * df['volume']).fillna(0).cumsum()
        return obv


class FactorEvaluator:
    """
    Factor Evaluator
    
    [Features]
    1. Factor effectiveness evaluation
    2. Factor correlation analysis
    3. Factor selection
    """
    
    @staticmethod
    def evaluate_factor(
        factor_series: pd.Series,
        return_series: pd.Series,
        forward_period: int = 5
    ) -> Dict[str, Any]:
        """
        Evaluate single factor effectiveness
        
        Args:
            factor_series: Factor values
            return_series: Price returns
            forward_period: Forward looking period
            
        Returns:
            Evaluation results
        """
        if factor_series is None or return_series is None:
            return {'error': 'Invalid input'}
        
        future_returns = return_series.shift(-forward_period)
        
        valid_data = pd.DataFrame({
            'factor': factor_series,
            'future_return': future_returns
        }).dropna()
        
        if len(valid_data) < 50:
            return {'error': 'Insufficient data'}
        
        factor_rank = valid_data['factor'].rank(pct=True)
        top_quintile = factor_rank >= 0.8
        bottom_quintile = factor_rank <= 0.2
        
        top_return = valid_data[top_quintile]['future_return'].mean()
        bottom_return = valid_data[bottom_quintile]['future_return'].mean()
        
        long_short_return = top_return - bottom_return
        
        correlation = valid_data['factor'].corr(valid_data['future_return'])
        
        ic = correlation
        icir = ic / valid_data['factor'].expanding().corr(valid_data['future_return']).std() if len(valid_data) > 100 else 0
        
        win_rate = (valid_data[top_quintile]['future_return'] > 0).mean()
        
        return {
            'ic': ic,
            'icir': icir,
            'correlation': correlation,
            'long_short_return': long_short_return,
            'top_quintile_return': top_return,
            'bottom_quintile_return': bottom_return,
            'win_rate': win_rate,
            'sample_count': len(valid_data),
            'effective': abs(ic) > 0.02 and win_rate > 0.52
        }
    
    @staticmethod
    def analyze_factor_correlation(factors: Dict[str, pd.Series]) -> pd.DataFrame:
        """
        Analyze factor correlations
        
        Args:
            factors: Dict of factor series
            
        Returns:
            Correlation matrix
        """
        df = pd.DataFrame(factors)
        corr_matrix = df.corr()
        return corr_matrix
    
    @staticmethod
    def select_effective_factors(
        factors: Dict[str, pd.Series],
        return_series: pd.Series,
        forward_period: int = 5,
        min_ic: float = 0.02,
        min_win_rate: float = 0.52
    ) -> List[str]:
        """
        Select effective factors
        
        Args:
            factors: Dict of factor series
            return_series: Price returns
            forward_period: Forward looking period
            min_ic: Minimum IC threshold
            min_win_rate: Minimum win rate threshold
            
        Returns:
            List of effective factor names
        """
        effective_factors = []
        
        for factor_name, factor_series in factors.items():
            evaluation = FactorEvaluator.evaluate_factor(
                factor_series, return_series, forward_period
            )
            
            if 'error' not in evaluation:
                if evaluation['ic'] >= min_ic and evaluation['win_rate'] >= min_win_rate:
                    effective_factors.append(factor_name)
        
        return effective_factors


class FactorLibrary:
    """
    Enhanced Factor Library
    
    Combines factor calculation and evaluation
    """
    
    def __init__(self):
        self.calculator = FactorCalculator()
        self.evaluator = FactorEvaluator()
    
    def calculate_all_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate all factors
        
        Args:
            df: OHLCV DataFrame
            
        Returns:
            DataFrame with all factors
        """
        if df is None or len(df) < 60:
            return df
        
        result_df = df.copy()
        
        value_factors = self.calculator.calculate_value_factors(df)
        technical_factors = self.calculator.calculate_technical_factors(df)
        volume_factors = self.calculator.calculate_volume_factors(df)
        sentiment_factors = self.calculator.calculate_sentiment_factors(df)
        
        all_factors = {**value_factors, **technical_factors, **volume_factors, **sentiment_factors}
        
        for factor_name, factor_series in all_factors.items():
            result_df[factor_name] = factor_series
        
        return result_df
    
    def evaluate_factors(
        self,
        df: pd.DataFrame,
        factor_names: List[str] = None,
        forward_period: int = 5
    ) -> Dict[str, Any]:
        """
        Evaluate factors
        
        Args:
            df: DataFrame with factors
            factor_names: List of factor names to evaluate
            forward_period: Forward looking period
            
        Returns:
            Evaluation results
        """
        if 'close' not in df.columns:
            return {'error': 'Missing close price'}
        
        return_series = df['close'].pct_change(forward_period)
        
        if factor_names is None:
            factor_names = [col for col in df.columns if col not in ['open', 'high', 'low', 'close', 'volume', 'trade_date']]
        
        results = {}
        for factor_name in factor_names:
            if factor_name in df.columns:
                results[factor_name] = self.evaluator.evaluate_factor(
                    df[factor_name], return_series, forward_period
                )
        
        corr_matrix = self.evaluator.analyze_factor_correlation(
            {name: df[name] for name in factor_names if name in df.columns}
        )
        
        effective_factors = self.evaluator.select_effective_factors(
            {name: df[name] for name in factor_names if name in df.columns},
            return_series,
            forward_period
        )
        
        return {
            'factor_evaluations': results,
            'correlation_matrix': corr_matrix,
            'effective_factors': effective_factors
        }


def get_factor_library() -> FactorLibrary:
    """Get factor library instance"""
    return FactorLibrary()


if __name__ == '__main__':
    library = get_factor_library()
    print("Factor Library module loaded")
