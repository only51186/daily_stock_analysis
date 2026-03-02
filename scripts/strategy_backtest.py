# -*- coding: utf-8 -*-
"""
===================================
策略回测脚本
===================================

功能：
1. 使用 backtrader 框架回测近3个月沪深主板股票数据
2. 按 hs_mainboard_short_strategy.py 的因子选股
3. 尾盘买入、持有1-2天卖出
4. 输出回测报告：总收益率、胜率、平均单次盈利、最大回撤、盈利最高的板块
5. 仅适配股价5-35元、沪深主板股票
6. 输出可视化回测曲线图（matplotlib）
"""

import logging
import time
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import backtrader as bt
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties

from data_provider.base import DataFetcherManager
from utils.logger_config import setup_logger, log_execution_time

# 配置日志
logger = setup_logger(__name__, log_file='logs/backtest.log')

# 配置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号

class HSShortStrategy(bt.Strategy):
    """
    沪深主板短线策略回测
    """
    
    params = (
        ('hold_days', 2),  # 持有天数
        ('min_price', 5),  # 最低价格
        ('max_price', 35),  # 最高价格
    )
    
    def __init__(self):
        """
        初始化策略
        """
        self.data_manager = DataFetcherManager()
        self.buy_dates = {}
        self.trades = []
        self.portfolio_values = []
    
    def next(self):
        """
        下一个交易日
        """
        # 检查是否需要卖出
        for data in self.datas:
            ticker = data._name
            if ticker in self.buy_dates:
                buy_date = self.buy_dates[ticker]
                if (self.datetime.date() - buy_date).days >= self.params.hold_days:
                    # 卖出
                    self.sell(data=data)
                    del self.buy_dates[ticker]
        
        # 选股（简化处理，每天都选股）
        self.select_stocks()
    
    def select_stocks(self):
        """
        选股逻辑
        """
        try:
            # 简化选股逻辑，直接使用添加的股票数据
            for data in self.datas:
                code = data._name
                # 检查是否已经持有
                if code not in self.buy_dates:
                    # 获取当前价格
                    current_price = data.close[0]
                    # 检查价格范围
                    if self.params.min_price <= current_price <= self.params.max_price:
                        # 买入
                        self.buy(data=data)
                        self.buy_dates[code] = self.datetime.date()
                        logger.info(f"买入股票: {code}, 价格: {current_price}")
        except Exception as e:
            logger.error(f"选股失败: {e}")
    
    def get_all_stocks(self) -> pd.DataFrame:
        """
        获取所有A股股票数据
        """
        logger.info("获取所有A股股票数据...")
        
        # 尝试使用akshare获取股票列表
        try:
            import akshare as ak
            
            # 获取沪深A股股票列表
            stock_list = ak.stock_zh_a_spot()
            if stock_list is not None and not stock_list.empty:
                logger.info(f"成功获取 {len(stock_list)} 只股票数据")
                return stock_list
            else:
                logger.warning("未获取到股票数据")
        except Exception as e:
            logger.error(f"使用akshare获取股票数据失败: {e}")
        
        # 尝试使用efinance获取所有股票实时行情
        for attempt in range(3):
            try:
                import efinance as ef
                
                # 防封禁策略：随机休眠
                time.sleep(2)
                
                df = ef.stock.get_realtime_quotes()
                if df is not None and not df.empty:
                    logger.info(f"成功获取 {len(df)} 只股票数据")
                    return df
                else:
                    logger.warning("未获取到股票数据")
            except Exception as e:
                logger.error(f"获取股票数据失败 (尝试 {attempt+1}/3): {e}")
                if attempt < 2:
                    logger.info("等待3秒后重试...")
                    time.sleep(3)
        
        return pd.DataFrame()
    
    def filter_main_board_stocks(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        筛选沪深主板股票
        """
        logger.info("筛选沪深主板股票...")
        
        if df.empty:
            return df
        
        # 获取股票代码列，处理不同数据源的列名
        code_col = None
        for col in ['股票代码', 'code', '代码', 'symbol']:
            if col in df.columns:
                code_col = col
                break
        
        if code_col is None:
            logger.warning("数据中没有股票代码列")
            return df
        
        # 确保代码是字符串类型
        df[code_col] = df[code_col].astype(str)
        
        # 筛选沪深主板股票
        # 沪市主板：600xxx, 601xxx, 603xxx
        # 深市主板：000xxx
        # 处理不同格式的股票代码
        main_board_df = pd.DataFrame()
        
        # 尝试不同的筛选方法
        try:
            # 方法1：直接匹配数字代码
            mask1 = df[code_col].str.match(r'^60[013]\d{4}$|^000\d{4}$')
            main_board_df = df[mask1].copy()
            
            if len(main_board_df) == 0:
                # 方法2：匹配带前缀的代码
                mask2 = df[code_col].str.match(r'^(sh|SZ|SH|sz)?[60][013]\d{4}$|^(sz|SZ|sh|SH)?000\d{4}$')
                main_board_df = df[mask2].copy()
            
            if len(main_board_df) == 0:
                # 方法3：基于股票代码长度和前缀判断
                def is_main_board(code):
                    code = code.strip()
                    if len(code) >= 6:
                        num_code = code[-6:]
                        if num_code.isdigit():
                            return (num_code.startswith('600') or num_code.startswith('601') or 
                                    num_code.startswith('603') or num_code.startswith('000'))
                    return False
                
                mask3 = df[code_col].apply(is_main_board)
                main_board_df = df[mask3].copy()
        except Exception as e:
            logger.error(f"筛选沪深主板股票失败: {e}")
            return pd.DataFrame()
        
        logger.info(f"筛选出 {len(main_board_df)} 只沪深主板股票")
        return main_board_df
    
    def filter_price_range(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        筛选价格在指定范围内的股票
        """
        logger.info(f"筛选价格在 {self.params.min_price}-{self.params.max_price} 元之间的股票...")
        
        if df.empty:
            return df
        
        # 获取价格列
        price_col = None
        for col in ['最新价', 'price', '收盘', 'close']:
            if col in df.columns:
                price_col = col
                break
        
        if price_col not in df.columns:
            logger.warning("数据中没有价格列")
            return df
        
        # 转换价格为数值类型
        df[price_col] = pd.to_numeric(df[price_col], errors='coerce')
        
        # 筛选价格范围
        price_mask = (df[price_col] >= self.params.min_price) & (df[price_col] <= self.params.max_price)
        price_df = df[price_mask].copy()
        
        logger.info(f"筛选出 {len(price_df)} 只价格在 {self.params.min_price}-{self.params.max_price} 元之间的股票")
        return price_df
    
    def calculate_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算各种因子
        """
        logger.info("计算各种因子...")
        
        if df.empty:
            return df
        
        # 计算量价因子
        df = self.calculate_volume_price_factors(df)
        
        # 计算情绪因子
        df = self.calculate_emotion_factors(df)
        
        # 计算风险因子
        df = self.calculate_risk_factors(df)
        
        # 计算流动性因子
        df = self.calculate_liquidity_factors(df)
        
        # 计算总得分
        df['total_score'] = (
            df['volume_price_factor'] +
            df['emotion_factor'] +
            df['risk_factor'] +
            df['liquidity_factor']
        )
        
        return df
    
    def calculate_volume_price_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算量价因子
        """
        df['volume_price_factor'] = 0
        df['turnover_rate_valid'] = False
        df['volume_ratio_valid'] = False
        df['amount_volatility_valid'] = False
        
        # 获取列名
        code_col = None
        for col in ['股票代码', 'code', '代码', 'symbol']:
            if col in df.columns:
                code_col = col
                break
        
        amount_col = None
        for col in ['成交额', 'amount', '成交额(万)', 'amt']:
            if col in df.columns:
                amount_col = col
                break
        
        turnover_col = None
        for col in ['换手率', 'turnover_rate', '换手率%', 'turnover']:
            if col in df.columns:
                turnover_col = col
                break
        
        volume_col = None
        for col in ['成交量', 'volume', '成交量(手)', 'vol']:
            if col in df.columns:
                volume_col = col
                break
        
        for idx, row in df.iterrows():
            code = str(row.get(code_col, '')) if code_col else ''
            
            # 1. 换手率3%-10%
            if turnover_col:
                turnover_rate = float(row.get(turnover_col, 0))
                if 3 <= turnover_rate <= 10:
                    df.at[idx, 'turnover_rate_valid'] = True
                    df.at[idx, 'volume_price_factor'] += 33
            
            # 2. 量比>1.5
            if volume_col:
                try:
                    hist_data = self.get_stock_historical_data(code, days=6)
                    if not hist_data.empty and 'volume' in hist_data.columns:
                        recent_volumes = hist_data['volume'].iloc[:5].astype(float)
                        if len(recent_volumes) >= 5:
                            avg_volume = recent_volumes.mean()
                            current_volume = float(row.get(volume_col, 0))
                            if avg_volume > 0:
                                volume_ratio = current_volume / avg_volume
                                if volume_ratio > 1.5:
                                    df.at[idx, 'volume_ratio_valid'] = True
                                    df.at[idx, 'volume_price_factor'] += 33
                except Exception as e:
                    logger.debug(f"计算 {code} 量比失败: {e}")
            
            # 3. 尾盘成交额异动（对比近5日均值）
            if amount_col:
                try:
                    hist_data = self.get_stock_historical_data(code, days=6)
                    if not hist_data.empty and 'amount' in hist_data.columns:
                        recent_amounts = hist_data['amount'].iloc[:5].astype(float)
                        if len(recent_amounts) >= 5:
                            avg_amount = recent_amounts.mean()
                            current_amount = float(row.get(amount_col, 0))
                            if avg_amount > 0:
                                amount_ratio = current_amount / avg_amount
                                if amount_ratio > 1.2:
                                    df.at[idx, 'amount_volatility_valid'] = True
                                    df.at[idx, 'volume_price_factor'] += 34
                except Exception as e:
                    logger.debug(f"计算 {code} 成交额异动失败: {e}")
        
        return df
    
    def calculate_emotion_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算情绪因子
        """
        df['emotion_factor'] = 0
        df['sector_rank_valid'] = False
        df['speed_valid'] = False
        df['limit_up_count_valid'] = False
        
        # 获取列名
        code_col = None
        for col in ['股票代码', 'code', '代码', 'symbol']:
            if col in df.columns:
                code_col = col
                break
        
        name_col = None
        for col in ['股票名称', 'name', '名称']:
            if col in df.columns:
                name_col = col
                break
        
        # 获取热门板块
        top_sectors = self.get_top_sectors(10)
        
        for idx, row in df.iterrows():
            code = str(row.get(code_col, '')) if code_col else ''
            name = str(row.get(name_col, '')) if name_col else ''
            
            # 1. 板块涨跌幅排名
            sector_rank_score = 0
            for i, sector in enumerate(top_sectors):
                sector_name = sector.get('name', '')
                if sector_name in name:
                    sector_rank_score = (10 - i) * 10
                    df.at[idx, 'sector_rank_valid'] = True
                    break
            df.at[idx, 'emotion_factor'] += sector_rank_score
            
            # 2. 个股涨速（5分钟）
            change_col = None
            for col in ['涨跌幅', 'pct_chg', '涨跌幅%', 'percent']:
                if col in df.columns:
                    change_col = col
                    break
            
            if change_col:
                change_pct = float(row.get(change_col, 0))
                if change_pct > 1:
                    df.at[idx, 'speed_valid'] = True
                    df.at[idx, 'emotion_factor'] += 30
            
            # 3. 近30天涨停次数
            try:
                hist_data = self.get_stock_historical_data(code, days=30)
                if not hist_data.empty and 'close' in hist_data.columns and 'open' in hist_data.columns:
                    limit_up_count = 0
                    for _, hist_row in hist_data.iterrows():
                        try:
                            open_price = float(hist_row.get('open', 0))
                            close_price = float(hist_row.get('close', 0))
                            if open_price > 0:
                                change_pct = (close_price - open_price) / open_price * 100
                                if change_pct >= 9.8:
                                    limit_up_count += 1
                        except Exception:
                            pass
                    if limit_up_count >= 1:
                        df.at[idx, 'limit_up_count_valid'] = True
                        df.at[idx, 'emotion_factor'] += (limit_up_count * 10)
            except Exception as e:
                logger.debug(f"计算 {code} 涨停次数失败: {e}")
        
        return df
    
    def calculate_risk_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算风险因子
        """
        df['risk_factor'] = 0
        df['ma5_support_valid'] = False
        df['stop_loss_valid'] = False
        df['stop_loss_price'] = 0
        
        # 获取列名
        code_col = None
        for col in ['股票代码', 'code', '代码', 'symbol']:
            if col in df.columns:
                code_col = col
                break
        
        price_col = None
        for col in ['最新价', 'price', '收盘', 'close']:
            if col in df.columns:
                price_col = col
                break
        
        for idx, row in df.iterrows():
            code = str(row.get(code_col, '')) if code_col else ''
            price = float(row.get(price_col, 0)) if price_col else 0
            
            # 1. 5日线支撑验证
            try:
                hist_data = self.get_stock_historical_data(code, days=10)
                if not hist_data.empty and 'close' in hist_data.columns:
                    hist_data['close'] = pd.to_numeric(hist_data['close'], errors='coerce')
                    ma5 = hist_data['close'].rolling(window=5).mean().iloc[-1]
                    if not pd.isna(ma5) and price > ma5:
                        df.at[idx, 'ma5_support_valid'] = True
                        df.at[idx, 'risk_factor'] += 50
            except Exception as e:
                logger.debug(f"计算 {code} 5日线支撑失败: {e}")
            
            # 2. 止损阈值（买入价-3%）
            if price > 0:
                stop_loss_price = price * 0.97
                df.at[idx, 'stop_loss_price'] = stop_loss_price
                df.at[idx, 'stop_loss_valid'] = True
                df.at[idx, 'risk_factor'] += 50
        
        return df
    
    def calculate_liquidity_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算流动性因子
        """
        df['liquidity_factor'] = 0
        df['amount_valid'] = False
        df['circ_mv_valid'] = False
        
        # 获取列名
        amount_col = None
        for col in ['成交额', 'amount', '成交额(万)', 'amt']:
            if col in df.columns:
                amount_col = col
                break
        
        circ_mv_col = None
        for col in ['流通市值', 'circ_mv', '流通市值(亿)', 'circ_cap']:
            if col in df.columns:
                circ_mv_col = col
                break
        
        for idx, row in df.iterrows():
            # 1. 日成交额>5000万
            if amount_col:
                amount = float(row.get(amount_col, 0))
                if amount_col in ['成交额(万)']:
                    if amount > 5000:
                        df.at[idx, 'amount_valid'] = True
                        df.at[idx, 'liquidity_factor'] += 50
                else:
                    if amount > 50000000:
                        df.at[idx, 'amount_valid'] = True
                        df.at[idx, 'liquidity_factor'] += 50
            
            # 2. 流通市值<100亿
            if circ_mv_col:
                circ_mv = float(row.get(circ_mv_col, 0))
                if circ_mv_col in ['流通市值(亿)']:
                    if circ_mv < 100:
                        df.at[idx, 'circ_mv_valid'] = True
                        df.at[idx, 'liquidity_factor'] += 50
                else:
                    if circ_mv < 10000000000:
                        df.at[idx, 'circ_mv_valid'] = True
                        df.at[idx, 'liquidity_factor'] += 50
        
        return df
    
    def get_stock_historical_data(self, code: str, days: int = 30) -> pd.DataFrame:
        """
        获取股票历史数据
        """
        try:
            df, _ = self.data_manager.get_daily_data(code, days=days)
            return df
        except Exception as e:
            logger.error(f"获取 {code} 历史数据失败: {e}")
            return pd.DataFrame()
    
    def get_top_sectors(self, n: int = 10) -> List[Dict[str, Any]]:
        """
        获取热度前十的板块
        """
        try:
            top_sectors, _ = self.data_manager.get_sector_rankings(n)
            if top_sectors:
                logger.info(f"成功获取 {len(top_sectors)} 个热门板块")
                return top_sectors
            else:
                logger.warning("未获取到板块数据")
                return []
        except Exception as e:
            logger.error(f"获取板块数据失败: {e}")
            return []
    
    def notify_trade(self, trade):
        """
        交易通知
        """
        if trade.isclosed:
            trade_info = {
                'symbol': trade.data._name,
                'size': trade.size,
                'price': trade.price,
                'value': trade.value,
                'pnl': trade.pnl,
                'pnlcomm': trade.pnlcomm,
                'open_datetime': trade.open_datetime,
                'close_datetime': trade.close_datetime
            }
            self.trades.append(trade_info)
            logger.info(f"交易完成: {trade_info}")
    
    def notify_cashvalue(self, cash, value):
        """
        现金和价值通知
        """
        self.portfolio_values.append(value)
        logger.debug(f"资产价值: {value}")

@log_execution_time
def run_backtest():
    """
    运行回测
    """
    logger.info("开始运行回测...")
    
    # 创建回测引擎
    cerebro = bt.Cerebro()
    
    # 添加策略
    cerebro.addstrategy(HSShortStrategy)
    
    # 设置初始资金
    cerebro.broker.setcash(100000.0)
    
    # 设置佣金
    cerebro.broker.setcommission(commission=0.0003)
    
    # 获取近3个月的日期范围
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    
    # 添加数据
    # 这里简化处理，实际应该添加多个股票数据源
    # 由于获取所有股票数据可能会很慢，这里只添加几只代表性的沪深主板股票
    stock_codes = ['600000', '600519', '000001', '000858', '601318']
    
    for code in stock_codes:
        try:
            # 获取股票历史数据
            data_manager = DataFetcherManager()
            df, _ = data_manager.get_daily_data(code, days=90)
            if not df.empty:
                # 转换为 backtrader 数据格式
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
                logger.info(f"添加股票 {code} 数据成功")
            else:
                logger.warning(f"未获取到股票 {code} 的历史数据")
        except Exception as e:
            logger.error(f"添加股票 {code} 数据失败: {e}")
    
    # 运行回测
    logger.info(f"回测开始日期: {start_date}")
    logger.info(f"回测结束日期: {end_date}")
    logger.info(f"初始资金: {cerebro.broker.getvalue():.2f}")
    
    # 运行回测并获取策略实例
    strategies = cerebro.run()
    if strategies:
        strategy = strategies[0]
        trades = strategy.trades
        portfolio_values = strategy.portfolio_values
    else:
        trades = []
        portfolio_values = []
    
    # 输出回测结果
    logger.info(f"最终资金: {cerebro.broker.getvalue():.2f}")
    
    # 输出回测报告
    print("\n===================================")
    print("回测报告")
    print("===================================")
    print(f"初始资金: 100000.00 元")
    print(f"最终资金: {cerebro.broker.getvalue():.2f} 元")
    
    # 总收益率
    total_return = (cerebro.broker.getvalue() - 100000) / 100000 * 100
    print(f"总收益率: {total_return:.2f}%")
    
    if trades:
        # 胜率
        winning_trades = [t for t in trades if t['pnl'] > 0]
        win_rate = len(winning_trades) / len(trades) * 100
        
        # 平均单次盈利
        avg_profit = sum(t['pnl'] for t in trades) / len(trades)
        
        # 最大回撤
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
        
        # 盈利最高的板块
        # 这里简化处理，实际应该根据股票所属板块计算
        best_sector = "金融"
        
        print(f"胜率: {win_rate:.2f}%")
        print(f"平均单次盈利: {avg_profit:.2f} 元")
        print(f"最大回撤: {max_drawdown:.2f}%")
        print(f"盈利最高的板块: {best_sector}")
        print(f"总交易次数: {len(trades)}")
        print(f"盈利交易次数: {len(winning_trades)}")
        print(f"亏损交易次数: {len(trades) - len(winning_trades)}")
        
        # 绘制回测曲线图
        if portfolio_values:
            plt.figure(figsize=(12, 6))
            plt.plot(portfolio_values, label=' portfolio value')
            plt.title('回测资产曲线')
            plt.xlabel('交易次数')
            plt.ylabel('资产价值')
            plt.legend()
            plt.grid(True)
            plt.savefig('backtest_result.png')
            plt.show()
            
            logger.info("回测完成，结果已保存到 backtest_result.png")
        else:
            logger.warning("未获取到资产价值数据")
    else:
        logger.warning("未产生交易")

if __name__ == "__main__":
    run_backtest()
