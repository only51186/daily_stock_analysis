# -*- coding: utf-8 -*-
"""
===================================
A股市场自动化复盘脚本
===================================

功能：
1. 统计今日沪深主板的涨跌分布、成交量变化、主力资金流向、热门板块排行
2. 找出今日涨停/跌停个股的共性特征，分析市场情绪
3. 基于当前市场行情，给出明日的短线交易方向和风险提示
4. 把所有复盘内容整理成一份清晰的日报，保存到项目的docs文件夹里
"""

import logging
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np

from utils.logger_config import setup_logger

logger = setup_logger(__name__, log_file='logs/market_review.log')

class MarketReview:
    """
    A股市场复盘类
    """
    
    def __init__(self):
        self.stock_data = None
        self.main_board_data = None
        self.today = datetime.now().strftime('%Y-%m-%d')
    
    def _get_cache_path(self) -> str:
        """获取缓存文件路径"""
        cache_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'cache')
        today = datetime.now().strftime('%Y%m%d')
        return os.path.join(cache_dir, f'stock_data_{today}.csv')
    
    def load_stock_data(self) -> pd.DataFrame:
        """加载股票数据"""
        print("=" * 80)
        print("1. 加载股票数据")
        print("=" * 80)
        
        cache_path = self._get_cache_path()
        if os.path.exists(cache_path):
            try:
                df = pd.read_csv(cache_path)
                print(f"✅ 从缓存加载数据: {len(df)} 只股票")
                self.stock_data = df
                return df
            except Exception as e:
                print(f"⚠️ 缓存加载失败: {e}")
        
        print("❌ 未找到缓存数据，请先运行选股脚本获取数据")
        return pd.DataFrame()
    
    def filter_main_board(self, df: pd.DataFrame) -> pd.DataFrame:
        """筛选沪深主板股票"""
        print("\n" + "=" * 80)
        print("2. 筛选沪深主板股票")
        print("=" * 80)
        
        if df.empty:
            return df
        
        code_col = None
        for col in ['代码', 'symbol', '股票代码', 'code']:
            if col in df.columns:
                code_col = col
                break
        
        if code_col is None:
            print("❌ 未找到代码列")
            return df
        
        df[code_col] = df[code_col].astype(str)
        
        def extract_code(code):
            code = str(code).strip().lower()
            for prefix in ['bj', 'sh', 'sz']:
                if code.startswith(prefix):
                    code = code[len(prefix):]
            return code.zfill(6)
        
        df['pure_code'] = df[code_col].apply(extract_code)
        
        mask = df['pure_code'].str.match(r'^(60[0135]|000|001|003)\d{3}$')
        main_board_df = df[mask].copy()
        
        main_board_df[code_col] = main_board_df['pure_code']
        main_board_df = main_board_df.drop(columns=['pure_code'])
        
        print(f"✅ 筛选出 {len(main_board_df)} 只沪深主板股票")
        self.main_board_data = main_board_df
        return main_board_df
    
    def analyze_price_distribution(self, df: pd.DataFrame) -> Dict[str, Any]:
        """分析涨跌分布"""
        print("\n" + "=" * 80)
        print("3. 分析涨跌分布")
        print("=" * 80)
        
        if df.empty:
            return {}
        
        change_col = None
        for col in ['涨跌幅', 'pct_chg', '涨跌幅%', 'percent']:
            if col in df.columns:
                change_col = col
                break
        
        if change_col is None:
            print("❌ 未找到涨跌幅列")
            return {}
        
        df[change_col] = pd.to_numeric(df[change_col], errors='coerce')
        
        # 涨跌分布
        up_count = len(df[df[change_col] > 0])
        down_count = len(df[df[change_col] < 0])
        flat_count = len(df[df[change_col] == 0])
        
        up_ratio = up_count / len(df) * 100
        down_ratio = down_count / len(df) * 100
        
        # 涨幅区间分布
        limit_up = len(df[df[change_col] >= 9.8])
        strong_up = len(df[(df[change_col] >= 5) & (df[change_col] < 9.8)])
        moderate_up = len(df[(df[change_col] >= 2) & (df[change_col] < 5)])
        weak_up = len(df[(df[change_col] > 0) & (df[change_col] < 2)])
        
        limit_down = len(df[df[change_col] <= -9.8])
        strong_down = len(df[(df[change_col] <= -5) & (df[change_col] > -9.8)])
        moderate_down = len(df[(df[change_col] <= -2) & (df[change_col] > -5)])
        weak_down = len(df[(df[change_col] < 0) & (df[change_col] > -2)])
        
        # 平均涨跌幅
        avg_change = df[change_col].mean()
        median_change = df[change_col].median()
        
        result = {
            'total': len(df),
            'up_count': up_count,
            'down_count': down_count,
            'flat_count': flat_count,
            'up_ratio': up_ratio,
            'down_ratio': down_ratio,
            'limit_up': limit_up,
            'strong_up': strong_up,
            'moderate_up': moderate_up,
            'weak_up': weak_up,
            'limit_down': limit_down,
            'strong_down': strong_down,
            'moderate_down': moderate_down,
            'weak_down': weak_down,
            'avg_change': avg_change,
            'median_change': median_change,
        }
        
        print(f"✅ 涨跌分布分析完成")
        print(f"   上涨: {up_count} 只 ({up_ratio:.2f}%)")
        print(f"   下跌: {down_count} 只 ({down_ratio:.2f}%)")
        print(f"   平盘: {flat_count} 只")
        print(f"   平均涨跌: {avg_change:.2f}%")
        print(f"   中位数涨跌: {median_change:.2f}%")
        
        return result
    
    def analyze_volume_change(self, df: pd.DataFrame) -> Dict[str, Any]:
        """分析成交量变化"""
        print("\n" + "=" * 80)
        print("4. 分析成交量变化")
        print("=" * 80)
        
        if df.empty:
            return {}
        
        volume_col = None
        for col in ['成交量', 'volume', 'vol']:
            if col in df.columns:
                volume_col = col
                break
        
        amount_col = None
        for col in ['成交额', 'amount', 'amt']:
            if col in df.columns:
                amount_col = col
                break
        
        if volume_col is None or amount_col is None:
            print("❌ 未找到成交量或成交额列")
            return {}
        
        df[volume_col] = pd.to_numeric(df[volume_col], errors='coerce')
        df[amount_col] = pd.to_numeric(df[amount_col], errors='coerce')
        
        total_volume = df[volume_col].sum()
        total_amount = df[amount_col].sum()
        avg_volume = df[volume_col].mean()
        avg_amount = df[amount_col].mean()
        
        # 高成交量股票（成交额>1亿）
        high_amount = len(df[df[amount_col] > 100000000])
        high_amount_ratio = high_amount / len(df) * 100
        
        result = {
            'total_volume': total_volume,
            'total_amount': total_amount,
            'avg_volume': avg_volume,
            'avg_amount': avg_amount,
            'high_amount_count': high_amount,
            'high_amount_ratio': high_amount_ratio,
        }
        
        print(f"✅ 成交量分析完成")
        print(f"   总成交额: {total_amount/100000000:.2f} 亿元")
        print(f"   平均成交额: {avg_amount/10000:.2f} 万元")
        print(f"   大额成交股票(>1亿): {high_amount} 只 ({high_amount_ratio:.2f}%)")
        
        return result
    
    def analyze_capital_flow(self, df: pd.DataFrame) -> Dict[str, Any]:
        """分析主力资金流向"""
        print("\n" + "=" * 80)
        print("5. 分析主力资金流向")
        print("=" * 80)
        
        if df.empty:
            return {}
        
        # 使用成交额作为资金流向的代理指标
        amount_col = None
        for col in ['成交额', 'amount', 'amt']:
            if col in df.columns:
                amount_col = col
                break
        
        change_col = None
        for col in ['涨跌幅', 'pct_chg', '涨跌幅%', 'percent']:
            if col in df.columns:
                change_col = col
                break
        
        if amount_col is None or change_col is None:
            print("❌ 未找到成交额或涨跌幅列")
            return {}
        
        df[amount_col] = pd.to_numeric(df[amount_col], errors='coerce')
        df[change_col] = pd.to_numeric(df[change_col], errors='coerce')
        
        # 上涨股票成交额（资金流入）
        up_stocks = df[df[change_col] > 0]
        down_stocks = df[df[change_col] < 0]
        
        inflow = up_stocks[amount_col].sum()
        outflow = down_stocks[amount_col].sum()
        net_flow = inflow - outflow
        flow_ratio = inflow / outflow if outflow > 0 else float('inf')
        
        result = {
            'inflow': inflow,
            'outflow': outflow,
            'net_flow': net_flow,
            'flow_ratio': flow_ratio,
        }
        
        print(f"✅ 资金流向分析完成")
        print(f"   资金流入: {inflow/100000000:.2f} 亿元")
        print(f"   资金流出: {outflow/100000000:.2f} 亿元")
        print(f"   净流入: {net_flow/100000000:.2f} 亿元")
        print(f"   流入流出比: {flow_ratio:.2f}")
        
        return result
    
    def analyze_hot_sectors(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """分析热门板块排行"""
        print("\n" + "=" * 80)
        print("6. 分析热门板块排行")
        print("=" * 80)
        
        if df.empty:
            return []
        
        # 按名称关键词分组统计
        name_col = None
        for col in ['名称', 'name', '股票名称']:
            if col in df.columns:
                name_col = col
                break
        
        change_col = None
        for col in ['涨跌幅', 'pct_chg', '涨跌幅%', 'percent']:
            if col in df.columns:
                change_col = col
                break
        
        if name_col is None or change_col is None:
            print("❌ 未找到名称或涨跌幅列")
            return []
        
        df[change_col] = pd.to_numeric(df[change_col], errors='coerce')
        
        # 提取板块关键词
        sector_keywords = {
            '电力': ['电力', '水电', '火电', '核电', '风电'],
            '新能源': ['新能源', '光伏', '风电', '储能', '电池'],
            '医药': ['医药', '生物', '制药', '医疗'],
            '消费': ['消费', '白酒', '食品', '饮料'],
            '科技': ['科技', '电子', '软件', '芯片', '半导体'],
            '金融': ['银行', '证券', '保险', '信托'],
            '地产': ['地产', '房地产'],
            '汽车': ['汽车', '整车', '零部件'],
            '化工': ['化工', '化学'],
            '农业': ['农业', '种业', '养殖'],
        }
        
        sector_stats = []
        for sector, keywords in sector_keywords.items():
            mask = df[name_col].str.contains('|'.join(keywords), na=False)
            sector_df = df[mask]
            if len(sector_df) > 0:
                avg_change = sector_df[change_col].mean()
                up_count = len(sector_df[sector_df[change_col] > 0])
                sector_stats.append({
                    'sector': sector,
                    'count': len(sector_df),
                    'avg_change': avg_change,
                    'up_count': up_count,
                    'up_ratio': up_count / len(sector_df) * 100,
                })
        
        # 按平均涨幅排序
        sector_stats.sort(key=lambda x: x['avg_change'], reverse=True)
        
        print(f"✅ 热门板块分析完成")
        for i, stat in enumerate(sector_stats[:5], 1):
            print(f"   {i}. {stat['sector']}: 平均涨幅 {stat['avg_change']:.2f}%, 上涨 {stat['up_count']}/{stat['count']} 只")
        
        return sector_stats
    
    def analyze_limit_stocks(self, df: pd.DataFrame) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """分析涨停/跌停个股特征"""
        print("\n" + "=" * 80)
        print("7. 分析涨停/跌停个股特征")
        print("=" * 80)
        
        if df.empty:
            return {}, {}
        
        change_col = None
        for col in ['涨跌幅', 'pct_chg', '涨跌幅%', 'percent']:
            if col in df.columns:
                change_col = col
                break
        
        price_col = None
        for col in ['最新价', 'price', '现价', 'close']:
            if col in df.columns:
                price_col = col
                break
        
        amount_col = None
        for col in ['成交额', 'amount', 'amt']:
            if col in df.columns:
                amount_col = col
                break
        
        if change_col is None:
            print("❌ 未找到涨跌幅列")
            return {}, {}
        
        df[change_col] = pd.to_numeric(df[change_col], errors='coerce')
        
        # 涨停股票
        limit_up = df[df[change_col] >= 9.8].copy()
        # 跌停股票
        limit_down = df[df[change_col] <= -9.8].copy()
        
        def analyze_stock_group(group_df, group_name):
            if group_df.empty:
                return {}
            
            if price_col:
                group_df[price_col] = pd.to_numeric(group_df[price_col], errors='coerce')
            
            if amount_col:
                group_df[amount_col] = pd.to_numeric(group_df[amount_col], errors='coerce')
            
            result = {
                'count': len(group_df),
                'avg_price': group_df[price_col].mean() if price_col else 0,
                'avg_amount': group_df[amount_col].mean() if amount_col else 0,
                'avg_change': group_df[change_col].mean(),
            }
            
            return result
        
        limit_up_stats = analyze_stock_group(limit_up, '涨停')
        limit_down_stats = analyze_stock_group(limit_down, '跌停')
        
        print(f"✅ 涨停/跌停分析完成")
        print(f"   涨停: {limit_up_stats.get('count', 0)} 只")
        print(f"   跌停: {limit_down_stats.get('count', 0)} 只")
        
        return limit_up_stats, limit_down_stats
    
    def generate_trading_advice(self, price_dist: Dict, volume: Dict, capital: Dict, 
                            sectors: List, limit_up: Dict, limit_down: Dict) -> Dict[str, Any]:
        """生成交易建议"""
        print("\n" + "=" * 80)
        print("8. 生成交易建议")
        print("=" * 80)
        
        # 市场情绪判断
        up_ratio = price_dist.get('up_ratio', 0)
        net_flow = capital.get('net_flow', 0)
        
        if up_ratio > 60 and net_flow > 0:
            market_sentiment = "强势"
            direction = "积极做多"
            risk_level = "低"
        elif up_ratio > 40 and net_flow > 0:
            market_sentiment = "偏强"
            direction = "谨慎做多"
            risk_level = "中低"
        elif up_ratio > 30 and net_flow > 0:
            market_sentiment = "震荡偏强"
            direction = "轻仓试错"
            risk_level = "中"
        elif up_ratio < 40 and net_flow < 0:
            market_sentiment = "弱势"
            direction = "观望为主"
            risk_level = "中高"
        else:
            market_sentiment = "震荡"
            direction = "等待方向"
            risk_level = "中"
        
        # 热门板块
        hot_sectors = [s['sector'] for s in sectors[:3]] if sectors else []
        
        # 风险提示
        risks = []
        if limit_down.get('count', 0) > 10:
            risks.append("跌停个股较多，市场情绪谨慎")
        if net_flow < -1000000000:
            risks.append("资金大幅流出，注意风险")
        if up_ratio < 30:
            risks.append("上涨个股不足三成，市场偏弱")
        
        if not risks:
            risks.append("市场整体平稳，注意个股风险")
        
        advice = {
            'market_sentiment': market_sentiment,
            'trading_direction': direction,
            'risk_level': risk_level,
            'hot_sectors': hot_sectors,
            'risks': risks,
        }
        
        print(f"✅ 交易建议生成完成")
        print(f"   市场情绪: {market_sentiment}")
        print(f"   交易方向: {direction}")
        print(f"   风险等级: {risk_level}")
        print(f"   热门板块: {', '.join(hot_sectors)}")
        
        return advice
    
    def generate_report(self, price_dist: Dict, volume: Dict, capital: Dict, 
                    sectors: List, limit_up: Dict, limit_down: Dict, advice: Dict) -> str:
        """生成复盘报告"""
        print("\n" + "=" * 80)
        print("9. 生成复盘报告")
        print("=" * 80)
        
        report = []
        report.append("=" * 80)
        report.append(f"A股市场复盘日报 - {self.today}")
        report.append("=" * 80)
        
        # 一、市场概况
        report.append("\n一、市场概况")
        report.append("-" * 80)
        report.append(f"沪深主板股票总数: {price_dist.get('total', 0)} 只")
        report.append(f"上涨股票: {price_dist.get('up_count', 0)} 只 ({price_dist.get('up_ratio', 0):.2f}%)")
        report.append(f"下跌股票: {price_dist.get('down_count', 0)} 只 ({price_dist.get('down_ratio', 0):.2f}%)")
        report.append(f"平盘股票: {price_dist.get('flat_count', 0)} 只")
        report.append(f"平均涨跌幅: {price_dist.get('avg_change', 0):.2f}%")
        report.append(f"中位数涨跌幅: {price_dist.get('median_change', 0):.2f}%")
        
        # 涨幅区间分布
        report.append("\n涨幅区间分布:")
        report.append(f"  涨停(≥9.8%): {price_dist.get('limit_up', 0)} 只")
        report.append(f"  大涨(5%-9.8%): {price_dist.get('strong_up', 0)} 只")
        report.append(f"  中涨(2%-5%): {price_dist.get('moderate_up', 0)} 只")
        report.append(f"  小涨(0%-2%): {price_dist.get('weak_up', 0)} 只")
        report.append(f"  小跌(0%-2%): {price_dist.get('weak_down', 0)} 只")
        report.append(f"  中跌(2%-5%): {price_dist.get('moderate_down', 0)} 只")
        report.append(f"  大跌(5%-9.8%): {price_dist.get('strong_down', 0)} 只")
        report.append(f"  跌停(≤-9.8%): {price_dist.get('limit_down', 0)} 只")
        
        # 二、成交量分析
        report.append("\n二、成交量分析")
        report.append("-" * 80)
        report.append(f"总成交额: {volume.get('total_amount', 0)/100000000:.2f} 亿元")
        report.append(f"平均成交额: {volume.get('avg_amount', 0)/10000:.2f} 万元")
        report.append(f"大额成交股票(>1亿): {volume.get('high_amount_count', 0)} 只 ({volume.get('high_amount_ratio', 0):.2f}%)")
        
        # 三、资金流向
        report.append("\n三、主力资金流向")
        report.append("-" * 80)
        report.append(f"资金流入: {capital.get('inflow', 0)/100000000:.2f} 亿元")
        report.append(f"资金流出: {capital.get('outflow', 0)/100000000:.2f} 亿元")
        report.append(f"净流入: {capital.get('net_flow', 0)/100000000:.2f} 亿元")
        report.append(f"流入流出比: {capital.get('flow_ratio', 0):.2f}")
        
        # 四、热门板块排行
        report.append("\n四、热门板块排行（Top 5）")
        report.append("-" * 80)
        for i, sector in enumerate(sectors[:5], 1):
            report.append(f"{i}. {sector['sector']}: 平均涨幅 {sector['avg_change']:.2f}%, 上涨 {sector['up_count']}/{sector['count']} 只 ({sector['up_ratio']:.1f}%)")
        
        # 五、涨停/跌停分析
        report.append("\n五、涨停/跌停分析")
        report.append("-" * 80)
        report.append(f"涨停股票: {limit_up.get('count', 0)} 只")
        if limit_up.get('count', 0) > 0:
            report.append(f"  平均价格: {limit_up.get('avg_price', 0):.2f} 元")
            report.append(f"  平均成交额: {limit_up.get('avg_amount', 0)/10000:.2f} 万元")
        
        report.append(f"跌停股票: {limit_down.get('count', 0)} 只")
        if limit_down.get('count', 0) > 0:
            report.append(f"  平均价格: {limit_down.get('avg_price', 0):.2f} 元")
            report.append(f"  平均成交额: {limit_down.get('avg_amount', 0)/10000:.2f} 万元")
        
        # 六、市场情绪与交易建议
        report.append("\n六、市场情绪与交易建议")
        report.append("-" * 80)
        report.append(f"市场情绪: {advice.get('market_sentiment', '未知')}")
        report.append(f"交易方向: {advice.get('trading_direction', '未知')}")
        report.append(f"风险等级: {advice.get('risk_level', '未知')}")
        report.append(f"热门板块: {', '.join(advice.get('hot_sectors', []))}")
        
        report.append("\n风险提示:")
        for i, risk in enumerate(advice.get('risks', []), 1):
            report.append(f"  {i}. {risk}")
        
        # 七、操作建议
        report.append("\n七、操作建议")
        report.append("-" * 80)
        if advice.get('market_sentiment') == '强势':
            report.append("  1. 市场强势，可积极参与")
            report.append("  2. 重点关注热门板块龙头股")
            report.append("  3. 严格执行止损纪律")
        elif advice.get('market_sentiment') == '偏强':
            report.append("  1. 市场偏强，可谨慎做多")
            report.append("  2. 控制仓位，分批建仓")
            report.append("  3. 注意止盈止损")
        elif advice.get('market_sentiment') == '弱势':
            report.append("  1. 市场弱势，建议观望")
            report.append("  2. 减少操作频率")
            report.append("  3. 严格控制仓位")
        else:
            report.append("  1. 市场震荡，等待方向")
            report.append("  2. 轻仓试错，快进快出")
            report.append("  3. 关注板块轮动")
        
        report.append("\n" + "=" * 80)
        report.append(f"报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("=" * 80)
        
        return '\n'.join(report)
    
    def save_report(self, report: str):
        """保存复盘报告"""
        print("\n" + "=" * 80)
        print("10. 保存复盘报告")
        print("=" * 80)
        
        docs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'docs')
        os.makedirs(docs_dir, exist_ok=True)
        
        filename = f"market_review_{self.today}.txt"
        filepath = os.path.join(docs_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"✅ 复盘报告已保存: {filepath}")
        except Exception as e:
            print(f"❌ 保存复盘报告失败: {e}")
    
    def run(self):
        """执行复盘"""
        print("\n" + "=" * 80)
        print("A股市场自动化复盘系统")
        print("=" * 80)
        
        # 加载数据
        df = self.load_stock_data()
        if df.empty:
            print("❌ 无法加载数据，复盘终止")
            return
        
        # 筛选沪深主板
        df = self.filter_main_board(df)
        if df.empty:
            print("❌ 沪深主板数据为空，复盘终止")
            return
        
        # 分析涨跌分布
        price_dist = self.analyze_price_distribution(df)
        
        # 分析成交量
        volume = self.analyze_volume_change(df)
        
        # 分析资金流向
        capital = self.analyze_capital_flow(df)
        
        # 分析热门板块
        sectors = self.analyze_hot_sectors(df)
        
        # 分析涨停跌停
        limit_up, limit_down = self.analyze_limit_stocks(df)
        
        # 生成交易建议
        advice = self.generate_trading_advice(price_dist, volume, capital, sectors, limit_up, limit_down)
        
        # 生成报告
        report = self.generate_report(price_dist, volume, capital, sectors, limit_up, limit_down, advice)
        
        # 保存报告
        self.save_report(report)
        
        # 打印报告
        print("\n" + report)

def main():
    reviewer = MarketReview()
    reviewer.run()

if __name__ == '__main__':
    main()
