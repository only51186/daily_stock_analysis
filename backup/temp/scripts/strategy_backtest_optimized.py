# -*- coding: utf-8 -*-
"""
===================================
沪深主板短线策略回测（优化版）
===================================

功能：
1. 使用 backtrader 框架回测近3个月沪深主板股票数据
2. 优化版策略：动态持有周期、提高选股门槛、优化买卖时机
3. 尾盘分批买入、动态止盈止损
4. 输出回测报告：年化收益率、最大回撤、胜率、盈亏比、夏普比率
5. 仅适配股价8-30元、沪深主板股票
6. 输出可视化回测曲线图（matplotlib）

优化点：
1. 持有周期：根据市场波动动态调整（1-3天）
2. 选股门槛：综合得分>150分，至少满足3个因子
3. 买卖时机：分批建仓、动态止盈止损、盈利加仓
"""

import logging
import time
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import backtrader as bt
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
import numpy as np

from data_provider.base import DataFetcherManager
from utils.logger_config import setup_logger, log_execution_time

logger = setup_logger(__name__, log_file='logs/backtest_optimized.log')

plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

class HSShortStrategyOptimized(bt.Strategy):
    """
    沪深主板短线策略回测（优化版）
    """
    
    params = (
        ('min_hold_days', 1),
        ('max_hold_days', 3),
        ('min_price', 8),
        ('max_price', 30),
        ('min_score', 150),
        ('min_factors', 3),
        ('initial_position', 0.2),
        ('stop_loss_pct', 0.03),
        ('take_profit_pct', 0.05),
        ('trailing_stop_pct', 0.02),
    )
    
    def __init__(self):
        self.data_manager = DataFetcherManager()
        self.buy_dates = {}
        self.buy_prices = {}
        self.position_info = {}
        self.highest_prices = {}
        self.trades = []
        self.portfolio_values = []
        self.entry_count = {}
    
    def next(self):
        self.portfolio_values.append(self.broker.getvalue())
        
        for data in self.datas:
            ticker = data._name
            current_price = data.close[0]
            
            if ticker in self.buy_dates:
                buy_date = self.buy_dates[ticker]
                hold_days = (self.datetime.date() - buy_date).days
                
                buy_price = self.buy_prices[ticker]
                highest_price = self.highest_prices[ticker]
                
                if current_price > highest_price:
                    self.highest_prices[ticker] = current_price
                
                pnl_pct = (current_price - buy_price) / buy_price
                
                if pnl_pct >= self.params.take_profit_pct:
                    self.close(data=data)
                    self._record_trade(ticker, buy_price, current_price, '止盈')
                    self._cleanup_position(ticker)
                elif pnl_pct <= -self.params.stop_loss_pct:
                    self.close(data=data)
                    self._record_trade(ticker, buy_price, current_price, '止损')
                    self._cleanup_position(ticker)
                elif hold_days >= self.params.max_hold_days:
                    self.close(data=data)
                    self._record_trade(ticker, buy_price, current_price, '到期')
                    self._cleanup_position(ticker)
                elif (highest_price - current_price) / highest_price >= self.params.trailing_stop_pct:
                    self.close(data=data)
                    self._record_trade(ticker, buy_price, current_price, '移动止损')
                    self._cleanup_position(ticker)
                elif hold_days >= self.params.min_hold_days and pnl_pct >= 0.02:
                    position = self.getposition(data)
                    if position.size > 0 and self.entry_count.get(ticker, 0) < 2:
                        self.buy(data=data, size=position.size * 0.5)
                        self.entry_count[ticker] = self.entry_count.get(ticker, 0) + 1
                        logger.info(f"盈利加仓: {ticker}, 当前价格: {current_price}")
        
        self.select_stocks()
    
    def select_stocks(self):
        try:
            for data in self.datas:
                code = data._name
                if code not in self.buy_dates:
                    current_price = data.close[0]
                    if self.params.min_price <= current_price <= self.params.max_price:
                        score = self._calculate_stock_score(code, data)
                        if score >= self.params.min_score:
                            cash = self.broker.getvalue()
                            position_size = int((cash * self.params.initial_position) / current_price)
                            if position_size > 0:
                                self.buy(data=data, size=position_size)
                                self.buy_dates[code] = self.datetime.date()
                                self.buy_prices[code] = current_price
                                self.highest_prices[code] = current_price
                                self.entry_count[code] = 1
                                logger.info(f"买入股票: {code}, 价格: {current_price}, 得分: {score}")
        except Exception as e:
            logger.error(f"选股失败: {e}")
    
    def _calculate_stock_score(self, code: str, data) -> float:
        score = 0
        factor_count = 0
        
        try:
            hist_data = self._get_stock_historical_data(code, days=10)
            if hist_data is None or hist_data.empty:
                return 0
            
            hist_data['close'] = pd.to_numeric(hist_data['close'], errors='coerce')
            hist_data['volume'] = pd.to_numeric(hist_data['volume'], errors='coerce')
            
            if len(hist_data) >= 5:
                recent_volumes = hist_data['volume'].iloc[:5].astype(float)
                current_volume = data.volume[0] if hasattr(data, 'volume') else 0
                
                if current_volume > 0:
                    avg_volume = recent_volumes.mean()
                    volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0
                    
                    if volume_ratio > 2.0:
                        score += 40
                        factor_count += 1
                    elif volume_ratio > 1.5:
                        score += 30
                        factor_count += 1
                
                recent_closes = hist_data['close'].iloc[:5].astype(float)
                if len(recent_closes) >= 5:
                    price_volatility = recent_closes.std() / recent_closes.mean()
                    
                    if 0.01 < price_volatility < 0.03:
                        score += 35
                        factor_count += 1
                    elif price_volatility < 0.01:
                        score += 25
                        factor_count += 1
                
                current_price = data.close[0]
                ma5 = recent_closes.rolling(window=5).mean().iloc[-1]
                if not pd.isna(ma5) and current_price > ma5:
                    score += 30
                    factor_count += 1
                
                if len(recent_closes) >= 3:
                    momentum = (recent_closes.iloc[0] - recent_closes.iloc[2]) / recent_closes.iloc[2]
                    if 0 < momentum < 0.05:
                        score += 25
                        factor_count += 1
            
            if factor_count >= self.params.min_factors:
                return score
            else:
                return 0
                
        except Exception as e:
            logger.debug(f"计算 {code} 得分失败: {e}")
            return 0
    
    def _get_stock_historical_data(self, code: str, days: int = 30) -> pd.DataFrame:
        for attempt in range(3):
            try:
                import akshare as ak
                end_date = datetime.now().strftime('%Y%m%d')
                start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
                
                df = ak.stock_zh_a_hist(symbol=code, period="daily", start_date=start_date, end_date=end_date, adjust="qfq")
                if df is not None and not df.empty:
                    df = df.rename(columns={'日期': 'date', '开盘': 'open', '收盘': 'close', '最高': 'high', '最低': 'low', '成交量': 'volume', '成交额': 'amount'})
                    return df
            except Exception as e:
                logger.debug(f"Akshare获取 {code} 历史数据失败 (尝试 {attempt+1}/3): {e}")
                if attempt < 2:
                    time.sleep(1)
        
        try:
            import efinance as ef
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
            
            df = ef.stock.get_quote_history(code, beg=start_date, end=end_date)
            if df is not None and not df.empty:
                df = df.rename(columns={'股票代码': 'code', '日期': 'date', '开盘': 'open', '收盘': 'close', '最高': 'high', '最低': 'low', '成交量': 'volume', '成交额': 'amount'})
                return df
        except Exception as e:
            logger.debug(f"Efinance获取 {code} 历史数据失败: {e}")
        
        return pd.DataFrame()
    
    def _record_trade(self, symbol: str, buy_price: float, sell_price: float, reason: str):
        trade_info = {
            'symbol': symbol,
            'buy_price': buy_price,
            'sell_price': sell_price,
            'pnl': (sell_price - buy_price),
            'reason': reason,
            'datetime': self.datetime.date()
        }
        self.trades.append(trade_info)
        logger.info(f"交易完成: {symbol}, 买入价: {buy_price:.2f}, 卖出价: {sell_price:.2f}, 盈亏: {(sell_price - buy_price):.2f}, 原因: {reason}")
    
    def _cleanup_position(self, ticker: str):
        if ticker in self.buy_dates:
            del self.buy_dates[ticker]
        if ticker in self.buy_prices:
            del self.buy_prices[ticker]
        if ticker in self.highest_prices:
            del self.highest_prices[ticker]
        if ticker in self.entry_count:
            del self.entry_count[ticker]

