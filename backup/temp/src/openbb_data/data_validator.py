# -*- coding: utf-8 -*-
"""
===================================
数据校验模块
===================================

功能：
1. 数据完整性校验
2. 数值合理性校验
3. 异常值检测和处理
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ValidationErrorType(Enum):
    """校验错误类型"""
    MISSING_COLUMN = "missing_column"
    NULL_VALUE = "null_value"
    NEGATIVE_VOLUME = "negative_volume"
    PRICE_LOGIC_ERROR = "price_logic_error"
    EXTREME_CHANGE = "extreme_change"
    DUPLICATE_DATE = "duplicate_date"
    DATE_GAP = "date_gap"


@dataclass
class ValidationError:
    """校验错误"""
    error_type: ValidationErrorType
    message: str
    details: Dict[str, Any]


@dataclass
class ValidationResult:
    """校验结果"""
    is_valid: bool
    errors: List[ValidationError]
    warnings: List[str]
    data_quality_score: float  # 0-100


class DataValidator:
    """
    数据校验器
    
    提供全面的数据质量检查
    """
    
    # 核心字段
    REQUIRED_COLUMNS = ['open', 'high', 'low', 'close', 'volume', 'trade_date']
    
    # A股涨跌停限制
    A_SHARE_LIMIT = 0.10  # 10%
    
    # ST股涨跌停限制
    ST_SHARE_LIMIT = 0.05  # 5%
    
    # 创业板/科创板涨跌停限制
    GEM_LIMIT = 0.20  # 20%
    
    def __init__(self):
        """初始化数据校验器"""
        self.errors: List[ValidationError] = []
        self.warnings: List[str] = []
        logger.info("数据校验器初始化完成")
    
    def validate(
        self,
        df: pd.DataFrame,
        symbol: Optional[str] = None,
        strict_mode: bool = False
    ) -> ValidationResult:
        """
        执行完整数据校验
        
        Args:
            df: 待校验数据
            symbol: 股票代码（用于特定校验）
            strict_mode: 严格模式（任何错误都视为失败）
            
        Returns:
            ValidationResult: 校验结果
        """
        self.errors = []
        self.warnings = []
        
        if df is None or df.empty:
            self.errors.append(ValidationError(
                error_type=ValidationErrorType.NULL_VALUE,
                message="数据为空",
                details={}
            ))
            return ValidationResult(
                is_valid=False,
                errors=self.errors,
                warnings=self.warnings,
                data_quality_score=0.0
            )
        
        # 执行各项校验
        self._check_required_columns(df)
        self._check_null_values(df)
        self._check_volume_validity(df)
        self._check_price_logic(df)
        self._check_price_changes(df, symbol)
        self._check_duplicate_dates(df)
        self._check_date_continuity(df)
        
        # 计算质量分数
        quality_score = self._calculate_quality_score(df)
        
        # 判断是否通过
        is_valid = len(self.errors) == 0 or (not strict_mode and quality_score >= 80)
        
        logger.info(f"数据校验完成: 通过={is_valid}, 质量分数={quality_score:.1f}, 错误={len(self.errors)}, 警告={len(self.warnings)}")
        
        return ValidationResult(
            is_valid=is_valid,
            errors=self.errors,
            warnings=self.warnings,
            data_quality_score=quality_score
        )
    
    def _check_required_columns(self, df: pd.DataFrame):
        """检查必需字段"""
        missing_cols = [col for col in self.REQUIRED_COLUMNS if col not in df.columns]
        if missing_cols:
            self.errors.append(ValidationError(
                error_type=ValidationErrorType.MISSING_COLUMN,
                message=f"缺少必需字段: {missing_cols}",
                details={'missing_columns': missing_cols}
            ))
    
    def _check_null_values(self, df: pd.DataFrame):
        """检查空值"""
        null_counts = df[self.REQUIRED_COLUMNS].isnull().sum()
        total_nulls = null_counts.sum()
        
        if total_nulls > 0:
            null_cols = null_counts[null_counts > 0].to_dict()
            self.errors.append(ValidationError(
                error_type=ValidationErrorType.NULL_VALUE,
                message=f"存在{total_nulls}个空值",
                details={'null_columns': null_cols}
            ))
    
    def _check_volume_validity(self, df: pd.DataFrame):
        """检查成交量有效性"""
        if 'volume' in df.columns:
            negative_volume = (df['volume'] < 0).sum()
            if negative_volume > 0:
                self.errors.append(ValidationError(
                    error_type=ValidationErrorType.NEGATIVE_VOLUME,
                    message=f"存在{negative_volume}条负成交量记录",
                    details={'negative_count': negative_volume}
                ))
            
            zero_volume = (df['volume'] == 0).sum()
            if zero_volume > 0:
                self.warnings.append(f"存在{zero_volume}条零成交量记录（可能是停牌）")
    
    def _check_price_logic(self, df: pd.DataFrame):
        """检查价格逻辑"""
        if all(col in df.columns for col in ['low', 'high', 'close', 'open']):
            # 检查 low <= close <= high
            invalid_close = ~((df['low'] <= df['close']) & (df['close'] <= df['high']))
            if invalid_close.any():
                self.errors.append(ValidationError(
                    error_type=ValidationErrorType.PRICE_LOGIC_ERROR,
                    message=f"存在{invalid_close.sum()}条价格逻辑错误",
                    details={'invalid_count': int(invalid_close.sum())}
                ))
            
            # 检查 low <= open <= high
            invalid_open = ~((df['low'] <= df['open']) & (df['open'] <= df['high']))
            if invalid_open.any():
                self.errors.append(ValidationError(
                    error_type=ValidationErrorType.PRICE_LOGIC_ERROR,
                    message=f"存在{invalid_open.sum()}条开盘价逻辑错误",
                    details={'invalid_count': int(invalid_open.sum())}
                ))
    
    def _check_price_changes(self, df: pd.DataFrame, symbol: Optional[str] = None):
        """检查价格涨跌幅"""
        if 'close' not in df.columns or len(df) < 2:
            return
        
        # 计算涨跌幅
        df_copy = df.copy()
        df_copy['pct_change'] = df_copy['close'].pct_change()
        
        # 根据股票类型确定限制
        limit = self.A_SHARE_LIMIT
        if symbol:
            if 'ST' in symbol.upper():
                limit = self.ST_SHARE_LIMIT
            elif symbol.startswith('3') or symbol.startswith('68'):
                limit = self.GEM_LIMIT
        
        # 检查极端涨跌幅
        extreme_changes = df_copy[df_copy['pct_change'].abs() > limit]
        if not extreme_changes.empty:
            self.errors.append(ValidationError(
                error_type=ValidationErrorType.EXTREME_CHANGE,
                message=f"存在{len(extreme_changes)}条涨跌幅超过{limit:.0%}的记录",
                details={
                    'limit': limit,
                    'extreme_count': len(extreme_changes),
                    'max_change': float(df_copy['pct_change'].abs().max())
                }
            ))
    
    def _check_duplicate_dates(self, df: pd.DataFrame):
        """检查重复日期"""
        if 'trade_date' in df.columns:
            duplicates = df['trade_date'].duplicated().sum()
            if duplicates > 0:
                self.errors.append(ValidationError(
                    error_type=ValidationErrorType.DUPLICATE_DATE,
                    message=f"存在{duplicates}条重复日期记录",
                    details={'duplicate_count': duplicates}
                ))
    
    def _check_date_continuity(self, df: pd.DataFrame):
        """检查日期连续性"""
        if 'trade_date' not in df.columns or len(df) < 2:
            return
        
        # 转换为日期类型
        dates = pd.to_datetime(df['trade_date']).sort_values()
        
        # 计算日期间隔
        date_diff = dates.diff().dt.days
        
        # 检查异常间隔（超过5天，排除周末）
        abnormal_gaps = date_diff[date_diff > 5].count()
        if abnormal_gaps > 0:
            self.warnings.append(f"存在{abnormal_gaps}处超过5天的数据间隔（可能是长假或停牌）")
    
    def _calculate_quality_score(self, df: pd.DataFrame) -> float:
        """
        计算数据质量分数
        
        Args:
            df: 数据DataFrame
            
        Returns:
            float: 质量分数（0-100）
        """
        if df is None or df.empty:
            return 0.0
        
        score = 100.0
        
        # 根据错误数量扣分
        score -= len(self.errors) * 10
        
        # 根据警告数量扣分
        score -= len(self.warnings) * 2
        
        # 确保分数在0-100范围内
        return max(0.0, min(100.0, score))
    
    def fix_common_issues(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        修复常见问题
        
        Args:
            df: 原始数据
            
        Returns:
            pd.DataFrame: 修复后的数据
        """
        df = df.copy()
        
        # 1. 删除重复日期
        if 'trade_date' in df.columns:
            before_count = len(df)
            df = df.drop_duplicates(subset=['trade_date'], keep='first')
            after_count = len(df)
            if before_count != after_count:
                logger.info(f"删除{before_count - after_count}条重复记录")
        
        # 2. 填充空值（使用前向填充）
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in df.columns:
                df[col] = df[col].fillna(method='ffill')
        
        # 3. 确保成交量非负
        if 'volume' in df.columns:
            df['volume'] = df['volume'].clip(lower=0)
        
        # 4. 修复价格逻辑错误
        if all(col in df.columns for col in ['low', 'high', 'close', 'open']):
            # 确保 low <= close <= high
            df['close'] = df[['low', 'close', 'high']].clip(axis=1)
            # 确保 low <= open <= high
            df['open'] = df[['low', 'open', 'high']].clip(axis=1)
        
        logger.info(f"数据修复完成，剩余{len(df)}条记录")
        return df


def validate_stock_data(
    df: pd.DataFrame,
    symbol: Optional[str] = None,
    auto_fix: bool = True
) -> Tuple[bool, pd.DataFrame, ValidationResult]:
    """
    便捷函数：校验股票数据
    
    Args:
        df: 待校验数据
        symbol: 股票代码
        auto_fix: 是否自动修复
        
    Returns:
        Tuple[bool, pd.DataFrame, ValidationResult]: (是否通过, 修复后的数据, 校验结果)
    """
    validator = DataValidator()
    
    # 先校验
    result = validator.validate(df, symbol)
    
    # 自动修复
    if auto_fix and not result.is_valid:
        df = validator.fix_common_issues(df)
        # 重新校验
        result = validator.validate(df, symbol)
    
    return result.is_valid, df, result
