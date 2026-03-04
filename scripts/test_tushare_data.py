
# -*- coding: utf-8 -*-
"""
测试Tushare免费版数据获取能力
"""
import sys
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

def test_tushare_data():
    print("=" * 80)
    print("测试Tushare免费版数据获取能力")
    print("=" * 80)
    
    tushare_token = os.getenv('TUSHARE_TOKEN')
    if not tushare_token or tushare_token == 'your_tushare_token_here':
        print("Tushare Token未配置")
        return False
    
    try:
        import tushare as ts
        import time
        
        print("\n1. 初始化Tushare API...")
        pro = ts.pro_api(tushare_token)
        print("API初始化成功")
        
        # 尝试获取最近5天的数据
        print("\n2. 获取行情数据 (daily接口)...")
        for i in range(5):
            check_date = (datetime.now() - timedelta(days=i)).strftime('%Y%m%d')
            print("   尝试日期:", check_date)
            
            try:
                df = pro.daily(trade_date=check_date)
                
                if df is not None and not df.empty:
                    print("   获取成功:", len(df), "只股票")
                    print("   列名:", df.columns.tolist())
                    
                    # 显示第一只股票的数据
                    if len(df) > 0:
                        print("\n   示例数据:")
                        print(df.iloc[0])
                    
                    # 等待一下
                    time.sleep(0.5)
                    
                    # 尝试获取股票基础信息
                    print("\n3. 获取股票基础信息 (stock_basic接口)...")
                    try:
                        stock_basic = pro.stock_basic(exchange='', list_status='L')
                        if stock_basic is not None and not stock_basic.empty:
                            print("   获取成功:", len(stock_basic), "只股票")
                            print("   列名:", stock_basic.columns.tolist())
                            
                            # 显示第一只股票的数据
                            if len(stock_basic) > 0:
                                print("\n   示例数据:")
                                print(stock_basic.iloc[0])
                    except Exception as e:
                        print("   获取失败:", e)
                    
                    time.sleep(0.5)
                    
                    # 尝试获取每日指标
                    print("\n4. 获取每日指标 (daily_basic接口)...")
                    try:
                        df_daily = pro.daily_basic(ts_code='', trade_date=check_date)
                        if df_daily is not None and not df_daily.empty:
                            print("   获取成功:", len(df_daily), "只股票")
                            print("   列名:", df_daily.columns.tolist())
                            
                            # 显示第一只股票的数据
                            if len(df_daily) > 0:
                                print("\n   示例数据:")
                                print(df_daily.iloc[0])
                        else:
                            print("   返回空数据")
                    except Exception as e:
                        print("   获取失败:", e)
                    
                    return True
                    
            except Exception as e:
                print("   ", check_date, "获取失败:", e)
                continue
        
        print("\n未获取到任何数据")
        return False
        
    except Exception as e:
        print("\nTushare调用失败:", e)
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    test_tushare_data()

