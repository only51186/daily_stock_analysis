# -*- coding: utf-8 -*-
"""
检查沪深主板股票数量
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.data.data_manager import DataManager
import pandas as pd

def check_stock_count():
    """检查股票数量"""
    print("=" * 80)
    print("检查沪深主板股票数量")
    print("=" * 80)
    
    dm = DataManager()
    
    # 获取所有股票数据
    data = dm.get_stock_daily()
    
    if data.empty:
        print("❌ 数据库中没有股票数据")
        return
    
    print(f"📊 总股票数量: {len(data)} 只")
    print(f"📅 数据日期: {data['date'].iloc[0]}")
    
    # 分类统计
    print("\n📈 股票分类统计:")
    
    # 1. 沪深主板A股（60/00开头）
    main_board = data[data['code'].str.startswith(('60', '00'), na=False)]
    print(f"   沪深主板A股: {len(main_board)} 只")
    
    # 2. 创业板（30开头）
    gem_board = data[data['code'].str.startswith('30', na=False)]
    print(f"   创业板: {len(gem_board)} 只")
    
    # 3. 科创板（68开头）
    star_board = data[data['code'].str.startswith('68', na=False)]
    print(f"   科创板: {len(star_board)} 只")
    
    # 4. 北交所（bj开头）
    bj_board = data[data['code'].str.startswith('bj', na=False)]
    print(f"   北交所: {len(bj_board)} 只")
    
    # 5. 其他
    other_board = data[~data['code'].str.startswith(('60', '00', '30', '68', 'bj'), na=False)]
    print(f"   其他: {len(other_board)} 只")
    
    # 显示沪深主板股票详情
    if len(main_board) > 0:
        print(f"\n📋 沪深主板股票列表 ({len(main_board)} 只):")
        print("=" * 120)
        print(f"{'代码':<10} {'名称':<15} {'涨幅(%)':<8} {'收盘价':<8} {'换手率(%)':<10} {'量比':<8} {'成交额(万)':<12}")
        print("=" * 120)
        
        for i, (_, stock) in enumerate(main_board.iterrows(), 1):
            code = stock.get('code', 'N/A')
            name = stock.get('name', 'N/A')
            pct_chg = stock.get('pct_chg', 0)
            close = stock.get('close', 0)
            turnover = stock.get('turnover', 0)
            volume_ratio = stock.get('volume_ratio', 0)
            amount = stock.get('amount', 0)
            
            # 格式化显示
            amount_formatted = f"{amount/10000:.0f}" if amount > 0 else "N/A"
            
            print(f"{code:<10} {name:<15} {pct_chg:<8.2f} {close:<8.2f} {turnover:<10.2f} {volume_ratio:<8.2f} {amount_formatted:<12}")
        
        print("=" * 120)
        
        # 统计主板股票信息
        print(f"\n📊 沪深主板股票统计:")
        print(f"   平均涨幅: {main_board['pct_chg'].mean():.2f}%")
        print(f"   最高涨幅: {main_board['pct_chg'].max():.2f}%")
        print(f"   最低涨幅: {main_board['pct_chg'].min():.2f}%")
        print(f"   平均换手率: {main_board['turnover'].mean():.2f}%")
        print(f"   平均量比: {main_board['volume_ratio'].mean():.2f}")
        print(f"   总成交额: {main_board['amount'].sum()/10000:.0f} 万元")
    
    # 检查股票代码格式
    print(f"\n🔍 股票代码格式分析:")
    codes = data['code'].unique()
    print(f"   唯一代码数量: {len(codes)}")
    print("   前10个代码:")
    for i, code in enumerate(codes[:10], 1):
        print(f"     {i}. {code}")

if __name__ == "__main__":
    check_stock_count()