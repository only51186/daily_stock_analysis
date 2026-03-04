
# -*- coding: utf-8 -*-
"""
===================================
尾盘选股程序 V2（次日早盘买入策略）
===================================
功能：
1. 每天下午6点之后选股，次日早盘买入
2. 筛选范围：沪深主板A股（60/00开头）
3. 排除ST股、退市风险股、停牌股、新股（上市不满1个月）
4. 数据源：首选Akshare（完全免费，数据完整），失败自动切换Tushare
"""

import sys
import os
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from dotenv import load_dotenv

load_dotenv()

class EveningStockSelector:
    """尾盘选股器（次日早盘买入策略）"""
    
    def __init__(self):
        self.stock_data = None
        self.selected_stocks = []
        self.data_source = None
        self.today = datetime.now().strftime('%Y-%m-%d')
        
    def get_stock_data(self):
        """获取股票数据，首选Akshare，失败自动切换Tushare"""
        print("=" * 80)
        print("1. 获取股票数据")
        print("=" * 80)
        
        # 首先尝试Akshare（首选，完全免费，数据完整）
        print("尝试使用Akshare数据源...")
        
        # 尝试东方财富接口（数据更完整）
        for retry in range(3):
            try:
                import akshare as ak
                print(f"使用Akshare东方财富接口... (尝试 {retry + 1}/3)")
                
                df = ak.stock_zh_a_spot_em()
                
                if df is not None and not df.empty:
                    print(f"✅ Akshare数据获取成功: {len(df)} 只股票")
                    self.data_source = "Akshare-EM"
                    
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
                        if old_col in df.columns:
                            df[new_col] = df[old_col]
                    
                    return df
                else:
                    print("⚠️ 东方财富接口未获取到数据")
            except Exception as e:
                print(f"⚠️ 东方财富接口获取失败: {str(e)[:100]}")
            
            if retry < 2:
                print("   等待3秒后重试...")
                time.sleep(3)
        
        # 切换至Tushare（仅作为备用，120积分仅支持daily接口）
        print("\n🔄 自动切换至Tushare备用数据源...")
        print("⚠️ Tushare 120积分仅支持日线行情接口，建议优先使用Akshare")
        tushare_token = os.getenv('TUSHARE_TOKEN')
        if tushare_token and tushare_token != 'your_tushare_token_here':
            try:
                print("尝试使用Tushare数据源...")
                import tushare as ts
                pro = ts.pro_api(tushare_token)
                
                for i in range(5):
                    check_date = (datetime.now() - timedelta(days=i)).strftime('%Y%m%d')
                    print(f"尝试获取 {check_date} 的数据...")
                    
                    try:
                        df = pro.daily(trade_date=check_date)
                        
                        if df is not None and not df.empty:
                            print(f"✅ Tushare行情数据获取成功: {len(df)} 只股票 (日期: {check_date})")
                            self.data_source = f"Tushare-{check_date}"
                            
                            df = df.rename(columns={
                                'ts_code': 'code',
                                'trade_date': 'date',
                                'open': 'open',
                                'high': 'high',
                                'low': 'low',
                                'close': 'close',
                                'pre_close': 'pre_close',
                                'change': 'change',
                                'pct_chg': 'pct_chg',
                                'vol': 'volume',
                                'amount': 'amount'
                            })
                            
                            df['pct_chg'] = pd.to_numeric(df['pct_chg'], errors='coerce')
                            
                            print(f"✅ Tushare数据获取成功: {len(df)} 只股票")
                            print("⚠️ 注意：Tushare 120积分无法获取名称、换手率、量比等数据")
                            return df
                    except Exception as e:
                        print(f"   {check_date} 数据获取失败: {e}")
                        continue
                
                print("⚠️ Tushare未获取到最近5天的数据")
            except Exception as e:
                print(f"⚠️ Tushare调用失败: {str(e)[:100]}")
                import traceback
                traceback.print_exc()
        else:
            print("⚠️ Tushare Token未配置或无效")
        
        print("❌ 所有数据源均无法获取数据")
        return pd.DataFrame()
    
    def filter_main_board(self, df):
        """筛选沪深主板股票（60/00开头），排除ST股等"""
        print("\n" + "=" * 80)
        print("2. 筛选沪深主板股票")
        print("=" * 80)
        
        if df.empty:
            return df
        
        code_col = None
        for col in ['code', 'ts_code', '股票代码', '代码']:
            if col in df.columns:
                code_col = col
                break
        
        if code_col is None:
            print("❌ 未找到代码列")
            return df
        
        df[code_col] = df[code_col].astype(str)
        
        def extract_code(code):
            code = str(code).strip().upper()
            if '.' in code:
                code = code.split('.')[0]
            for prefix in ['BJ', 'SH', 'SZ']:
                if code.startswith(prefix):
                    code = code[2:]
            return code.zfill(6)
        
        df['pure_code'] = df[code_col].apply(extract_code)
        
        mask = df['pure_code'].str.match(r'^(60[0135]|000|001|003)\d{3}$')
        df = df[mask].copy()
        print(f"✅ 沪深主板筛选: {len(df)} 只")
        
        name_col = None
        for col in ['name', '名称', '股票名称']:
            if col in df.columns:
                name_col = col
                break
        
        if name_col:
            st_mask = df[name_col].str.contains(r'ST|\*ST|S\*ST|SST|退市', na=False, regex=True)
            df = df[~st_mask].copy()
            print(f"✅ 排除ST/退市股: {st_mask.sum()} 只")
        
        price_col = None
        for col in ['close', '最新价', '收盘']:
            if col in df.columns:
                price_col = col
                break
        
        if price_col:
            df[price_col] = pd.to_numeric(df[price_col], errors='coerce')
            suspended_mask = (df[price_col] <= 0) | df[price_col].isna()
            df = df[~suspended_mask].copy()
            print(f"✅ 排除停牌股: {suspended_mask.sum()} 只")
        
        def is_new_stock(code):
            code = str(code).zfill(6)
            if code.startswith('60'):
                return code >= '605000'
            elif code.startswith('00'):
                return code >= '003000'
            return False
        
        new_stock_mask = df['pure_code'].apply(is_new_stock)
        df = df[~new_stock_mask].copy()
        print(f"✅ 排除新股: {new_stock_mask.sum()} 只")
        
        df['code'] = df['pure_code']
        df = df.drop(columns=['pure_code'])
        
        print(f"✅ 最终剩余: {len(df)} 只")
        return df
    
    def apply_selection_criteria(self, df):
        """应用选股条件"""
        print("\n" + "=" * 80)
        print("3. 应用选股条件")
        print("=" * 80)
        
        if df.empty:
            return df
        
        pct_chg_col = None
        for col in ['pct_chg', '涨跌幅']:
            if col in df.columns:
                pct_chg_col = col
                break
        
        turnover_col = None
        for col in ['turnover', '换手率']:
            if col in df.columns:
                turnover_col = col
                break
        
        volume_ratio_col = None
        for col in ['volume_ratio', '量比']:
            if col in df.columns:
                volume_ratio_col = col
                break
        
        circ_mv_col = None
        for col in ['circ_mv', '流通市值']:
            if col in df.columns:
                circ_mv_col = col
                break
        
        amount_col = None
        for col in ['amount', '成交额']:
            if col in df.columns:
                amount_col = col
                break
        
        print(f"   使用列: 涨幅={pct_chg_col}, 换手={turnover_col}, 量比={volume_ratio_col}, 市值={circ_mv_col}, 成交额={amount_col}")
        
        df['selection_score'] = 0
        df['selection_logic'] = ''
        
        for idx, row in df.iterrows():
            score = 0
            logic = []
            
            if pct_chg_col:
                pct_chg = float(row.get(pct_chg_col, 0))
                if 2 <= pct_chg <= 6:
                    score += 30
                    logic.append('涨幅适中')
                elif 0 <= pct_chg < 2:
                    score += 10
                    logic.append('小幅上涨')
            
            if turnover_col:
                turnover = float(row.get(turnover_col, 0))
                if 2 <= turnover <= 12:
                    score += 20
                    logic.append('换手健康')
                elif turnover > 0:
                    score += 5
                    logic.append('有换手')
            
            if volume_ratio_col:
                volume_ratio = float(row.get(volume_ratio_col, 0))
                if 1.0 <= volume_ratio <= 6:
                    score += 20
                    logic.append('量能配合')
                elif volume_ratio > 0:
                    score += 5
                    logic.append('有量比')
            
            if circ_mv_col:
                circ_mv = float(row.get(circ_mv_col, 0))
                if circ_mv > 100000000:
                    circ_mv = circ_mv / 100000000
                if 20 <= circ_mv <= 300:
                    score += 20
                    logic.append('市值适中')
                elif circ_mv > 0:
                    score += 5
                    logic.append('有市值')
            
            if amount_col:
                amount = float(row.get(amount_col, 0))
                if amount > 30000000:
                    score += 10
                    logic.append('资金活跃')
                elif amount > 10000000:
                    score += 5
                    logic.append('有成交额')
            
            df.at[idx, 'selection_score'] = score
            df.at[idx, 'selection_logic'] = ', '.join(logic)
        
        score_dist = df['selection_score'].value_counts().sort_index(ascending=False)
        print(f"   得分分布:")
        for score, count in score_dist.head(10).items():
            print(f"     {score}分: {count}只")
        
        print(f"✅ 选股条件应用完成")
        return df
    
    def select_stocks(self, df):
        """筛选符合条件的股票"""
        print("\n" + "=" * 80)
        print("4. 筛选符合条件的股票")
        print("=" * 80)
        
        if df.empty:
            return df
        
        selected = df[df['selection_score'] >= 30].copy()
        selected = selected.sort_values('selection_score', ascending=False)
        selected = selected.head(20)
        
        print(f"✅ 筛选出 {len(selected)} 只符合条件的股票")
        return selected
    
    def format_output(self, df):
        """格式化输出"""
        if df.empty:
            return "未找到符合条件的股票"
        
        output = []
        output.append("\n" + "=" * 80)
        output.append(f"尾盘选股结果（次日早盘买入）- {self.today}")
        output.append(f"数据源: {self.data_source}")
        output.append("=" * 80)
        
        for i, (idx, row) in enumerate(df.iterrows(), 1):
            code = row.get('code', 'N/A')
            name = row.get('name', 'N/A')
            close = float(row.get('close', 0))
            pct_chg = float(row.get('pct_chg', 0))
            turnover = float(row.get('turnover', 0))
            volume_ratio = float(row.get('volume_ratio', 0))
            circ_mv = float(row.get('circ_mv', 0))
            
            if circ_mv > 100000000:
                circ_mv = circ_mv / 100000000
            
            score = int(row.get('selection_score', 0))
            logic = row.get('selection_logic', '')
            
            output.append(f"\n{i}. {code} {name}")
            output.append(f"   收盘价: {close:.2f} 元  涨幅: {pct_chg:+.2f}%")
            output.append(f"   换手率: {turnover:.2f}%  量比: {volume_ratio:.2f}")
            output.append(f"   流通市值: {circ_mv:.2f} 亿")
            output.append(f"   综合得分: {score} 分")
            output.append(f"   入选逻辑: {logic}")
        
        output.append("\n" + "=" * 80)
        output.append("💡 操作建议：")
        output.append("   1. 次日早盘择机买入，建议开盘30分钟内完成")
        output.append("   2. 严格设置止损，跌破止损价立即离场")
        output.append("   3. 达到止盈目标可分批减仓")
        output.append("   4. 单只股票仓位不超过20%")
        output.append("   5. 持有周期：1-3天，超短线策略")
        output.append("=" * 80)
        
        return '\n'.join(output)
    
    def run(self):
        """执行尾盘选股"""
        print("\n" + "=" * 80)
        print("尾盘选股程序（次日早盘买入策略）")
        print("=" * 80)
        
        df = self.get_stock_data()
        if df.empty:
            print("❌ 无法获取股票数据")
            return pd.DataFrame()
        
        df = self.filter_main_board(df)
        df = self.apply_selection_criteria(df)
        df = self.select_stocks(df)
        
        result = self.format_output(df)
        print(result)
        
        return df

def main():
    selector = EveningStockSelector()
    selector.run()

if __name__ == '__main__':
    main()

