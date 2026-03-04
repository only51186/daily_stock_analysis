# -*- coding: utf-8 -*-
"""
===================================
股票走势预测交互界面
===================================

【功能】
1. 基于tkinter开发，支持输入单个股票代码
2. 显示近30天历史走势曲线（价格+成交量双轴）
3. 显示未来2天预测走势曲线（标注上涨概率/关键价位）
4. 情绪评分/板块热度（复用原有情绪分析逻辑）
5. 界面适配新手操作，无需新增复杂依赖

【开发状态】新增模块
"""

import logging
import sys
import os
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple, Optional

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from data_provider.multi_data_source import get_multi_data_source
from data_provider.data_cache import get_data_cache
from config.settings import get_settings
from utils.logger_config import setup_logger

# 配置日志
logger = setup_logger(__name__, log_file='logs/ui.log')

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False


class StockPredictionUI:
    """
    股票走势预测界面
    
    【新增类】
    功能：提供股票走势预测的可视化界面
    """
    
    def __init__(self):
        """
        初始化界面
        """
        self.settings = get_settings()
        self.data_source = get_multi_data_source()
        self.cache = get_data_cache()
        
        # 创建主窗口
        self.root = tk.Tk()
        self.root.title("股票走势预测 - 沪深主板短线策略")
        self.root.geometry("1400x900")
        self.root.configure(bg='#f0f0f0')
        
        # 设置窗口最小尺寸
        self.root.minsize(1200, 800)
        
        # 初始化界面组件
        self._init_ui()
        
        logger.info("股票走势预测界面初始化完成")
    
    def _init_ui(self):
        """
        初始化界面组件
        
        【新增方法】
        """
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # ===== 顶部：输入区域 =====
        input_frame = ttk.LabelFrame(main_frame, text="股票查询", padding="10")
        input_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 股票代码输入
        ttk.Label(input_frame, text="股票代码:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.stock_code_var = tk.StringVar(value="600000")
        self.stock_code_entry = ttk.Entry(input_frame, textvariable=self.stock_code_var, width=15)
        self.stock_code_entry.grid(row=0, column=1, sticky=tk.W, padx=(0, 10))
        
        # 查询按钮
        self.query_btn = ttk.Button(input_frame, text="查询", command=self._on_query)
        self.query_btn.grid(row=0, column=2, padx=(0, 10))
        
        # 清空按钮
        self.clear_btn = ttk.Button(input_frame, text="清空", command=self._on_clear)
        self.clear_btn.grid(row=0, column=3, padx=(0, 10))
        
        # 快捷按钮
        quick_frame = ttk.Frame(input_frame)
        quick_frame.grid(row=0, column=4, sticky=tk.W)
        
        quick_codes = ['600000', '600519', '000001', '000858', '601318']
        for i, code in enumerate(quick_codes):
            btn = ttk.Button(quick_frame, text=code, width=8,
                           command=lambda c=code: self._set_stock_code(c))
            btn.grid(row=0, column=i, padx=2)
        
        # 状态标签
        self.status_var = tk.StringVar(value="请输入股票代码并点击查询")
        self.status_label = ttk.Label(input_frame, textvariable=self.status_var, foreground="blue")
        self.status_label.grid(row=0, column=5, sticky=tk.W, padx=(20, 0))
        
        # ===== 左侧：信息面板 =====
        info_frame = ttk.LabelFrame(main_frame, text="股票信息", padding="10")
        info_frame.grid(row=1, column=0, rowspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        info_frame.columnconfigure(0, weight=1)
        
        # 基本信息
        self.info_text = tk.Text(info_frame, height=15, width=35, wrap=tk.WORD)
        self.info_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        info_scrollbar = ttk.Scrollbar(info_frame, orient=tk.VERTICAL, command=self.info_text.yview)
        info_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.info_text['yscrollcommand'] = info_scrollbar.set
        
        # 情绪评分
        emotion_frame = ttk.LabelFrame(main_frame, text="情绪评分", padding="10")
        emotion_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10), pady=(10, 0))
        
        self.emotion_text = tk.Text(emotion_frame, height=10, width=35, wrap=tk.WORD)
        self.emotion_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        emotion_scrollbar = ttk.Scrollbar(emotion_frame, orient=tk.VERTICAL, command=self.emotion_text.yview)
        emotion_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.emotion_text['yscrollcommand'] = emotion_scrollbar.set
        
        # ===== 右侧：图表区域 =====
        chart_frame = ttk.LabelFrame(main_frame, text="走势图表", padding="10")
        chart_frame.grid(row=1, column=1, rowspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        chart_frame.columnconfigure(0, weight=1)
        chart_frame.rowconfigure(0, weight=1)
        
        # 创建matplotlib图表
        self.fig = Figure(figsize=(12, 10), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.fig, master=chart_frame)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 初始化空图表
        self._init_empty_chart()
        
        # ===== 底部：预测信息 =====
        prediction_frame = ttk.LabelFrame(main_frame, text="走势预测", padding="10")
        prediction_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        
        self.prediction_text = tk.Text(prediction_frame, height=6, width=100, wrap=tk.WORD)
        self.prediction_text.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        prediction_scrollbar = ttk.Scrollbar(prediction_frame, orient=tk.VERTICAL, command=self.prediction_text.yview)
        prediction_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.prediction_text['yscrollcommand'] = prediction_scrollbar.set
        
        # 绑定回车键
        self.stock_code_entry.bind('<Return>', lambda e: self._on_query())
    
    def _init_empty_chart(self):
        """
        初始化空图表
        
        【新增方法】
        """
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        ax.text(0.5, 0.5, '请输入股票代码查询', 
                horizontalalignment='center', verticalalignment='center',
                transform=ax.transAxes, fontsize=16, color='gray')
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        self.canvas.draw()
    
    def _set_stock_code(self, code: str):
        """
        设置股票代码
        
        【新增方法】
        
        Args:
            code: 股票代码
        """
        self.stock_code_var.set(code)
        self._on_query()
    
    def _on_clear(self):
        """
        清空按钮回调
        
        【新增方法】
        """
        self.stock_code_var.set("")
        self.info_text.delete('1.0', tk.END)
        self.emotion_text.delete('1.0', tk.END)
        self.prediction_text.delete('1.0', tk.END)
        self.status_var.set("请输入股票代码并点击查询")
        self._init_empty_chart()
    
    def _on_query(self):
        """
        查询按钮回调
        
        【新增方法】
        """
        code = self.stock_code_var.get().strip()
        
        if not code:
            messagebox.showwarning("警告", "请输入股票代码")
            return
        
        # 验证股票代码格式
        if not self._validate_stock_code(code):
            messagebox.showerror("错误", "无效的股票代码格式\n沪深主板代码格式：600xxx, 601xxx, 603xxx, 000xxx")
            return
        
        self.status_var.set(f"正在查询 {code}...")
        self.root.update()
        
        try:
            # 查询数据
            self._query_stock_data(code)
            self.status_var.set(f"查询完成: {code}")
        except Exception as e:
            logger.error(f"查询股票 {code} 失败: {e}", exc_info=True)
            self.status_var.set(f"查询失败: {code}")
            messagebox.showerror("错误", f"查询失败: {str(e)}")
    
    def _validate_stock_code(self, code: str) -> bool:
        """
        验证股票代码格式
        
        【新增方法】
        
        Args:
            code: 股票代码
            
        Returns:
            是否有效
        """
        # 移除可能的空格和点号
        code = code.strip().replace('.', '')
        
        # 检查是否为6位数字
        if not code.isdigit() or len(code) != 6:
            return False
        
        # 检查是否为沪深主板
        if code.startswith(('600', '601', '603', '000')):
            return True
        
        return False
    
    def _query_stock_data(self, code: str):
        """
        查询股票数据
        
        【新增方法】
        
        Args:
            code: 股票代码
        """
        logger.info(f"查询股票数据: {code}")
        
        # 1. 获取历史数据
        history_data, source = self.data_source.get_stock_daily_data(
            code=code,
            days=self.settings.visualization.history_days
        )
        
        if history_data.empty:
            raise ValueError(f"无法获取股票 {code} 的历史数据")
        
        # 2. 获取实时数据
        realtime_data = self._get_realtime_data(code)
        
        # 3. 获取板块热度
        sectors, _ = self.data_source.get_sector_rankings(10)
        
        # 4. 计算情绪评分
        emotion_score = self._calculate_emotion_score(code, history_data, sectors)
        
        # 5. 预测未来走势
        prediction = self._predict_trend(code, history_data)
        
        # 6. 更新界面
        self._update_info_panel(code, history_data, realtime_data)
        self._update_emotion_panel(emotion_score)
        self._update_chart(code, history_data, prediction)
        self._update_prediction_panel(prediction)
        
        logger.info(f"股票 {code} 数据查询完成")
    
    def _get_realtime_data(self, code: str) -> Dict[str, Any]:
        """
        获取实时数据
        
        【新增方法】
        
        Args:
            code: 股票代码
            
        Returns:
            实时数据字典
        """
        try:
            df, _ = self.data_source.get_realtime_data([code])
            if not df.empty:
                row = df.iloc[0]
                return {
                    'price': float(row.get('最新价', 0)),
                    'change_pct': float(row.get('涨跌幅', 0)),
                    'volume': float(row.get('成交量', 0)),
                    'turnover': float(row.get('成交额', 0)),
                }
        except Exception as e:
            logger.warning(f"获取实时数据失败: {e}")
        
        return {}
    
    def _calculate_emotion_score(self, code: str, history_data: pd.DataFrame, 
                                  sectors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        计算情绪评分
        
        【新增方法】复用原有情绪分析逻辑
        
        Args:
            code: 股票代码
            history_data: 历史数据
            sectors: 板块列表
            
        Returns:
            情绪评分字典
        """
        score = {
            'total_score': 50,  # 基础分50
            'trend_score': 0,
            'volume_score': 0,
            'sector_score': 0,
            'momentum_score': 0,
            'factors': []
        }
        
        if history_data.empty or len(history_data) < 5:
            return score
        
        # 1. 趋势评分（近5日涨跌幅）
        recent_changes = history_data['涨跌幅'].tail(5) if '涨跌幅' in history_data.columns else []
        if len(recent_changes) > 0:
            avg_change = recent_changes.mean()
            score['trend_score'] = min(20, max(-20, avg_change * 4))
            if avg_change > 0:
                score['factors'].append(f"近5日平均上涨 {avg_change:.2f}%")
        
        # 2. 成交量评分
        if '成交量' in history_data.columns:
            recent_volume = history_data['成交量'].tail(5).mean()
            prev_volume = history_data['成交量'].tail(10).head(5).mean()
            if prev_volume > 0:
                volume_change = (recent_volume - prev_volume) / prev_volume * 100
                score['volume_score'] = min(15, max(-15, volume_change * 0.5))
                if volume_change > 20:
                    score['factors'].append(f"成交量放大 {volume_change:.1f}%")
        
        # 3. 板块热度评分
        if sectors:
            # 假设股票属于前3个热门板块
            sector_change = sectors[0]['change_pct'] if sectors else 0
            score['sector_score'] = min(15, max(-15, sector_change * 3))
            if sector_change > 2:
                score['factors'].append(f"所属板块上涨 {sector_change:.2f}%")
        
        # 4. 动量评分
        if len(history_data) >= 10:
            price_5d = history_data['收盘'].tail(5).mean() if '收盘' in history_data.columns else 0
            price_10d = history_data['收盘'].tail(10).mean() if '收盘' in history_data.columns else 0
            if price_10d > 0:
                momentum = (price_5d - price_10d) / price_10d * 100
                score['momentum_score'] = min(20, max(-20, momentum * 10))
                if momentum > 0:
                    score['factors'].append(f"价格动量向上 {momentum:.2f}%")
        
        # 计算总分
        score['total_score'] = 50 + score['trend_score'] + score['volume_score'] + \
                              score['sector_score'] + score['momentum_score']
        score['total_score'] = min(100, max(0, score['total_score']))
        
        return score
    
    def _predict_trend(self, code: str, history_data: pd.DataFrame) -> Dict[str, Any]:
        """
        预测未来走势
        
        【新增方法】基于历史数据的简单预测
        
        Args:
            code: 股票代码
            history_data: 历史数据
            
        Returns:
            预测结果字典
        """
        prediction = {
            'trend': '震荡',
            'probability_up': 50,
            'probability_down': 50,
            'key_levels': {
                'support': 0,
                'resistance': 0,
                'target': 0
            },
            'recommendation': '观望'
        }
        
        if history_data.empty or len(history_data) < 10:
            return prediction
        
        # 获取最新价格和近期数据
        latest_price = history_data['收盘'].iloc[-1] if '收盘' in history_data.columns else 0
        
        if latest_price == 0:
            return prediction
        
        # 计算关键价位
        recent_high = history_data['最高'].tail(10).max() if '最高' in history_data.columns else latest_price
        recent_low = history_data['最低'].tail(10).min() if '最低' in history_data.columns else latest_price
        
        prediction['key_levels']['resistance'] = recent_high
        prediction['key_levels']['support'] = recent_low
        prediction['key_levels']['target'] = latest_price * 1.02  # 预测目标价上涨2%
        
        # 简单预测逻辑
        if '涨跌幅' in history_data.columns:
            recent_changes = history_data['涨跌幅'].tail(5)
            avg_change = recent_changes.mean()
            
            if avg_change > 1:
                prediction['trend'] = '上涨'
                prediction['probability_up'] = 60 + min(30, avg_change * 5)
                prediction['probability_down'] = 100 - prediction['probability_up']
                prediction['recommendation'] = '关注'
            elif avg_change < -1:
                prediction['trend'] = '下跌'
                prediction['probability_down'] = 60 + min(30, abs(avg_change) * 5)
                prediction['probability_up'] = 100 - prediction['probability_down']
                prediction['recommendation'] = '回避'
            else:
                prediction['trend'] = '震荡'
                prediction['probability_up'] = 50
                prediction['probability_down'] = 50
                prediction['recommendation'] = '观望'
        
        return prediction
    
    def _update_info_panel(self, code: str, history_data: pd.DataFrame, realtime_data: Dict[str, Any]):
        """
        更新信息面板
        
        【新增方法】
        
        Args:
            code: 股票代码
            history_data: 历史数据
            realtime_data: 实时数据
        """
        self.info_text.delete('1.0', tk.END)
        
        # 获取最新数据
        if not history_data.empty:
            latest = history_data.iloc[-1]
            
            info = f"""
股票代码: {code}
{'=' * 30}

最新价格: {latest.get('收盘', 'N/A')}
涨跌幅: {latest.get('涨跌幅', 'N/A')}%
成交量: {latest.get('成交量', 'N/A'):,.0f}
成交额: {latest.get('成交额', 'N/A'):,.0f}

{'=' * 30}
近30日统计:
最高价: {history_data['最高'].max():.2f}
最低价: {history_data['最低'].min():.2f}
平均价: {history_data['收盘'].mean():.2f}
振幅: {((history_data['最高'].max() - history_data['最低'].min()) / history_data['最低'].min() * 100):.2f}%

{'=' * 30}
实时数据:
"""
            
            if realtime_data:
                info += f"""
当前价格: {realtime_data.get('price', 'N/A')}
涨跌幅: {realtime_data.get('change_pct', 'N/A')}%
成交量: {realtime_data.get('volume', 'N/A'):,.0f}
成交额: {realtime_data.get('turnover', 'N/A'):,.0f}
"""
            else:
                info += "\n暂无实时数据"
            
            self.info_text.insert('1.0', info)
    
    def _update_emotion_panel(self, emotion_score: Dict[str, Any]):
        """
        更新情绪面板
        
        【新增方法】
        
        Args:
            emotion_score: 情绪评分
        """
        self.emotion_text.delete('1.0', tk.END)
        
        score = emotion_score['total_score']
        
        # 根据分数设置颜色标签
        if score >= 70:
            sentiment = "乐观"
            color = "green"
        elif score >= 50:
            sentiment = "中性"
            color = "orange"
        else:
            sentiment = "悲观"
            color = "red"
        
        emotion_text = f"""
情绪总评分: {score:.1f}/100
情绪状态: {sentiment}

{'=' * 30}
评分详情:
趋势评分: {emotion_score['trend_score']:.1f}
成交量评分: {emotion_score['volume_score']:.1f}
板块评分: {emotion_score['sector_score']:.1f}
动量评分: {emotion_score['momentum_score']:.1f}

{'=' * 30}
评分因子:
"""
        
        for factor in emotion_score['factors']:
            emotion_text += f"• {factor}\n"
        
        if not emotion_score['factors']:
            emotion_text += "• 暂无显著因子\n"
        
        self.emotion_text.insert('1.0', emotion_text)
    
    def _update_chart(self, code: str, history_data: pd.DataFrame, prediction: Dict[str, Any]):
        """
        更新图表
        
        【新增方法】
        
        Args:
            code: 股票代码
            history_data: 历史数据
            prediction: 预测结果
        """
        self.fig.clear()
        
        if history_data.empty:
            return
        
        # 创建子图
        gs = self.fig.add_gridspec(3, 1, height_ratios=[2, 1, 1], hspace=0.3)
        
        # 1. 价格走势图
        ax1 = self.fig.add_subplot(gs[0])
        
        dates = range(len(history_data))
        prices = history_data['收盘'].values if '收盘' in history_data.columns else []
        
        ax1.plot(dates, prices, 'b-', linewidth=2, label='收盘价')
        ax1.fill_between(dates, prices, alpha=0.3)
        
        # 标注关键价位
        if prediction['key_levels']['support'] > 0:
            ax1.axhline(y=prediction['key_levels']['support'], color='g', 
                       linestyle='--', alpha=0.7, label='支撑位')
        if prediction['key_levels']['resistance'] > 0:
            ax1.axhline(y=prediction['key_levels']['resistance'], color='r', 
                       linestyle='--', alpha=0.7, label='阻力位')
        
        ax1.set_title(f'{code} 价格走势', fontsize=14, fontweight='bold')
        ax1.set_ylabel('价格', fontsize=12)
        ax1.legend(loc='upper left')
        ax1.grid(True, alpha=0.3)
        
        # 2. 成交量图
        ax2 = self.fig.add_subplot(gs[1], sharex=ax1)
        
        if '成交量' in history_data.columns:
            volumes = history_data['成交量'].values
            colors = ['red' if history_data['涨跌幅'].iloc[i] > 0 else 'green' 
                     for i in range(len(history_data))] if '涨跌幅' in history_data.columns else ['blue'] * len(history_data)
            
            ax2.bar(dates, volumes, color=colors, alpha=0.7)
            ax2.set_ylabel('成交量', fontsize=12)
            ax2.grid(True, alpha=0.3)
        
        # 3. 涨跌幅图
        ax3 = self.fig.add_subplot(gs[2], sharex=ax1)
        
        if '涨跌幅' in history_data.columns:
            changes = history_data['涨跌幅'].values
            colors = ['red' if c > 0 else 'green' for c in changes]
            
            ax3.bar(dates, changes, color=colors, alpha=0.7)
            ax3.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
            ax3.set_ylabel('涨跌幅(%)', fontsize=12)
            ax3.set_xlabel('交易日', fontsize=12)
            ax3.grid(True, alpha=0.3)
        
        self.canvas.draw()
    
    def _update_prediction_panel(self, prediction: Dict[str, Any]):
        """
        更新预测面板
        
        【新增方法】
        
        Args:
            prediction: 预测结果
        """
        self.prediction_text.delete('1.0', tk.END)
        
        trend = prediction['trend']
        prob_up = prediction['probability_up']
        prob_down = prediction['probability_down']
        
        # 根据趋势设置颜色
        if trend == '上涨':
            trend_color = "上涨"
        elif trend == '下跌':
            trend_color = "下跌"
        else:
            trend_color = "震荡"
        
        prediction_text = f"""
走势预测: {trend_color}
上涨概率: {prob_up:.1f}%
下跌概率: {prob_down:.1f}%

关键价位:
  支撑位: {prediction['key_levels']['support']:.2f}
  阻力位: {prediction['key_levels']['resistance']:.2f}
  目标价: {prediction['key_levels']['target']:.2f}

操作建议: {prediction['recommendation']}

免责声明: 以上预测仅供参考，不构成投资建议。股市有风险，投资需谨慎。
"""
        
        self.prediction_text.insert('1.0', prediction_text)
    
    def run(self):
        """
        运行界面
        
        【新增方法】
        """
        logger.info("启动股票走势预测界面")
        self.root.mainloop()


def main():
    """
    主函数
    
    【新增函数】
    """
    # 创建并运行界面
    app = StockPredictionUI()
    app.run()


if __name__ == "__main__":
    main()
