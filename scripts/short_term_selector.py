# -*- coding: utf-8 -*-
"""
沪深主板短线选股脚本

选股逻辑：
1. 筛选沪深主板（60/00开头）
2. 排除ST、退市风险、停牌个股
3. 横盘异动后回调结束
4. 成交量放量
5. 资金净流入
6. 短期具备上涨动能

输出：个股清单 + 操作参考区间
"""

import sys
import os
from pathlib import Path
from datetime import datetime, date
import pandas as pd
import numpy as np

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 缓存目录
CACHE_DIR = PROJECT_ROOT / 'data' / 'cache'
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def get_cache_file():
    """获取当天缓存文件路径"""
    today = date.today().strftime('%Y%m%d')
    return CACHE_DIR / f'stock_data_{today}.csv'


def load_cache():
    """加载缓存数据"""
    cache_file = get_cache_file()
    if cache_file.exists():
        try:
            df = pd.read_csv(cache_file, dtype={'代码': str})
            # 检查缓存是否是今天的
            if not df.empty:
                print(f"✅ 从缓存加载今日数据: {cache_file}")
                print(f"   缓存数据量: {len(df)} 只股票")
                return df
        except Exception as e:
            print(f"⚠️ 缓存加载失败: {e}")
    return None


def save_cache(df):
    """保存缓存数据"""
    if df.empty:
        return
    cache_file = get_cache_file()
    try:
        df.to_csv(cache_file, index=False, encoding='utf-8-sig')
        print(f"✅ 数据已缓存到: {cache_file}")
    except Exception as e:
        print(f"⚠️ 缓存保存失败: {e}")


def get_stock_data():
    """获取A股实时行情数据"""
    print("=" * 60)
    print("1. 获取A股实时行情数据")
    print("=" * 60)
    
    # 先尝试加载缓存
    cached_data = load_cache()
    if cached_data is not None:
        return cached_data
    
    import time
    
    # 尝试使用新浪财经接口（优先）
    for retry in range(3):
        try:
            import akshare as ak
            print(f"使用新浪财经接口获取数据... (尝试 {retry + 1}/3)")
            
            df = ak.stock_zh_a_spot()
            
            if df is not None and not df.empty:
                print(f"✅ 成功获取 {len(df)} 只股票数据")
                save_cache(df)  # 保存缓存
                return df
            else:
                print("⚠️ 新浪接口未获取到数据")
        except Exception as e:
            print(f"⚠️ 新浪接口获取失败: {str(e)[:80]}")
        
        if retry < 2:
            print("   等待3秒后重试...")
            time.sleep(3)
    
    # 尝试使用东方财富接口
    for retry in range(3):
        try:
            import akshare as ak
            print(f"使用东方财富接口获取数据... (尝试 {retry + 1}/3)")
            
            df = ak.stock_zh_a_spot_em()
            
            if df is not None and not df.empty:
                print(f"✅ 成功获取 {len(df)} 只股票数据")
                return df
            else:
                print("⚠️ 东方财富接口未获取到数据")
        except Exception as e:
            print(f"⚠️ 东方财富接口获取失败: {str(e)[:80]}")
        
        if retry < 2:
            print("   等待3秒后重试...")
            time.sleep(3)
    
    print("❌ 所有数据源均无法获取数据，请检查网络连接")
    return pd.DataFrame()


def filter_main_board(df):
    """筛选沪深主板股票"""
    print("\n" + "=" * 60)
    print("2. 筛选沪深主板股票（60/00开头）")
    print("=" * 60)
    
    if df.empty:
        return df
    
    # 获取代码列（支持多种列名）
    code_col = None
    for col in ['代码', 'symbol', '股票代码', 'code']:
        if col in df.columns:
            code_col = col
            break
    
    if code_col is None:
        print("❌ 未找到代码列")
        return df
    
    # 确保代码是字符串，去除可能的前缀
    df[code_col] = df[code_col].astype(str)
    
    # 提取纯数字代码（去除 bj/sh/sz 等前缀）
    def extract_code(code):
        code = str(code).strip().lower()
        # 去除常见前缀
        for prefix in ['bj', 'sh', 'sz', 'sh', 'sz']:
            if code.startswith(prefix):
                code = code[len(prefix):]
        return code.zfill(6)
    
    df['pure_code'] = df[code_col].apply(extract_code)
    
    # 筛选沪深主板
    # 沪市主板：600xxx, 601xxx, 603xxx, 605xxx
    # 深市主板：000xxx, 001xxx, 003xxx
    mask = df['pure_code'].str.match(r'^(60[0135]|000|001|003)\d{3}$')
    main_board_df = df[mask].copy()
    
    # 更新代码列为纯数字
    main_board_df[code_col] = main_board_df['pure_code']
    main_board_df = main_board_df.drop(columns=['pure_code'])
    
    print(f"✅ 筛选出 {len(main_board_df)} 只沪深主板股票")
    return main_board_df


