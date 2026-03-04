# -*- coding: utf-8 -*-
"""
===================================
Master Strategies Backtest & Verification System
===================================

[Features]
1. Backtest all 3 master strategies
2. Generate detailed reports
3. Three-in-one strategy comparison
4. Parameter optimization
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data_layer import get_enhanced_data_manager
from src.backtest_layer import get_enhanced_backtester, BacktestResult
from src.strategies.master_investor_strategies import (
    get_master_strategies,
    get_three_in_one_strategy
)
from utils.trae_memory import get_memory

logger = logging.getLogger(__name__)


class MasterStrategyBacktester:
    """
    Backtester for master investor strategies
    """
    
    def __init__(self, initial_capital: float = 100000.0):
        self.initial_capital = initial_capital
        self.backtester = get_enhanced_backtester(initial_capital=initial_capital)
        self.data_manager = get_enhanced_data_manager()
        self.results: Dict[str, BacktestResult] = {}
        self.memory = get_memory()
    
    def backtest_single_strategy(
        self,
        symbol: str,
        strategy,
        start_date: str = None,
        end_date: str = None
    ) -> Optional[BacktestResult]:
        """
        Backtest single strategy
        
        Args:
            symbol: Stock code
            strategy: Strategy object
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            BacktestResult
        """
        logger.info(f"Backtesting {strategy.name} on {symbol}...")
        
        df, source = self.data_manager.get_stock_data(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date
        )
        
        if df is None or df.empty:
            logger.error(f"No data for {symbol}")
            return None
        
        result = self.backtester.run(df, strategy)
        self.results[strategy.name] = result
        
        logger.info(f"Completed {strategy.name} - Win Rate: {result.win_rate:.2%}, Total Return: {result.total_return:.2%}")
        
        return result
    
    def backtest_all_strategies(
        self,
        symbol: str,
        start_date: str = None,
        end_date: str = None
    ) -> Dict[str, BacktestResult]:
        """
        Backtest all 3 master strategies
        
        Args:
            symbol: Stock code
            start_date: Start date
            end_date: End date
            
        Returns:
            Dict of results
        """
        logger.info("=" * 80)
        logger.info("BACKTESTING ALL 3 MASTER STRATEGIES")
        logger.info("=" * 80)
        
        strategies = get_master_strategies()
        
        for strategy in strategies:
            self.backtest_single_strategy(symbol, strategy, start_date, end_date)
        
        logger.info("\nBacktesting Three-In-One strategy...")
        three_in_one = get_three_in_one_strategy()
        self.backtest_single_strategy(symbol, three_in_one, start_date, end_date)
        
        return self.results
    
    def print_comparison_table(self):
        """Print strategy comparison table"""
        if not self.results:
            print("No results to display")
            return
        
        print("\n" + "=" * 140)
        print("STRATEGY COMPARISON")
        print("=" * 140)
        
        header = f"{'Strategy':<25} {'Win Rate':<12} {'Total Return':<15} {'Annual Return':<15} {'Max DD':<12} {'Sharpe':<10} {'Trades':<10} {'P/L Ratio':<12}"
        print(header)
        print("-" * 140)
        
        for name, result in self.results.items():
            row = (f"{name:<25} "
                   f"{result.win_rate:<12.2%} "
                   f"{result.total_return:<15.2%} "
                   f"{result.annual_return:<15.2%} "
                   f"{result.max_drawdown:<12.2%} "
                   f"{result.sharpe_ratio:<10.2f} "
                   f"{result.total_trades:<10} "
                   f"{result.profit_loss_ratio:<12.2f}")
            print(row)
        
        print("=" * 140)
    
    def get_best_strategy(self, sort_by: str = 'sharpe_ratio') -> Tuple[str, BacktestResult]:
        """Get best performing strategy"""
        if not self.results:
            return None, None
        
        sorted_strategies = sorted(
            self.results.items(),
            key=lambda x: getattr(x[1], sort_by, 0),
            reverse=True
        )
        
        return sorted_strategies[0]
    
    def generate_report(
        self,
        strategy_name: str,
        output_path: str = None
    ) -> str:
        """Generate detailed backtest report"""
        if strategy_name not in self.results:
            return f"No results for {strategy_name}"
        
        result = self.results[strategy_name]
        
        report = []
        report.append("=" * 80)
        report.append(f"BACKTEST REPORT: {strategy_name}")
        report.append("=" * 80)
        report.append("")
        report.append(f"Test Period: 2024.01 - 2026.03")
        report.append(f"Initial Capital: ¥{self.initial_capital:,.2f}")
        report.append("")
        report.append("--- Trading Statistics ---")
        report.append(f"Total Trades: {result.total_trades}")
        report.append(f"Winning Trades: {result.winning_trades}")
        report.append(f"Losing Trades: {result.losing_trades}")
        report.append(f"Win Rate: {result.win_rate:.2%}")
        report.append("")
        report.append("--- Return Metrics ---")
        report.append(f"Total Return: {result.total_return:.2%}")
        report.append(f"Annual Return: {result.annual_return:.2%}")
        report.append(f"Total PnL: ¥{result.total_pnl:,.2f}")
        report.append("")
        report.append("--- Profit/Loss Analysis ---")
        report.append(f"Avg Profit per Trade: ¥{result.avg_profit_per_trade:.2f}")
        report.append(f"Avg Profit per Win: ¥{result.avg_profit_per_win:.2f}")
        report.append(f"Avg Loss per Loss: ¥{result.avg_loss_per_loss:.2f}")
        report.append(f"Profit/Loss Ratio: {result.profit_loss_ratio:.2f}")
        report.append("")
        report.append("--- Risk Metrics ---")
        report.append(f"Max Drawdown: {result.max_drawdown:.2%}")
        report.append(f"Max Drawdown Duration: {result.max_drawdown_duration} days")
        report.append(f"Sharpe Ratio: {result.sharpe_ratio:.2f}")
        report.append(f"Sortino Ratio: {result.sortino_ratio:.2f}")
        report.append(f"Calmar Ratio: {result.calmar_ratio:.2f}")
        report.append("")
        report.append("--- Consecutive Stats ---")
        report.append(f"Max Consecutive Wins: {result.max_consecutive_wins}")
        report.append(f"Max Consecutive Losses: {result.max_consecutive_losses}")
        report.append("=" * 80)
        
        report_text = "\n".join(report)
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report_text)
            logger.info(f"Report saved to {output_path}")
        
        return report_text
    
    def run_complete_verification(
        self,
        symbol: str = '000001.SZ',
        start_date: str = None,
        end_date: str = None
    ) -> Dict[str, Any]:
        """
        Run complete verification process
        
        Args:
            symbol: Stock code
            start_date: Start date
            end_date: End date
            
        Returns:
            Verification results
        """
        if start_date is None:
            start_date = '2024-01-01'
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        logger.info("Starting complete verification...")
        
        self.backtest_all_strategies(symbol, start_date, end_date)
        
        self.print_comparison_table()
        
        best_name, best_result = self.get_best_strategy()
        
        if best_name:
            logger.info(f"\nBest Strategy: {best_name}")
            self.backtester.print_report(best_result)
        
        output_dir = Path(__file__).parent.parent / 'reports'
        output_dir.mkdir(exist_ok=True)
        
        for name in self.results:
            report_path = output_dir / f"{name}_回测报告.md"
            self.generate_report(name, str(report_path))
        
        return {
            'results': self.results,
            'best_strategy': (best_name, best_result)
        }


def get_master_backtester(initial_capital: float = 100000.0) -> MasterStrategyBacktester:
    """Get master strategy backtester instance"""
    return MasterStrategyBacktester(initial_capital)


if __name__ == '__main__':
    print("Master Strategy Backtester loaded")
    
    backtester = get_master_backtester()
    
    print("\nRunning verification on 000001.SZ...")
    backtester.run_complete_verification('000001.SZ')
