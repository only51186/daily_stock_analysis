# -*- coding: utf-8 -*-
"""
检查股票数据，分析为什么没有选出股票（修复版）
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.data.smart_data_manager import SmartDataManager
import pandas as pd

def analyze_stock_data():
    """分析股票数据"""
    print("=" * 80)
    print("分析股票数据 - 为什么没有选出股票")
    print("=" * 80)
    
    smart_dm = SmartDataManager()
    
    # 获取所有股票数据
    data = smart_dm.get_smart_stock_daily()
    
    if data.empty:
        print("❌ 没有获取到股票数据")
        return
    
    print(f"📊 总股票数量: {len(data)} 只")
    print(f"📅 数据日期: {data['date'].iloc[0]}")
    
    # 检查数据列
    print("\n📋 数据列信息:")
    for col in data.columns:
        print(f"   {col}: {data[col].dtype}")
    
    # 修复数据类型问题
    print("\n🔧 修复数据类型...")
    numeric_columns = ['turnover', 'volume_ratio', 'circ_mv', 'total_mv', 'amplitude']
    for col in numeric_columns:
        if col in data.columns:
            data[col] = pd.to_numeric(data[col], errors='coerce')
            print(f"   修复 {col}: {data[col].dtype}")
    
    # 检查沪深主板A股（60/00开头）
    print("\n🔍 检查沪深主板A股:")
    main_board = data[data['code'].str.startswith(('60', '00'), na=False)]
    print(f"   沪深主板A股数量: {len(main_board)} 只")
    
    if len(main_board) > 0:
        print("   前5只主板股票:")
        for i, (_, stock) in enumerate(main_board.head(5).iterrows(), 1):
            print(f"     {i}. {stock['code']} {stock.get('name', 'N/A')}")
    
    # 检查涨幅分布
    if 'pct_chg' in data.columns:
        print("\n📈 涨幅分布:")
        pct_chg_stats = data['pct_chg'].describe()
        print(f"   最小值: {pct_chg_stats['min']:.2f}%")
        print(f"   最大值: {pct_chg_stats['max']:.2f}%")
        print(f"   平均值: {pct_chg_stats['mean']:.2f}%")
        print(f"   中位数: {data['pct_chg'].median():.2f}%")
        
        # 涨幅区间统计
        ranges = [(-10, -5), (-5, 0), (0, 1), (1, 3), (3, 5), (5, 10), (10, 100)]
        for low, high in ranges:
            count = len(data[(data['pct_chg'] >= low) & (data['pct_chg'] < high)])
            print(f"   {low}%~{high}%: {count} 只")
    
    # 检查换手率分布
    if 'turnover' in data.columns:
        print("\n🔄 换手率分布:")
        turnover_stats = data['turnover'].describe()
        print(f"   最小值: {turnover_stats['min']:.2f}%")
        print(f"   最大值: {turnover_stats['max']:.2f}%")
        print(f"   平均值: {turnover_stats['mean']:.2f}%")
        
        # 换手率区间统计
        ranges = [(0, 1), (1, 3), (3, 5), (5, 10), (10, 20), (20, 100)]
        for low, high in ranges:
            count = len(data[(data['turnover'] >= low) & (data['turnover'] < high)])
            print(f"   {low}%~{high}%: {count} 只")
    
    # 检查量比分布
    if 'volume_ratio' in data.columns:
        print("\n📊 量比分布:")
        volume_ratio_stats = data['volume_ratio'].describe()
        print(f"   最小值: {volume_ratio_stats['min']:.2f}")
        print(f"   最大值: {volume_ratio_stats['max']:.2f}")
        print(f"   平均值: {volume_ratio_stats['mean']:.2f}")
        
        # 量比区间统计
        ranges = [(0, 0.5), (0.5, 1), (1, 1.2), (1.2, 2), (2, 5), (5, 100)]
        for low, high in ranges:
            count = len(data[(data['volume_ratio'] >= low) & (data['volume_ratio'] < high)])
            if count > 0:
                print(f"   {low}~{high}: {count} 只")
    
    # 检查流通市值分布
    if 'circ_mv' in data.columns:
        print("\n💰 流通市值分布 (亿元):")
        circ_mv_stats = data['circ_mv'].describe()
        print(f"   最小值: {circ_mv_stats['min']:.2f}")
        print(f"   最大值: {circ_mv_stats['max']:.2f}")
        print(f"   平均值: {circ_mv_stats['mean']:.2f}")
        
        # 流通市值区间统计
        ranges = [(0, 10), (10, 30), (30, 50), (50, 100), (100, 200), (200, 1000)]
        for low, high in ranges:
            count = len(data[(data['circ_mv'] >= low) & (data['circ_mv'] < high)])
            if count > 0:
                print(f"   {low}~{high}亿: {count} 只")
    
    # 尝试放宽筛选条件
    print("\n🔧 尝试放宽筛选条件:")
    
    # 条件1: 只筛选主板股票
    filtered = data[data['code'].str.startswith(('60', '00'), na=False)]
    print(f"   主板股票: {len(filtered)} 只")
    
    # 条件2: 排除ST股
    if 'name' in filtered.columns:
        filtered = filtered[~filtered['name'].str.contains('ST|退', na=False)]
        print(f"   排除ST股后: {len(filtered)} 只")
    
    # 条件3: 涨幅1%-10%
    if 'pct_chg' in filtered.columns:
        filtered = filtered[(filtered['pct_chg'] >= 1) & (filtered['pct_chg'] <= 10)]
        print(f"   涨幅1%-10%: {len(filtered)} 只")
    
    # 条件4: 换手率1%-15%
    if 'turnover' in filtered.columns:
        filtered = filtered[(filtered['turnover'] >= 1) & (filtered['turnover'] <= 15)]
        print(f"   换手率1%-15%: {len(filtered)} 只")
    
    # 条件5: 量比0.8-10
    if 'volume_ratio' in filtered.columns:
        filtered = filtered[(filtered['volume_ratio'] >= 0.8) & (filtered['volume_ratio'] <= 10)]
        print(f"   量比0.8-10: {len(filtered)} 只")
    
    # 条件6: 流通市值10-500亿
    if 'circ_mv' in filtered.columns:
        filtered = filtered[(filtered['circ_mv'] >= 10) & (filtered['circ_mv'] <= 500)]
        print(f"   流通市值10-500亿: {len(filtered)} 只")
    
    print(f"\n🎯 放宽条件后筛选结果: {len(filtered)} 只股票")
    
    if len(filtered) > 0:
        print("\n📋 符合条件的股票列表:")
        for i, (_, stock) in enumerate(filtered.head(20).iterrows(), 1):
            print(f"   {i}. {stock['code']} {stock.get('name', 'N/A')} "
                  f"涨幅: {stock.get('pct_chg', 0):.2f}% "
                  f"换手: {stock.get('turnover', 0):.2f}% "
                  f"量比: {stock.get('volume_ratio', 0):.2f} "
                  f"流通市值: {stock.get('circ_mv', 0):.2f}亿")
    
    # 检查原始筛选条件
    print("\n🔍 检查原始筛选条件:")
    
    # 原始条件: 涨幅3%-5%
    if 'pct_chg' in data.columns:
        count_3_5 = len(data[(data['pct_chg'] >= 3) & (data['pct_chg'] <= 5)])
        print(f"   涨幅3%-5%: {count_3_5} 只")
    
    # 原始条件: 换手率3%-10%
    if 'turnover' in data.columns:
        count_turnover = len(data[(data['turnover'] >= 3) & (data['turnover'] <= 10)])
        print(f"   换手率3%-10%: {count_turnover} 只")
    
    # 原始条件: 量比1.2-5
    if 'volume_ratio' in data.columns:
        count_volume_ratio = len(data[(data['volume_ratio'] >= 1.2) & (data['volume_ratio'] <= 5)])
        print(f"   量比1.2-5: {count_volume_ratio} 只")

if __name__ == "__main__":
    analyze_stock_data()