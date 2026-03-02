# -*- coding: utf-8 -*-
"""
===================================
结果推送模块
===================================

功能：
1. 使用豆包 API 将选股结果发送到豆包专属对话
2. 支持推送板块推荐、个股推荐、回测报告等
"""

import logging
import json
import requests
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_fixed

from config.settings import get_settings

logger = logging.getLogger(__name__)


class NotificationSender:
    """
    通知发送类
    
    【修改类】新增统一推送函数和重试机制
    
    使用豆包 API 发送消息
    """
    
    def __init__(self, api_key: str = None):
        """
        初始化通知发送器
        
        【修改方法】支持从配置文件读取API Key
        
        Args:
            api_key: 豆包 API 密钥，默认从配置文件读取
        """
        self.settings = get_settings().doubao
        
        self.api_key = api_key or self.settings.api_key
        self.api_url = self.settings.api_url
        self.model = self.settings.model
        self.max_tokens = self.settings.max_tokens
        self.temperature = self.settings.temperature
        self.retry_times = self.settings.retry_times
        self.retry_delay = self.settings.retry_delay
        
        # Token监控
        self.token_usage = 0
        self.token_limit = 10000  # 假设的token限额
        
        logger.info("通知发送器初始化完成")
    
    def send_stock_selection_result(self, sectors: List[Dict[str, Any]], stocks: List[Dict[str, Any]]) -> bool:
        """
        发送选股结果
        
        Args:
            sectors: 推荐板块列表
            stocks: 推荐个股列表
            
        Returns:
            是否发送成功
        """
        message = self._format_stock_selection_message(sectors, stocks)
        return self._send_message(message)
    
    def send_backtest_result(self, result: Dict[str, Any]) -> bool:
        """
        发送回测结果
        
        Args:
            result: 回测结果字典
            
        Returns:
            是否发送成功
        """
        message = self._format_backtest_message(result)
        return self._send_message(message)
    
    def send_daily_review(self, review_data: Dict[str, Any]) -> bool:
        """
        发送每日复盘结果
        
        Args:
            review_data: 复盘数据字典
            
        Returns:
            是否发送成功
        """
        message = self._format_daily_review_message(review_data)
        return self._send_message(message)
    
    def _format_stock_selection_message(self, sectors: List[Dict[str, Any]], stocks: List[Dict[str, Any]]) -> str:
        """
        格式化选股结果消息
        
        Args:
            sectors: 推荐板块列表
            stocks: 推荐个股列表
            
        Returns:
            格式化后的消息
        """
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        message = f"""
📊 沪深主板短线策略选股结果
🕐 时间：{current_time}

🔥 热度前十的板块：
"""
        
        for i, sector in enumerate(sectors[:10], 1):
            message += f"{i}. {sector.get('name', 'N/A')} ({sector.get('change_pct', 0):.2f}%)\n"
        
        message += f"""
📈 推荐可操作个股 (超短线持有1-2天)：
"""
        
        if stocks:
            for i, stock in enumerate(stocks[:10], 1):
                message += f"{i}. {stock.get('code', 'N/A')} {stock.get('name', 'N/A')} "
                message += f"价格:{stock.get('price', 0):.2f} "
                message += f"涨跌幅:{stock.get('change_pct', 0):.2f}% "
                message += f"得分:{stock.get('total_score', 0):.1f}\n"
        else:
            message += "暂无符合条件的股票\n"
        
        message += """
💡 操作建议：
1. 超短线操作，建议持有1-2天
2. 关注热门板块中的龙头个股
3. 控制仓位，单只股票建议不超过总资金的20%
4. 设置止损位，建议在成本价下方3%左右
5. 密切关注大盘走势，如遇系统性风险及时止损
6. 推荐股票仅供参考，不构成投资建议
"""
        
        return message
    
    def _format_backtest_message(self, result: Dict[str, Any]) -> str:
        """
        格式化回测结果消息
        
        Args:
            result: 回测结果字典
            
        Returns:
            格式化后的消息
        """
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        message = f"""
📈 策略回测报告
🕐 时间：{current_time}

💰 资金情况：
• 初始资金：{result.get('initial_capital', 0):.2f} 元
• 最终资金：{result.get('final_capital', 0):.2f} 元
• 总收益率：{result.get('total_return', 0):.2f}%

📊 交易统计：
• 总交易次数：{result.get('total_trades', 0)}
• 盈利交易次数：{result.get('winning_trades', 0)}
• 亏损交易次数：{result.get('losing_trades', 0)}
• 胜率：{result.get('win_rate', 0):.2f}%

💵 盈利分析：
• 平均单次盈利：{result.get('avg_profit', 0):.2f} 元
• 最大回撤：{result.get('max_drawdown', 0):.2f}%
• 盈利最高的板块：{result.get('best_sector', 'N/A')}

⚠️ 风险提示：
• 回测结果仅供参考，不保证未来收益
• 实际交易需考虑手续费、滑点等因素
• 请根据自身风险承受能力谨慎投资
"""
        
        return message
    
    def _format_daily_review_message(self, review_data: Dict[str, Any]) -> str:
        """
        格式化每日复盘消息
        
        Args:
            review_data: 复盘数据字典
            
        Returns:
            格式化后的消息
        """
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        message = f"""
📋 每日策略复盘
🕐 时间：{current_time}

📊 前日推荐表现：
• 推荐股票数：{review_data.get('recommended_count', 0)}
• 平均涨幅：{review_data.get('avg_change', 0):.2f}%
• 盈利股票数：{review_data.get('profit_count', 0)}
• 亏损股票数：{review_data.get('loss_count', 0)}
• 准确率：{review_data.get('accuracy', 0):.2f}%

🎯 因子表现分析：
• 量价因子准确率：{review_data.get('volume_price_accuracy', 0):.2f}%
• 情绪因子准确率：{review_data.get('emotion_accuracy', 0):.2f}%
• 风险因子准确率：{review_data.get('risk_accuracy', 0):.2f}%
• 流动性因子准确率：{review_data.get('liquidity_accuracy', 0):.2f}%

🔧 参数优化建议：
• 换手率范围：{review_data.get('turnover_range_suggestion', '3%-10%')}
• 量比阈值：{review_data.get('volume_ratio_suggestion', '>1.5')}
• 持有天数：{review_data.get('hold_days_suggestion', '1-2天')}

💡 改进建议：
{review_data.get('improvement_suggestions', '暂无建议')}
"""
        
        return message
    
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(5))
    def _send_message(self, message: str) -> bool:
        """
        发送消息到豆包
        
        【修改方法】新增重试机制（3次自动重试）
        
        Args:
            message: 消息内容
            
        Returns:
            是否发送成功
        """
        try:
            # Token监控：剩余<10%时切换轻量化推理
            if self._check_token_threshold():
                logger.warning("Token额度不足，切换轻量化推理")
                message = self._optimize_message(message)
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": message
                    }
                ],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens
            }
            
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                # 更新token使用量
                self._update_token_usage(response)
                logger.info("消息发送成功")
                return True
            else:
                logger.error(f"消息发送失败，状态码: {response.status_code}")
                logger.error(f"响应内容: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"发送消息时发生错误: {e}")
            raise  # 抛出异常以便重试
    
    def _check_token_threshold(self) -> bool:
        """
        检查Token额度是否低于阈值
        
        【新增方法】Token监控
        
        Returns:
            是否低于阈值
        """
        if not self.settings.token_monitor_enabled:
            return False
        
        usage_percent = (self.token_usage / self.token_limit) * 100
        remaining_percent = 100 - usage_percent
        
        logger.debug(f"Token使用情况: {self.token_usage}/{self.token_limit} ({usage_percent:.1f}%)")
        
        return remaining_percent < self.settings.token_threshold_percent
    
    def _update_token_usage(self, response):
        """
        更新Token使用量
        
        【新增方法】
        
        Args:
            response: API响应
        """
        try:
            data = response.json()
            if 'usage' in data and 'total_tokens' in data['usage']:
                self.token_usage += data['usage']['total_tokens']
                logger.debug(f"本次使用Token: {data['usage']['total_tokens']}, 累计: {self.token_usage}")
        except Exception as e:
            logger.warning(f"更新Token使用量失败: {e}")
    
    def _optimize_message(self, message: str) -> str:
        """
        优化消息内容（减少Token使用）
        
        【新增方法】省Token优化
        
        Args:
            message: 原始消息
            
        Returns:
            优化后的消息
        """
        # 删除冗余描述，仅保留核心内容
        lines = message.split('\n')
        optimized_lines = []
        
        for line in lines:
            # 删除装饰性字符
            line = line.replace('📊', '').replace('📈', '').replace('🔥', '')
            line = line.replace('💡', '').replace('⚠️', '').replace('💰', '')
            line = line.replace('🕐', '').replace('🏆', '').replace('📋', '')
            line = line.replace('🎯', '').replace('🔧', '').replace('📢', '')
            
            # 跳过空行和纯装饰行
            if line.strip() and not line.strip().startswith('='):
                optimized_lines.append(line)
        
        return '\n'.join(optimized_lines)
    
    def send_unified_notification(self, notification_type: str, data: Dict[str, Any]) -> bool:
        """
        统一推送函数
        
        【新增方法】合并选股结果推送和回测结果推送
        
        Args:
            notification_type: 通知类型（selection/backtest/review）
            data: 通知数据
            
        Returns:
            是否发送成功
        """
        logger.info(f"发送统一通知: {notification_type}")
        
        try:
            if notification_type == 'selection':
                return self.send_stock_selection_result(
                    data.get('sectors', []),
                    data.get('stocks', [])
                )
            elif notification_type == 'backtest':
                return self.send_backtest_result(data)
            elif notification_type == 'review':
                return self.send_daily_review(data)
            else:
                logger.warning(f"未知的通知类型: {notification_type}")
                return False
                
        except Exception as e:
            logger.error(f"发送统一通知失败: {e}")
            return False
    
    def send_custom_message(self, title: str, content: str) -> bool:
        """
        发送自定义消息
        
        Args:
            title: 消息标题
            content: 消息内容
            
        Returns:
            是否发送成功
        """
        message = f"""
📢 {title}
🕐 时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{content}
"""
        return self._send_message(message)


# 单例模式
_notification_sender = None


def get_notification_sender(api_key: str = None) -> Optional[NotificationSender]:
    """
    获取通知发送器实例（单例）
    
    Args:
        api_key: 豆包 API 密钥，默认从配置文件读取
        
    Returns:
        NotificationSender实例
    """
    global _notification_sender
    
    if _notification_sender is None:
        _notification_sender = NotificationSender(api_key)
    
    return _notification_sender


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    sender = get_notification_sender()
    
    # 测试发送选股结果
    print("\n测试发送选股结果:")
    test_sectors = [
        {'name': '半导体', 'change_pct': 5.2},
        {'name': '新能源', 'change_pct': 3.8},
    ]
    test_stocks = [
        {'code': '600000', 'name': '浦发银行', 'price': 10.5, 'change_pct': 2.1, 'total_score': 85.5},
        {'code': '600519', 'name': '贵州茅台', 'price': 1500.0, 'change_pct': 1.5, 'total_score': 78.2},
    ]
    sender.send_stock_selection_result(test_sectors, test_stocks)
    
    # 测试发送回测结果
    print("\n测试发送回测结果:")
    test_backtest = {
        'initial_capital': 100000,
        'final_capital': 102500,
        'total_return': 2.5,
        'total_trades': 50,
        'winning_trades': 30,
        'losing_trades': 20,
        'win_rate': 60.0,
        'avg_profit': 50.0,
        'max_drawdown': 3.2,
        'best_sector': '金融'
    }
    sender.send_backtest_result(test_backtest)
