# -*- coding: utf-8 -*-
"""
===================================
统一策略执行引擎 (Strategy Engine)
===================================

【优化说明】
1. 统一策略执行流程，提供标准化接口
2. 集成因子库和数据访问层
3. 完善的回测逻辑和绩效分析
4. 支持多策略并行执行
5. 完善的异常处理和容错机制

【调用方式】
```python
from src.core.strategy_engine import StrategyEngine, StrategyConfig

# 创建策略引擎
engine = StrategyEngine()

# 运行选股策略
results = engine.run_selection_strategy(
    stock_codes=['600000', '000001'],
    min_score=70
)

# 运行回测
backtest_results = engine.run_backtest(
    stock_code='600000',
    start_date='2024-01-01',
    end_date='2024-03-01'
)
```
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Dict, List, Any, Optional, Union, Tuple, Callable
from pathlib import Path

import pandas as pd
import numpy as np
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import get_config
from src.core.factor_library import (
    FactorLibrary, FactorType, FactorResult, FactorConfig, get_factor_library
)
from src.core.data_access_layer import (
    DataAccessLayer, DataType, DataResponse, get_data_access_layer
)

logger = logging.getLogger(__name__)


class StrategyType(Enum):
    """策略类型枚举"""
    SELECTION = auto()         # 选股策略
    BACKTEST = auto()          # 回测策略
    OPTIMIZATION = auto()      # 优化策略
    REVIEW = auto()            # 复盘策略


class StrategyError(Exception):
    """策略异常基类"""
    pass


class StrategyExecutionError(StrategyError):
    """策略执行异常"""
    pass


class StrategyValidationError(StrategyError):
    """策略验证异常"""
    pass


@dataclass
class StrategyConfig:
    """策略配置"""
    # 选股参数
    price_min: float = 5.0
    price_max: float = 35.0
    min_score: float = 70.0
    max_stocks: int = 20
    
    # 因子权重
    factor_weights: Dict[FactorType, float] = field(default_factory=lambda: {
        FactorType.VOLUME_PRICE: 0.3,
        FactorType.EMOTION: 0.25,
        FactorType.RISK: 0.25,
        FactorType.LIQUIDITY: 0.2
    })
    
    # 回测参数
    initial_capital: float = 100000.0
    position_size: float = 0.2           # 单笔仓位20%
    stop_loss_pct: float = -3.0          # 止损-3%
    take_profit_pct: float = 5.0         # 止盈5%
    hold_days: int = 2                   # 持有天数
    
    # 执行参数
    max_workers: int = 5
    use_cache: bool = True


@dataclass
class SelectionResult:
    """选股结果"""
    stock_code: str
    stock_name: str
    current_price: float
    composite_score: float
    factor_scores: Dict[FactorType, float]
    rank: int
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'stock_code': self.stock_code,
            'stock_name': self.stock_name,
            'current_price': self.current_price,
            'composite_score': self.composite_score,
            'factor_scores': {k.name: v for k, v in self.factor_scores.items()},
            'rank': self.rank,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata
        }


@dataclass
class TradeRecord:
    """交易记录"""
    stock_code: str
    entry_date: datetime
    entry_price: float
    exit_date: Optional[datetime] = None
    exit_price: Optional[float] = None
    shares: int = 0
    pnl: float = 0.0
    pnl_pct: float = 0.0
    exit_reason: str = ""  # 'stop_loss', 'take_profit', 'hold_days', 'manual'
    
    def close_trade(self, exit_date: datetime, exit_price: float, reason: str):
        """平仓"""
        self.exit_date = exit_date
        self.exit_price = exit_price
        self.pnl = (exit_price - self.entry_price) * self.shares
        self.pnl_pct = (exit_price - self.entry_price) / self.entry_price * 100
        self.exit_reason = reason


@dataclass
class BacktestResult:
    """回测结果"""
    stock_code: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_capital: float
    total_return: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_profit: float
    avg_loss: float
    profit_factor: float
    max_drawdown: float
    sharpe_ratio: float
    trades: List[TradeRecord] = field(default_factory=list)
    daily_returns: List[float] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'stock_code': self.stock_code,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'initial_capital': self.initial_capital,
            'final_capital': self.final_capital,
            'total_return': self.total_return,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': self.win_rate,
            'avg_profit': self.avg_profit,
            'avg_loss': self.avg_loss,
            'profit_factor': self.profit_factor,
            'max_drawdown': self.max_drawdown,
            'sharpe_ratio': self.sharpe_ratio,
            'trades': [
                {
                    'stock_code': t.stock_code,
                    'entry_date': t.entry_date.isoformat(),
                    'entry_price': t.entry_price,
                    'exit_date': t.exit_date.isoformat() if t.exit_date else None,
                    'exit_price': t.exit_price,
                    'pnl': t.pnl,
                    'pnl_pct': t.pnl_pct,
                    'exit_reason': t.exit_reason
                }
                for t in self.trades
            ]
        }


class BaseStrategy(ABC):
    """策略基类"""
    
    def __init__(self, config: StrategyConfig):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """执行策略"""
        pass
    
    def validate_inputs(self, **kwargs) -> bool:
        """验证输入参数"""
        return True


class SelectionStrategy(BaseStrategy):
    """选股策略"""
    
    def __init__(self, config: StrategyConfig, 
                 factor_lib: Optional[FactorLibrary] = None,
                 data_layer: Optional[DataAccessLayer] = None):
        super().__init__(config)
        self.factor_lib = factor_lib or get_factor_library()
        self.data_layer = data_layer or get_data_access_layer()
    
    def execute(self, stock_codes: List[str], **kwargs) -> List[SelectionResult]:
        """
        执行选股策略
        
        Args:
            stock_codes: 股票代码列表
            **kwargs: 其他参数
            
        Returns:
            List[SelectionResult]: 选股结果列表
        """
        self.logger.info(f"开始选股，共 {len(stock_codes)} 只股票")
        
        results = []
        
        for stock_code in stock_codes:
            try:
                result = self._analyze_stock(stock_code)
                if result and result.composite_score >= self.config.min_score:
                    results.append(result)
            except Exception as e:
                self.logger.error(f"分析股票 {stock_code} 失败: {e}")
                continue
        
        # 排序
        results.sort(key=lambda x: x.composite_score, reverse=True)
        
        # 限制数量
        if len(results) > self.config.max_stocks:
            results = results[:self.config.max_stocks]
        
        # 更新排名
        for i, result in enumerate(results):
            result.rank = i + 1
        
        self.logger.info(f"选股完成，选出 {len(results)} 只股票")
        return results
    
    def _analyze_stock(self, stock_code: str) -> Optional[SelectionResult]:
        """分析单只股票"""
        # 获取数据
        response = self.data_layer.get_data(
            DataType.STOCK_DAILY,
            stock_code=stock_code,
            days=30
        )
        
        if response.is_empty():
            return None
        
        data = response.data
        
        # 价格过滤
        latest_price = data['收盘'].iloc[-1] if '收盘' in data.columns else 0
        if not (self.config.price_min <= latest_price <= self.config.price_max):
            return None
        
        # 计算因子
        factor_types = list(self.config.factor_weights.keys())
        factor_results = {}
        
        for factor_type in factor_types:
            try:
                result = self.factor_lib.calculate_factor(
                    stock_code, data, factor_type
                )
                factor_results[factor_type] = result
            except Exception as e:
                self.logger.warning(f"计算 {factor_type.name} 因子失败: {e}")
                continue
        
        # 计算综合得分
        composite_score = self.factor_lib.calculate_composite_score(
            factor_results, self.config.factor_weights
        )
        
        # 获取股票名称
        stock_name = data.get('股票名称', [''])[-1] if '股票名称' in data.columns else stock_code
        
        return SelectionResult(
            stock_code=stock_code,
            stock_name=stock_name,
            current_price=latest_price,
            composite_score=composite_score,
            factor_scores={ft: fr.score for ft, fr in factor_results.items()},
            rank=0,
            metadata={
                'factor_details': {ft.name: fr.metadata for ft, fr in factor_results.items()}
            }
        )


class BacktestStrategy(BaseStrategy):
    """回测策略"""
    
    def __init__(self, config: StrategyConfig,
                 data_layer: Optional[DataAccessLayer] = None):
        super().__init__(config)
        self.data_layer = data_layer or get_data_access_layer()
    
    def execute(self, stock_code: str, start_date: str, end_date: str, **kwargs) -> BacktestResult:
        """
        执行回测
        
        Args:
            stock_code: 股票代码
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            **kwargs: 其他参数
            
        Returns:
            BacktestResult: 回测结果
        """
        self.logger.info(f"开始回测 {stock_code} ({start_date} ~ {end_date})")
        
        # 获取数据
        response = self.data_layer.get_data(
            DataType.STOCK_DAILY,
            stock_code=stock_code,
            days=252  # 一年数据
        )
        
        if response.is_empty():
            raise StrategyExecutionError(f"无法获取 {stock_code} 的数据")
        
        data = response.data
        
        # 过滤日期范围
        data['日期'] = pd.to_datetime(data['日期'])
        mask = (data['日期'] >= start_date) & (data['日期'] <= end_date)
        data = data[mask].copy()
        
        if len(data) < 10:
            raise StrategyExecutionError("数据不足，无法回测")
        
        # 执行回测
        trades = self._simulate_trades(stock_code, data)
        
        # 计算绩效指标
        result = self._calculate_metrics(stock_code, start_date, end_date, trades)
        
        self.logger.info(f"回测完成，共 {len(trades)} 笔交易")
        return result
    
    def _simulate_trades(self, stock_code: str, data: pd.DataFrame) -> List[TradeRecord]:
        """模拟交易"""
        trades = []
        current_position = None
        
        for i in range(len(data) - 1):
            current_bar = data.iloc[i]
            next_bar = data.iloc[i + 1]
            
            date = current_bar['日期']
            price = current_bar['收盘']
            
            # 简单的买入信号：价格突破5日均线
            if current_position is None:
                ma5 = data['收盘'].iloc[max(0, i-4):i+1].mean()
                if price > ma5:
                    # 买入
                    shares = int(self.config.initial_capital * self.config.position_size / price)
                    if shares > 0:
                        current_position = TradeRecord(
                            stock_code=stock_code,
                            entry_date=date,
                            entry_price=price,
                            shares=shares
                        )
            
            else:
                # 检查止损
                loss_pct = (price - current_position.entry_price) / current_position.entry_price * 100
                if loss_pct <= self.config.stop_loss_pct:
                    current_position.close_trade(date, price, 'stop_loss')
                    trades.append(current_position)
                    current_position = None
                    continue
                
                # 检查止盈
                if loss_pct >= self.config.take_profit_pct:
                    current_position.close_trade(date, price, 'take_profit')
                    trades.append(current_position)
                    current_position = None
                    continue
                
                # 检查持有天数
                days_held = (date - current_position.entry_date).days
                if days_held >= self.config.hold_days:
                    current_position.close_trade(date, price, 'hold_days')
                    trades.append(current_position)
                    current_position = None
                    continue
        
        # 平仓剩余持仓
        if current_position is not None:
            last_bar = data.iloc[-1]
            current_position.close_trade(
                last_bar['日期'], 
                last_bar['收盘'], 
                'end_of_period'
            )
            trades.append(current_position)
        
        return trades
    
    def _calculate_metrics(self, stock_code: str, start_date: str, end_date: str, 
                          trades: List[TradeRecord]) -> BacktestResult:
        """计算绩效指标"""
        if not trades:
            return BacktestResult(
                stock_code=stock_code,
                start_date=datetime.strptime(start_date, '%Y-%m-%d'),
                end_date=datetime.strptime(end_date, '%Y-%m-%d'),
                initial_capital=self.config.initial_capital,
                final_capital=self.config.initial_capital,
                total_return=0.0,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0.0,
                avg_profit=0.0,
                avg_loss=0.0,
                profit_factor=0.0,
                max_drawdown=0.0,
                sharpe_ratio=0.0,
                trades=[]
            )
        
        # 基础统计
        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if t.pnl > 0)
        losing_trades = total_trades - winning_trades
        win_rate = winning_trades / total_trades * 100 if total_trades > 0 else 0
        
        # 盈亏统计
        profits = [t.pnl for t in trades if t.pnl > 0]
        losses = [t.pnl for t in trades if t.pnl < 0]
        
        avg_profit = np.mean(profits) if profits else 0
        avg_loss = np.mean(losses) if losses else 0
        
        total_profit = sum(profits)
        total_loss = abs(sum(losses))
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        
        # 计算最终资金
        total_pnl = sum(t.pnl for t in trades)
        final_capital = self.config.initial_capital + total_pnl
        total_return = total_pnl / self.config.initial_capital * 100
        
        # 计算最大回撤（简化版）
        cumulative = [self.config.initial_capital]
        for trade in trades:
            cumulative.append(cumulative[-1] + trade.pnl)
        
        max_drawdown = 0
        peak = cumulative[0]
        for value in cumulative:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak * 100
            max_drawdown = max(max_drawdown, drawdown)
        
        # 计算夏普比率（简化版，假设无风险利率为0）
        returns = [t.pnl_pct for t in trades]
        sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252) if len(returns) > 1 and np.std(returns) > 0 else 0
        
        return BacktestResult(
            stock_code=stock_code,
            start_date=datetime.strptime(start_date, '%Y-%m-%d'),
            end_date=datetime.strptime(end_date, '%Y-%m-%d'),
            initial_capital=self.config.initial_capital,
            final_capital=final_capital,
            total_return=total_return,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            avg_profit=avg_profit,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            trades=trades,
            daily_returns=returns
        )


class StrategyEngine:
    """
    统一策略执行引擎
    
    【优化说明】
    1. 统一策略执行入口
    2. 集成因子库和数据访问层
    3. 完善的异常处理
    4. 支持多策略并行执行
    """
    
    def __init__(self, config: Optional[StrategyConfig] = None):
        """
        初始化策略引擎
        
        Args:
            config: 策略配置
        """
        self.config = config or StrategyConfig()
        self.factor_lib = get_factor_library()
        self.data_layer = get_data_access_layer()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 初始化策略
        self._strategies: Dict[StrategyType, BaseStrategy] = {
            StrategyType.SELECTION: SelectionStrategy(self.config, self.factor_lib, self.data_layer),
            StrategyType.BACKTEST: BacktestStrategy(self.config, self.data_layer),
        }
        
        self.logger.info("策略引擎初始化完成")
    
    def run_selection_strategy(self, stock_codes: List[str], **kwargs) -> List[SelectionResult]:
        """
        运行选股策略
        
        Args:
            stock_codes: 股票代码列表
            **kwargs: 其他参数
            
        Returns:
            List[SelectionResult]: 选股结果
        """
        strategy = self._strategies[StrategyType.SELECTION]
        return strategy.execute(stock_codes, **kwargs)
    
    def run_backtest(self, stock_code: str, start_date: str, end_date: str, **kwargs) -> BacktestResult:
        """
        运行回测
        
        Args:
            stock_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            **kwargs: 其他参数
            
        Returns:
            BacktestResult: 回测结果
        """
        strategy = self._strategies[StrategyType.BACKTEST]
        return strategy.execute(stock_code, start_date, end_date, **kwargs)
    
    def run_batch_backtest(self, stock_codes: List[str], start_date: str, end_date: str,
                          **kwargs) -> Dict[str, BacktestResult]:
        """
        批量回测
        
        Args:
            stock_codes: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            **kwargs: 其他参数
            
        Returns:
            Dict[str, BacktestResult]: 回测结果字典
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        results = {}
        
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            future_to_code = {
                executor.submit(self.run_backtest, code, start_date, end_date, **kwargs): code
                for code in stock_codes
            }
            
            for future in as_completed(future_to_code):
                code = future_to_code[future]
                try:
                    result = future.result()
                    results[code] = result
                except Exception as e:
                    self.logger.error(f"回测 {code} 失败: {e}")
                    continue
        
        return results
    
    def get_strategy_stats(self) -> Dict[str, Any]:
        """获取策略统计信息"""
        return {
            'config': {
                'price_range': [self.config.price_min, self.config.price_max],
                'min_score': self.config.min_score,
                'max_stocks': self.config.max_stocks,
                'factor_weights': {k.name: v for k, v in self.config.factor_weights.items()},
                'stop_loss': self.config.stop_loss_pct,
                'take_profit': self.config.take_profit_pct,
                'hold_days': self.config.hold_days
            },
            'factor_library_stats': self.factor_lib.get_cache_stats(),
            'data_layer_stats': self.data_layer.get_cache_stats()
        }


# 单例模式
_strategy_engine_instance: Optional[StrategyEngine] = None


def get_strategy_engine(config: Optional[StrategyConfig] = None) -> StrategyEngine:
    """
    获取策略引擎实例（单例）
    
    Args:
        config: 策略配置
        
    Returns:
        StrategyEngine: 策略引擎实例
    """
    global _strategy_engine_instance
    
    if _strategy_engine_instance is None:
        _strategy_engine_instance = StrategyEngine(config)
    
    return _strategy_engine_instance


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    engine = get_strategy_engine()
    
    # 测试获取统计信息
    print("策略统计:", engine.get_strategy_stats())
    
    print("策略引擎测试完成")