def filter_st_and_suspended(df):
    """排除ST、退市风险、停牌个股"""
    print("\n" + "=" * 60)
    print("3. 排除ST、退市风险、停牌个股")
    print("=" * 60)
    
    if df.empty:
        return df
    
    # 获取名称列（支持多种列名）
    name_col = None
    for col in ['名称', 'name', '股票名称']:
        if col in df.columns:
            name_col = col
            break
    
    if name_col is None:
        print("⚠️ 未找到名称列，跳过ST筛选")
        return df
    
    # 排除ST股票（转义特殊字符）
    st_mask = ~df[name_col].str.contains(r'ST|\*ST|S\*ST|SST', case=False, na=False)
    
    # 排除退市风险
    delist_mask = ~df[name_col].str.contains('退|退市', case=False, na=False)
    
    # 排除停牌（成交量为0或最新价为0）
    volume_col = None
    for col in ['成交量', 'volume', '成交数量']:
        if col in df.columns:
            volume_col = col
            break
    
    price_col = None
    for col in ['最新价', 'price', '收盘', 'close']:
        if col in df.columns:
            price_col = col
            break
    
    if volume_col is None or price_col is None:
        print("⚠️ 未找到成交量或价格列，跳过停牌筛选")
        return df[st_mask & delist_mask].copy()
    
    # 确保数值类型
    df[volume_col] = pd.to_numeric(df[volume_col], errors='coerce').fillna(0)
    df[price_col] = pd.to_numeric(df[price_col], errors='coerce').fillna(0)
    
    active_mask = (df[volume_col] > 0) & (df[price_col] > 0)
    
    # 合并筛选条件
    filtered_df = df[st_mask & delist_mask & active_mask].copy()
    
    excluded_count = len(df) - len(filtered_df)
    print(f"✅ 排除 {excluded_count} 只股票（ST/退市/停牌）")
    print(f"✅ 剩余 {len(filtered_df)} 只股票")
    
    return filtered_df


def filter_price_range(df, min_price=5, max_price=35):
    """筛选价格范围"""
    print("\n" + "=" * 60)
    print(f"4. 筛选价格范围 {min_price}-{max_price} 元")
    print("=" * 60)
    
    if df.empty:
        return df
    
    price_col = None
    for col in ['最新价', 'price', '收盘', 'close']:
        if col in df.columns:
            price_col = col
            break
    
    if price_col is None:
        print("⚠️ 未找到价格列")
        return df
    
    price_mask = (df[price_col] >= min_price) & (df[price_col] <= max_price)
    filtered_df = df[price_mask].copy()
    
    print(f"✅ 筛选出 {len(filtered_df)} 只股票")
    return filtered_df


