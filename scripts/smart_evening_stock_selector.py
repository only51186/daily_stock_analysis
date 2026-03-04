# -*- coding: utf-8 -*-
"""
===================================
智能尾盘选股程序（使用智能数据管理器）
===================================

功能：
1. 使用智能数据管理器，自动判断15点前后数据策略
2. 每次选股前自动检查数据存在性，避免重复下载
3. 基于时间的数据获取策略

时间策略：
- 15:00之前：使用昨天数据选股
- 15:00之后：使用当天数据选股
- 每次选股前检查数据存在性
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
from src.data.smart_data_manager import SmartDataManager

logger = setup_logger(__name__, log_file='logs/smart_evening_selector.log')

load_dotenv()

class SmartEveningStockSelector:
    """
    智能尾盘选股器（使用智能数据管理器）
    """
    
    def __init__(self):
        self.stock_data = None
        self.selected_stocks = []
        self.data_source = "SmartDataManager"
        self.today = datetime.now().strftime('%Y-%m-%d')
        self.smart_dm = SmartDataManager()
        
    def get_stock_data(self) -> pd.DataFrame:
        """
        智能获取股票数据
        使用智能数据管理器，自动判断15点前后数据策略
        """
        print("=" * 80)
        print("1. 智能获取股票数据")
        print("=" * 80)
        
        print("📊 使用智能数据管理器...")
        
        # 使用智能数据管理器获取数据
        data = self.smart_dm.get_smart_stock_daily()
        
        if data.empty:
            print("❌ 无法获取股票数据")
            return pd.DataFrame()
        
        print(f"✅ 智能获取数据成功: {len(data)} 只股票")
        
        # 标准化列名
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
            if old_col in data.columns:
                data[new_col] = data[old_col]
        
        # 确保数值类型正确
        numeric_columns = ['open', 'high', 'low', 'close', 'pre_close', 
                         'change', 'pct_chg', 'volume', 'amount', 
                         'turnover', 'volume_ratio', 'circ_mv', 
                         'total_mv', 'amplitude']
        
        for col in numeric_columns:
            if col in data.columns:
                data[col] = pd.to_numeric(data[col], errors='coerce')
        
        return data
    
    def filter_stocks(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        筛选符合条件的股票
        """
        print("\n2. 筛选符合条件的股票")
        print("=" * 80)
        
        if df.empty:
            print("❌ 数据为空，无法筛选")
            return pd.DataFrame()
        
        # 复制数据避免修改原数据
        filtered_df = df.copy()
        
        # 筛选沪深主板A股（60/00开头）
        filtered_df = filtered_df[
            filtered_df['code'].str.startswith(('60', '00'), na=False)
        ]
        print(f"✅ 沪深主板A股: {len(filtered_df)} 只")
        
        # 排除ST股
        filtered_df = filtered_df[
            ~filtered_df['name'].str.contains('ST|退', na=False)
        ]
        print(f"✅ 排除ST股后: {len(filtered_df)} 只")
        
        # 筛选涨幅3%-5%
        if 'pct_chg' in filtered_df.columns:
            filtered_df = filtered_df[
                (filtered_df['pct_chg'] >= 3) & 
                (filtered_df['pct_chg'] <= 5)
            ]
            print(f"✅ 涨幅3%-5%: {len(filtered_df)} 只")
        
        # 筛选换手率3%-10%
        if 'turnover' in filtered_df.columns:
            filtered_df = filtered_df[
                (filtered_df['turnover'] >= 3) & 
                (filtered_df['turnover'] <= 10)
            ]
            print(f"✅ 换手率3%-10%: {len(filtered_df)} 只")
        
        # 筛选量比1.2-5
        if 'volume_ratio' in filtered_df.columns:
            filtered_df = filtered_df[
                (filtered_df['volume_ratio'] >= 1.2) & 
                (filtered_df['volume_ratio'] <= 5)
            ]
            print(f"✅ 量比1.2-5: {len(filtered_df)} 只")
        
        # 筛选流通市值30亿-200亿
        if 'circ_mv' in filtered_df.columns:
            filtered_df = filtered_df[
                (filtered_df['circ_mv'] >= 30) & 
                (filtered_df['circ_mv'] <= 200)
            ]
            print(f"✅ 流通市值30亿-200亿: {len(filtered_df)} 只")
        
        print(f"🎯 最终筛选结果: {len(filtered_df)} 只股票")
        
        return filtered_df
    
    def select_stocks(self) -> List[Dict[str, Any]]:
        """
        执行选股流程
        """
        print("=" * 80)
        print("开始智能尾盘选股")
        print("=" * 80)
        
        # 1. 获取股票数据
        self.stock_data = self.get_stock_data()
        
        if self.stock_data.empty:
            print("❌ 获取股票数据失败")
            return []
        
        # 2. 筛选股票
        filtered_stocks = self.filter_stocks(self.stock_data)
        
        if filtered_stocks.empty:
            print("❌ 没有符合条件的股票")
            return []
        
        # 3. 排序并选择前10只
        if 'pct_chg' in filtered_stocks.columns:
            filtered_stocks = filtered_stocks.sort_values('pct_chg', ascending=False)
        
        selected_df = filtered_stocks.head(10)
        
        # 4. 转换为字典列表
        self.selected_stocks = []
        for _, row in selected_df.iterrows():
            stock_info = {
                'code': row.get('code', ''),
                'name': row.get('name', ''),
                'close': row.get('close', 0),
                'pct_chg': row.get('pct_chg', 0),
                'turnover': row.get('turnover', 0),
                'volume_ratio': row.get('volume_ratio', 0),
                'circ_mv': row.get('circ_mv', 0),
                'amount': row.get('amount', 0),
                'date': row.get('date', self.today)
            }
            self.selected_stocks.append(stock_info)
        
        print(f"\n🎯 选股完成！共选出 {len(self.selected_stocks)} 只股票")
        
        # 打印选股结果
        for i, stock in enumerate(self.selected_stocks, 1):
            print(f"{i}. {stock['code']} {stock['name']} "
                  f"涨幅: {stock['pct_chg']:.2f}% "
                  f"换手: {stock['turnover']:.2f}% "
                  f"量比: {stock['volume_ratio']:.2f}")
        
        return self.selected_stocks
    
    def save_results(self):
        """
        保存选股结果
        """
        if not self.selected_stocks:
            print("❌ 没有选股结果需要保存")
            return
        
        # 保存到文件
        results_dir = 'results'
        os.makedirs(results_dir, exist_ok=True)
        
        filename = f"{results_dir}/smart_evening_selection_{self.today}.txt"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"智能尾盘选股结果 - {self.today}\n")
            f.write("=" * 50 + "\n")
            f.write(f"数据源: {self.data_source}\n")
            f.write(f"选股时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"选股数量: {len(self.selected_stocks)}\n\n")
            
            for i, stock in enumerate(self.selected_stocks, 1):
                f.write(f"{i}. {stock['code']} {stock['name']} "
                       f"收盘价: {stock['close']:.2f} "
                       f"涨幅: {stock['pct_chg']:.2f}% "
                       f"换手: {stock['turnover']:.2f}% "
                       f"量比: {stock['volume_ratio']:.2f} "
                       f"流通市值: {stock['circ_mv']:.2f}亿\n")
        
        print(f"✅ 选股结果已保存到: {filename}")


def main():
    """
    主函数
    """
    print("🚀 启动智能尾盘选股程序")
    
    selector = SmartEveningStockSelector()
    
    # 执行选股
    selected_stocks = selector.select_stocks()
    
    # 保存结果
    selector.save_results()
    
    print("\n✅ 智能尾盘选股程序执行完成")


if __name__ == "__main__":
    main()