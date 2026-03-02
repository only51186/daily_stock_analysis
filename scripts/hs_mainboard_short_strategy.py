# -*- coding: utf-8 -*-
"""
===================================
沪深主板短线策略脚本
===================================

功能：
1. 分析A股市场热度前十的板块
2. 筛选符合条件的沪深主板股票
3. 计算量价因子、情绪因子、风险因子和流动性因子
4. 推荐明天上涨概率高的板块和个股
5. 适合超短线持有一两天的操作建议

因子库：
1. 量价因子：尾盘成交额异动（对比近5日均值）、换手率3%-10%、量比>1.5
2. 情绪因子：板块涨跌幅排名、个股涨速（5分钟）、近30天涨停次数
3. 风险因子：5日线支撑验证、止损阈值（买入价-3%）
4. 流动性因子：日成交额>5000万、流通市值<100亿
5. 适配条件：沪深主板、股价5-35元
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

from data_provider.base import DataFetcherManager
from utils.notification_sender import get_notification_sender
from utils.logger_config import setup_logger, log_execution_time, log_error

# 配置日志
logger = setup_logger(__name__, log_file='logs/strategy.log')

class HSShortStrategy:
    """
    沪深主板短线策略
    """
    
    def __init__(self):
        """
        初始化策略
        """
        self.data_manager = DataFetcherManager()
        self.notification_sender = get_notification_sender()
        self.enable_notification = True
    
    @log_execution_time
    def get_top_sectors(self, n: int = 10) -> List[Dict[str, Any]]:
        """
        获取热度前十的板块
        
        Args:
            n: 返回板块数量
            
        Returns:
            板块列表，每个元素包含板块名称和涨跌幅
        """
        logger.info(f"获取热度前{n}的板块...")
        
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
    
    @log_execution_time
    def get_all_stocks(self) -> pd.DataFrame:
        """
        获取所有A股股票数据
        
        Returns:
            包含股票代码、名称、价格等信息的DataFrame
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
        
        # 尝试使用数据提供者管理器获取股票数据
        try:
            logger.info("尝试使用数据提供者管理器获取股票数据...")
            # 这里可以添加使用数据提供者管理器获取股票数据的逻辑
            # 暂时返回空DataFrame
        except Exception as e:
            logger.error(f"使用数据提供者管理器获取股票数据失败: {e}")
        
        # 如果所有方法都失败，返回空DataFrame
        logger.warning("所有获取股票数据的方法都失败了")
        return pd.DataFrame()
    
    def filter_main_board_stocks(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        筛选沪深主板股票
        
        沪深主板股票代码规则：
        - 沪市主板：600xxx, 601xxx, 603xxx
        - 深市主板：000xxx
        
        Args:
            df: 股票数据DataFrame
            
        Returns:
            筛选后的沪深主板股票DataFrame
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
        
        # 打印前几行股票代码，查看格式
        logger.info(f"股票代码列名: {code_col}")
        logger.info(f"前5行股票代码: {df[code_col].head().tolist()}")
        
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
                # 沪市主板：600xxx, 601xxx, 603xxx（6位数字）
                # 深市主板：000xxx（6位数字）
                def is_main_board(code):
                    # 去除前缀
                    code = code.strip()
                    if len(code) >= 6:
                        # 取最后6位数字
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
    
    def filter_price_range(self, df: pd.DataFrame, min_price: float = 5, max_price: float = 35) -> pd.DataFrame:
        """
        筛选价格在指定范围内的股票
        
        Args:
            df: 股票数据DataFrame
            min_price: 最低价格
            max_price: 最高价格
            
        Returns:
            筛选后的股票DataFrame
        """
        logger.info(f"筛选价格在 {min_price}-{max_price} 元之间的股票...")
        
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
        price_mask = (df[price_col] >= min_price) & (df[price_col] <= max_price)
        price_df = df[price_mask].copy()
        
        logger.info(f"筛选出 {len(price_df)} 只价格在 {min_price}-{max_price} 元之间的股票")
        return price_df
    
    def get_stock_historical_data(self, code: str, days: int = 30) -> pd.DataFrame:
        """
        获取股票历史数据
        
        Args:
            code: 股票代码
            days: 获取天数
            
        Returns:
            股票历史数据DataFrame
        """
        try:
            df, _ = self.data_manager.get_daily_data(code, days=days)
            return df
        except Exception as e:
            logger.error(f"获取 {code} 历史数据失败: {e}")
            return pd.DataFrame()
    
    def calculate_volume_price_factors(self, stock_data: pd.DataFrame) -> pd.DataFrame:
        """
        计算量价因子
        
        1. 尾盘成交额异动（对比近5日均值）
        2. 换手率3%-10%
        3. 量比>1.5
        
        Args:
            stock_data: 股票数据DataFrame
            
        Returns:
            包含量价因子的DataFrame
        """
        logger.info("计算量价因子...")
        
        if stock_data.empty:
            return stock_data
        
        # 获取列名
        code_col = None
        for col in ['股票代码', 'code', '代码', 'symbol']:
            if col in stock_data.columns:
                code_col = col
                break
        
        amount_col = None
        for col in ['成交额', 'amount', '成交额(万)', 'amt']:
            if col in stock_data.columns:
                amount_col = col
                break
        
        turnover_col = None
        for col in ['换手率', 'turnover_rate', '换手率%', 'turnover']:
            if col in stock_data.columns:
                turnover_col = col
                break
        
        volume_col = None
        for col in ['成交量', 'volume', '成交量(手)', 'vol']:
            if col in stock_data.columns:
                volume_col = col
                break
        
        # 计算量价因子
        stock_data['volume_price_factor'] = 0
        stock_data['turnover_rate_valid'] = False
        stock_data['volume_ratio_valid'] = False
        stock_data['amount_volatility_valid'] = False
        
        for idx, row in stock_data.iterrows():
            code = str(row.get(code_col, '')) if code_col else ''
            
            # 1. 换手率3%-10%
            if turnover_col:
                turnover_rate = float(row.get(turnover_col, 0))
                if 3 <= turnover_rate <= 10:
                    stock_data.at[idx, 'turnover_rate_valid'] = True
                    stock_data.at[idx, 'volume_price_factor'] += 33
            
            # 2. 量比>1.5
            # 简单计算：当前成交量 / 近5日平均成交量
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
                                    stock_data.at[idx, 'volume_ratio_valid'] = True
                                    stock_data.at[idx, 'volume_price_factor'] += 33
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
                                if amount_ratio > 1.2:  # 成交额放大20%以上
                                    stock_data.at[idx, 'amount_volatility_valid'] = True
                                    stock_data.at[idx, 'volume_price_factor'] += 34
                except Exception as e:
                    logger.debug(f"计算 {code} 成交额异动失败: {e}")
        
        return stock_data
    
    def calculate_emotion_factors(self, stock_data: pd.DataFrame, top_sectors: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        计算情绪因子
        
        1. 板块涨跌幅排名
        2. 个股涨速（5分钟）
        3. 近30天涨停次数
        
        Args:
            stock_data: 股票数据DataFrame
            top_sectors: 热门板块列表
            
        Returns:
            包含情绪因子的DataFrame
        """
        logger.info("计算情绪因子...")
        
        if stock_data.empty:
            return stock_data
        
        # 获取列名
        code_col = None
        for col in ['股票代码', 'code', '代码', 'symbol']:
            if col in stock_data.columns:
                code_col = col
                break
        
        name_col = None
        for col in ['股票名称', 'name', '名称']:
            if col in stock_data.columns:
                name_col = col
                break
        
        # 计算情绪因子
        stock_data['emotion_factor'] = 0
        stock_data['sector_rank_valid'] = False
        stock_data['speed_valid'] = False
        stock_data['limit_up_count_valid'] = False
        
        for idx, row in stock_data.iterrows():
            code = str(row.get(code_col, '')) if code_col else ''
            name = str(row.get(name_col, '')) if name_col else ''
            
            # 1. 板块涨跌幅排名
            # 简单实现：检查股票所属板块是否在热门板块中
            # 实际应用中需要获取股票所属板块
            sector_rank_score = 0
            for i, sector in enumerate(top_sectors):
                sector_name = sector.get('name', '')
                # 简单匹配：如果股票名称包含板块名称，认为属于该板块
                if sector_name in name:
                    sector_rank_score = (10 - i) * 10  # 排名越靠前分数越高
                    stock_data.at[idx, 'sector_rank_valid'] = True
                    break
            stock_data.at[idx, 'emotion_factor'] += sector_rank_score
            
            # 2. 个股涨速（5分钟）
            # 简单实现：使用当前涨跌幅作为近似
            change_col = None
            for col in ['涨跌幅', 'pct_chg', '涨跌幅%', 'percent']:
                if col in stock_data.columns:
                    change_col = col
                    break
            
            if change_col:
                change_pct = float(row.get(change_col, 0))
                if change_pct > 1:  # 5分钟涨速大于1%
                    stock_data.at[idx, 'speed_valid'] = True
                    stock_data.at[idx, 'emotion_factor'] += 30
            
            # 3. 近30天涨停次数
            try:
                hist_data = self.get_stock_historical_data(code, days=30)
                if not hist_data.empty and 'close' in hist_data.columns and 'open' in hist_data.columns:
                    # 简单计算：收盘价大于开盘价9.8%以上认为涨停
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
                    if limit_up_count >= 1:  # 近30天至少有1次涨停
                        stock_data.at[idx, 'limit_up_count_valid'] = True
                        stock_data.at[idx, 'emotion_factor'] += (limit_up_count * 10)
            except Exception as e:
                logger.debug(f"计算 {code} 涨停次数失败: {e}")
        
        return stock_data
    
    def calculate_risk_factors(self, stock_data: pd.DataFrame) -> pd.DataFrame:
        """
        计算风险因子
        
        1. 5日线支撑验证
        2. 止损阈值（买入价-3%）
        
        Args:
            stock_data: 股票数据DataFrame
            
        Returns:
            包含风险因子的DataFrame
        """
        logger.info("计算风险因子...")
        
        if stock_data.empty:
            return stock_data
        
        # 获取列名
        code_col = None
        for col in ['股票代码', 'code', '代码', 'symbol']:
            if col in stock_data.columns:
                code_col = col
                break
        
        price_col = None
        for col in ['最新价', 'price', '收盘', 'close']:
            if col in stock_data.columns:
                price_col = col
                break
        
        # 计算风险因子
        stock_data['risk_factor'] = 0
        stock_data['ma5_support_valid'] = False
        stock_data['stop_loss_valid'] = False
        stock_data['stop_loss_price'] = 0
        
        for idx, row in stock_data.iterrows():
            code = str(row.get(code_col, '')) if code_col else ''
            price = float(row.get(price_col, 0)) if price_col else 0
            
            # 1. 5日线支撑验证
            try:
                hist_data = self.get_stock_historical_data(code, days=10)
                if not hist_data.empty and 'close' in hist_data.columns:
                    # 计算5日均线
                    hist_data['close'] = pd.to_numeric(hist_data['close'], errors='coerce')
                    ma5 = hist_data['close'].rolling(window=5).mean().iloc[-1]
                    if not pd.isna(ma5) and price > ma5:  # 当前价格在5日均线上方
                        stock_data.at[idx, 'ma5_support_valid'] = True
                        stock_data.at[idx, 'risk_factor'] += 50
            except Exception as e:
                logger.debug(f"计算 {code} 5日线支撑失败: {e}")
            
            # 2. 止损阈值（买入价-3%）
            if price > 0:
                stop_loss_price = price * 0.97
                stock_data.at[idx, 'stop_loss_price'] = stop_loss_price
                stock_data.at[idx, 'stop_loss_valid'] = True
                stock_data.at[idx, 'risk_factor'] += 50
        
        return stock_data
    
    def calculate_liquidity_factors(self, stock_data: pd.DataFrame) -> pd.DataFrame:
        """
        计算流动性因子
        
        1. 日成交额>5000万
        2. 流通市值<100亿
        
        Args:
            stock_data: 股票数据DataFrame
            
        Returns:
            包含流动性因子的DataFrame
        """
        logger.info("计算流动性因子...")
        
        if stock_data.empty:
            return stock_data
        
        # 获取列名
        amount_col = None
        for col in ['成交额', 'amount', '成交额(万)', 'amt']:
            if col in stock_data.columns:
                amount_col = col
                break
        
        circ_mv_col = None
        for col in ['流通市值', 'circ_mv', '流通市值(亿)', 'circ_cap']:
            if col in stock_data.columns:
                circ_mv_col = col
                break
        
        # 计算流动性因子
        stock_data['liquidity_factor'] = 0
        stock_data['amount_valid'] = False
        stock_data['circ_mv_valid'] = False
        
        for idx, row in stock_data.iterrows():
            # 1. 日成交额>5000万
            if amount_col:
                amount = float(row.get(amount_col, 0))
                # 处理不同单位
                if amount_col in ['成交额(万)']:
                    if amount > 5000:  # 已经是万单位
                        stock_data.at[idx, 'amount_valid'] = True
                        stock_data.at[idx, 'liquidity_factor'] += 50
                else:
                    if amount > 50000000:  # 转换为元
                        stock_data.at[idx, 'amount_valid'] = True
                        stock_data.at[idx, 'liquidity_factor'] += 50
            
            # 2. 流通市值<100亿
            if circ_mv_col:
                circ_mv = float(row.get(circ_mv_col, 0))
                # 处理不同单位
                if circ_mv_col in ['流通市值(亿)']:
                    if circ_mv < 100:  # 已经是亿单位
                        stock_data.at[idx, 'circ_mv_valid'] = True
                        stock_data.at[idx, 'liquidity_factor'] += 50
                else:
                    if circ_mv < 10000000000:  # 转换为元
                        stock_data.at[idx, 'circ_mv_valid'] = True
                        stock_data.at[idx, 'liquidity_factor'] += 50
        
        return stock_data
    
    def filter_stocks_by_factors(self, stock_data: pd.DataFrame) -> pd.DataFrame:
        """
        根据因子筛选股票
        
        Args:
            stock_data: 包含因子的股票数据DataFrame
            
        Returns:
            筛选后的股票DataFrame
        """
        logger.info("根据因子筛选股票...")
        
        if stock_data.empty:
            return stock_data
        
        # 筛选所有因子都有效的股票
        # 注意：这里使用宽松条件，只要大部分因子有效即可
        mask = (
            (stock_data['turnover_rate_valid'] | stock_data['volume_ratio_valid'] | stock_data['amount_volatility_valid']) &
            (stock_data['sector_rank_valid'] | stock_data['speed_valid'] | stock_data['limit_up_count_valid']) &
            (stock_data['ma5_support_valid'] & stock_data['stop_loss_valid']) &
            (stock_data['amount_valid'] & stock_data['circ_mv_valid'])
        )
        
        filtered_df = stock_data[mask].copy()
        
        logger.info(f"筛选出 {len(filtered_df)} 只符合因子条件的股票")
        return filtered_df
    
    def calculate_total_score(self, stock_data: pd.DataFrame) -> pd.DataFrame:
        """
        计算总得分
        
        Args:
            stock_data: 包含因子的股票数据DataFrame
            
        Returns:
            包含总得分的股票DataFrame
        """
        logger.info("计算总得分...")
        
        if stock_data.empty:
            return stock_data
        
        # 计算总得分
        stock_data['total_score'] = (
            stock_data['volume_price_factor'] +
            stock_data['emotion_factor'] +
            stock_data['risk_factor'] +
            stock_data['liquidity_factor']
        )
        
        # 按总得分排序
        stock_data = stock_data.sort_values('total_score', ascending=False)
        
        return stock_data
    
    def analyze_stocks(self, df: pd.DataFrame, top_sectors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        分析股票，计算各种因子
        
        Args:
            df: 股票数据DataFrame
            top_sectors: 热门板块列表
            
        Returns:
            分析结果列表
        """
        logger.info("分析股票，计算各种因子...")
        
        if df.empty:
            return []
        
        # 计算各种因子
        df = self.calculate_volume_price_factors(df)
        df = self.calculate_emotion_factors(df, top_sectors)
        df = self.calculate_risk_factors(df)
        df = self.calculate_liquidity_factors(df)
        
        # 根据因子筛选股票
        filtered_df = self.filter_stocks_by_factors(df)
        
        # 计算总得分
        scored_df = self.calculate_total_score(filtered_df)
        
        # 转换为结果列表
        results = []
        
        # 获取列名
        code_col = None
        for col in ['股票代码', 'code', '代码', 'symbol']:
            if col in scored_df.columns:
                code_col = col
                break
        
        name_col = None
        for col in ['股票名称', 'name', '名称']:
            if col in scored_df.columns:
                name_col = col
                break
        
        price_col = None
        for col in ['最新价', 'price', '收盘', 'close']:
            if col in scored_df.columns:
                price_col = col
                break
        
        change_col = None
        for col in ['涨跌幅', 'pct_chg', '涨跌幅%', 'percent']:
            if col in scored_df.columns:
                change_col = col
                break
        
        for _, row in scored_df.iterrows():
            code = str(row.get(code_col, '')) if code_col else ''
            name = str(row.get(name_col, '')) if name_col else ''
            price = float(row.get(price_col, 0)) if price_col else 0
            change_pct = float(row.get(change_col, 0)) if change_col else 0
            
            results.append({
                'code': code,
                'name': name,
                'price': price,
                'change_pct': change_pct,
                'total_score': row.get('total_score', 0),
                'volume_price_factor': row.get('volume_price_factor', 0),
                'emotion_factor': row.get('emotion_factor', 0),
                'risk_factor': row.get('risk_factor', 0),
                'liquidity_factor': row.get('liquidity_factor', 0),
                'stop_loss_price': row.get('stop_loss_price', 0),
                'turnover_rate_valid': row.get('turnover_rate_valid', False),
                'volume_ratio_valid': row.get('volume_ratio_valid', False),
                'amount_volatility_valid': row.get('amount_volatility_valid', False),
                'sector_rank_valid': row.get('sector_rank_valid', False),
                'speed_valid': row.get('speed_valid', False),
                'limit_up_count_valid': row.get('limit_up_count_valid', False),
                'ma5_support_valid': row.get('ma5_support_valid', False),
                'stop_loss_valid': row.get('stop_loss_valid', False),
                'amount_valid': row.get('amount_valid', False),
                'circ_mv_valid': row.get('circ_mv_valid', False)
            })
        
        logger.info(f"成功分析 {len(results)} 只股票")
        return results
    
    @log_execution_time
    def run(self):
        """
        执行短线策略流程
        """
        logger.info("开始执行沪深主板短线策略...")
        
        # 1. 获取热度前十的板块
        top_sectors = self.get_top_sectors(10)
        
        # 2. 获取所有A股股票数据
        all_stocks = self.get_all_stocks()
        
        # 3. 筛选沪深主板股票
        main_board_stocks = self.filter_main_board_stocks(all_stocks)
        
        # 4. 筛选价格在5-35元之间的股票
        price_filtered_stocks = self.filter_price_range(main_board_stocks, 5, 35)
        
        # 5. 分析股票，计算各种因子
        analyzed_stocks = self.analyze_stocks(price_filtered_stocks, top_sectors)
        
        # 6. 生成推荐结果
        self.generate_recommendation(top_sectors, analyzed_stocks)
    
    def generate_recommendation(self, top_sectors: List[Dict[str, Any]], analyzed_stocks: List[Dict[str, Any]]):
        """
        生成推荐结果
        
        Args:
            top_sectors: 热门板块列表
            analyzed_stocks: 分析后的股票列表
        """
        logger.info("生成推荐结果...")
        
        # 生成日期
        today = datetime.now().strftime('%Y-%m-%d')
        
        print(f"\n===================================")
        print(f"沪深主板短线策略推荐 ({today})")
        print(f"===================================")
        
        # 输出热门板块
        print(f"\n🔥 热度前十的板块:")
        print(f"{'-' * 60}")
        print(f"{'板块名称':<20} {'涨跌幅':>10} {'推荐指数':>10}")
        print(f"{'-' * 60}")
        
        for i, sector in enumerate(top_sectors, 1):
            name = sector.get('name', '')
            change_pct = sector.get('change_pct', 0)
            # 计算推荐指数（基于涨跌幅）
            recommend_index = min(100, max(0, 50 + change_pct * 5))
            print(f"{i}. {name:<18} {change_pct:>10.2f}% {recommend_index:>10.1f}")
        
        # 输出推荐个股
        print(f"\n📈 推荐可操作个股 (超短线持有1-2天):")
        print(f"{'-' * 150}")
        print(f"{'代码':<10} {'名称':<15} {'价格':>8} {'涨跌幅':>10} {'总得分':>10} {'止损价':>10} {'因子状态':>40}")
        print(f"{'-' * 150}")
        
        # 只输出总得分高于150的股票
        recommended_stocks = [stock for stock in analyzed_stocks if stock['total_score'] > 150][:10]
        
        for i, stock in enumerate(recommended_stocks, 1):
            code = stock['code']
            name = stock['name']
            price = stock['price']
            change_pct = stock['change_pct']
            total_score = stock['total_score']
            stop_loss_price = stock['stop_loss_price']
            
            # 因子状态
            factors = []
            if stock['turnover_rate_valid']: factors.append('换手率')
            if stock['volume_ratio_valid']: factors.append('量比')
            if stock['amount_volatility_valid']: factors.append('成交额异动')
            if stock['sector_rank_valid']: factors.append('板块排名')
            if stock['speed_valid']: factors.append('涨速')
            if stock['limit_up_count_valid']: factors.append('涨停次数')
            if stock['ma5_support_valid']: factors.append('5日线支撑')
            if stock['amount_valid']: factors.append('成交额')
            if stock['circ_mv_valid']: factors.append('流通市值')
            
            factors_str = ','.join(factors)[:40]
            
            print(f"{i}. {code:<8} {name:<15} {price:>8.2f} {change_pct:>10.2f}% {total_score:>10.1f} {stop_loss_price:>10.2f} {factors_str:>40}")
        
        # 输出操作建议
        print(f"\n💡 操作建议:")
        print(f"{'-' * 60}")
        print(f"1. 超短线操作，建议持有1-2天")
        print(f"2. 关注热门板块中的龙头个股")
        print(f"3. 控制仓位，单只股票建议不超过总资金的20%")
        print(f"4. 设置止损位，建议在成本价下方3%左右")
        print(f"5. 密切关注大盘走势，如遇系统性风险及时止损")
        print(f"6. 推荐股票仅供参考，不构成投资建议")
        print(f"{'-' * 60}")
        
        # 7. 发送结果到豆包
        self.send_result_to_doubao(top_sectors, recommended_stocks)
    
    def send_result_to_doubao(self, top_sectors: List[Dict[str, Any]], recommended_stocks: List[Dict[str, Any]]):
        """
        发送结果到豆包
        
        Args:
            top_sectors: 热门板块列表
            recommended_stocks: 推荐个股列表
        """
        if not self.enable_notification:
            logger.info("通知功能已禁用")
            return
        
        try:
            logger.info("开始发送结果到豆包...")
            success = self.notification_sender.send_stock_selection_result(top_sectors, recommended_stocks)
            
            if success:
                logger.info("结果发送成功")
            else:
                logger.warning("结果发送失败")
        except Exception as e:
            logger.error(f"发送结果到豆包时发生错误: {e}")

if __name__ == "__main__":
    strategy = HSShortStrategy()
    strategy.run()
