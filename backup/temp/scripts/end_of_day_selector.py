# -*- coding: utf-8 -*-
"""
===================================
沪深主板尾盘选股脚本
===================================

功能：
1. 分析A股市场热度前十的板块
2. 筛选热度前50的沪深主板股票
3. 按照股价5-35元进行过滤
4. 推荐明天上涨概率高的板块和个股
5. 适合超短线持有一两天的操作建议
"""

import logging
import time
import sys
import os
from datetime import datetime
from typing import List, Dict, Any

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from data_provider.base import DataFetcherManager
from data_provider.efinance_fetcher import _is_etf_code

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
)
logger = logging.getLogger(__name__)

class EndOfDaySelector:
    """
    尾盘选股器
    """
    
    def __init__(self):
        """
        初始化选股器
        """
        self.data_manager = DataFetcherManager()
    
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
                return pd.DataFrame()
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
                    return pd.DataFrame()
            except Exception as e:
                logger.error(f"获取股票数据失败 (尝试 {attempt+1}/3): {e}")
                if attempt < 2:
                    logger.info("等待3秒后重试...")
                    time.sleep(3)
                else:
                    return pd.DataFrame()
        
        # 尝试使用数据提供者管理器获取股票数据
        try:
            logger.info("尝试使用数据提供者管理器获取股票数据...")
            # 这里可以添加使用数据提供者管理器获取股票数据的逻辑
            # 暂时返回空DataFrame
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"使用数据提供者管理器获取股票数据失败: {e}")
            return pd.DataFrame()
    
    def get_main_board_stocks(self) -> pd.DataFrame:
        """
        获取沪深主板股票数据
        
        Returns:
            包含沪深主板股票代码、名称、价格等信息的DataFrame
        """
        logger.info("获取沪深主板股票数据...")
        
        # 先获取所有A股股票
        all_stocks = self.get_all_stocks()
        if all_stocks.empty:
            return pd.DataFrame()
        
        # 获取股票代码列
        code_col = None
        for col in ['股票代码', 'code', '代码', 'symbol']:
            if col in all_stocks.columns:
                code_col = col
                break
        
        if code_col is None:
            logger.warning("数据中没有股票代码列")
            return pd.DataFrame()
        
        # 打印前几行股票代码，查看格式
        logger.info(f"股票代码列名: {code_col}")
        logger.info(f"前5行股票代码: {all_stocks[code_col].head().tolist()}")
        
        # 确保代码是字符串类型
        all_stocks[code_col] = all_stocks[code_col].astype(str)
        
        # 筛选沪深主板股票
        # 沪市主板：600xxx, 601xxx, 603xxx
        # 深市主板：000xxx
        # 处理不同格式的股票代码
        main_board_df = pd.DataFrame()
        
        # 尝试不同的筛选方法
        try:
            # 方法1：直接匹配数字代码
            mask1 = all_stocks[code_col].str.match(r'^60[013]\d{4}$|^000\d{4}$')
            main_board_df = all_stocks[mask1].copy()
            
            if len(main_board_df) == 0:
                # 方法2：匹配带前缀的代码
                mask2 = all_stocks[code_col].str.match(r'^(sh|SZ|SH|sz)?[60][013]\d{4}$|^(sz|SZ|sh|SH)?000\d{4}$')
                main_board_df = all_stocks[mask2].copy()
            
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
                
                mask3 = all_stocks[code_col].apply(is_main_board)
                main_board_df = all_stocks[mask3].copy()
        except Exception as e:
            logger.error(f"筛选沪深主板股票失败: {e}")
            return pd.DataFrame()
        
        logger.info(f"筛选出 {len(main_board_df)} 只沪深主板股票")
        return main_board_df
    
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
        # 处理可能的前缀，如"sh"、"sz"或"sh."、"sz."
        main_board_mask = df[code_col].str.match(r'^(sh|sh\.)?60[013]\d{4}$|^(sz|sz\.)?000\d{4}$')
        main_board_df = df[main_board_mask].copy()
        
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
        price_col = '最新价' if '最新价' in df.columns else 'price'
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
    
    def get_top_stocks(self, df: pd.DataFrame, n: int = 50) -> pd.DataFrame:
        """
        获取热度前50的股票
        
        Args:
            df: 股票数据DataFrame
            n: 返回股票数量
            
        Returns:
            热度前n的股票DataFrame
        """
        logger.info(f"获取热度前{n}的股票...")
        
        if df.empty:
            return df
        
        # 获取涨跌幅列
        change_col = '涨跌幅' if '涨跌幅' in df.columns else 'pct_chg'
        if change_col not in df.columns:
            logger.warning("数据中没有涨跌幅列")
            return df
        
        # 转换涨跌幅为数值类型
        df[change_col] = pd.to_numeric(df[change_col], errors='coerce')
        
        # 按涨跌幅排序，取前n个
        top_df = df.nlargest(n, change_col).copy()
        
        logger.info(f"成功获取 {len(top_df)} 只热门股票")
        return top_df
    
    def analyze_stocks(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        分析股票，计算上涨概率
        
        Args:
            df: 股票数据DataFrame
            
        Returns:
            分析结果列表
        """
        logger.info("分析股票，计算上涨概率...")
        
        if df.empty:
            return []
        
        results = []
        
        # 获取列名，处理不同数据源的列名
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
        
        price_col = None
        for col in ['最新价', 'price', '收盘', 'close']:
            if col in df.columns:
                price_col = col
                break
        
        change_col = None
        for col in ['涨跌幅', 'pct_chg', '涨跌幅%', 'percent']:
            if col in df.columns:
                change_col = col
                break
        
        volume_col = None
        for col in ['成交量', 'volume', '成交量(手)', 'vol']:
            if col in df.columns:
                volume_col = col
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
        
        for _, row in df.iterrows():
            code = str(row.get(code_col, '')) if code_col else ''
            name = str(row.get(name_col, '')) if name_col else ''
            price = float(row.get(price_col, 0)) if price_col else 0
            change_pct = float(row.get(change_col, 0)) if change_col else 0
            volume = float(row.get(volume_col, 0)) if volume_col else 0
            amount = float(row.get(amount_col, 0)) if amount_col else 0
            turnover_rate = float(row.get(turnover_col, 0)) if turnover_col else 0
            
            # 计算上涨概率（基于涨跌幅、成交量、换手率等因素）
            # 这里使用简单的计算方法，实际可以使用更复杂的模型
            up_probability = min(100, max(0, 
                50 + change_pct * 2 + 
                (turnover_rate - 2) * 5 + 
                (volume / 100000000) * 0.1
            ))
            
            # 计算短期强度
            short_term_strength = min(100, max(0, 
                change_pct * 3 + 
                (turnover_rate - 1) * 10
            ))
            
            results.append({
                'code': code,
                'name': name,
                'price': price,
                'change_pct': change_pct,
                'volume': volume,
                'amount': amount,
                'turnover_rate': turnover_rate,
                'up_probability': round(up_probability, 2),
                'short_term_strength': round(short_term_strength, 2)
            })
        
        # 按上涨概率排序
        results.sort(key=lambda x: x['up_probability'], reverse=True)
        
        logger.info(f"成功分析 {len(results)} 只股票")
        return results
    
    def run(self):
        """
        执行尾盘选股流程
        """
        logger.info("开始执行尾盘选股流程...")
        
        # 1. 获取热度前十的板块
        top_sectors = self.get_top_sectors(10)
        
        # 2. 获取沪深主板股票数据
        main_board_stocks = self.get_main_board_stocks()
        
        # 3. 筛选价格在5-35元之间的股票
        price_filtered_stocks = self.filter_price_range(main_board_stocks, 5, 35)
        
        # 4. 获取热度前50的股票
        top_stocks = self.get_top_stocks(price_filtered_stocks, 50)
        
        # 5. 分析股票，计算上涨概率
        analyzed_stocks = self.analyze_stocks(top_stocks)
        
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
        print(f"沪深主板尾盘选股推荐 ({today})")
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
        print(f"{'-' * 100}")
        print(f"{'代码':<10} {'名称':<15} {'价格':>8} {'涨跌幅':>10} {'换手率':>10} {'上涨概率':>12} {'短期强度':>12}")
        print(f"{'-' * 100}")
        
        # 只输出上涨概率高于60%的股票
        recommended_stocks = [stock for stock in analyzed_stocks if stock['up_probability'] > 60][:10]
        
        for i, stock in enumerate(recommended_stocks, 1):
            code = stock['code']
            name = stock['name']
            price = stock['price']
            change_pct = stock['change_pct']
            turnover_rate = stock['turnover_rate']
            up_probability = stock['up_probability']
            short_term_strength = stock['short_term_strength']
            
            print(f"{i}. {code:<8} {name:<15} {price:>8.2f} {change_pct:>10.2f}% {turnover_rate:>10.2f}% {up_probability:>12.2f}% {short_term_strength:>12.2f}")
        
        # 输出操作建议
        print(f"\n💡 操作建议:")
        print(f"{'-' * 60}")
        print(f"1. 超短线操作，建议持有1-2天")
        print(f"2. 关注热门板块中的龙头个股")
        print(f"3. 控制仓位，单只股票建议不超过总资金的20%")
        print(f"4. 设置止损位，建议在成本价下方5%左右")
        print(f"5. 密切关注大盘走势，如遇系统性风险及时止损")
        print(f"6. 推荐股票仅供参考，不构成投资建议")
        print(f"{'-' * 60}")

if __name__ == "__main__":
    selector = EndOfDaySelector()
    selector.run()
