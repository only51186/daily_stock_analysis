# -*- coding: utf-8 -*-
"""
确认股票数据的真实日期
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.data.data_manager import DataManager
import pandas as pd

def check_real_date():
    """确认真实数据日期"""
    print("=" * 80)
    print("确认股票数据的真实日期")
    print("=" * 80)
    
    dm = DataManager()
    data = dm.get_stock_daily()
    
    if data.empty:
        print("❌ 数据库中没有股票数据")
        return
    
    print(f"📊 总股票数量: {len(data)} 只")
    
    # 检查数据日期
    if 'date' in data.columns:
        unique_dates = sorted(data['date'].unique())
        
        print(f"\n📅 数据中的所有日期:")
        for i, date in enumerate(unique_dates, 1):
            count = len(data[data['date'] == date])
            print(f"   {i}. {date}: {count} 只股票")
        
        # 最新日期
        latest_date = unique_dates[-1] if unique_dates else None
        print(f"\n🎯 最新数据日期: {latest_date}")
        
        # 检查今天和昨天的真实日期
        today = datetime.now()
        today_str = today.strftime('%Y-%m-%d')
        yesterday = (today - pd.Timedelta(days=1))
        yesterday_str = yesterday.strftime('%Y-%m-%d')
        
        print(f"\n📆 日期对比:")
        print(f"   今天日期: {today_str}")
        print(f"   昨天日期: {yesterday_str}")
        print(f"   最新数据日期: {latest_date}")
        
        # 判断数据日期
        if latest_date == today_str:
            print("✅ 数据是最新的（今天）")
            return 'today'
        elif latest_date == yesterday_str:
            print("⚠️ 数据是昨天的")
            return 'yesterday'
        else:
            print("❌ 数据不是今天也不是昨天")
            return 'other'
    
    return 'unknown'

if __name__ == "__main__":
    result = check_real_date()
    print(f"\n📋 数据日期判断结果: {result}")