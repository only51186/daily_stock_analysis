# -*- coding: utf-8 -*-
"""
===================================
Enhanced Backtest System
===================================

[Features]
1. Ultra-short-term full-position backtesting
2. Comprehensive performance metrics
3. Detailed trade analysis
4. Visualization support
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class Trade:
    """Trade record"""
    entry_date: str
    entry_price: float
    exit_date: str
    exit_price: float
    shares: int
    direction: str  # 'long'
    pnl: float
    pnl_pct: float
    holding_days: int


@dataclass
class BacktestResult:
    """Backtest result"""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_return: float
    annual_return: float
    total_pnl: float
    avg_profit_per_trade: float
    avg_profit_per_win: float
    avg_loss_per_loss: float
    profit_loss_ratio: float
    max_drawdown: float
    max_drawdown_duration: int
    consecutive_wins: int
    consecutive_losses: int
    max_consecutive_wins: int
    max_consecutive_losses: int
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    trades: List[Trade]
    equity_curve: pd.Series
    drawdown_curve: pd.Series


class StrategyBase:
    """Base class for trading strategies"""
    
    def __init__(self, name: str):
        self.name = name
        self.params = {}
    
    def set_params(self, **kwargs):
        """Set strategy parameters"""
        self.params.update(kwargs)
    
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """
        Generate trading signals
        
        Args:
            df: OHLCV DataFrame
            
        Returns:
            Series of signals: 1 = buy, -1 = sell, 0 = hold
        """
        raise NotImplementedError
    
    def should_buy(self, df: pd.DataFrame, idx: int) -> bool:
        """Check if should buy at index"""
        raise NotImplementedError
    
    def should_sell(self, df: pd.DataFrame, idx: int, entry_idx: int) -> bool:
        """Check if should sell at index"""
        raise NotImplementedError


class UltraShortTermStrategy(StrategyBase):
    """
    Ultra-short-term strategy base class
    
    [Rules]
    - Market: Shanghai/Shenzhen main board
    - Style: Ultra-short-term (1-5 days)
    - Operation: Full position in/out
    """
    
    def __init__(
        self,
        name: str,
        max_holding_days: int = 5,
        stop_loss_pct: float = -0.05,
        take_profit_pct: float = 0.10
    ):
        super().__init__(name)
        self.max_holding_days = max_holding_days
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct


class EnhancedBacktester:
    """
    Enhanced Backtester
    
    [Features]
    - Ultra-short-term full-position backtesting
    - Detailed performance metrics
    - Drawdown analysis
    - Consecutive win/loss tracking
    """
    
    def __init__(
        self,
        initial_capital: float = 100000.0,
        commission_rate: float = 0.0003,
        slippage_pct: float = 0.001
    ):
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.slippage_pct = slippage_pct
    
    def run(
        self,
        df: pd.DataFrame,
        strategy: StrategyBase
    ) -> BacktestResult:
        """
        Run backtest
        
        Args:
            df: OHLCV DataFrame with trade_date
            strategy: Trading strategy
            
        Returns:
            BacktestResult
        """
        if df is None or len(df) < 30:
            raise ValueError("Insufficient data")
        
        df = df.copy().sort_values('trade_date').reset_index(drop=True)
        
        capital = self.initial_capital
        position = 0
        entry_price = 0.0
        entry_idx = -1
        entry_date = ''
        shares = 0
        
        trades = []
        equity = [capital]
        dates = [df['trade_date'].iloc[0]]
        
        consecutive_wins = 0
        consecutive_losses = 0
        max_consecutive_wins = 0
        max_consecutive_losses = 0
        
        for idx in range(1, len(df)):
            current_date = df['trade_date'].iloc[idx]
            current_close = df['close'].iloc[idx]
            current_open = df['open'].iloc[idx]
            
            if position == 0:
                if strategy.should_buy(df, idx):
                    entry_idx = idx
                    entry_date = current_date
                    
                    buy_price = current_open * (1 + self.slippage_pct)
                    
                    commission = capital * self.commission_rate
                    available_capital = capital - commission
                    shares = int(available_capital / buy_price / 100) * 100
                    
                    if shares > 0:
                        entry_price = buy_price
                        position = shares
                        capital -= shares * buy_price + shares * buy_price * self.commission_rate
                        
                        logger.debug(f"BUY: {current_date} @ {buy_price:.2f}, {shares} shares")
            
            elif position > 0:
                holding_days = idx - entry_idx
                current_pnl_pct = (current_close - entry_price) / entry_price
                
                should_exit = False
                
                if strategy.should_sell(df, idx, entry_idx):
                    should_exit = True
                elif hasattr(strategy, 'max_holding_days') and holding_days >= strategy.max_holding_days:
                    should_exit = True
                elif hasattr(strategy, 'stop_loss_pct') and current_pnl_pct <= strategy.stop_loss_pct:
                    should_exit = True
                elif hasattr(strategy, 'take_profit_pct') and current_pnl_pct >= strategy.take_profit_pct:
                    should_exit = True
                
                if should_exit:
                    sell_price = current_open * (1 - self.slippage_pct)
                    
                    proceeds = shares * sell_price
                    commission = proceeds * self.commission_rate
                    
                    pnl = proceeds - commission - position * entry_price
                    pnl_pct = (sell_price - entry_price) / entry_price
                    
                    trade = Trade(
                        entry_date=entry_date,
                        entry_price=entry_price,
                        exit_date=current_date,
                        exit_price=sell_price,
                        shares=shares,
                        direction='long',
                        pnl=pnl,
                        pnl_pct=pnl_pct,
                        holding_days=holding_days
                    )
                    trades.append(trade)
                    
                    capital += proceeds - commission
                    
                    if pnl > 0:
                        consecutive_wins += 1
                        consecutive_losses = 0
                        max_consecutive_wins = max(max_consecutive_wins, consecutive_wins)
                    else:
                        consecutive_losses += 1
                        consecutive_wins = 0
                        max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)
                    
                    logger.debug(f"SELL: {current_date} @ {sell_price:.2f}, PnL: {pnl_pct:.2%}")
                    
                    position = 0
                    shares = 0
                    entry_price = 0
                    entry_idx = -1
            
            current_equity = capital + position * current_close
            equity.append(current_equity)
            dates.append(current_date)
        
        if position > 0:
            final_close = df['close'].iloc[-1]
            final_date = df['trade_date'].iloc[-1]
            
            sell_price = final_close
            proceeds = shares * sell_price
            commission = proceeds * self.commission_rate
            
            pnl = proceeds - commission - position * entry_price
            pnl_pct = (sell_price - entry_price) / entry_price
            holding_days = len(df) - 1 - entry_idx
            
            trade = Trade(
                entry_date=entry_date,
                entry_price=entry_price,
                exit_date=final_date,
                exit_price=sell_price,
                shares=shares,
                direction='long',
                pnl=pnl,
                pnl_pct=pnl_pct,
                holding_days=holding_days
            )
            trades.append(trade)
            
            capital += proceeds - commission
            equity[-1] = capital
        
        equity_curve = pd.Series(equity, index=dates)
        drawdown_curve = self._calculate_drawdown(equity_curve)
        
        result = self._calculate_metrics(
            trades=trades,
            equity_curve=equity_curve,
            drawdown_curve=drawdown_curve,
            initial_capital=self.initial_capital,
            max_consecutive_wins=max_consecutive_wins,
            max_consecutive_losses=max_consecutive_losses
        )
        
        return result
    
    def _calculate_drawdown(self, equity_curve: pd.Series) -> pd.Series:
        """Calculate drawdown curve"""
        running_max = equity_curve.expanding().max()
        drawdown = (equity_curve - running_max) / running_max
        return drawdown
    
    def _calculate_metrics(
        self,
        trades: List[Trade],
        equity_curve: pd.Series,
        drawdown_curve: pd.Series,
        initial_capital: float,
        max_consecutive_wins: int,
        max_consecutive_losses: int
    ) -> BacktestResult:
        """Calculate performance metrics"""
        total_trades = len(trades)
        
        if total_trades == 0:
            return BacktestResult(
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0.0,
                total_return=0.0,
                annual_return=0.0,
                total_pnl=0.0,
                avg_profit_per_trade=0.0,
                avg_profit_per_win=0.0,
                avg_loss_per_loss=0.0,
                profit_loss_ratio=0.0,
                max_drawdown=0.0,
                max_drawdown_duration=0,
                consecutive_wins=0,
                consecutive_losses=0,
                max_consecutive_wins=0,
                max_consecutive_losses=0,
                sharpe_ratio=0.0,
                sortino_ratio=0.0,
                calmar_ratio=0.0,
                trades=trades,
                equity_curve=equity_curve,
                drawdown_curve=drawdown_curve
            )
        
        winning_trades = [t for t in trades if t.pnl > 0]
        losing_trades = [t for t in trades if t.pnl <= 0]
        
        win_rate = len(winning_trades) / total_trades
        
        total_pnl = sum(t.pnl for t in trades)
        total_return = total_pnl / initial_capital
        
        days = len(equity_curve)
        annual_return = (1 + total_return) ** (252 / days) - 1 if days > 0 else 0
        
        avg_profit_per_trade = total_pnl / total_trades
        avg_profit_per_win = sum(t.pnl for t in winning_trades) / len(winning_trades) if winning_trades else 0
        avg_loss_per_loss = sum(t.pnl for t in losing_trades) / len(losing_trades) if losing_trades else 0
        profit_loss_ratio = abs(avg_profit_per_win / avg_loss_per_loss) if avg_loss_per_loss != 0 else float('inf')
        
        max_drawdown = drawdown_curve.min()
        
        drawdown_duration = 0
        max_drawdown_duration = 0
        in_drawdown = False
        
        for dd in drawdown_curve:
            if dd < 0:
                if not in_drawdown:
                    in_drawdown = True
                    drawdown_duration = 1
                else:
                    drawdown_duration += 1
                max_drawdown_duration = max(max_drawdown_duration, drawdown_duration)
            else:
                in_drawdown = False
                drawdown_duration = 0
        
        daily_returns = equity_curve.pct_change().dropna()
        
        sharpe_ratio = np.sqrt(252) * daily_returns.mean() / daily_returns.std() if daily_returns.std() != 0 else 0
        
        downside_returns = daily_returns[daily_returns < 0]
        sortino_ratio = np.sqrt(252) * daily_returns.mean() / downside_returns.std() if len(downside_returns) > 0 and downside_returns.std() != 0 else 0
        
        calmar_ratio = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0
        
        consecutive_wins = 0
        consecutive_losses = 0
        
        for trade in trades:
            if trade.pnl > 0:
                consecutive_wins += 1
                consecutive_losses = 0
            else:
                consecutive_losses += 1
                consecutive_wins = 0
        
        return BacktestResult(
            total_trades=total_trades,
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            win_rate=win_rate,
            total_return=total_return,
            annual_return=annual_return,
            total_pnl=total_pnl,
            avg_profit_per_trade=avg_profit_per_trade,
            avg_profit_per_win=avg_profit_per_win,
            avg_loss_per_loss=avg_loss_per_loss,
            profit_loss_ratio=profit_loss_ratio,
            max_drawdown=max_drawdown,
            max_drawdown_duration=max_drawdown_duration,
            consecutive_wins=consecutive_wins,
            consecutive_losses=consecutive_losses,
            max_consecutive_wins=max_consecutive_wins,
            max_consecutive_losses=max_consecutive_losses,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            calmar_ratio=calmar_ratio,
            trades=trades,
            equity_curve=equity_curve,
            drawdown_curve=drawdown_curve
        )
    
    def print_report(self, result: BacktestResult):
        """Print formatted backtest report"""
        print("\n" + "=" * 80)
        print("BACKTEST REPORT")
        print("=" * 80)
        
        print(f"\nTrading Statistics:")
        print(f"  Total Trades: {result.total_trades}")
        print(f"  Winning Trades: {result.winning_trades}")
        print(f"  Losing Trades: {result.losing_trades}")
        print(f"  Win Rate: {result.win_rate:.2%}")
        
        print(f"\nReturn Metrics:")
        print(f"  Total Return: {result.total_return:.2%}")
        print(f"  Annual Return: {result.annual_return:.2%}")
        print(f"  Total PnL: ¥{result.total_pnl:.2f}")
        
        print(f"\nProfit/Loss Analysis:")
        print(f"  Avg Profit per Trade: ¥{result.avg_profit_per_trade:.2f}")
        print(f"  Avg Profit per Win: ¥{result.avg_profit_per_win:.2f}")
        print(f"  Avg Loss per Loss: ¥{result.avg_loss_per_loss:.2f}")
        print(f"  Profit/Loss Ratio: {result.profit_loss_ratio:.2f}")
        
        print(f"\nRisk Metrics:")
        print(f"  Max Drawdown: {result.max_drawdown:.2%}")
        print(f"  Max Drawdown Duration: {result.max_drawdown_duration} days")
        print(f"  Sharpe Ratio: {result.sharpe_ratio:.2f}")
        print(f"  Sortino Ratio: {result.sortino_ratio:.2f}")
        print(f"  Calmar Ratio: {result.calmar_ratio:.2f}")
        
        print(f"\nConsecutive Stats:")
        print(f"  Max Consecutive Wins: {result.max_consecutive_wins}")
        print(f"  Max Consecutive Losses: {result.max_consecutive_losses}")
        
        print("\n" + "=" * 80)


def get_enhanced_backtester(
    initial_capital: float = 100000.0,
    commission_rate: float = 0.0003,
    slippage_pct: float = 0.001
) -> EnhancedBacktester:
    """Get enhanced backtester instance"""
    return EnhancedBacktester(initial_capital, commission_rate, slippage_pct)


if __name__ == '__main__':
    backtester = get_enhanced_backtester()
    print("Enhanced Backtester module loaded")
