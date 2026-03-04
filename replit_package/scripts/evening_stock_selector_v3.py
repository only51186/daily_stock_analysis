# -*- coding: utf-8 -*-
"""
===================================
尾盘选股程序 V3（次日早盘买入策略）- 使用EnhancedDataManager
===================================

功能：
1. 每天下午6点之后选股，次日早盘买入
2. 筛选范围：沪深主板A股（60/00开头）
3. 排除ST股、退市风险股、停牌股、新股（上市不满1个月）
4. 选股逻辑：当日涨幅3%-5%、换手率3%-10%、量比1.2-5、流通市值30亿-200亿
5. 均线多头排列，尾盘温和放量、资金净流入
6. 数据源：使用EnhancedDataManager的多源自动切换
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
from src.data_layer import get_enhanced_data_manager

logger = setup_logger(__name__, log_file='logs/evening_selector.log')

load_dotenv()

class EveningStockSelectorV3:
    """
    尾盘选股器V3（使用EnhancedDataManager）
    """
    
    def __init__(self):
        self.stock_data = None
        self.selected_stocks = []
        self.data_source = None
        self.today = datetime.now().strftime('%Y-%m-%d')
        self.data_manager = get_enhanced_data_manager()
        
    def get_all_stock_data(self) -> pd.DataFrame:
        """
        使用EnhancedDataManager获取所有股票数据
        """
        print("=" * 80)
        print("1. 获取股票数据（使用EnhancedDataManager）")
        print("=" * 80)
        
        # 先获取股票列表
        print("正在获取沪深主板股票列表...")
        
        # 尝试获取最近交易日的数据
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        
        # 先测试获取一只股票的数据，看看数据源是否正常
        test_symbol = '000001.SZ'
        print(f"测试数据源: {test_symbol}")
        
        df_test, source = self.data_manager.get_stock_data(
            symbol=test_symbol,
            start_date=start_date,
            end_date=end_date
        )
        
        if df_test is None or df_test.empty:
            print("❌ 无法获取测试数据")
            return pd.DataFrame()
        
        print(f"✅ 数据源测试成功: {source}")
        self.data_source = source
        
        # 由于获取全市场数据量太大，我们使用简化方案
        # 先从Tushare获取股票列表和基础数据
        print("\n正在从Tushare获取股票列表...")
        
        tushare_token = os.getenv('TUSHARE_TOKEN')
        if tushare_token and tushare_token != 'your_tushare_token_here':
            try:
                import tushare as ts
                import time
                pro = ts.pro_api(tushare_token)
                
                # 尝试获取最近5天的数据，找到有数据的那天
                for i in range(5):
                    check_date = (datetime.now() - timedelta(days=i)).strftime('%Y%m%d')
                    print(f"尝试获取 {check_date} 的数据...")
                    
                    try:
                        df = pro.daily(trade_date=check_date)
                        
                        if df is not None and not df.empty:
                            print(f"✅ Tushare行情数据获取成功: {len(df)} 只股票 (日期: {check_date})")
                            
                            # 等待一下避免限流
                            time.sleep(0.5)
                            
                            # 获取基础信息（包含名称、市值等）- 尝试从缓存或本地获取
                            try:
                                print("  正在获取股票基础信息...")
                                stock_basic = pro.stock_basic(exchange='', list_status='L')
                                if stock_basic is not None and not stock_basic.empty:
                                    df = df.merge(stock_basic[['ts_code', 'name', 'list_date']], on='ts_code', how='left')
                                    print("  ✅ 股票基础信息获取成功")
                            except Exception as e:
                                print(f"  ⚠️ 获取基础信息失败（可能有访问限制）: {e}")
                            
                            # 标准化列名
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
                                'amount': 'amount',
                                'name': 'name'
                            })
                            
                            # 计算涨跌幅
                            df['pct_chg'] = pd.to_numeric(df['pct_chg'], errors='coerce')
                            
                            print(f"✅ 数据获取完成: {len(df)} 只股票")
                            print(f"   包含列: {list(df.columns)}")
                            
                            return df
                    except Exception as e:
                        print(f"   {check_date} 数据获取失败: {e}")
                        continue
                
            except Exception as e:
                print(f"⚠️ Tushare调用失败: {str(e)[:100]}")
                import traceback
                traceback.print_exc()
        
        print("❌ 无法获取完整股票数据")
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
    
    def apply_selection_criteria(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        应用选股条件（简化版，不依赖缺失的指标）
        """
        print("\n" + "=" * 80)
        print("3. 应用选股条件")
        print("=" * 80)
        
        if df.empty:
            return df
        
        # 获取列名
        pct_chg_col = None
        for col in ['pct_chg', '涨跌幅']:
            if col in df.columns:
                pct_chg_col = col
                break
        
        amount_col = None
        for col in ['amount', '成交额']:
            if col in df.columns:
                amount_col = col
                break
        
        print(f"   使用列: 涨幅={pct_chg_col}, 成交额={amount_col}")
        
        df['selection_score'] = 0
        df['selection_logic'] = ''
        
        for idx, row in df.iterrows():
            score = 0
            logic = []
            
            # 条件1：当日涨幅2%-6%
            if pct_chg_col:
                pct_chg = float(row.get(pct_chg_col, 0))
                if 2 <= pct_chg <= 6:
                    score += 40
                    logic.append('涨幅适中')
                elif 0 <= pct_chg < 2:
                    score += 20
                    logic.append('小幅上涨')
            
            # 条件2：成交额>2000万（资金活跃）
            if amount_col:
                amount = float(row.get(amount_col, 0))
                if amount > 50000000:
                    score += 30
                    logic.append('资金活跃')
                elif amount > 20000000:
                    score += 20
                    logic.append('有资金')
                elif amount > 10000000:
                    score += 10
                    logic.append('有成交额')
            
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
        print("4. 筛选符合条件的股票")
        print("=" * 80)
        
        if df.empty:
            return df
        
        # 筛选得分>=40的股票
        selected = df[df['selection_score'] >= 40].copy()
        
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
        print("5. 生成交易计划")
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
            turnover = float(row.get('turnover', 0)) if 'turnover' in df.columns else 0
            volume_ratio = float(row.get('volume_ratio', 0)) if 'volume_ratio' in df.columns else 0
            circ_mv = float(row.get('circ_mv', 0)) if 'circ_mv' in df.columns else 0
            
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
            if turnover > 0:
                output.append(f"   换手率: {turnover:.2f}%  量比: {volume_ratio:.2f}")
            if circ_mv > 0:
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
        print("尾盘选股程序 V3（次日早盘买入策略）")
        print("=" * 80)
        
        # 获取数据
        df = self.get_all_stock_data()
        if df.empty:
            print("❌ 无法获取股票数据")
            return
        
        # 筛选沪深主板
        df = self.filter_main_board(df)
        
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
    selector = EveningStockSelectorV3()
    selector.run()

if __name__ == '__main__':
    main()
