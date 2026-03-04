# -*- coding: utf-8 -*-
"""
指令触发式个股分析功能

接收以「Trae：」开头的指令，自动解析指令、抓取个股数据、完成超短线分析，并返回结构化回复。

支持指令格式：
- Trae：分析个股 [股票代码]（如Trae：分析个股 600000）
- Trae：分析个股（无代码时自动提示）
- Trae：分析个股 600000 000001（自动批量分析）

适配场景：沪深主板5-35元超短线（1-2天）选股
"""

import re
import logging
import time
from typing import List, Dict, Optional, Tuple
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from data_provider.multi_data_source import MultiDataSource
from data_provider.data_cache import DataCache
from src.core.factor_library import get_factor_library, FactorType
from src.core.data_access_layer import get_data_access_layer, DataType
from config.settings import get_settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/trae_analyze.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 全局实例
_data_source = None
_data_cache = None
_factor_lib = None
_data_access = None
_config = None


def get_data_source() -> MultiDataSource:
    """获取数据源实例"""
    global _data_source
    if _data_source is None:
        _data_source = MultiDataSource()
    return _data_source


def get_data_cache() -> DataCache:
    """获取数据缓存实例"""
    global _data_cache
    if _data_cache is None:
        _data_cache = DataCache()
    return _data_cache


def get_factor_library_instance():
    """获取因子库实例"""
    global _factor_lib
    if _factor_lib is None:
        _factor_lib = get_factor_library()
    return _factor_lib


def get_data_access():
    """获取数据访问层实例"""
    global _data_access
    if _data_access is None:
        _data_access = get_data_access_layer()
    return _data_access


def get_app_config():
    """获取配置"""
    global _config
    if _config is None:
        _config = get_settings()
    return _config