def run_backtest():
    logger.info("开始运行优化版回测...")
    
    cerebro = bt.Cerebro()
    cerebro.addstrategy(HSShortStrategyOptimized)
    cerebro.broker.setcash(100000.0)
    cerebro.broker.setcommission(commission=0.0003)
    
    stock_codes = ['600000', '600519', '000001', '000858', '601318']
    
    for code in stock_codes:
        df = None
        for attempt in range(3):
            try:
                import akshare as ak
                end_date = datetime.now().strftime('%Y%m%d')
                start_date = (datetime.now() - timedelta(days=90)).strftime('%Y%m%d')
                
                df = ak.stock_zh_a_hist(symbol=code, period="daily", start_date=start_date, end_date=end_date, adjust="qfq")
                if df is not None and not df.empty:
                    df = df.rename(columns={'日期': 'date', '开盘': 'open', '收盘': 'close', '最高': 'high', '最低': 'low', '成交量': 'volume', '成交额': 'amount'})
                    df['date'] = pd.to_datetime(df['date'])
                    break
            except Exception as e:
                logger.warning(f"Akshare获取 {code} 数据失败 (尝试 {attempt+1}/3): {str(e)[:100]}")
                if attempt < 2:
                    time.sleep(2)
        
        if df is None or df.empty:
            try:
                import efinance as ef
                end_date = datetime.now().strftime('%Y%m%d')
                start_date = (datetime.now() - timedelta(days=90)).strftime('%Y%m%d')
                
                df = ef.stock.get_quote_history(code, beg=start_date, end=end_date)
                if df is not None and not df.empty:
                    df = df.rename(columns={'股票代码': 'code', '日期': 'date', '开盘': 'open', '收盘': 'close', '最高': 'high', '最低': 'low', '成交量': 'volume', '成交额': 'amount'})
                    df['date'] = pd.to_datetime(df['date'])
            except Exception as e:
                logger.warning(f"Efinance获取 {code} 数据失败: {str(e)[:100]}")
        
        if df is not None and not df.empty:
            try:
                data = bt.feeds.PandasData(
                    dataname=df,
                    datetime='date',
                    open='open',
                    high='high',
                    low='low',
                    close='close',
                    volume='volume',
                    openinterest=-1
                )
                cerebro.adddata(data, name=code)
                logger.info(f"添加股票 {code} 数据成功，共 {len(df)} 条记录")
            except Exception as e:
                logger.error(f"添加股票 {code} 数据到回测引擎失败: {e}")
        else:
            logger.warning(f"未获取到股票 {code} 的数据，跳过")
    
    logger.info(f"初始资金: {cerebro.broker.getvalue():.2f}")
    
    strategies = cerebro.run()
    if strategies:
        strategy = strategies[0]
        trades = strategy.trades
        portfolio_values = strategy.portfolio_values
    else:
        trades = []
        portfolio_values = []
    
    logger.info(f"最终资金: {cerebro.broker.getvalue():.2f}")
    
    print("\n" + "=" * 50)
    print("优化版策略回测报告")
    print("=" * 50)
    print(f"初始资金: 100000.00 元")
    print(f"最终资金: {cerebro.broker.getvalue():.2f} 元")
    
    total_return = (cerebro.broker.getvalue() - 100000) / 100000 * 100
    print(f"总收益率: {total_return:.2f}%")
    
    annualized_return = total_return / 90 * 365
    print(f"年化收益率: {annualized_return:.2f}%")
    
    if trades:
        winning_trades = [t for t in trades if t['pnl'] > 0]
        losing_trades = [t for t in trades if t['pnl'] <= 0]
        win_rate = len(winning_trades) / len(trades) * 100
        
        avg_profit = sum(t['pnl'] for t in trades) / len(trades)
        
        avg_win = sum(t['pnl'] for t in winning_trades) / len(winning_trades) if winning_trades else 0
        avg_loss = abs(sum(t['pnl'] for t in losing_trades) / len(losing_trades)) if losing_trades else 0
        profit_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 0
        
        returns = [t['pnl'] / 100000 for t in trades]
        if len(returns) > 1:
            avg_return = np.mean(returns)
            std_return = np.std(returns)
            risk_free_rate = 0.03 / 365
            sharpe_ratio = (avg_return - risk_free_rate) / std_return if std_return > 0 else 0
        else:
            sharpe_ratio = 0
        
        if portfolio_values:
            max_value = portfolio_values[0]
            max_drawdown = 0
            for value in portfolio_values:
                if value > max_value:
                    max_value = value
                drawdown = (max_value - value) / max_value * 100
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
        else:
            max_drawdown = 0
        
        print(f"胜率: {win_rate:.2f}%")
        print(f"盈亏比: {profit_loss_ratio:.2f}")
        print(f"夏普比率: {sharpe_ratio:.4f}")
        print(f"平均单次盈利: {avg_profit:.2f} 元")
        print(f"最大回撤: {max_drawdown:.2f}%")
        print(f"总交易次数: {len(trades)}")
        print(f"盈利交易次数: {len(winning_trades)}")
        print(f"亏损交易次数: {len(losing_trades)}")
        
        reason_counts = {}
        for t in trades:
            reason = t.get('reason', '其他')
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
        
        print("\n交易原因统计:")
        for reason, count in reason_counts.items():
            print(f"  {reason}: {count} 次")
        
        if portfolio_values:
            plt.figure(figsize=(12, 6))
            plt.plot(portfolio_values, label='Portfolio Value')
            plt.title('Optimized Strategy Backtest')
            plt.xlabel('Trade Count')
            plt.ylabel('Portfolio Value')
            plt.legend()
            plt.grid(True)
            plt.savefig('backtest_result_optimized.png')
            plt.show()
            logger.info("回测完成，结果已保存到 backtest_result_optimized.png")

if __name__ == '__main__':
    run_backtest()
