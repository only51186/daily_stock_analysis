# -*- coding: utf-8 -*-
"""
===================================
一彬科技（001278）走势分析
===================================

功能：
1. 获取一彬科技历史股价数据
2. 分析走势特征
3. 预测未来走势
4. 生成可视化曲线图
"""

import logging
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import font_manager

from utils.logger_config import setup_logger

logger = setup_logger(__name__, log_file='logs/yibin_analysis.log')

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

class YibinAnalyzer:
    """
    一彬科技走势分析器
    """
    
    def __init__(self):
        self.stock_code = "001278"
        self.stock_name = "一彬科技"
        self.data = None
        
    def get_historical_data(self, days: int = 120) -> pd.DataFrame:
        """
        获取历史数据
        """
        print("=" * 80)
        print(f"获取 {self.stock_name}({self.stock_code}) 历史数据")
        print("=" * 80)
        
        try:
            import akshare as ak
            
            # 获取日线数据
            df = ak.stock_zh_a_hist(
                symbol=self.stock_code,
                period="daily",
                start_date=(datetime.now() - timedelta(days=days)).strftime('%Y%m%d'),
                end_date=datetime.now().strftime('%Y%m%d'),
                adjust="qfq"  # 前复权
            )
            
            if df is not None and not df.empty:
                print(f"✅ 成功获取 {len(df)} 个交易日数据")
                df['日期'] = pd.to_datetime(df['日期'])
                self.data = df
                return df
            else:
                print("⚠️ 未获取到数据")
                return pd.DataFrame()
                
        except Exception as e:
            print(f"❌ 数据获取失败: {str(e)}")
            return pd.DataFrame()
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算技术指标
        """
        print("\n" + "=" * 80)
        print("计算技术指标")
        print("=" * 80)
        
        if df.empty:
            return df
        
        # 移动平均线
        df['MA5'] = df['收盘'].rolling(window=5).mean()
        df['MA10'] = df['收盘'].rolling(window=10).mean()
        df['MA20'] = df['收盘'].rolling(window=20).mean()
        df['MA60'] = df['收盘'].rolling(window=60).mean()
        
        # MACD
        exp1 = df['收盘'].ewm(span=12, adjust=False).mean()
        exp2 = df['收盘'].ewm(span=26, adjust=False).mean()
        df['MACD_DIF'] = exp1 - exp2
        df['MACD_DEA'] = df['MACD_DIF'].ewm(span=9, adjust=False).mean()
        df['MACD_HIST'] = 2 * (df['MACD_DIF'] - df['MACD_DEA'])
        
        # RSI
        delta = df['收盘'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # 布林带
        df['BOLL_MID'] = df['收盘'].rolling(window=20).mean()
        df['BOLL_STD'] = df['收盘'].rolling(window=20).std()
        df['BOLL_UP'] = df['BOLL_MID'] + 2 * df['BOLL_STD']
        df['BOLL_DOWN'] = df['BOLL_MID'] - 2 * df['BOLL_STD']
        
        # 成交量均线
        df['VOL_MA5'] = df['成交量'].rolling(window=5).mean()
        df['VOL_MA10'] = df['成交量'].rolling(window=10).mean()
        
        print("✅ 技术指标计算完成")
        return df
    
    def analyze_trend(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        分析走势特征
        """
        print("\n" + "=" * 80)
        print("走势特征分析")
        print("=" * 80)
        
        if df.empty:
            return {}
        
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        
        analysis = {
            'current_price': latest['收盘'],
            'price_change': latest['涨跌幅'],
            'volume': latest['成交量'],
            'ma5': latest['MA5'],
            'ma10': latest['MA10'],
            'ma20': latest['MA20'],
            'ma60': latest['MA60'],
            'rsi': latest['RSI'],
            'macd_dif': latest['MACD_DIF'],
            'macd_dea': latest['MACD_DEA'],
            'macd_hist': latest['MACD_HIST'],
            'boll_up': latest['BOLL_UP'],
            'boll_mid': latest['BOLL_MID'],
            'boll_down': latest['BOLL_DOWN'],
        }
        
        # 趋势判断
        if latest['MA5'] > latest['MA10'] > latest['MA20']:
            trend = "多头排列（强势上涨）"
        elif latest['MA5'] < latest['MA10'] < latest['MA20']:
            trend = "空头排列（弱势下跌）"
        else:
            trend = "震荡整理"
        
        analysis['trend'] = trend
        
        # MACD判断
        if latest['MACD_DIF'] > latest['MACD_DEA'] and latest['MACD_HIST'] > 0:
            macd_signal = "金叉向上，多头信号"
        elif latest['MACD_DIF'] < latest['MACD_DEA'] and latest['MACD_HIST'] < 0:
            macd_signal = "死叉向下，空头信号"
        else:
            macd_signal = "趋势不明"
        
        analysis['macd_signal'] = macd_signal
        
        # RSI判断
        rsi = latest['RSI']
        if rsi > 70:
            rsi_signal = "超买区域，注意回调风险"
        elif rsi < 30:
            rsi_signal = "超卖区域，关注反弹机会"
        else:
            rsi_signal = "正常区间"
        
        analysis['rsi_signal'] = rsi_signal
        
        # 布林带位置
        price = latest['收盘']
        if price > latest['BOLL_UP']:
            boll_signal = "突破上轨，强势"
        elif price < latest['BOLL_DOWN']:
            boll_signal = "跌破下轨，弱势"
        else:
            boll_signal = "布林带内运行"
        
        analysis['boll_signal'] = boll_signal
        
        # 计算近期统计
        recent_5d = df.tail(5)
        recent_20d = df.tail(20)
        
        analysis['avg_volume_5d'] = recent_5d['成交量'].mean()
        analysis['price_change_5d'] = (latest['收盘'] - recent_5d.iloc[0]['收盘']) / recent_5d.iloc[0]['收盘'] * 100
        analysis['price_change_20d'] = (latest['收盘'] - recent_20d.iloc[0]['收盘']) / recent_20d.iloc[0]['收盘'] * 100
        analysis['volatility_20d'] = recent_20d['涨跌幅'].std()
        
        print(f"✅ 走势分析完成")
        return analysis
    
    def predict_future(self, df: pd.DataFrame, analysis: Dict) -> Dict[str, Any]:
        """
        预测未来走势
        """
        print("\n" + "=" * 80)
        print("未来走势预测")
        print("=" * 80)
        
        if df.empty:
            return {}
        
        latest = df.iloc[-1]
        current_price = latest['收盘']
        
        prediction = {
            'current_price': current_price,
            'prediction_date': (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d'),
        }
        
        # 基于技术指标综合判断
        score = 0
        reasons = []
        
        # MA趋势
        if latest['MA5'] > latest['MA10']:
            score += 1
            reasons.append("短期均线向上")
        else:
            score -= 1
            reasons.append("短期均线向下")
        
        # MACD
        if latest['MACD_HIST'] > 0:
            score += 1
            reasons.append("MACD红柱")
        else:
            score -= 1
            reasons.append("MACD绿柱")
        
        # RSI
        if 30 < latest['RSI'] < 70:
            score += 0.5
            reasons.append("RSI处于正常区间")
        elif latest['RSI'] < 30:
            score += 1
            reasons.append("RSI超卖，可能反弹")
        else:
            score -= 0.5
            reasons.append("RSI超买，注意风险")
        
        # 成交量
        if latest['成交量'] > latest['VOL_MA5']:
            score += 0.5
            reasons.append("成交量放大")
        
        # 布林带
        if latest['收盘'] > latest['BOLL_MID']:
            score += 0.5
            reasons.append("价格在中轨之上")
        
        prediction['score'] = score
        prediction['reasons'] = reasons
        
        # 预测价格区间
        volatility = analysis.get('volatility_20d', 2)
        
        if score >= 2:
            direction = "看涨"
            target_price = current_price * (1 + volatility / 100 * 2)
            support = current_price * 0.97
            resistance = current_price * 1.05
        elif score <= -2:
            direction = "看跌"
            target_price = current_price * (1 - volatility / 100 * 2)
            support = current_price * 0.95
            resistance = current_price * 1.03
        else:
            direction = "震荡"
            target_price = current_price
            support = current_price * 0.97
            resistance = current_price * 1.03
        
        prediction['direction'] = direction
        prediction['target_price'] = target_price
        prediction['support'] = support
        prediction['resistance'] = resistance
        prediction['expected_return'] = (target_price - current_price) / current_price * 100
        
        print(f"✅ 走势预测完成")
        return prediction
    
    def generate_chart(self, df: pd.DataFrame, analysis: Dict, prediction: Dict):
        """
        生成走势图
        """
        print("\n" + "=" * 80)
        print("生成走势图")
        print("=" * 80)
        
        if df.empty:
            print("❌ 无数据，无法生成图表")
            return
        
        # 创建图表
        fig, axes = plt.subplots(4, 1, figsize=(14, 12))
        fig.suptitle(f'{self.stock_name}({self.stock_code}) 走势分析', fontsize=16, fontweight='bold')
        
        dates = df['日期']
        
        # 1. K线图和均线
        ax1 = axes[0]
        ax1.plot(dates, df['收盘'], label='收盘价', color='black', linewidth=1.5)
        ax1.plot(dates, df['MA5'], label='MA5', color='blue', linewidth=1, alpha=0.7)
        ax1.plot(dates, df['MA10'], label='MA10', color='orange', linewidth=1, alpha=0.7)
        ax1.plot(dates, df['MA20'], label='MA20', color='green', linewidth=1, alpha=0.7)
        ax1.plot(dates, df['MA60'], label='MA60', color='red', linewidth=1, alpha=0.7)
        
        # 标记预测区间
        if prediction:
            ax1.axhline(y=prediction['support'], color='green', linestyle='--', alpha=0.5, label=f'支撑位 {prediction["support"]:.2f}')
            ax1.axhline(y=prediction['resistance'], color='red', linestyle='--', alpha=0.5, label=f'压力位 {prediction["resistance"]:.2f}')
        
        ax1.set_ylabel('价格（元）')
        ax1.set_title('股价走势与均线系统')
        ax1.legend(loc='upper left', fontsize=8)
        ax1.grid(True, alpha=0.3)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        
        # 2. 成交量
        ax2 = axes[1]
        colors = ['red' if df.iloc[i]['收盘'] >= df.iloc[i]['开盘'] else 'green' for i in range(len(df))]
        ax2.bar(dates, df['成交量'], color=colors, alpha=0.6, width=0.8)
        ax2.plot(dates, df['VOL_MA5'], label='VOL_MA5', color='blue', linewidth=1)
        ax2.plot(dates, df['VOL_MA10'], label='VOL_MA10', color='orange', linewidth=1)
        ax2.set_ylabel('成交量')
        ax2.set_title('成交量分析')
        ax2.legend(loc='upper left', fontsize=8)
        ax2.grid(True, alpha=0.3)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        
        # 3. MACD
        ax3 = axes[2]
        ax3.plot(dates, df['MACD_DIF'], label='DIF', color='blue', linewidth=1)
        ax3.plot(dates, df['MACD_DEA'], label='DEA', color='orange', linewidth=1)
        
        # MACD柱状图
        macd_colors = ['red' if h >= 0 else 'green' for h in df['MACD_HIST']]
        ax3.bar(dates, df['MACD_HIST'], color=macd_colors, alpha=0.6, width=0.8)
        ax3.axhline(y=0, color='black', linewidth=0.5)
        
        ax3.set_ylabel('MACD')
        ax3.set_title('MACD指标')
        ax3.legend(loc='upper left', fontsize=8)
        ax3.grid(True, alpha=0.3)
        ax3.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        
        # 4. RSI
        ax4 = axes[3]
        ax4.plot(dates, df['RSI'], label='RSI', color='purple', linewidth=1.5)
        ax4.axhline(y=70, color='red', linestyle='--', alpha=0.5, label='超买线(70)')
        ax4.axhline(y=30, color='green', linestyle='--', alpha=0.5, label='超卖线(30)')
        ax4.fill_between(dates, 30, 70, alpha=0.1, color='gray')
        
        ax4.set_ylabel('RSI')
        ax4.set_xlabel('日期')
        ax4.set_title('RSI相对强弱指标')
        ax4.legend(loc='upper left', fontsize=8)
        ax4.grid(True, alpha=0.3)
        ax4.set_ylim(0, 100)
        ax4.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        
        plt.tight_layout()
        
        # 保存图表
        output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'docs', 'charts')
        os.makedirs(output_dir, exist_ok=True)
        
        chart_path = os.path.join(output_dir, f'yibin_analysis_{datetime.now().strftime("%Y%m%d")}.png')
        plt.savefig(chart_path, dpi=150, bbox_inches='tight')
        print(f"✅ 图表已保存: {chart_path}")
        
        plt.close()
        
        return chart_path
    
    def print_analysis_report(self, analysis: Dict, prediction: Dict):
        """
        打印分析报告
        """
        print("\n" + "=" * 80)
        print(f"【{self.stock_name}】走势分析报告")
        print("=" * 80)
        
        print("\n一、当前状态")
        print("-" * 80)
        print(f"当前股价: {analysis['current_price']:.2f} 元")
        print(f"今日涨跌: {analysis['price_change']:+.2f}%")
        print(f"今日成交量: {analysis['volume']:,.0f} 手")
        
        print("\n二、均线系统")
        print("-" * 80)
        print(f"MA5:  {analysis['ma5']:.2f} 元")
        print(f"MA10: {analysis['ma10']:.2f} 元")
        print(f"MA20: {analysis['ma20']:.2f} 元")
        print(f"MA60: {analysis['ma60']:.2f} 元")
        print(f"趋势判断: {analysis['trend']}")
        
        print("\n三、技术指标")
        print("-" * 80)
        print(f"RSI(14): {analysis['rsi']:.2f} - {analysis['rsi_signal']}")
        print(f"MACD DIF: {analysis['macd_dif']:.4f}")
        print(f"MACD DEA: {analysis['macd_dea']:.4f}")
        print(f"MACD信号: {analysis['macd_signal']}")
        print(f"布林带: 上轨{analysis['boll_up']:.2f} / 中轨{analysis['boll_mid']:.2f} / 下轨{analysis['boll_down']:.2f}")
        print(f"布林带位置: {analysis['boll_signal']}")
        
        print("\n四、近期统计")
        print("-" * 80)
        print(f"5日涨跌幅: {analysis['price_change_5d']:+.2f}%")
        print(f"20日涨跌幅: {analysis['price_change_20d']:+.2f}%")
        print(f"20日波动率: {analysis['volatility_20d']:.2f}%")
        print(f"5日均量: {analysis['avg_volume_5d']:,.0f} 手")
        
        print("\n五、未来预测")
        print("-" * 80)
        print(f"预测方向: {prediction['direction']}")
        print(f"目标价位: {prediction['target_price']:.2f} 元")
        print(f"预期收益: {prediction['expected_return']:+.2f}%")
        print(f"支撑位: {prediction['support']:.2f} 元")
        print(f"压力位: {prediction['resistance']:.2f} 元")
        print(f"预测依据:")
        for reason in prediction['reasons']:
            print(f"  • {reason}")
        
        print("\n六、操作建议")
        print("-" * 80)
        if prediction['direction'] == "看涨":
            print("• 建议: 逢低关注，可在支撑位附近建仓")
            print("• 止损: 跌破支撑位考虑止损")
            print("• 止盈: 接近压力位可考虑减仓")
        elif prediction['direction'] == "看跌":
            print("• 建议: 观望为主，等待企稳信号")
            print("• 持仓: 考虑减仓或止损")
            print("• 抄底: 等待RSI进入超卖区且出现企稳信号")
        else:
            print("• 建议: 震荡行情，高抛低吸")
            print("• 区间: 在支撑位买入，压力位卖出")
            print("• 仓位: 控制仓位，灵活操作")
        
        print("\n" + "=" * 80)
        print("⚠️ 免责声明：以上分析仅供参考，不构成投资建议。股市有风险，投资需谨慎。")
        print("=" * 80)
    
    def run(self):
        """
        执行分析
        """
        print("\n" + "=" * 80)
        print(f"一彬科技（{self.stock_code}）走势分析系统")
        print("=" * 80)
        
        # 获取数据
        df = self.get_historical_data(days=120)
        if df.empty:
            print("❌ 无法获取数据，分析终止")
            return
        
        # 计算指标
        df = self.calculate_indicators(df)
        
        # 分析走势
        analysis = self.analyze_trend(df)
        
        # 预测未来
        prediction = self.predict_future(df, analysis)
        
        # 生成图表
        chart_path = self.generate_chart(df, analysis, prediction)
        
        # 打印报告
        self.print_analysis_report(analysis, prediction)
        
        return df, analysis, prediction, chart_path

def main():
    analyzer = YibinAnalyzer()
    analyzer.run()

if __name__ == '__main__':
    main()