def calculate_technical_indicators(df):
    """计算技术指标"""
    print("\n" + "=" * 60)
    print("5. 计算技术指标")
    print("=" * 60)
    
    if df.empty:
        return df
    
    # 获取列名（支持多种列名）
    code_col = None
    for col in ['代码', 'symbol', '股票代码', 'code']:
        if col in df.columns:
            code_col = col
            break
    
    price_col = None
    for col in ['最新价', 'price', '收盘', 'close']:
        if col in df.columns:
            price_col = col
            break
    
    change_col = None
    for col in ['涨跌幅', 'pct_chg', '涨跌幅%', 'percent']:
        if col in df.columns:
            change_col = col
            break
    
    volume_col = None
    for col in ['成交量', 'volume', '成交数量']:
        if col in df.columns:
            volume_col = col
            break
    
    amount_col = None
    for col in ['成交额', 'amount', '成交金额']:
        if col in df.columns:
            amount_col = col
            break
    
    turnover_col = None
    for col in ['换手率', 'turnover_rate', '换手率%']:
        if col in df.columns:
            turnover_col = col
            break
    
    high_col = None
    for col in ['最高', 'high', '最高价']:
        if col in df.columns:
            high_col = col
            break
    
    low_col = None
    for col in ['最低', 'low', '最低价']:
        if col in df.columns:
            low_col = col
            break
    
    # 初始化指标列
    df['score'] = 0
    df['volume_surge'] = False  # 成交量放量
    df['price_stable'] = False  # 价格稳定（横盘）
    df['pullback_done'] = False  # 回调结束
    df['fund_inflow'] = False  # 资金流入
    df['upward_momentum'] = False  # 上涨动能
    
    # 转换数值类型
    if change_col:
        df[change_col] = pd.to_numeric(df[change_col], errors='coerce').fillna(0)
    if volume_col:
        df[volume_col] = pd.to_numeric(df[volume_col], errors='coerce').fillna(0)
    if amount_col:
        df[amount_col] = pd.to_numeric(df[amount_col], errors='coerce').fillna(0)
    if turnover_col:
        df[turnover_col] = pd.to_numeric(df[turnover_col], errors='coerce').fillna(0)
    if high_col:
        df[high_col] = pd.to_numeric(df[high_col], errors='coerce').fillna(0)
    if low_col:
        df[low_col] = pd.to_numeric(df[low_col], errors='coerce').fillna(0)
    
    print("基于实时数据计算技术指标...")
    
    # 使用实时数据进行筛选
    for idx, row in df.iterrows():
        try:
            # 1. 成交量放量：成交额放大（成交额 > 5000万）
            if amount_col and row[amount_col] > 50000000:
                df.at[idx, 'volume_surge'] = True
                df.at[idx, 'score'] += 25
            
            # 2. 横盘异动：今日涨幅在1%-5%之间
            if change_col and 1 <= row[change_col] <= 5:
                df.at[idx, 'price_stable'] = True
                df.at[idx, 'score'] += 25
            
            # 3. 回调结束：今日涨幅大于0且小于3%
            if change_col and 0 < row[change_col] < 3:
                df.at[idx, 'pullback_done'] = True
                df.at[idx, 'score'] += 20
            
            # 4. 资金流入：换手率在3%-10%之间
            if turnover_col and 3 <= row[turnover_col] <= 10:
                df.at[idx, 'fund_inflow'] = True
                df.at[idx, 'score'] += 15
            
            # 5. 上涨动能：涨幅大于0
            if change_col and row[change_col] > 0:
                df.at[idx, 'upward_momentum'] = True
                df.at[idx, 'score'] += 15
                
        except Exception as e:
            continue
    
    print(f"✅ 技术指标计算完成")
    
    return df


def select_stocks(df):
    """选股筛选"""
    print("\n" + "=" * 60)
    print("6. 执行选股筛选")
    print("=" * 60)
    
    if df.empty:
        return df
    
    # 筛选条件：至少满足3个技术指标
    conditions = (
        (df['volume_surge']) |
        (df['price_stable']) |
        (df['pullback_done']) |
        (df['fund_inflow']) |
        (df['upward_momentum'])
    )
    
    # 至少满足2个条件
    condition_count = (
        df['volume_surge'].astype(int) +
        df['price_stable'].astype(int) +
        df['pullback_done'].astype(int) +
        df['fund_inflow'].astype(int) +
        df['upward_momentum'].astype(int)
    )
    
    filtered_df = df[(conditions) & (condition_count >= 2)].copy()
    
    # 按得分排序
    filtered_df = filtered_df.sort_values('score', ascending=False)
    
    print(f"✅ 筛选出 {len(filtered_df)} 只符合条件的股票")
    
    return filtered_df


