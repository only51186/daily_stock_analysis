# -*- coding: utf-8 -*-
"""
检查股票数据的最新日期
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.data.data_manager import DataManager
import pandas as pd

def check_data_date():
    """检查数据日期"""
    print("=" * 80)
    print("检查股票数据的最新日期")
    print("=" * 80)
    
    dm = DataManager()
    
    # 获取所有股票数据
    data = dm.get_stock_daily()
    
    if data.empty:
        print("❌ 数据库中没有股票数据")
        return
    
    print(f"📊 总股票数量: {len(data)} 只")
    
    # 检查数据日期
    if 'date' in data.columns:
        unique_dates = data['date'].unique()
        print(f"📅 数据中包含的日期: {len(unique_dates)} 个")
        
        # 按日期排序
        sorted_dates = sorted(unique_dates)
        
        print("\n📋 所有日期列表:")
        for i, date in enumerate(sorted_dates, 1):
            count = len(data[data['date'] == date])
            print(f"   {i}. {date}: {count} 只股票")
        
        # 最新日期
        latest_date = sorted_dates[-1] if sorted_dates else None
        print(f"\n🎯 最新数据日期: {latest_date}")
        
        # 检查今天和昨天
        today = datetime.now().strftime('%Y-%m-%d')
        yesterday = (datetime.now() - pd.Timedelta(days=1)).strftime('%Y-%m-%d')
        
        print(f"\n📆 时间对比:")
        print(f"   今天日期: {today}")
        print(f"   昨天日期: {yesterday}")
        print(f"   最新数据日期: {latest_date}")
        
        # 判断数据日期
        if latest_date == today:
            print("✅ 数据是最新的（今天）")
        elif latest_date == yesterday:
            print("⚠️ 数据是昨天的")
        else:
            print("❌ 数据不是今天也不是昨天")
        
        # 显示最新日期的股票统计
        latest_data = data[data['date'] == latest_date]
        if not latest_data.empty:
            print(f"\n📈 最新日期股票统计 ({latest_date}):")
            print(f"   股票数量: {len(latest_data)} 只")
            
            if 'pct_chg' in latest_data.columns:
                pct_stats = latest_data['pct_chg'].describe()
                print(f"   平均涨幅: {pct_stats['mean']:.2f}%")
                print(f"   最高涨幅: {pct_stats['max']:.2f}%")
                print(f"   最低涨幅: {pct_stats['min']:.2f}%")
            
            # 显示前10只股票
            print(f"\n📋 最新日期前10只股票:")
            for i, (_, stock) in enumerate(latest_data.head(10).iterrows(), 1):
                print(f"   {i}. {stock['code']} {stock.get('name', 'N/A')} "
                      f"涨幅: {stock.get('pct_chg', 0):.2f}% "
                      f"收盘价: {stock.get('close', 0):.2f}")
    
    # 检查数据完整性
    print(f"\n🔍 数据完整性检查:")
    
    # 检查是否有重复数据
    duplicate_count = data.duplicated(subset=['code', 'date']).sum()
    print(f"   重复数据条数: {duplicate_count}")
    
    # 检查缺失值
    missing_info = []
    for col in ['code', 'date', 'close', 'pct_chg']:
        if col in data.columns:
            missing_count = data[col].isna().sum()
            missing_info.append(f"{col}: {missing_count}")
    
    print(f"   缺失值统计: {', '.join(missing_info)}")
    
    # 检查股票代码格式
    print(f"\n🔧 股票代码格式检查:")
    codes = data['code'].unique()
    print(f"   唯一代码数量: {len(codes)}")
    
    # 分类统计
    main_board = data[data['code'].str.startswith(('60', '00'), na=False)]
    gem_board = data[data['code'].str.startswith('30', na=False)]
    star_board = data[data['code'].str.startswith('68', na=False)]
    
    print(f"   沪深主板A股: {len(main_board)} 只")
    print(f"   创业板: {len(gem_board)} 只")
    print(f"   科创板: {len(star_board)} 只")

if __name__ == "__main__":
    check_data_date()