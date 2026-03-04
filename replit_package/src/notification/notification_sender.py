# -*- coding: utf-8 -*-
"""
===================================
通知发送模块
===================================

【功能】
1. 通过豆包API发送通知
2. 支持结构化消息格式
3. 自动格式化关键信息
4. 错误重试机制

【核心特性】
- 结构化通知：清晰展示关键信息
- 高亮显示：重要信息突出显示
- 自动重试：发送失败自动重试
- 日志记录：完整记录发送过程
"""

import logging
import sys
import os
import time
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv
from utils.logger_config import setup_logger

logger = setup_logger(__name__, log_file='logs/notification.log')

load_dotenv()


class NotificationSender:
    """
    通知发送器
    
    【核心类】
    功能：
    1. 通过豆包API发送通知
    2. 格式化消息内容
    3. 处理发送错误和重试
    """
    
    def __init__(self):
        """
        初始化通知发送器
        """
        self.api_key = os.getenv('DOUBAO_API_KEY', '')
        self.api_url = os.getenv('DOUBAO_API_URL', 'https://ark.cn-beijing.volces.com/api/v3/chat/completions')
        self.model = os.getenv('DOUBAO_MODEL', 'Doubao-Seedream-5.0-lite')
        self.max_tokens = int(os.getenv('DOUBAO_MAX_TOKENS', '1000'))
        self.temperature = float(os.getenv('DOUBAO_TEMPERATURE', '0.7'))
        self.retry_times = int(os.getenv('DOUBAO_RETRY_TIMES', '3'))
        self.retry_delay = int(os.getenv('DOUBAO_RETRY_DELAY', '5'))
        self.enabled = os.getenv('DOUBAO_PUSH_ENABLED', 'true').lower() == 'true'
        
        logger.info(f"通知发送器初始化完成，启用状态: {self.enabled}")
    
    def _format_message(self, title: str, message: str, data: Dict[str, Any]) -> str:
        """
        格式化消息内容
        
        Args:
            title: 通知标题
            message: 通知消息
            data: 结构化数据
            
        Returns:
            格式化后的消息
        """
        formatted = []
        
        # 标题
        formatted.append("=" * 60)
        formatted.append(f"【{title}】")
        formatted.append("=" * 60)
        formatted.append(f"\n时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        formatted.append(f"\n{message}")
        
        # 结构化数据
        if data:
            formatted.append("\n" + "-" * 60)
            formatted.append("详细信息：")
            formatted.append("-" * 60)
            
            # 选股结果
            if 'stocks' in data:
                formatted.append("\n📊 选股结果：")
                stocks = data['stocks']
                for i, stock in enumerate(stocks[:10], 1):  # 最多显示10只
                    code = stock.get('code', '')
                    name = stock.get('name', '')
                    close = stock.get('close', 0)
                    pct_chg = stock.get('pct_chg', 0)
                    score = stock.get('selection_score', 0)
                    logic = stock.get('selection_logic', '')
                    buy_range = stock.get('buy_range', '')
                    stop_loss = stock.get('stop_loss', 0)
                    take_profit = stock.get('take_profit', 0)
                    
                    formatted.append(f"\n  {i}. {code} {name}")
                    formatted.append(f"     收盘: {close:.2f}元  涨幅: {pct_chg:+.2f}%")
                    formatted.append(f"     得分: {score}分  逻辑: {logic}")
                    formatted.append(f"     买入: {buy_range}元")
                    formatted.append(f"     止损: {stop_loss:.2f}元  止盈: {take_profit:.2f}元")
                
                if len(stocks) > 10:
                    formatted.append(f"\n  ... 还有{len(stocks) - 10}只股票")
            
            # 回测结果
            if 'win_rate' in data:
                formatted.append("\n📈 回测结果：")
                formatted.append(f"  总交易: {data.get('total_trades', 0)}次")
                formatted.append(f"  胜率: {data.get('win_rate', 0):.2f}%")
                formatted.append(f"  年化收益: {data.get('annualized_return', 0):.2f}%")
                formatted.append(f"  最大回撤: {data.get('max_drawdown', 0):.2f}%")
                formatted.append(f"  夏普比率: {data.get('sharpe_ratio', 0):.2f}")
                formatted.append(f"  盈亏比: {data.get('profit_loss_ratio', 0):.2f}")
            
            # 复盘数据
            if 'up_count' in data:
                formatted.append("\n📋 市场复盘：")
                formatted.append(f"  上涨: {data.get('up_count', 0)}只")
                formatted.append(f"  下跌: {data.get('down_count', 0)}只")
                formatted.append(f"  平盘: {data.get('flat_count', 0)}只")
                formatted.append(f"  平均涨跌: {data.get('avg_pct_chg', 0):.2f}%")
                formatted.append(f"  成交额: {data.get('total_amount', 0):.0f}亿元")
                formatted.append(f"  热门板块: {data.get('hot_sectors', '')}")
                formatted.append(f"  市场情绪: {data.get('market_sentiment', '')}")
                formatted.append(f"  交易建议: {data.get('trading_advice', '')}")
            
            # 任务结果
            if 'task_results' in data:
                formatted.append("\n📝 任务执行汇总：")
                for task_name, result in data['task_results'].items():
                    status = "✅ 成功" if result.get('success', False) else "❌ 失败"
                    formatted.append(f"  {result.get('task_name', task_name)}: {status}")
                    formatted.append(f"    {result.get('message', '')}")
        
        formatted.append("\n" + "=" * 60)
        formatted.append("⚠️ 免责声明：以上内容仅供参考，不构成投资建议")
        formatted.append("=" * 60)
        
        return '\n'.join(formatted)
    
    def _call_doubao_api(self, message: str) -> Dict[str, Any]:
        """
        调用豆包API
        
        Args:
            message: 要发送的消息
            
        Returns:
            API响应结果
        """
        if not self.api_key:
            logger.warning("豆包API Key未配置，跳过通知发送")
            return {'success': False, 'message': 'API Key未配置'}
        
        if not self.enabled:
            logger.info("通知推送已禁用，跳过发送")
            return {'success': False, 'message': '通知推送已禁用'}
        
        try:
            import requests
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_key}'
            }
            
            payload = {
                'model': self.model,
                'messages': [
                    {
                        'role': 'user',
                        'content': message
                    }
                ],
                'max_tokens': self.max_tokens,
                'temperature': self.temperature
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"豆包API调用成功: {result.get('usage', {})}")
                return {'success': True, 'data': result}
            else:
                error_msg = f"API调用失败: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return {'success': False, 'message': error_msg}
                
        except Exception as e:
            error_msg = f"API调用异常: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {'success': False, 'message': error_msg}
    
    def send_notification(self, title: str, message: str, 
                       data: Optional[Dict[str, Any]] = None,
                       retry: Optional[int] = None) -> Dict[str, Any]:
        """
        发送通知
        
        Args:
            title: 通知标题
            message: 通知消息
            data: 结构化数据（可选）
            retry: 重试次数（可选）
            
        Returns:
            发送结果
        """
        logger.info(f"准备发送通知: {title}")
        
        # 格式化消息
        formatted_message = self._format_message(title, message, data)
        
        # 确定重试次数
        retry_count = retry if retry is not None else self.retry_times
        
        # 重试机制
        for attempt in range(retry_count):
            try:
                logger.info(f"发送通知尝试 {attempt + 1}/{retry_count}")
                
                # 调用豆包API
                result = self._call_doubao_api(formatted_message)
                
                if result['success']:
                    logger.info(f"✅ 通知发送成功")
                    return {
                        'success': True,
                        'message': '通知发送成功',
                        'timestamp': datetime.now().isoformat()
                    }
                else:
                    logger.warning(f"通知发送失败: {result['message']}")
                    
                    if attempt < retry_count - 1:
                        wait_time = self.retry_delay * (attempt + 1)
                        logger.info(f"等待{wait_time}秒后重试...")
                        time.sleep(wait_time)
                    else:
                        logger.error(f"通知发送失败，已达到最大重试次数")
                        return {
                            'success': False,
                            'message': f"发送失败: {result['message']}",
                            'timestamp': datetime.now().isoformat()
                        }
            
            except Exception as e:
                logger.error(f"通知发送异常: {e}", exc_info=True)
                
                if attempt < retry_count - 1:
                    wait_time = self.retry_delay * (attempt + 1)
                    logger.info(f"等待{wait_time}秒后重试...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"通知发送失败，已达到最大重试次数")
                    return {
                        'success': False,
                        'message': f"发送异常: {str(e)}",
                        'timestamp': datetime.now().isoformat()
                    }
        
        return {
            'success': False,
            'message': '未知错误',
            'timestamp': datetime.now().isoformat()
        }
    
    def send_stock_selection_notification(self, stocks: List[Dict[str, Any]], 
                                      date: str) -> Dict[str, Any]:
        """
        发送选股结果通知
        
        Args:
            stocks: 选股结果列表
            date: 选股日期
            
        Returns:
            发送结果
        """
        title = f"尾盘选股结果 - {date}"
        message = f"今日选出{len(stocks)}只股票，建议次日早盘买入"
        
        data = {
            'stocks': stocks,
            'date': date
        }
        
        return self.send_notification(title, message, data)
    
    def send_backtest_notification(self, backtest_results: Dict[str, Any],
                                date: str) -> Dict[str, Any]:
        """
        发送回测结果通知
        
        Args:
            backtest_results: 回测结果字典
            date: 回测日期
            
        Returns:
            发送结果
        """
        title = f"历史回测结果 - {date}"
        message = f"策略回测完成，胜率{backtest_results.get('win_rate', 0):.2f}%"
        
        return self.send_notification(title, message, backtest_results)
    
    def send_review_notification(self, review_data: Dict[str, Any],
                            date: str) -> Dict[str, Any]:
        """
        发送复盘结果通知
        
        Args:
            review_data: 复盘数据字典
            date: 复盘日期
            
        Returns:
            发送结果
        """
        title = f"市场复盘报告 - {date}"
        message = f"市场复盘完成，交易建议：{review_data.get('trading_advice', '')}"
        
        return self.send_notification(title, message, review_data)
    
    def send_summary_notification(self, task_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        发送汇总通知
        
        Args:
            task_results: 任务结果字典
            
        Returns:
            发送结果
        """
        title = "股票量化系统 - 执行汇总"
        message = "所有定时任务执行完成"
        
        data = {
            'task_results': task_results
        }
        
        return self.send_notification(title, message, data)


# 全局通知发送器实例
_notification_sender_instance = None

def get_notification_sender() -> NotificationSender:
    """
    获取通知发送器单例
    
    Returns:
        NotificationSender实例
    """
    global _notification_sender_instance
    if _notification_sender_instance is None:
        _notification_sender_instance = NotificationSender()
    return _notification_sender_instance