def generate_recommendations(df):
    """生成推荐结果"""
    print("\n" + "=" * 60)
    print("7. 生成推荐结果")
    print("=" * 60)
    
    if df.empty:
        print("❌ 没有符合条件的股票")
        return []
    
    # 获取列名（支持多种列名）
    code_col = None
    for col in ['代码', 'symbol', '股票代码', 'code']:
        if col in df.columns:
            code_col = col
            break
    
    name_col = None
    for col in ['名称', 'name', '股票名称']:
        if col in df.columns:
            name_col = col
            break
    
    price_col = None
    for col in ['最新价', 'price', '收盘', 'close']:
        if col in df.columns:
            price_col = col
            break
    
    change_col = None
    for col in ['涨跌幅', 'pct_chg', '涨跌幅%', 'percent']:
        if col in df.columns:
            change_col = col
            break
    
    turnover_col = None
    for col in ['换手率', 'turnover_rate', '换手率%']:
        if col in df.columns:
            turnover_col = col
            break
    
    # 取前15只股票
    top_stocks = df.head(15)
    
    recommendations = []
    
    for _, row in top_stocks.iterrows():
        code = str(row[code_col]) if code_col else ''
        name = str(row[name_col]) if name_col else ''
        price = float(row[price_col]) if price_col else 0
        change_pct = float(row[change_col]) if change_col else 0
        turnover = float(row[turnover_col]) if turnover_col else 0
        score = float(row['score'])
        
        # 构建入选逻辑
        reasons = []
        if row['volume_surge']:
            reasons.append("成交量放量")
        if row['price_stable']:
            reasons.append("横盘异动")
        if row['pullback_done']:
            reasons.append("回调结束")
        if row['fund_inflow']:
            reasons.append("资金流入")
        if row['upward_momentum']:
            reasons.append("上涨动能")
        
        # 计算操作区间
        buy_low = round(price * 0.98, 2)  # 买入下限：-2%
        buy_high = round(price * 1.01, 2)  # 买入上限：+1%
        stop_loss = round(price * 0.97, 2)  # 止损价：-3%
        take_profit = round(price * 1.05, 2)  # 止盈价：+5%
        
        recommendations.append({
            'code': code,
            'name': name,
            'price': price,
            'change_pct': change_pct,
            'turnover': turnover,
            'score': score,
            'reasons': reasons,
            'buy_range': (buy_low, buy_high),
            'stop_loss': stop_loss,
            'take_profit': take_profit
        })
    
    return recommendations


def print_results(recommendations):
    """打印结果"""
    print("\n" + "=" * 80)
    print(f"沪深主板短线选股结果 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    if not recommendations:
        print("❌ 没有符合条件的股票")
        return
    
    print(f"\n📊 符合条件的个股清单（共 {len(recommendations)} 只）：")
    print("-" * 80)
    
    for i, stock in enumerate(recommendations, 1):
        print(f"\n{i}. {stock['code']} {stock['name']}")
        print(f"   当前价格: {stock['price']:.2f} 元")
        print(f"   今日涨跌: {stock['change_pct']:+.2f}%")
        print(f"   换手率: {stock['turnover']:.2f}%")
        print(f"   综合得分: {stock['score']:.0f}")
        print(f"   核心逻辑: {', '.join(stock['reasons'])}")
        print(f"   📌 操作参考区间:")
        print(f"      买入区间: {stock['buy_range'][0]:.2f} - {stock['buy_range'][1]:.2f} 元")
        print(f"      止损价位: {stock['stop_loss']:.2f} 元 (-3%)")
        print(f"      止盈目标: {stock['take_profit']:.2f} 元 (+5%)")
    
    print("\n" + "=" * 80)
    print("💡 操作建议：")
    print("-" * 80)
    print("1. 超短线操作，建议持有1-2天")
    print("2. 严格执行止损纪律，跌破止损价立即离场")
    print("3. 控制仓位，单只股票不超过总资金的20%")
    print("4. 关注大盘走势，系统性风险时及时减仓")
    print("5. 以上推荐仅供参考，不构成投资建议")
    print("=" * 80)


def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("沪深主板短线选股系统")
    print("=" * 80)
    
    # 1. 获取数据
    df = get_stock_data()
    if df.empty:
        print("❌ 无法获取股票数据，请检查网络连接")
        return
    
    # 2. 筛选沪深主板
    df = filter_main_board(df)
    
    # 3. 排除ST、退市、停牌
    df = filter_st_and_suspended(df)
    
    # 4. 筛选价格范围
    df = filter_price_range(df, 5, 35)
    
    # 5. 计算技术指标
    df = calculate_technical_indicators(df)
    
    # 6. 选股筛选
    df = select_stocks(df)
    
    # 7. 生成推荐
    recommendations = generate_recommendations(df)
    
    # 8. 打印结果
    print_results(recommendations)
    
    return recommendations


if __name__ == "__main__":
    main()
