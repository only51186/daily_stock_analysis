# -*- coding: utf-8 -*-
"""
检查股票数据详情
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.data.smart_data_manager import SmartDataManager
import pandas as pd

def check_stock_details():
    """检查股票数据详情"""
    print("=" * 80)
    print("检查股票数据详情")
    print("=" * 80)
    
    smart_dm = SmartDataManager()
    
    # 获取所有股票数据
    data = smart_dm.get_smart_stock_daily()
    
    if data.empty:
        print("❌ 没有获取到股票数据")
        return
    
    print(f"📊 总股票数量: {len(data)} 只")
    print(f"📅 数据日期: {data['date'].iloc[0]}")
    
    # 检查前10只股票的详细信息
    print("\n📋 前10只股票详情:")
    for i, (_, stock) in enumerate(data.head(10).iterrows(), 1):
        print(f"\n{i}. 代码: {stock['code']}")
        print(f"   名称: {stock.get('name', 'N/A')}")
        print(f"   涨幅: {stock.get('pct_chg', 'N/A')}%")
        print(f"   换手率: {stock.get('turnover', 'N/A')}")
        print(f"   量比: {stock.get('volume_ratio', 'N/A')}")
        print(f"   流通市值: {stock.get('circ_mv', 'N/A')}")
    
    # 检查股票代码格式
    print("\n🔍 股票代码格式分析:")
    codes = data['code'].unique()
    print(f"   唯一代码数量: {len(codes)}")
    print("   前10个代码:")
    for i, code in enumerate(codes[:10], 1):
        print(f"     {i}. {code}")
    
    # 检查代码前缀分布
    print("\n📊 代码前缀分布:")
    prefixes = {}
    for code in codes:
        if pd.notna(code) and len(str(code)) >= 2:
            prefix = str(code)[:2]
            prefixes[prefix] = prefixes.get(prefix, 0) + 1
    
    for prefix, count in sorted(prefixes.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"   {prefix}开头: {count} 只")
    
    # 检查是否有60/00开头的股票
    main_board_codes = [code for code in codes if str(code).startswith(('60', '00'))]
    print(f"\n🎯 沪深主板A股数量: {len(main_board_codes)} 只")
    
    if main_board_codes:
        print("   主板股票代码示例:")
        for code in main_board_codes[:5]:
            print(f"     {code}")

if __name__ == "__main__":
    check_stock_details()