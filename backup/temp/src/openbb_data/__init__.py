# -*- coding: utf-8 -*-
"""
===================================
OpenBB Data Module
===================================

封装OpenBB统一调用接口，提供多源兜底和数据完整性校验
"""

from .openbb_fetcher import OpenBBFetcher, get_openbb_stock_data
from .data_validator import DataValidator

__all__ = ['OpenBBFetcher', 'get_openbb_stock_data', 'DataValidator']
