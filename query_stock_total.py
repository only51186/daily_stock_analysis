# -*- coding: utf-8 -*-
"""
查询沪深主板股票准确总数
"""

import sys
import os
import akshare as ak
import pandas as pd
from datetime import datetime

def query_accurate_stock_count():
    """查询准确的股票总数"""
    print("=" * 80)
    print("查询沪深主板股票准确总数")
    print("=" * 80)
    
    try:
        # 方法1: 使用Akshare获取股票基本信息
        print("\n1. 使用Akshare获取股票基本信息...")
        
        # 获取A股基本信息
        stock_info_a_code_name_df = ak.stock_info_a_code_name()
        
        if not stock_info_a_code_name_df.empty:
            print(f"   A股总数: {len(stock_info_a_code_name_df)} 只")
            
            # 分类统计
            main_board = stock_info_a_code_name_df[stock_info_a_code_name_df['code'].str.startswith(('60', '00'))]
            gem_board = stock_info_a_code_name_df[stock_info_a_code_name_df['code'].str.startswith('30')]
            star_board = stock_info_a_code_name_df[stock_info_a_code_name_df['code'].str.startswith('68')]
            
            print(f"   沪深主板A股: {len(main_board)} 只")
            print(f"   创业板: {len(gem_board)} 只")
            print(f"   科创板: {len(star_board)} 只")
            
            # 显示前10只主板股票
            if len(main_board) > 0:
                print("\n   前10只主板股票:")
                for i, (_, stock) in enumerate(main_board.head(10).iterrows(), 1):
                    print(f"     {i}. {stock['code']} {stock['name']}")
        
        # 方法2: 获取实时行情数据
        print("\n2. 获取实时行情数据...")
        
        try:
            stock_zh_a_spot_df = ak.stock_zh_a_spot()
            if not stock_zh_a_spot_df.empty:
                print(f"   实时行情数据: {len(stock_zh_a_spot_df)} 只")
                
                # 分类统计
                main_board_spot = stock_zh_a_spot_df[stock_zh_a_spot_df['symbol'].str.startswith(('60', '00'))]
                gem_board_spot = stock_zh_a_spot_df[stock_zh_a_spot_df['symbol'].str.startswith('30')]
                star_board_spot = stock_zh_a_spot_df[stock_zh_a_spot_df['symbol'].str.startswith('68')]
                
                print(f"   沪深主板A股: {len(main_board_spot)} 只")
                print(f"   创业板: {len(gem_board_spot)} 只")
                print(f"   科创板: {len(star_board_spot)} 只")
                
        except Exception as e:
            print(f"   实时行情获取失败: {e}")
        
        # 方法3: 获取历史数据统计
        print("\n3. 获取历史数据统计...")
        
        try:
            # 获取所有A股列表
            stock_zh_a_hist_df = ak.stock_zh_a_hist(symbol="000001", period="daily", start_date="20240101", end_date="20240101", adjust="")
            print("   历史数据接口可用")
        except Exception as e:
            print(f"   历史数据获取失败: {e}")
        
        # 方法4: 使用Tushare（如果可用）
        print("\n4. 使用Tushare统计...")
        
        try:
            import tushare as ts
            # 设置token（如果有）
            # ts.set_token('your_token_here')
            pro = ts.pro_api()
            
            # 获取股票基本信息
            stock_basic = pro.stock_basic(exchange='', list_status='L', fields='ts_code,symbol,name,area,industry,list_date')
            print(f"   Tushare A股总数: {len(stock_basic)} 只")
            
            # 分类统计
            sh_main = stock_basic[stock_basic['ts_code'].str.startswith('60')]
            sz_main = stock_basic[stock_basic['ts_code'].str.startswith('00')]
            sz_gem = stock_basic[stock_basic['ts_code'].str.startswith('30')]
            sh_star = stock_basic[stock_basic['ts_code'].str.startswith('68')]
            
            print(f"   沪市主板: {len(sh_main)} 只")
            print(f"   深市主板: {len(sz_main)} 只")
            print(f"   创业板: {len(sz_gem)} 只")
            print(f"   科创板: {len(sh_star)} 只")
            
        except Exception as e:
            print(f"   Tushare获取失败: {e}")
            print("   需要设置Tushare token才能使用")
        
        # 总结
        print("\n" + "=" * 80)
        print("📊 沪深主板股票总数总结")
        print("=" * 80)
        
        # 根据多个数据源综合判断
        if len(main_board) > 0:
            print(f"✅ 沪深主板A股总数: 约 {len(main_board)} 只")
            print(f"   - 沪市主板（60开头）: 约 {len(main_board[main_board['code'].str.startswith('60')])} 只")
            print(f"   - 深市主板（00开头）: 约 {len(main_board[main_board['code'].str.startswith('00')])} 只")
            
            # 保存股票列表
            save_stock_list(main_board)
            
        else:
            print("❌ 无法获取准确的股票总数")
            
    except Exception as e:
        print(f"❌ 查询失败: {e}")
        print("\n💡 建议:")
        print("1. 检查网络连接")
        print("2. 检查Akshare库是否最新")
        print("3. 尝试使用其他数据源")

def save_stock_list(stock_df):
    """保存股票列表"""
    try:
        # 创建数据目录
        data_dir = os.path.join(os.path.dirname(__file__), 'data')
        os.makedirs(data_dir, exist_ok=True)
        
        # 保存股票列表
        filename = 'stock_list.csv'
        filepath = os.path.join(data_dir, filename)
        
        stock_df.to_csv(filepath, index=False, encoding='utf-8-sig')
        print(f"\n💾 股票列表已保存到: {filepath}")
        print(f"   包含 {len(stock_df)} 只股票")
        
        # 显示前20只股票
        print("\n📋 前20只股票代码:")
        for i, (_, stock) in enumerate(stock_df.head(20).iterrows(), 1):
            print(f"   {i:2d}. {stock['code']} {stock['name']}")
            
    except Exception as e:
        print(f"❌ 保存股票列表失败: {e}")

def main():
    """主函数"""
    print("开始查询沪深主板股票准确总数...")
    print(f"查询时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    query_accurate_stock_count()

if __name__ == "__main__":
    main()