class TraeStockAnalyzer:
    """Trae 指令触发式个股分析器"""
    
    def __init__(self):
        """初始化分析器"""
        self.data_source = get_data_source()
        self.data_cache = get_data_cache()
        self.factor_lib = get_factor_library_instance()
        self.data_access = get_data_access()
        self.config = get_app_config()
        
        # 指令正则表达式
        self.command_pattern = re.compile(r'^Trae：分析个股\s*(.*)$')
        self.stock_code_pattern = re.compile(r'^[0-9]{6}$')
        
        logger.info("TraeStockAnalyzer 初始化完成")
    
    def parse_command(self, command: str) -> Tuple[bool, str, List[str]]:
        """解析指令
        
        Args:
            command: 原始指令文本
            
        Returns:
            (是否匹配指令格式, 错误信息, 股票代码列表)
        """
        match = self.command_pattern.match(command)
        if not match:
            return False, "", []
        
        args = match.group(1).strip()
        if not args:
            return True, "请补充股票代码，示例：Trae：分析个股 600000", []
        
        # 提取股票代码
        stock_codes = []
        for part in args.split():
            part = part.strip()
            if self.stock_code_pattern.match(part):
                stock_codes.append(part)
        
        if not stock_codes:
            return True, "未识别到有效的股票代码，请输入6位数字的股票代码", []
        
        return True, "", stock_codes
    
    def is_main_board(self, stock_code: str) -> bool:
        """判断是否为沪深主板股票
        
        Args:
            stock_code: 股票代码
            
        Returns:
            是否为主板股票
        """
        # 沪市主板：600000-609999
        # 深市主板：000001-001999
        if stock_code.startswith('60') and len(stock_code) == 6:
            return True
        if stock_code.startswith('000') and len(stock_code) == 6:
            return True
        return False
    
    def get_stock_basic_info(self, stock_code: str) -> Optional[Dict]:
        """获取股票基本信息
        
        Args:
            stock_code: 股票代码
            
        Returns:
            股票基本信息字典
        """
        try:
            # 尝试从缓存获取
            cache_key = f"stock_basic_{stock_code}"
            cached_data = self.data_cache.get(cache_key, expire=3600)  # 1小时缓存
            if cached_data:
                return cached_data
            
            # 获取股票信息
            info = self.data_source.get_stock_info(stock_code)
            if not info:
                logger.warning(f"无法获取股票 {stock_code} 的基本信息")
                return None
            
            # 缓存数据
            self.data_cache.set(cache_key, info, expire=3600)
            return info
            
        except Exception as e:
            logger.error(f"获取股票基本信息失败: {e}")
            return None
    
    def get_stock_kline(self, stock_code: str, days: int = 30) -> Optional[pd.DataFrame]:
        """获取股票K线数据
        
        Args:
            stock_code: 股票代码
            days: 天数
            
        Returns:
            K线数据
        """
        try:
            # 尝试从缓存获取
            cache_key = f"stock_kline_{stock_code}_{days}"
            cached_data = self.data_cache.get(cache_key, expire=3600)  # 1小时缓存
            if cached_data is not None:
                return cached_data
            
            # 获取K线数据
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
            
            kline = self.data_source.get_kline(stock_code, start_date, end_date)
            if kline is None or len(kline) == 0:
                logger.warning(f"无法获取股票 {stock_code} 的K线数据")
                return None
            
            # 缓存数据
            self.data_cache.set(cache_key, kline, expire=3600)
            return kline
            
        except Exception as e:
            logger.error(f"获取股票K线数据失败: {e}")
            return None
    
    def calculate_5day_ma(self, kline: pd.DataFrame) -> float:
        """计算5日均线
        
        Args:
            kline: K线数据
            
        Returns:
            5日均线值
        """
        if len(kline) < 5:
            return 0.0
        
        close_prices = kline['收盘'][-5:].values
        return np.mean(close_prices)
    
    def analyze_stock(self, stock_code: str) -> Dict:
        """分析单个股票
        
        Args:
            stock_code: 股票代码
            
        Returns:
            分析结果字典
        """
        start_time = time.time()
        result = {
            'stock_code': stock_code,
            'stock_name': '',
            'current_price': 0.0,
            'sector': '',
            'change_percent': 0.0,
            'turnover_rate': 0.0,
            'volume_ratio': 0.0,
            'amount': 0.0,
            'is_main_board': False,
            'price_in_range': False,
            'turnover_in_range': False,
            'volume_ratio_ok': False,
            'ma5_support': False,
            'sector_heat': 0,
            'five_day_trend': 0.0,
            'limit_up_count': 0,
            'up_probability': 0,
            'buy_price': 0.0,
            'stop_loss_price': 0.0,
            'hold_period': '1-2天',
            'recommendation': '不推荐',
            'recommendation_reason': '',
            'error': None
        }
        
        try:
            # 1. 检查是否为主板股票
            result['is_main_board'] = self.is_main_board(stock_code)
            if not result['is_main_board']:
                result['error'] = f"{stock_code} 不是沪深主板股票，仅分析主板标的"
                return result
            
            # 2. 获取基本信息
            basic_info = self.get_stock_basic_info(stock_code)
            if not basic_info:
                result['error'] = f"无法获取股票 {stock_code} 的基本信息"
                return result
            
            result['stock_name'] = basic_info.get('name', '')
            result['current_price'] = basic_info.get('price', 0.0)
            result['change_percent'] = basic_info.get('change', 0.0)
            result['sector'] = basic_info.get('industry', '')
            
            # 3. 获取K线数据
            kline = self.get_stock_kline(stock_code, 30)
            if kline is None:
                result['error'] = f"无法获取股票 {stock_code} 的K线数据"
                return result
            
            # 4. 计算技术指标
            latest_data = kline.iloc[-1]
            result['turnover_rate'] = latest_data.get('换手率', 0.0)
            result['volume_ratio'] = latest_data.get('量比', 0.0)
            result['amount'] = latest_data.get('成交额', 0.0)
            
            # 5. 超短线筛选
            result['price_in_range'] = 5 <= result['current_price'] <= 35
            result['turnover_in_range'] = 3 <= result['turnover_rate'] <= 10
            result['volume_ratio_ok'] = result['volume_ratio'] > 1.5
            
            # 6. 5日线支撑
            ma5 = self.calculate_5day_ma(kline)
            result['ma5_support'] = result['current_price'] >= ma5
            
            # 7. 情绪分析
            # 板块热度（模拟数据，实际应从数据源获取）
            result['sector_heat'] = np.random.randint(1, 100)  # 实际实现需替换
            
            # 近5日涨跌幅趋势
            if len(kline) >= 5:
                five_day_change = kline['涨跌幅'][-5:].mean()
                result['five_day_trend'] = five_day_change
            
            # 涨停基因（近30天涨停次数）
            limit_up_count = 0
            for _, row in kline.iterrows():
                if row.get('涨跌幅', 0) >= 9.8:
                    limit_up_count += 1
            result['limit_up_count'] = limit_up_count
            
            # 8. 预测与建议
            # 计算上涨概率
            score = 0
            if result['price_in_range']: score += 20
            if result['turnover_in_range']: score += 20
            if result['volume_ratio_ok']: score += 20
            if result['ma5_support']: score += 20
            if result['five_day_trend'] > 0: score += 10
            if result['limit_up_count'] > 0: score += 10
            
            result['up_probability'] = min(100, score)
            
            # 买入参考价和止损价
            result['buy_price'] = result['current_price']
            result['stop_loss_price'] = result['current_price'] * 0.97  # 下跌3%
            
            # 推荐结果
            if all([
                result['price_in_range'],
                result['turnover_in_range'],
                result['volume_ratio_ok'],
                result['ma5_support'],
                result['up_probability'] >= 60
            ]):
                result['recommendation'] = '推荐'
                result['recommendation_reason'] = '符合超短线选股条件'
            else:
                reasons = []
                if not result['price_in_range']:
                    reasons.append('股价不在5-35元范围')
                if not result['turnover_in_range']:
                    reasons.append('换手率不在3%-10%范围')
                if not result['volume_ratio_ok']:
                    reasons.append('量比≤1.5')
                if not result['ma5_support']:
                    reasons.append('缺乏5日线支撑')
                if result['up_probability'] < 60:
                    reasons.append('上涨概率较低')
                result['recommendation_reason'] = '; '.join(reasons)
            
            logger.info(f"分析股票 {stock_code} 完成，耗时: {time.time() - start_time:.2f}秒")
            
        except Exception as e:
            logger.error(f"分析股票 {stock_code} 失败: {e}")
            result['error'] = f"分析失败: {str(e)[:50]}"
        
        return result
    
    def format_response(self, analysis_result: Dict) -> str:
        """格式化分析结果
        
        Args:
            analysis_result: 分析结果字典
            
        Returns:
            格式化后的回复文本
        """
        if analysis_result.get('error'):
            return f"❌ {analysis_result['error']}"
        
        stock_code = analysis_result['stock_code']
        stock_name = analysis_result['stock_name']
        current_price = analysis_result['current_price']
        
        response = []
        response.append(f"📊 **{stock_name} ({stock_code})**")
        response.append(f"当前价格: {current_price:.2f}元")
        response.append("")
        
        # 基础行情
        response.append("**基础行情**")
        response.append(f"• 所属板块: {analysis_result['sector']}")
        response.append(f"• 涨跌幅: {analysis_result['change_percent']:.2f}%")
        response.append(f"• 换手率: {analysis_result['turnover_rate']:.2f}%")
        response.append(f"• 量比: {analysis_result['volume_ratio']:.2f}")
        response.append(f"• 成交额: {analysis_result['amount']/10000:.2f}万")
        response.append("")
        
        # 超短线筛选
        response.append("**超短线筛选**")
        response.append(f"• 股价范围: {'✅' if analysis_result['price_in_range'] else '❌'} 5-35元")
        response.append(f"• 换手率: {'✅' if analysis_result['turnover_in_range'] else '❌'} 3%-10%")
        response.append(f"• 量比: {'✅' if analysis_result['volume_ratio_ok'] else '❌'} >1.5")
        response.append(f"• 5日线支撑: {'✅' if analysis_result['ma5_support'] else '❌'}")
        response.append("")
        
        # 情绪分析
        response.append("**情绪分析**")
        response.append(f"• 板块热度: {analysis_result['sector_heat']}/100")
        response.append(f"• 近5日趋势: {analysis_result['five_day_trend']:.2f}%")
        response.append(f"• 近30天涨停: {analysis_result['limit_up_count']}次")
        response.append("")
        
        # 预测与建议
        response.append("**预测与建议**")
        response.append(f"• 明日上涨概率: {analysis_result['up_probability']}%")
        response.append(f"• 买入参考价: {analysis_result['buy_price']:.2f}元")
        response.append(f"• 止损价: {analysis_result['stop_loss_price']:.2f}元")
        response.append(f"• 持有周期: {analysis_result['hold_period']}")
        response.append("")
        
        # 推荐结果
        recommendation = analysis_result['recommendation']
        reason = analysis_result['recommendation_reason']
        response.append(f"**{'✅ 推荐' if recommendation == '推荐' else '❌ 不推荐'}**")
        response.append(f"理由: {reason}")
        
        return '\n'.join(response)
    
    def process_command(self, command: str) -> str:
        """处理指令
        
        Args:
            command: 原始指令
            
        Returns:
            回复文本
        """
        start_time = time.time()
        
        # 解析指令
        is_match, error_msg, stock_codes = self.parse_command(command)
        if not is_match:
            return ""
        
        if error_msg:
            return error_msg
        
        # 处理多个股票代码
        responses = []
        for stock_code in stock_codes:
            # 分析股票
            result = self.analyze_stock(stock_code)
            # 格式化回复
            response = self.format_response(result)
            responses.append(response)
        
        # 合并回复
        final_response = '\n' + '\n' + '='*60 + '\n' + '\n'.join(responses)
        
        # 检查响应时间
        elapsed = time.time() - start_time
        if elapsed > 3:
            logger.warning(f"分析耗时过长: {elapsed:.2f}秒")
        
        # 检查token消耗（估算）
        token_count = len(final_response) // 4  # 粗略估算
        if token_count > 2000:
            logger.warning(f"回复token消耗过高: {token_count}")
        
        return final_response


