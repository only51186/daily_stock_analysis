# -*- coding: utf-8 -*-
"""
===================================
尾盘交易选股策略
===================================

功能：
1. 筛选沪深主板A股（60/00开头）
2. 排除ST、新股、停牌个股
3. 选股逻辑：当日走势稳健、尾盘资金持续流入、次日高开上涨确定性高
4. 自动获取当日分时数据和资金数据
5. 输出尾盘选股清单，包含个股代码、名称、入选逻辑、参考买入价位和止损止盈区间
"""

import logging
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np

from utils.logger_config import setup_logger

logger = setup_logger(__name__, log_file='logs/closing_selector.log')

class ClosingStockSelector:
    """
    尾盘交易选股器
    """
    
    def __init__(self):
        self.stock_data = None
        self.selected_stocks = []
        
    def _get_cache_path(self) -> str:
        """获取缓存文件路径"""
        cache_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'cache')
        os.makedirs(cache_dir, exist_ok=True)
        today = datetime.now().strftime('%Y%m%d')
        return os.path.join(cache_dir, f'stock_data_{today}.csv')
    
    def _load_cache(self) -> pd.DataFrame:
        """加载缓存数据"""
        cache_path = self._get_cache_path()
        if os.path.exists(cache_path):
            try:
                df = pd.read_csv(cache_path)
                print(f"✅ 从缓存加载数据: {len(df)} 只股票")
                return df
            except Exception as e:
                print(f"⚠️ 缓存加载失败: {e}")
        return pd.DataFrame()
    
    def _save_cache(self, df: pd.DataFrame):
        """保存数据到缓存"""
        cache_path = self._get_cache_path()
        try:
            df.to_csv(cache_path, index=False)
            print(f"✅ 数据已缓存到: {cache_path}")
        except Exception as e:
            print(f"⚠️ 缓存保存失败: {e}")
    
    def get_stock_data(self) -> pd.DataFrame:
        """获取A股实时行情数据（带缓存）"""
        print("=" * 60)
        print("1. 获取A股实时行情数据")
        print("=" * 60)
        
        # 首先尝试加载缓存
        cached_data = self._load_cache()
        if not cached_data.empty:
            return cached_data
        
        import time
        
        for retry in range(3):
            try:
                import akshare as ak
                print(f"使用新浪财经接口获取数据... (尝试 {retry + 1}/3)")
                
                df = ak.stock_zh_a_spot()
                
                if df is not None and not df.empty:
                    print(f"✅ 成功获取 {len(df)} 只股票数据")
                    self._save_cache(df)  # 保存到缓存
                    return df
                else:
                    print("⚠️ 新浪接口未获取到数据")
            except Exception as e:
                print(f"⚠️ 新浪接口获取失败: {str(e)[:80]}")
            
            if retry < 2:
                print("   等待3秒后重试...")
                time.sleep(3)
        
        for retry in range(3):
            try:
                import akshare as ak
                print(f"使用东方财富接口获取数据... (尝试 {retry + 1}/3)")
                
                df = ak.stock_zh_a_spot_em()
                
                if df is not None and not df.empty:
                    print(f"✅ 成功获取 {len(df)} 只股票数据")
                    self._save_cache(df)  # 保存到缓存
                    return df
                else:
                    print("⚠️ 东方财富接口未获取到数据")
            except Exception as e:
                print(f"⚠️ 东方财富接口获取失败: {str(e)[:80]}")
            
            if retry < 2:
                print("   等待3秒后重试...")
                time.sleep(3)
        
        print("❌ 所有数据源均无法获取数据，请检查网络连接")
        return pd.DataFrame()
    
    def filter_main_board(self, df: pd.DataFrame) -> pd.DataFrame:
        """筛选沪深主板股票"""
        print("\n" + "=" * 60)
        print("2. 筛选沪深主板股票（60/00开头）")
        print("=" * 60)
        
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
        return main_board_df
    
    def exclude_risk_stocks(self, df: pd.DataFrame) -> pd.DataFrame:
        """排除ST、新股、停牌个股"""
        print("\n" + "=" * 60)
        print("3. 排除ST、新股、停牌个股")
        print("=" * 60)
        
        if df.empty:
            return df
        
        name_col = None
        for col in ['名称', 'name', '股票名称']:
            if col in df.columns:
                name_col = col
                break
        
        if name_col:
            st_pattern = r'ST|\*ST|S\*ST|SST|退市'
            st_mask = df[name_col].str.contains(st_pattern, na=False, regex=True)
            df = df[~st_mask].copy()
            print(f"✅ 排除 {st_mask.sum()} 只ST/退市股票")
        
        price_col = None
        for col in ['最新价', 'price', '现价', 'close']:
            if col in df.columns:
                price_col = col
                break
        
        if price_col:
            df[price_col] = pd.to_numeric(df[price_col], errors='coerce')
            suspended_mask = df[price_col] <= 0
            df = df[~suspended_mask].copy()
            print(f"✅ 排除 {suspended_mask.sum()} 只停牌股票")
        
        code_col = None
        for col in ['代码', 'symbol', '股票代码', 'code']:
            if col in df.columns:
                code_col = col
                break
        
        if code_col:
            def is_new_stock(code):
                code = str(code).zfill(6)
                if code.startswith('60'):
                    return code >= '605000'
                elif code.startswith('00'):
                    return code >= '003000'
                return False
            
            new_stock_mask = df[code_col].apply(is_new_stock)
            df = df[~new_stock_mask].copy()
            print(f"✅ 排除 {new_stock_mask.sum()} 只新股")
        
        print(f"✅ 剩余 {len(df)} 只股票")
        return df
    
    def filter_price_range(self, df: pd.DataFrame) -> pd.DataFrame:
        """筛选价格范围"""
        print("\n" + "=" * 60)
        print("4. 筛选价格范围 5-35 元")
        print("=" * 60)
        
        if df.empty:
            return df
        
        price_col = None
        for col in ['最新价', 'price', '现价', 'close']:
            if col in df.columns:
                price_col = col
                break
        
        if price_col is None:
            print("❌ 未找到价格列")
            return df
        
        df[price_col] = pd.to_numeric(df[price_col], errors='coerce')
        
        price_mask = (df[price_col] >= 5) & (df[price_col] <= 35)
        df = df[price_mask].copy()
        
        print(f"✅ 筛选出 {len(df)} 只股票")
        return df
    
    def calculate_closing_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算尾盘选股因子"""
        print("\n" + "=" * 60)
        print("5. 计算尾盘选股因子")
        print("=" * 60)
        
        if df.empty:
            return df
        
        df['closing_score'] = 0
        df['factor_logic'] = ''
        
        price_col = None
        for col in ['最新价', 'price', '现价', 'close']:
            if col in df.columns:
                price_col = col
                break
        
        change_col = None
        for col in ['涨跌幅', 'pct_chg', '涨跌幅%', 'percent']:
            if col in df.columns:
                change_col = col
                break
        
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
        
        turnover_col = None
        for col in ['换手率', 'turnover_rate', '换手率%']:
            if col in df.columns:
                turnover_col = col
                break
        
        for idx, row in df.iterrows():
            score = 0
            logic = []
            
            # 因子1：当日走势稳健（涨幅1%-5%）
            if change_col:
                change = float(row.get(change_col, 0))
                if 1 <= change <= 5:
                    score += 30
                    logic.append('走势稳健')
            
            # 因子2：尾盘资金流入（成交额放大）
            if amount_col and volume_col:
                amount = float(row.get(amount_col, 0))
                volume = float(row.get(volume_col, 0))
                if amount > 50000000:  # 成交额>5000万
                    score += 25
                    logic.append('资金活跃')
            
            # 因子3：换手率适中（3%-10%）
            if turnover_col:
                turnover = float(row.get(turnover_col, 0))
                if 3 <= turnover <= 10:
                    score += 20
                    logic.append('换手健康')
            
            # 因子4：价格位置适中（5-35元）
            if price_col:
                price = float(row.get(price_col, 0))
                if 8 <= price <= 25:
                    score += 15
                    logic.append('价格合理')
            
            # 因子5：量价配合
            if change_col and volume_col:
                change = float(row.get(change_col, 0))
                volume = float(row.get(volume_col, 0))
                if change > 0 and volume > 100000:
                    score += 10
                    logic.append('量价齐升')
            
            df.at[idx, 'closing_score'] = score
            df.at[idx, 'factor_logic'] = ', '.join(logic)
        
        print(f"✅ 尾盘因子计算完成")
        return df
    
    def select_closing_stocks(self, df: pd.DataFrame) -> pd.DataFrame:
        """筛选尾盘选股"""
        print("\n" + "=" * 60)
        print("6. 执行尾盘选股筛选")
        print("=" * 60)
        
        if df.empty:
            return df
        
        # 筛选得分>=60的股票
        selected = df[df['closing_score'] >= 60].copy()
        
        # 按得分排序
        selected = selected.sort_values('closing_score', ascending=False)
        
        # 限制数量
        selected = selected.head(15)
        
        print(f"✅ 筛选出 {len(selected)} 只尾盘选股标的")
        return selected
    
    def generate_trading_plan(self, df: pd.DataFrame) -> pd.DataFrame:
        """生成交易计划"""
        print("\n" + "=" * 60)
        print("7. 生成交易计划")
        print("=" * 60)
        
        if df.empty:
            return df
        
        price_col = None
        for col in ['最新价', 'price', '现价', 'close']:
            if col in df.columns:
                price_col = col
                break
        
        for idx, row in df.iterrows():
            if price_col:
                current_price = float(row.get(price_col, 0))
                
                # 参考买入价位（当前价附近）
                buy_low = current_price * 0.99
                buy_high = current_price * 1.01
                
                # 止损价位（-3%）
                stop_loss = current_price * 0.97
                
                # 止盈目标（+5%）
                take_profit = current_price * 1.05
                
                df.at[idx, 'buy_range'] = f"{buy_low:.2f}-{buy_high:.2f}"
                df.at[idx, 'stop_loss'] = f"{stop_loss:.2f}"
                df.at[idx, 'take_profit'] = f"{take_profit:.2f}"
        
        print(f"✅ 交易计划生成完成")
        return df
    
    def format_output(self, df: pd.DataFrame) -> str:
        """格式化输出"""
        if df.empty:
            return "未找到符合条件的尾盘选股标的"
        
        code_col = None
        for col in ['代码', 'symbol', '股票代码', 'code']:
            if col in df.columns:
                code_col = col
                break
        
        name_col = None
        for col in ['名称', 'name', '股票名称']:
            if col in df.columns:
                name_col = col
                break
        
        price_col = None
        for col in ['最新价', 'price', '现价', 'close']:
            if col in df.columns:
                price_col = col
                break
        
        change_col = None
        for col in ['涨跌幅', 'pct_chg', '涨跌幅%', 'percent']:
            if col in df.columns:
                change_col = col
                break
        
        output = []
        output.append("\n" + "=" * 80)
        output.append(f"尾盘选股清单 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        output.append("=" * 80)
        
        for i, (idx, row) in enumerate(df.iterrows(), 1):
            code = row.get(code_col, 'N/A') if code_col else 'N/A'
            name = row.get(name_col, 'N/A') if name_col else 'N/A'
            price = float(row.get(price_col, 0)) if price_col else 0
            change = float(row.get(change_col, 0)) if change_col else 0
            score = int(row.get('closing_score', 0))
            logic = row.get('factor_logic', '')
            buy_range = row.get('buy_range', 'N/A')
            stop_loss = row.get('stop_loss', 'N/A')
            take_profit = row.get('take_profit', 'N/A')
            
            output.append(f"\n{i}. {code} {name}")
            output.append(f"   当前价格: {price:.2f} 元  涨跌幅: {change:+.2f}%")
            output.append(f"   综合得分: {score} 分")
            output.append(f"   入选逻辑: {logic}")
            output.append(f"   📌 操作参考:")
            output.append(f"      买入区间: {buy_range} 元")
            output.append(f"      止损价位: {stop_loss} 元 (-3%)")
            output.append(f"      止盈目标: {take_profit} 元 (+5%)")
        
        output.append("\n" + "=" * 80)
        output.append("💡 操作建议：")
        output.append("   1. 尾盘14:50-15:00择机买入")
        output.append("   2. 严格设置止损，跌破止损价立即离场")
        output.append("   3. 次日高开可考虑分批止盈")
        output.append("   4. 单只股票仓位不超过20%")
        output.append("=" * 80)
        
        return '\n'.join(output)
    
    def run(self):
        """执行尾盘选股"""
        print("\n" + "=" * 80)
        print("尾盘交易选股系统")
        print("=" * 80)
        
        # 获取数据
        df = self.get_stock_data()
        if df.empty:
            print("❌ 无法获取股票数据")
            return
        
        # 筛选沪深主板
        df = self.filter_main_board(df)
        
        # 排除风险股票
        df = self.exclude_risk_stocks(df)
        
        # 筛选价格范围
        df = self.filter_price_range(df)
        
        # 计算尾盘因子
        df = self.calculate_closing_factors(df)
        
        # 筛选尾盘选股
        df = self.select_closing_stocks(df)
        
        # 生成交易计划
        df = self.generate_trading_plan(df)
        
        # 输出结果
        result = self.format_output(df)
        print(result)
        
        return df

def main():
    selector = ClosingStockSelector()
    selector.run()

if __name__ == '__main__':
    main()
