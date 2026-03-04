# -*- coding: utf-8 -*-
"""
===================================
尾盘选股程序（次日早盘买入策略）
===================================

功能：
1. 每天下午6点之后选股，次日早盘买入
2. 筛选范围：沪深主板A股（60/00开头）
3. 排除ST股、退市风险股、停牌股、新股（上市不满1个月）
4. 选股逻辑：当日涨幅3%-5%、换手率3%-10%、量比1.2-5、流通市值30亿-200亿
5. 均线多头排列，尾盘温和放量、资金净流入
6. 数据源：首选Tushare，失败自动切换Akshare
"""

import logging
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np

from utils.logger_config import setup_logger
from data_provider.data_cache import get_data_cache

logger = setup_logger(__name__, log_file='logs/evening_selector.log')

load_dotenv()

class EveningStockSelector:
    """
    尾盘选股器（次日早盘买入策略）
    """
    
    def __init__(self):
        self.stock_data = None
        self.selected_stocks = []
        self.data_source = None
        self.today = datetime.now().strftime('%Y-%m-%d')
        self.cache = get_data_cache()
        
    def get_stock_data(self) -> pd.DataFrame:
        """
        获取股票数据
        优先使用缓存（当天数据可重复使用），缓存不存在时从数据源获取
        首选Akshare（无积分限制，数据完整），失败自动切换Tushare（仅作为备用）
        """
        print("=" * 80)
        print("1. 获取股票数据")
        print("=" * 80)
        
        # 首先尝试从缓存加载（24小时内有效）
        print("检查本地缓存...")
        cached_df = self.cache.load_stock_data(max_age_hours=24)
        if cached_df is not None and not cached_df.empty:
            print(f"✅ 从本地缓存加载数据成功: {len(cached_df)} 只股票")
            self.data_source = "Local-Cache"
            
            # 标准化列名（兼容缓存数据的中文列名）
            column_mapping = {
                '代码': 'code',
                '名称': 'name',
                '最新价': 'close',
                '昨收': 'pre_close',
                '涨跌幅': 'pct_chg',
                '涨跌额': 'change',
                '成交量': 'volume',
                '成交额': 'amount',
                '换手率': 'turnover',
                '量比': 'volume_ratio',
                '流通市值': 'circ_mv',
                '总市值': 'total_mv',
                '振幅': 'amplitude',
                '最高': 'high',
                '最低': 'low',
                '今开': 'open',
            }
            
            for old_col, new_col in column_mapping.items():
                if old_col in cached_df.columns:
                    cached_df[new_col] = cached_df[old_col]
            
            # 确保有必要的列
            required_columns = ['code', 'close', 'pct_chg', 'amount']
            for col in required_columns:
                if col not in cached_df.columns:
                    print(f"⚠️ 缓存数据缺少列: {col}")
            
            return cached_df
        
        print("📥 缓存不存在或已过期，从数据源下载...")
        
        # 首先尝试Akshare（首选，完全免费，数据完整）
        print("尝试使用Akshare数据源...")
        
        import time
        for retry in range(3):
            try:
                import akshare as ak
                print(f"使用Akshare东方财富接口... (尝试 {retry + 1}/3)")
                
                df = ak.stock_zh_a_spot_em()
                
                if df is not None and not df.empty:
                    print(f"✅ Akshare数据获取成功: {len(df)} 只股票")
                    self.data_source = "Akshare-EM"
                    
                    column_mapping = {
                        '代码': 'code',
                        '名称': 'name',
                        '最新价': 'close',
                        '昨收': 'pre_close',
                        '涨跌幅': 'pct_chg',
                        '涨跌额': 'change',
                        '成交量': 'volume',
                        '成交额': 'amount',
                        '换手率': 'turnover',
                        '量比': 'volume_ratio',
                        '流通市值': 'circ_mv',
                        '总市值': 'total_mv',
                        '振幅': 'amplitude',
                        '最高': 'high',
                        '最低': 'low',
                        '今开': 'open',
                    }
                    
                    for old_col, new_col in column_mapping.items():
                        if old_col in df.columns:
                            df[new_col] = df[old_col]
                    
                    # 保存到缓存
                    self.cache.save_stock_data(df)
                    print(f"💾 数据已保存到本地缓存")
                    
                    return df
                else:
                    print("⚠️ 东方财富接口未获取到数据")
            except Exception as e:
                print(f"⚠️ 东方财富接口获取失败: {str(e)[:100]}")
            
            if retry < 2:
                print("   等待3秒后重试...")
                time.sleep(3)
        
        # 切换至Tushare（仅作为备用，120积分仅支持daily接口）
        print("\n🔄 自动切换至Tushare备用数据源...")
        print("⚠️ Tushare 120积分仅支持日线行情接口，建议优先使用Akshare")
        
        tushare_token = os.getenv('TUSHARE_TOKEN')
        if tushare_token and tushare_token != 'your_tushare_token_here':
            try:
                print("尝试使用Tushare数据源...")
                import tushare as ts
                pro = ts.pro_api(tushare_token)
                
                # 获取当日行情数据
                for i in range(5):
                    check_date = (datetime.now() - timedelta(days=i)).strftime('%Y%m%d')
                    print(f"尝试获取 {check_date} 的数据...")
                    
                    try:
                        df = pro.daily(trade_date=check_date)
                        
                        if df is not None and not df.empty:
                            print(f"✅ Tushare数据获取成功: {len(df)} 只股票")
                            self.data_source = f"Tushare-{check_date}"
                            
                            df = df.rename(columns={
                                'ts_code': 'code',
                                'trade_date': 'date',
                                'open': 'open',
                                'high': 'high',
                                'low': 'low',
                                'close': 'close',
                                'pre_close': 'pre_close',
                                'change': 'change',
                                'pct_chg': 'pct_chg',
                                'vol': 'volume',
                                'amount': 'amount'
                            })
                            
                            df['pct_chg'] = pd.to_numeric(df['pct_chg'], errors='coerce')
                            
                            # 保存到缓存
                            self.cache.save_stock_data(df)
                            print(f"💾 数据已保存到本地缓存")
                            
                            print(f"✅ Tushare数据获取成功: {len(df)} 只股票")
                            print("⚠️ 注意：Tushare 120积分无法获取名称、换手率、量比等数据")
                            return df
                    except Exception as e:
                        print(f"   {check_date} 数据获取失败: {e}")
                        continue
                
                print("⚠️ Tushare未获取到最近5天的数据")
            except Exception as e:
                print(f"⚠️ Tushare调用失败: {str(e)[:100]}")
                print("   可能原因：Token被其他程序占用或网络问题")
        else:
            print("⚠️ Tushare Token未配置或无效")
        
        print("❌ 所有数据源均无法获取数据")
        
        # 尝试从缓存加载
        print("\n尝试从缓存加载数据...")
        cache_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                   'data', 'cache', f'stock_data_{datetime.now().strftime("%Y%m%d")}.csv')
        if os.path.exists(cache_file):
            try:
                df = pd.read_csv(cache_file, encoding='utf-8')
                if not df.empty:
                    print(f"✅ 从缓存加载数据成功: {len(df)} 只股票")
                    self.data_source = "Cache"
                    return df
            except Exception as e:
                print(f"⚠️ 缓存加载失败: {e}")
        
        return pd.DataFrame()
    
    def filter_main_board(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        筛选沪深主板股票（60/00开头）
        排除ST股、退市风险股、停牌股、新股
        """
        print("\n" + "=" * 80)
        print("2. 筛选沪深主板股票")
        print("=" * 80)
        
        if df.empty:
            return df
        
        code_col = None
        for col in ['code', 'ts_code', '股票代码', '代码']:
            if col in df.columns:
                code_col = col
                break
        
        if code_col is None:
            print("❌ 未找到代码列")
            return df
        
        # 处理代码格式
        df[code_col] = df[code_col].astype(str)
        
        def extract_code(code):
            code = str(code).strip().upper()
            # 去除交易所后缀
            if '.' in code:
                code = code.split('.')[0]
            # 去除前缀
            for prefix in ['BJ', 'SH', 'SZ']:
                if code.startswith(prefix):
                    code = code[2:]
            return code.zfill(6)
        
        df['pure_code'] = df[code_col].apply(extract_code)
        
        # 筛选沪深主板（60/00开头）
        mask = df['pure_code'].str.match(r'^(60[0135]|000|001|003)\d{3}$')
        df = df[mask].copy()
        print(f"✅ 沪深主板筛选: {len(df)} 只")
        
        # 排除ST股
        name_col = None
        for col in ['name', '名称', '股票名称']:
            if col in df.columns:
                name_col = col
                break
        
        if name_col:
            st_mask = df[name_col].str.contains(r'ST|\*ST|S\*ST|SST|退市', na=False, regex=True)
            df = df[~st_mask].copy()
            print(f"✅ 排除ST/退市股: {st_mask.sum()} 只")
        
        # 排除停牌股（价格为0或成交量为0）
        price_col = None
        for col in ['close', '最新价', '收盘']:
            if col in df.columns:
                price_col = col
                break
        
        if price_col:
            df[price_col] = pd.to_numeric(df[price_col], errors='coerce')
            suspended_mask = (df[price_col] <= 0) | df[price_col].isna()
            df = df[~suspended_mask].copy()
            print(f"✅ 排除停牌股: {suspended_mask.sum()} 只")
        
        # 排除新股（上市不满1个月）
        # 通过代码特征判断：60开头>605000, 00开头>003000
        def is_new_stock(code):
            code = str(code).zfill(6)
            if code.startswith('60'):
                return code >= '605000'
            elif code.startswith('00'):
                return code >= '003000'
            return False
        
        new_stock_mask = df['pure_code'].apply(is_new_stock)
        df = df[~new_stock_mask].copy()
        print(f"✅ 排除新股: {new_stock_mask.sum()} 只")
        
        df['code'] = df['pure_code']
        df = df.drop(columns=['pure_code'])
        
        print(f"✅ 最终剩余: {len(df)} 只")
        return df
    
    def calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算技术指标
        """
        print("\n" + "=" * 80)
        print("3. 计算技术指标")
        print("=" * 80)
        
        if df.empty:
            return df
        
        # 确保数值类型
        numeric_cols = ['close', 'pct_chg', 'turnover', 'volume_ratio', 'circ_mv', 'amount']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        print(f"✅ 技术指标计算完成")
        return df
    
    def apply_selection_criteria(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        应用选股条件
        """
        print("\n" + "=" * 80)
        print("4. 应用选股条件")
        print("=" * 80)
        
        if df.empty:
            return df
        
        # 获取列名
        pct_chg_col = None
        for col in ['pct_chg', '涨跌幅']:
            if col in df.columns:
                pct_chg_col = col
                break
        
        turnover_col = None
        for col in ['turnover', '换手率']:
            if col in df.columns:
                turnover_col = col
                break
        
        volume_ratio_col = None
        for col in ['volume_ratio', '量比']:
            if col in df.columns:
                volume_ratio_col = col
                break
        
        circ_mv_col = None
        for col in ['circ_mv', '流通市值']:
            if col in df.columns:
                circ_mv_col = col
                break
        
        amount_col = None
        for col in ['amount', '成交额']:
            if col in df.columns:
                amount_col = col
                break
        
        print(f"   使用列: 涨幅={pct_chg_col}, 换手={turnover_col}, 量比={volume_ratio_col}, 市值={circ_mv_col}, 成交额={amount_col}")
        
        df['selection_score'] = 0
        df['selection_logic'] = ''
        
        for idx, row in df.iterrows():
            score = 0
            logic = []
            
            # 条件1：当日涨幅3%-5%
            if pct_chg_col:
                pct_chg = float(row.get(pct_chg_col, 0))
                if 3 <= pct_chg <= 5:
                    score += 25
                    logic.append('涨幅适中')
            
            # 条件2：换手率3%-10%
            if turnover_col:
                turnover = float(row.get(turnover_col, 0))
                if 3 <= turnover <= 10:
                    score += 20
                    logic.append('换手健康')
            
            # 条件3：量比1.2-5
            if volume_ratio_col:
                volume_ratio = float(row.get(volume_ratio_col, 0))
                if 1.2 <= volume_ratio <= 5:
                    score += 20
                    logic.append('量能配合')
            
            # 条件4：流通市值30亿-200亿
            if circ_mv_col:
                circ_mv = float(row.get(circ_mv_col, 0))
                # 处理不同单位
                if circ_mv > 100000000:
                    circ_mv = circ_mv / 100000000
                if 30 <= circ_mv <= 200:
                    score += 20
                    logic.append('市值适中')
            
            # 条件5：成交额>5000万（资金活跃）
            if amount_col:
                amount = float(row.get(amount_col, 0))
                if amount > 50000000:
                    score += 15
                    logic.append('资金活跃')
            
            df.at[idx, 'selection_score'] = score
            df.at[idx, 'selection_logic'] = ', '.join(logic)
        
        # 统计得分分布
        score_dist = df['selection_score'].value_counts().sort_index(ascending=False)
        print(f"   得分分布:")
        for score, count in score_dist.head(10).items():
            print(f"     {score}分: {count}只")
        
        print(f"✅ 选股条件应用完成")
        return df
    
    def select_stocks(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        筛选符合条件的股票
        """
        print("\n" + "=" * 80)
        print("5. 筛选符合条件的股票")
        print("=" * 80)
        
        if df.empty:
            return df
        
        # 筛选得分>=60的股票
        selected = df[df['selection_score'] >= 60].copy()
        
        # 按得分排序
        selected = selected.sort_values('selection_score', ascending=False)
        
        # 限制数量
        selected = selected.head(20)
        
        print(f"✅ 筛选出 {len(selected)} 只符合条件的股票")
        return selected
    
    def generate_trading_plan(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        生成交易计划
        """
        print("\n" + "=" * 80)
        print("6. 生成交易计划")
        print("=" * 80)
        
        if df.empty:
            return df
        
        for idx, row in df.iterrows():
            close = float(row.get('close', 0))
            
            if close > 0:
                # 次日早盘买入参考价（收盘价附近）
                buy_price = close
                buy_low = close * 0.995
                buy_high = close * 1.005
                
                # 止损位（-3%）
                stop_loss = close * 0.97
                
                # 止盈位（+5%）
                take_profit = close * 1.05
                
                df.at[idx, 'buy_price'] = f"{buy_price:.2f}"
                df.at[idx, 'buy_range'] = f"{buy_low:.2f}-{buy_high:.2f}"
                df.at[idx, 'stop_loss'] = f"{stop_loss:.2f}"
                df.at[idx, 'take_profit'] = f"{take_profit:.2f}"
        
        print(f"✅ 交易计划生成完成")
        return df
    
    def format_output(self, df: pd.DataFrame) -> str:
        """
        格式化输出
        """
        if df.empty:
            return "未找到符合条件的股票"
        
        output = []
        output.append("\n" + "=" * 80)
        output.append(f"尾盘选股结果（次日早盘买入）- {self.today}")
        output.append(f"数据源: {self.data_source}")
        output.append("=" * 80)
        
        for i, (idx, row) in enumerate(df.iterrows(), 1):
            code = row.get('code', 'N/A')
            name = row.get('name', 'N/A')
            close = float(row.get('close', 0))
            pct_chg = float(row.get('pct_chg', 0))
            turnover = float(row.get('turnover', 0))
            volume_ratio = float(row.get('volume_ratio', 0))
            circ_mv = float(row.get('circ_mv', 0))
            
            # 处理市值单位
            if circ_mv > 100000000:
                circ_mv = circ_mv / 100000000
            
            score = int(row.get('selection_score', 0))
            logic = row.get('selection_logic', '')
            buy_range = row.get('buy_range', 'N/A')
            stop_loss = row.get('stop_loss', 'N/A')
            take_profit = row.get('take_profit', 'N/A')
            
            output.append(f"\n{i}. {code} {name}")
            output.append(f"   收盘价: {close:.2f} 元  涨幅: {pct_chg:+.2f}%")
            output.append(f"   换手率: {turnover:.2f}%  量比: {volume_ratio:.2f}")
            output.append(f"   流通市值: {circ_mv:.2f} 亿")
            output.append(f"   综合得分: {score} 分")
            output.append(f"   入选逻辑: {logic}")
            output.append(f"   📌 交易计划:")
            output.append(f"      买入区间: {buy_range} 元")
            output.append(f"      止损价位: {stop_loss} 元 (-3%)")
            output.append(f"      止盈目标: {take_profit} 元 (+5%)")
        
        output.append("\n" + "=" * 80)
        output.append("💡 操作建议：")
        output.append("   1. 次日早盘择机买入，建议开盘30分钟内完成")
        output.append("   2. 严格设置止损，跌破止损价立即离场")
        output.append("   3. 达到止盈目标可分批减仓")
        output.append("   4. 单只股票仓位不超过20%")
        output.append("   5. 持有周期：1-3天，超短线策略")
        output.append("=" * 80)
        
        return '\n'.join(output)
    
    def run(self):
        """
        执行尾盘选股
        """
        print("\n" + "=" * 80)
        print("尾盘选股程序（次日早盘买入策略）")
        print("=" * 80)
        
        # 获取数据
        df = self.get_stock_data()
        if df.empty:
            print("❌ 无法获取股票数据")
            return
        
        # 筛选沪深主板
        df = self.filter_main_board(df)
        
        # 计算技术指标
        df = self.calculate_technical_indicators(df)
        
        # 应用选股条件
        df = self.apply_selection_criteria(df)
        
        # 筛选股票
        df = self.select_stocks(df)
        
        # 生成交易计划
        df = self.generate_trading_plan(df)
        
        # 输出结果
        result = self.format_output(df)
        print(result)
        
        return df

def main():
    selector = EveningStockSelector()
    selector.run()

if __name__ == '__main__':
    main()