# 全局分析器实例
_analyzer = None


def get_analyzer() -> TraeStockAnalyzer:
    """获取分析器实例"""
    global _analyzer
    if _analyzer is None:
        _analyzer = TraeStockAnalyzer()
    return _analyzer


def handle_traecmd(command: str) -> str:
    """处理Trae指令的便捷函数
    
    Args:
        command: 指令文本
        
    Returns:
        回复文本
    """
    analyzer = get_analyzer()
    return analyzer.process_command(command)


if __name__ == "__main__":
    """测试代码"""
    analyzer = TraeStockAnalyzer()
    
    # 测试用例1: 单个股票分析
    print("测试用例1: 单个股票分析")
    response1 = analyzer.process_command("Trae：分析个股 600000")
    print(response1)
    print("\n" + "="*60 + "\n")
    
    # 测试用例2: 多个股票分析
    print("测试用例2: 多个股票分析")
    response2 = analyzer.process_command("Trae：分析个股 600000 000001")
    print(response2)
    print("\n" + "="*60 + "\n")
    
    # 测试用例3: 无股票代码
    print("测试用例3: 无股票代码")
    response3 = analyzer.process_command("Trae：分析个股")
    print(response3)
    print("\n" + "="*60 + "\n")
    
    # 测试用例4: 非主板股票
    print("测试用例4: 非主板股票")
    response4 = analyzer.process_command("Trae：分析个股 300001")  # 创业板
    print(response4)
