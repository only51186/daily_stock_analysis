# -*- coding: utf-8 -*-
"""
自适应选股程序 - 适配当前数据格式
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.data.smart_data_manager import SmartDataManager
import pandas as pd

class AdaptiveStockSelector:
    """自适应选股器"""
    
    def __init__(self):
        self.smart_dm = SmartDataManager()
        
    def select_stocks(self):
        """自适应选股"""
        print("=" * 80)
        print("自适应选股程序")
        print("=" * 80)
        
        # 获取数据
        data = self.smart_dm.get_smart_stock_daily()
        
        if data.empty:
            print("❌ 没有获取到股票数据")
            return []
        
        print(f"📊 总股票数量: {len(data)} 只")
        
        # 自适应筛选条件
        filtered = data.copy()
        
        # 1. 排除北交所股票（技术指标缺失）
        filtered = filtered[~filtered['code'].str.startswith('bj', na=False)]
        print(f"✅ 排除北交所后: {len(filtered)} 只")
        
        # 2. 排除ST股
        if 'name' in filtered.columns:
            filtered = filtered[~filtered['name'].str.contains('ST|退', na=False)]
            print(f"✅ 排除ST股后: {len(filtered)} 只")
        
        # 3. 涨幅筛选（放宽条件）
        if 'pct_chg' in filtered.columns:
            # 由于当前市场环境较差，放宽涨幅条件
            filtered = filtered[(filtered['pct_chg'] >= 0) & (filtered['pct_chg'] <= 10)]
            print(f"✅ 涨幅0%-10%: {len(filtered)} 只")
        
        # 4. 由于技术指标缺失，使用其他可用条件
        # 按涨幅排序，选择表现较好的股票
        if 'pct_chg' in filtered.columns:
            filtered = filtered.sort_values('pct_chg', ascending=False)
        
        # 5. 选择前20只表现最好的股票
        result = filtered.head(20)
        
        print(f"🎯 最终选股结果: {len(result)} 只")
        
        return result
    
    def display_results(self, stocks):
        """显示选股结果"""
        if len(stocks) == 0:
            print("❌ 没有符合条件的股票")
            return
        
        print("\n📋 选股结果列表:")
        print("=" * 120)
        print(f"{'排名':<4} {'代码':<10} {'名称':<15} {'涨幅(%)':<8} {'收盘价':<8} {'成交额(万)':<12} {'日期':<12}")
        print("=" * 120)
        
        for i, (_, stock) in enumerate(stocks.iterrows(), 1):
            code = stock.get('code', 'N/A')
            name = stock.get('name', 'N/A')
            pct_chg = stock.get('pct_chg', 0)
            close = stock.get('close', 0)
            amount = stock.get('amount', 0)
            date = stock.get('date', 'N/A')
            
            # 格式化显示
            amount_formatted = f"{amount/10000:.0f}" if amount > 0 else "N/A"
            
            print(f"{i:<4} {code:<10} {name:<15} {pct_chg:<8.2f} {close:<8.2f} {amount_formatted:<12} {date:<12}")
        
        print("=" * 120)
        
        # 统计信息
        print(f"\n📊 统计信息:")
        print(f"   平均涨幅: {stocks['pct_chg'].mean():.2f}%")
        print(f"   最高涨幅: {stocks['pct_chg'].max():.2f}%")
        print(f"   最低涨幅: {stocks['pct_chg'].min():.2f}%")
        print(f"   总成交额: {stocks['amount'].sum()/10000:.0f} 万元")

def main():
    """主函数"""
    selector = AdaptiveStockSelector()
    
    # 执行选股
    selected_stocks = selector.select_stocks()
    
    # 显示结果
    selector.display_results(selected_stocks)
    
    # 保存结果到文件
    if len(selected_stocks) > 0:
        output_file = "adaptive_selection_results.csv"
        selected_stocks.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\n💾 选股结果已保存到: {output_file}")

if __name__ == "__main__":
    main()