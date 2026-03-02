# -*- coding: utf-8 -*-
"""
===================================
每日复盘脚本
===================================

功能：
1. 对比前一日推荐的股票实际涨跌
2. 更新因子权重，让策略越用越准
3. 输出复盘报告
"""

import logging
import sys
import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from data_provider.base import DataFetcherManager
from utils.notification_sender import get_notification_sender

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
)
logger = logging.getLogger(__name__)


class DailyReview:
    """
    每日复盘类
    
    对比前一日推荐的股票实际涨跌，更新因子权重
    """
    
    def __init__(self):
        """
        初始化复盘器
        """
        self.data_manager = DataFetcherManager()
        self.notification_sender = get_notification_sender()
        
        # 因子权重
        self.factor_weights = {
            'volume_price': 0.25,
            'emotion': 0.25,
            'risk': 0.25,
            'liquidity': 0.25,
        }
        
        # 加载历史权重
        self._load_factor_weights()
        
        logger.info("每日复盘器初始化完成")
    
    def _load_factor_weights(self):
        """
        加载历史因子权重
        """
        weights_file = 'data_cache/factor_weights.json'
        
        try:
            if os.path.exists(weights_file):
                with open(weights_file, 'r', encoding='utf-8') as f:
                    self.factor_weights = json.load(f)
                logger.info(f"加载历史因子权重: {self.factor_weights}")
        except Exception as e:
            logger.warning(f"加载历史因子权重失败: {e}")
    
    def _save_factor_weights(self):
        """
        保存因子权重
        """
        weights_file = 'data_cache/factor_weights.json'
        
        try:
            os.makedirs(os.path.dirname(weights_file), exist_ok=True)
            with open(weights_file, 'w', encoding='utf-8') as f:
                json.dump(self.factor_weights, f, ensure_ascii=False, indent=2)
            logger.info(f"保存因子权重: {self.factor_weights}")
        except Exception as e:
            logger.error(f"保存因子权重失败: {e}")
    
    def _load_previous_recommendations(self) -> List[Dict[str, Any]]:
        """
        加载前一日推荐股票
        
        Returns:
            推荐股票列表
        """
        recommendations_file = 'data_cache/previous_recommendations.json'
        
        try:
            if os.path.exists(recommendations_file):
                with open(recommendations_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('stocks', [])
        except Exception as e:
            logger.warning(f"加载前一日推荐股票失败: {e}")
        
        return []
    
    def _save_current_recommendations(self, stocks: List[Dict[str, Any]]):
        """
        保存当前推荐股票
        """
        recommendations_file = 'data_cache/previous_recommendations.json'
        
        try:
            os.makedirs(os.path.dirname(recommendations_file), exist_ok=True)
            data = {
                'date': datetime.now().strftime('%Y-%m-%d'),
                'stocks': stocks
            }
            with open(recommendations_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"保存当前推荐股票: {len(stocks)} 只")
        except Exception as e:
            logger.error(f"保存当前推荐股票失败: {e}")
    
    def _get_actual_performance(self, code: str) -> Optional[float]:
        """
        获取股票实际表现
        
        Args:
            code: 股票代码
            
        Returns:
            实际涨跌幅
        """
        try:
            df, _ = self.data_manager.get_daily_data(code, days=2)
            if not df.empty and len(df) >= 2:
                # 获取最新两天的数据
                latest = df.iloc[-1]
                previous = df.iloc[-2]
                
                # 计算涨跌幅
                close_price = float(latest.get('close', 0))
                prev_close = float(previous.get('close', 0))
                
                if prev_close > 0:
                    change_pct = (close_price - prev_close) / prev_close * 100
                    return change_pct
        except Exception as e:
            logger.warning(f"获取股票 {code} 实际表现失败: {e}")
        
        return None
    
    def _update_factor_weights(self, performance_data: List[Dict[str, Any]]):
        """
        更新因子权重
        
        Args:
            performance_data: 表现数据列表
        """
        if not performance_data:
            logger.warning("无表现数据，跳过权重更新")
            return
        
        # 计算各因子的准确率
        factor_accuracy = {
            'volume_price': [],
            'emotion': [],
            'risk': [],
            'liquidity': []
        }
        
        for data in performance_data:
            actual_change = data.get('actual_change', 0)
            
            # 量价因子
            if data.get('turnover_rate_valid', False):
                if actual_change > 0:
                    factor_accuracy['volume_price'].append(1)
                else:
                    factor_accuracy['volume_price'].append(0)
            
            # 情绪因子
            if data.get('sector_rank_valid', False) or data.get('speed_valid', False):
                if actual_change > 0:
                    factor_accuracy['emotion'].append(1)
                else:
                    factor_accuracy['emotion'].append(0)
            
            # 风险因子
            if data.get('ma5_support_valid', False):
                if actual_change > 0:
                    factor_accuracy['risk'].append(1)
                else:
                    factor_accuracy['risk'].append(0)
            
            # 流动性因子
            if data.get('amount_valid', False) or data.get('circ_mv_valid', False):
                if actual_change > 0:
                    factor_accuracy['liquidity'].append(1)
                else:
                    factor_accuracy['liquidity'].append(0)
        
        # 计算平均准确率
        for factor in factor_accuracy:
            if factor_accuracy[factor]:
                accuracy = sum(factor_accuracy[factor]) / len(factor_accuracy[factor])
                logger.info(f"{factor} 因子准确率: {accuracy:.2%}")
                
                # 更新权重（准确率越高，权重越大）
                self.factor_weights[factor] = 0.1 + accuracy * 0.9
        
        # 归一化权重
        total_weight = sum(self.factor_weights.values())
        for factor in self.factor_weights:
            self.factor_weights[factor] /= total_weight
        
        logger.info(f"更新后因子权重: {self.factor_weights}")
        
        # 保存权重
        self._save_factor_weights()
    
    def run_review(self):
        """
        执行每日复盘
        """
        logger.info("开始执行每日复盘...")
        
        # 1. 加载前一日推荐股票
        previous_recommendations = self._load_previous_recommendations()
        
        if not previous_recommendations:
            logger.warning("无前一日推荐股票，跳过复盘")
            return
        
        logger.info(f"加载前一日推荐股票: {len(previous_recommendations)} 只")
        
        # 2. 获取实际表现
        performance_data = []
        
        for stock in previous_recommendations:
            code = stock.get('code', '')
            
            # 获取实际涨跌幅
            actual_change = self._get_actual_performance(code)
            
            if actual_change is not None:
                performance_data.append({
                    'code': code,
                    'name': stock.get('name', ''),
                    'actual_change': actual_change,
                    'turnover_rate_valid': stock.get('turnover_rate_valid', False),
                    'sector_rank_valid': stock.get('sector_rank_valid', False),
                    'speed_valid': stock.get('speed_valid', False),
                    'ma5_support_valid': stock.get('ma5_support_valid', False),
                    'amount_valid': stock.get('amount_valid', False),
                    'circ_mv_valid': stock.get('circ_mv_valid', False),
                })
        
        logger.info(f"获取实际表现数据: {len(performance_data)} 只")
        
        # 3. 计算统计指标
        if performance_data:
            profit_count = sum(1 for d in performance_data if d['actual_change'] > 0)
            loss_count = sum(1 for d in performance_data if d['actual_change'] <= 0)
            accuracy = profit_count / len(performance_data) * 100
            avg_change = sum(d['actual_change'] for d in performance_data) / len(performance_data)
            
            # 计算各因子准确率
            volume_price_accuracy = 0
            emotion_accuracy = 0
            risk_accuracy = 0
            liquidity_accuracy = 0
            
            for data in performance_data:
                if data['actual_change'] > 0:
                    if data['turnover_rate_valid']:
                        volume_price_accuracy += 1
                    if data['sector_rank_valid'] or data['speed_valid']:
                        emotion_accuracy += 1
                    if data['ma5_support_valid']:
                        risk_accuracy += 1
                    if data['amount_valid'] or data['circ_mv_valid']:
                        liquidity_accuracy += 1
            
            total_profit = profit_count
            if total_profit > 0:
                volume_price_accuracy = volume_price_accuracy / total_profit * 100
                emotion_accuracy = emotion_accuracy / total_profit * 100
                risk_accuracy = risk_accuracy / total_profit * 100
                liquidity_accuracy = liquidity_accuracy / total_profit * 100
            
            # 4. 更新因子权重
            self._update_factor_weights(performance_data)
            
            # 5. 生成复盘报告
            review_data = {
                'recommended_count': len(previous_recommendations),
                'avg_change': avg_change,
                'profit_count': profit_count,
                'loss_count': loss_count,
                'accuracy': accuracy,
                'volume_price_accuracy': volume_price_accuracy,
                'emotion_accuracy': emotion_accuracy,
                'risk_accuracy': risk_accuracy,
                'liquidity_accuracy': liquidity_accuracy,
                'turnover_range_suggestion': '3%-10%',
                'volume_ratio_suggestion': '>1.5',
                'hold_days_suggestion': '1-2天',
                'improvement_suggestions': self._generate_improvement_suggestions(performance_data),
            }
            
            # 6. 输出复盘报告
            self._generate_review_report(review_data)
            
            # 7. 发送复盘结果到豆包
            self._send_review_to_doubao(review_data)
        else:
            logger.warning("无实际表现数据，跳过复盘")
    
    def _generate_improvement_suggestions(self, performance_data: List[Dict[str, Any]]) -> str:
        """
        生成改进建议
        
        Args:
            performance_data: 表现数据列表
            
        Returns:
            改进建议字符串
        """
        suggestions = []
        
        avg_change = sum(d['actual_change'] for d in performance_data) / len(performance_data)
        
        if avg_change < 0:
            suggestions.append("1. 整体表现不佳，建议调整因子权重")
            suggestions.append("2. 考虑增加风险因子的权重")
        elif avg_change > 2:
            suggestions.append("1. 整体表现良好，可以保持当前策略")
        else:
            suggestions.append("1. 整体表现一般，建议微调参数")
        
        # 检查各因子表现
        volume_price_valid_count = sum(1 for d in performance_data if d['turnover_rate_valid'] and d['actual_change'] > 0)
        emotion_valid_count = sum(1 for d in performance_data if (d['sector_rank_valid'] or d['speed_valid']) and d['actual_change'] > 0)
        
        if volume_price_valid_count < emotion_valid_count:
            suggestions.append("2. 情绪因子表现更好，建议提高情绪因子权重")
        elif emotion_valid_count < volume_price_valid_count:
            suggestions.append("2. 量价因子表现更好，建议提高量价因子权重")
        
        return '\n'.join(suggestions)
    
    def _generate_review_report(self, review_data: Dict[str, Any]):
        """
        生成复盘报告
        
        Args:
            review_data: 复盘数据
        """
        logger.info("生成复盘报告...")
        
        print(f"\n===================================")
        print(f"每日策略复盘")
        print(f"===================================")
        
        print(f"\n📊 前日推荐表现:")
        print(f"• 推荐股票数：{review_data['recommended_count']}")
        print(f"• 平均涨幅：{review_data['avg_change']:.2f}%")
        print(f"• 盈利股票数：{review_data['profit_count']}")
        print(f"• 亏损股票数：{review_data['loss_count']}")
        print(f"• 准确率：{review_data['accuracy']:.2f}%")
        
        print(f"\n🎯 因子表现分析:")
        print(f"• 量价因子准确率：{review_data['volume_price_accuracy']:.2f}%")
        print(f"• 情绪因子准确率：{review_data['emotion_accuracy']:.2f}%")
        print(f"• 风险因子准确率：{review_data['risk_accuracy']:.2f}%")
        print(f"• 流动性因子准确率：{review_data['liquidity_accuracy']:.2f}%")
        
        print(f"\n🔧 参数优化建议:")
        print(f"• 换手率范围：{review_data['turnover_range_suggestion']}")
        print(f"• 量比阈值：{review_data['volume_ratio_suggestion']}")
        print(f"• 持有天数：{review_data['hold_days_suggestion']}")
        
        print(f"\n💡 改进建议:")
        print(f"{review_data['improvement_suggestions']}")
    
    def _send_review_to_doubao(self, review_data: Dict[str, Any]):
        """
        发送复盘结果到豆包
        
        Args:
            review_data: 复盘数据
        """
        try:
            logger.info("开始发送复盘结果到豆包...")
            success = self.notification_sender.send_daily_review(review_data)
            
            if success:
                logger.info("复盘结果发送成功")
            else:
                logger.warning("复盘结果发送失败")
        except Exception as e:
            logger.error(f"发送复盘结果到豆包时发生错误: {e}")


def main():
    """
    主函数
    """
    logger.info("开始每日复盘...")
    
    # 创建复盘器
    reviewer = DailyReview()
    
    # 执行复盘
    reviewer.run_review()
    
    logger.info("每日复盘完成")


if __name__ == "__main__":
    main()
