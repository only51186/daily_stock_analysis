# -*- coding: utf-8 -*-
"""
===================================
优化模块兼容性验证测试
===================================

【测试说明】
1. 验证所有优化后的模块与内置库的兼容性
2. 测试所有库的调用场景
3. 输出验证结果清单

【运行方式】
```bash
python -m pytest tests/test_optimized_modules.py -v
```
"""

import sys
import os
import unittest
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestFactorLibrary(unittest.TestCase):
    """因子库测试"""
    
    @classmethod
    def setUpClass(cls):
        """测试类初始化"""
        logger.info("=" * 60)
        logger.info("开始测试：因子库 (FactorLibrary)")
        logger.info("=" * 60)
    
    def test_01_import_factor_library(self):
        """测试1：导入因子库模块"""
        try:
            from src.core.factor_library import (
                FactorLibrary, FactorType, FactorResult, FactorConfig,
                VolumePriceFactorCalculator, EmotionFactorCalculator,
                RiskFactorCalculator, LiquidityFactorCalculator,
                get_factor_library
            )
            logger.info("✅ 测试1通过：因子库模块导入成功")
            self.assertTrue(True)
        except Exception as e:
            logger.error(f"❌ 测试1失败：{e}")
            self.fail(f"导入失败: {e}")
    
    def test_02_create_factor_library(self):
        """测试2：创建因子库实例"""
        try:
            from src.core.factor_library import FactorLibrary, FactorConfig
            
            config = FactorConfig()
            factor_lib = FactorLibrary(config)
            
            logger.info("✅ 测试2通过：因子库实例创建成功")
            self.assertIsNotNone(factor_lib)
        except Exception as e:
            logger.error(f"❌ 测试2失败：{e}")
            self.fail(f"创建失败: {e}")
    
    def test_03_get_factor_library_singleton(self):
        """测试3：获取因子库单例"""
        try:
            from src.core.factor_library import get_factor_library
            
            factor_lib1 = get_factor_library()
            factor_lib2 = get_factor_library()
            
            self.assertEqual(id(factor_lib1), id(factor_lib2))
            logger.info("✅ 测试3通过：因子库单例模式工作正常")
        except Exception as e:
            logger.error(f"❌ 测试3失败：{e}")
            self.fail(f"单例测试失败: {e}")
    
    def test_04_factor_calculator_initialization(self):
        """测试4：因子计算器初始化"""
        try:
            from src.core.factor_library import (
                FactorConfig, VolumePriceFactorCalculator,
                EmotionFactorCalculator, RiskFactorCalculator, LiquidityFactorCalculator
            )
            
            config = FactorConfig()
            
            vp_calc = VolumePriceFactorCalculator(config)
            em_calc = EmotionFactorCalculator(config)
            ri_calc = RiskFactorCalculator(config)
            li_calc = LiquidityFactorCalculator(config)
            
            self.assertIsNotNone(vp_calc)
            self.assertIsNotNone(em_calc)
            self.assertIsNotNone(ri_calc)
            self.assertIsNotNone(li_calc)
            
            logger.info("✅ 测试4通过：所有因子计算器初始化成功")
        except Exception as e:
            logger.error(f"❌ 测试4失败：{e}")
            self.fail(f"计算器初始化失败: {e}")
    
    def test_05_calculate_factor_with_mock_data(self):
        """测试5：使用模拟数据计算因子"""
        try:
            from src.core.factor_library import (
                FactorLibrary, FactorType, FactorConfig
            )
            
            # 创建模拟数据
            dates = pd.date_range(end=datetime.now(), periods=30, freq='D')
            mock_data = pd.DataFrame({
                '日期': dates,
                '收盘': np.random.uniform(10, 20, 30),
                '开盘': np.random.uniform(10, 20, 30),
                '最高': np.random.uniform(10, 22, 30),
                '最低': np.random.uniform(9, 20, 30),
                '成交量': np.random.uniform(1000000, 5000000, 30),
                '成交额': np.random.uniform(10000000, 50000000, 30),
                '换手率': np.random.uniform(3, 10, 30),
                '涨跌幅': np.random.uniform(-5, 5, 30),
                '量比': np.random.uniform(0.5, 3, 30),
                '流通市值': np.random.uniform(500000000, 5000000000, 30)
            })
            
            config = FactorConfig()
            factor_lib = FactorLibrary(config)
            
            # 测试计算量价因子
            result = factor_lib.calculate_factor('600000', mock_data, FactorType.VOLUME_PRICE)
            
            self.assertIsNotNone(result)
            self.assertEqual(result.stock_code, '600000')
            self.assertEqual(result.factor_type, FactorType.VOLUME_PRICE)
            self.assertTrue(0 <= result.score <= 100)
            
            logger.info(f"✅ 测试5通过：因子计算成功，得分={result.score:.2f}")
        except Exception as e:
            logger.error(f"❌ 测试5失败：{e}")
            self.fail(f"因子计算失败: {e}")
    
    def test_06_calculate_all_factors(self):
        """测试6：计算所有类型因子"""
        try:
            from src.core.factor_library import (
                FactorLibrary, FactorType, FactorConfig
            )
            
            dates = pd.date_range(end=datetime.now(), periods=30, freq='D')
            mock_data = pd.DataFrame({
                '日期': dates,
                '收盘': np.random.uniform(10, 20, 30),
                '开盘': np.random.uniform(10, 20, 30),
                '最高': np.random.uniform(10, 22, 30),
                '最低': np.random.uniform(9, 20, 30),
                '成交量': np.random.uniform(1000000, 5000000, 30),
                '成交额': np.random.uniform(10000000, 50000000, 30),
                '换手率': np.random.uniform(3, 10, 30),
                '涨跌幅': np.random.uniform(-5, 5, 30),
                '量比': np.random.uniform(0.5, 3, 30),
                '流通市值': np.random.uniform(500000000, 5000000000, 30)
            })
            
            config = FactorConfig()
            factor_lib = FactorLibrary(config)
            
            factor_types = [
                FactorType.VOLUME_PRICE,
                FactorType.EMOTION,
                FactorType.RISK,
                FactorType.LIQUIDITY
            ]
            
            results = {}
            for ft in factor_types:
                result = factor_lib.calculate_factor('600000', mock_data, ft)
                results[ft] = result
                self.assertIsNotNone(result)
                self.assertTrue(0 <= result.score <= 100)
            
            logger.info("✅ 测试6通过：所有因子类型计算成功")
        except Exception as e:
            logger.error(f"❌ 测试6失败：{e}")
            self.fail(f"多因子计算失败: {e}")
    
    def test_07_cache_functionality(self):
        """测试7：缓存功能"""
        try:
            from src.core.factor_library import FactorLibrary, FactorConfig
            
            config = FactorConfig(cache_enabled=True, cache_ttl_seconds=3600)
            factor_lib = FactorLibrary(config)
            
            # 获取缓存统计
            stats = factor_lib.get_cache_stats()
            
            self.assertIn('cache_size', stats)
            self.assertIn('cache_enabled', stats)
            self.assertIn('cache_ttl_seconds', stats)
            
            logger.info(f"✅ 测试7通过：缓存功能正常，统计={stats}")
        except Exception as e:
            logger.error(f"❌ 测试7失败：{e}")
            self.fail(f"缓存测试失败: {e}")
    
    def test_08_calculate_composite_score(self):
        """测试8：计算综合得分"""
        try:
            from src.core.factor_library import (
                FactorLibrary, FactorType, FactorResult, FactorConfig
            )
            
            config = FactorConfig()
            factor_lib = FactorLibrary(config)
            
            # 创建模拟因子结果
            factor_results = {
                FactorType.VOLUME_PRICE: FactorResult(
                    stock_code='600000',
                    factor_type=FactorType.VOLUME_PRICE,
                    score=80,
                    raw_value={},
                    normalized_value=0.8
                ),
                FactorType.EMOTION: FactorResult(
                    stock_code='600000',
                    factor_type=FactorType.EMOTION,
                    score=70,
                    raw_value={},
                    normalized_value=0.7
                ),
                FactorType.RISK: FactorResult(
                    stock_code='600000',
                    factor_type=FactorType.RISK,
                    score=90,
                    raw_value={},
                    normalized_value=0.9
                ),
                FactorType.LIQUIDITY: FactorResult(
                    stock_code='600000',
                    factor_type=FactorType.LIQUIDITY,
                    score=75,
                    raw_value={},
                    normalized_value=0.75
                )
            }
            
            weights = {
                FactorType.VOLUME_PRICE: 0.3,
                FactorType.EMOTION: 0.25,
                FactorType.RISK: 0.25,
                FactorType.LIQUIDITY: 0.2
            }
            
            composite_score = factor_lib.calculate_composite_score(factor_results, weights)
            
            expected_score = 80*0.3 + 70*0.25 + 90*0.25 + 75*0.2
            self.assertAlmostEqual(composite_score, expected_score, places=1)
            
            logger.info(f"✅ 测试8通过：综合得分计算正确，得分={composite_score:.2f}")
        except Exception as e:
            logger.error(f"❌ 测试8失败：{e}")
            self.fail(f"综合得分计算失败: {e}")


class TestDataAccessLayer(unittest.TestCase):
    """数据访问层测试"""
    
    @classmethod
    def setUpClass(cls):
        """测试类初始化"""
        logger.info("=" * 60)
        logger.info("开始测试：数据访问层 (DataAccessLayer)")
        logger.info("=" * 60)
    
    def test_01_import_data_access_layer(self):
        """测试1：导入数据访问层模块"""
        try:
            from src.core.data_access_layer import (
                DataAccessLayer, DataType, DataResponse, DataRequest,
                DataCacheConfig, CacheManager, get_data_access_layer
            )
            logger.info("✅ 测试1通过：数据访问层模块导入成功")
            self.assertTrue(True)
        except Exception as e:
            logger.error(f"❌ 测试1失败：{e}")
            self.fail(f"导入失败: {e}")
    
    def test_02_create_data_access_layer(self):
        """测试2：创建数据访问层实例"""
        try:
            from src.core.data_access_layer import DataAccessLayer, DataCacheConfig
            
            cache_config = DataCacheConfig()
            dal = DataAccessLayer(cache_config)
            
            logger.info("✅ 测试2通过：数据访问层实例创建成功")
            self.assertIsNotNone(dal)
        except Exception as e:
            logger.error(f"❌ 测试2失败：{e}")
            self.fail(f"创建失败: {e}")
    
    def test_03_get_data_access_layer_singleton(self):
        """测试3：获取数据访问层单例"""
        try:
            from src.core.data_access_layer import get_data_access_layer
            
            dal1 = get_data_access_layer()
            dal2 = get_data_access_layer()
            
            self.assertEqual(id(dal1), id(dal2))
            logger.info("✅ 测试3通过：数据访问层单例模式工作正常")
        except Exception as e:
            logger.error(f"❌ 测试3失败：{e}")
            self.fail(f"单例测试失败: {e}")
    
    def test_04_cache_manager(self):
        """测试4：缓存管理器"""
        try:
            from src.core.data_access_layer import CacheManager, DataCacheConfig
            
            config = DataCacheConfig()
            cache = CacheManager(config)
            
            # 测试设置缓存
            cache.set('test_key', {'data': 'test'})
            
            # 测试获取缓存
            data = cache.get('test_key')
            self.assertIsNotNone(data)
            self.assertEqual(data['data'], 'test')
            
            # 测试缓存统计
            stats = cache.get_stats()
            self.assertIn('memory_cache_size', stats)
            
            logger.info(f"✅ 测试4通过：缓存管理器工作正常，统计={stats}")
        except Exception as e:
            logger.error(f"❌ 测试4失败：{e}")
            self.fail(f"缓存管理器测试失败: {e}")
    
    def test_05_data_request_cache_key(self):
        """测试5：数据请求缓存键生成"""
        try:
            from src.core.data_access_layer import DataRequest, DataType
            
            request = DataRequest(
                data_type=DataType.STOCK_DAILY,
                stock_code='600000',
                params={'days': 30}
            )
            
            cache_key = request.get_cache_key()
            
            self.assertIsNotNone(cache_key)
            self.assertIsInstance(cache_key, str)
            self.assertEqual(len(cache_key), 32)  # MD5哈希长度
            
            logger.info(f"✅ 测试5通过：缓存键生成正确，key={cache_key[:16]}...")
        except Exception as e:
            logger.error(f"❌ 测试5失败：{e}")
            self.fail(f"缓存键生成失败: {e}")
    
    def test_06_data_response_validation(self):
        """测试6：数据响应验证"""
        try:
            from src.core.data_access_layer import DataResponse, DataType
            
            # 测试空数据
            empty_response = DataResponse(
                data=None,
                data_type=DataType.STOCK_DAILY,
                stock_code='600000'
            )
            self.assertTrue(empty_response.is_empty())
            
            # 测试有效数据
            valid_response = DataResponse(
                data=pd.DataFrame({'col': [1, 2, 3]}),
                data_type=DataType.STOCK_DAILY,
                stock_code='600000'
            )
            self.assertFalse(valid_response.is_empty())
            self.assertTrue(valid_response.validate(['col']))
            
            logger.info("✅ 测试6通过：数据响应验证功能正常")
        except Exception as e:
            logger.error(f"❌ 测试6失败：{e}")
            self.fail(f"数据响应验证失败: {e}")
    
    def test_07_validate_stock_code(self):
        """测试7：股票代码验证"""
        try:
            from src.core.data_access_layer import get_data_access_layer
            
            dal = get_data_access_layer()
            
            # 有效代码
            self.assertTrue(dal.validate_stock_code('600000'))
            self.assertTrue(dal.validate_stock_code('601318'))
            self.assertTrue(dal.validate_stock_code('603000'))
            self.assertTrue(dal.validate_stock_code('000001'))
            
            # 无效代码
            self.assertFalse(dal.validate_stock_code(''))
            self.assertFalse(dal.validate_stock_code('123'))
            self.assertFalse(dal.validate_stock_code('abc'))
            self.assertFalse(dal.validate_stock_code('900001'))
            
            logger.info("✅ 测试7通过：股票代码验证功能正常")
        except Exception as e:
            logger.error(f"❌ 测试7失败：{e}")
            self.fail(f"股票代码验证失败: {e}")
    
    def test_08_filter_main_board_stocks(self):
        """测试8：筛选沪深主板股票"""
        try:
            from src.core.data_access_layer import get_data_access_layer
            
            dal = get_data_access_layer()
            
            # 创建测试数据
            df = pd.DataFrame({
                '股票代码': ['600000', '300001', '601318', '688001', '000001', '900001'],
                '股票名称': ['浦发银行', '特锐德', '中国平安', '某某科创', '平安银行', '其他']
            })
            
            filtered = dal.filter_main_board_stocks(df)
            
            self.assertEqual(len(filtered), 3)  # 600000, 601318, 000001
            self.assertIn('600000', filtered['股票代码'].values)
            self.assertIn('000001', filtered['股票代码'].values)
            self.assertNotIn('300001', filtered['股票代码'].values)  # 创业板
            self.assertNotIn('688001', filtered['股票代码'].values)  # 科创板
            
            logger.info("✅ 测试8通过：沪深主板筛选功能正常")
        except Exception as e:
            logger.error(f"❌ 测试8失败：{e}")
            self.fail(f"主板筛选失败: {e}")


class TestStrategyEngine(unittest.TestCase):
    """策略引擎测试"""
    
    @classmethod
    def setUpClass(cls):
        """测试类初始化"""
        logger.info("=" * 60)
        logger.info("开始测试：策略引擎 (StrategyEngine)")
        logger.info("=" * 60)
    
    def test_01_import_strategy_engine(self):
        """测试1：导入策略引擎模块"""
        try:
            from src.core.strategy_engine import (
                StrategyEngine, StrategyConfig, StrategyType,
                SelectionResult, BacktestResult, TradeRecord,
                SelectionStrategy, BacktestStrategy,
                get_strategy_engine
            )
            logger.info("✅ 测试1通过：策略引擎模块导入成功")
            self.assertTrue(True)
        except Exception as e:
            logger.error(f"❌ 测试1失败：{e}")
            self.fail(f"导入失败: {e}")
    
    def test_02_create_strategy_engine(self):
        """测试2：创建策略引擎实例"""
        try:
            from src.core.strategy_engine import StrategyEngine, StrategyConfig
            
            config = StrategyConfig()
            engine = StrategyEngine(config)
            
            logger.info("✅ 测试2通过：策略引擎实例创建成功")
            self.assertIsNotNone(engine)
        except Exception as e:
            logger.error(f"❌ 测试2失败：{e}")
            self.fail(f"创建失败: {e}")
    
    def test_03_get_strategy_engine_singleton(self):
        """测试3：获取策略引擎单例"""
        try:
            from src.core.strategy_engine import get_strategy_engine
            
            engine1 = get_strategy_engine()
            engine2 = get_strategy_engine()
            
            self.assertEqual(id(engine1), id(engine2))
            logger.info("✅ 测试3通过：策略引擎单例模式工作正常")
        except Exception as e:
            logger.error(f"❌ 测试3失败：{e}")
            self.fail(f"单例测试失败: {e}")
    
    def test_04_strategy_config(self):
        """测试4：策略配置"""
        try:
            from src.core.strategy_engine import StrategyConfig
            from src.core.factor_library import FactorType
            
            config = StrategyConfig(
                price_min=5.0,
                price_max=35.0,
                min_score=70.0,
                max_stocks=20
            )
            
            self.assertEqual(config.price_min, 5.0)
            self.assertEqual(config.price_max, 35.0)
            self.assertEqual(config.min_score, 70.0)
            self.assertEqual(config.max_stocks, 20)
            self.assertIn(FactorType.VOLUME_PRICE, config.factor_weights)
            
            logger.info("✅ 测试4通过：策略配置功能正常")
        except Exception as e:
            logger.error(f"❌ 测试4失败：{e}")
            self.fail(f"策略配置测试失败: {e}")
    
    def test_05_selection_result(self):
        """测试5：选股结果"""
        try:
            from src.core.strategy_engine import SelectionResult
            from src.core.factor_library import FactorType
            
            result = SelectionResult(
                stock_code='600000',
                stock_name='浦发银行',
                current_price=10.5,
                composite_score=85.5,
                factor_scores={
                    FactorType.VOLUME_PRICE: 80,
                    FactorType.EMOTION: 75,
                    FactorType.RISK: 90,
                    FactorType.LIQUIDITY: 85
                },
                rank=1
            )
            
            # 测试转换为字典
            result_dict = result.to_dict()
            
            self.assertEqual(result_dict['stock_code'], '600000')
            self.assertEqual(result_dict['stock_name'], '浦发银行')
            self.assertEqual(result_dict['composite_score'], 85.5)
            self.assertEqual(result_dict['rank'], 1)
            
            logger.info("✅ 测试5通过：选股结果功能正常")
        except Exception as e:
            logger.error(f"❌ 测试5失败：{e}")
            self.fail(f"选股结果测试失败: {e}")
    
    def test_06_backtest_result(self):
        """测试6：回测结果"""
        try:
            from src.core.strategy_engine import BacktestResult, TradeRecord
            from datetime import datetime
            
            # 创建交易记录
            trade = TradeRecord(
                stock_code='600000',
                entry_date=datetime(2024, 1, 1),
                entry_price=10.0,
                shares=1000
            )
            trade.close_trade(datetime(2024, 1, 3), 11.0, 'take_profit')
            
            # 创建回测结果
            result = BacktestResult(
                stock_code='600000',
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 3, 1),
                initial_capital=100000,
                final_capital=105000,
                total_return=5.0,
                total_trades=10,
                winning_trades=6,
                losing_trades=4,
                win_rate=60.0,
                avg_profit=500,
                avg_loss=-200,
                profit_factor=2.5,
                max_drawdown=3.0,
                sharpe_ratio=1.2,
                trades=[trade]
            )
            
            # 测试转换为字典
            result_dict = result.to_dict()
            
            self.assertEqual(result_dict['stock_code'], '600000')
            self.assertEqual(result_dict['total_return'], 5.0)
            self.assertEqual(result_dict['win_rate'], 60.0)
            self.assertEqual(len(result_dict['trades']), 1)
            
            logger.info("✅ 测试6通过：回测结果功能正常")
        except Exception as e:
            logger.error(f"❌ 测试6失败：{e}")
            self.fail(f"回测结果测试失败: {e}")
    
    def test_07_get_strategy_stats(self):
        """测试7：获取策略统计信息"""
        try:
            from src.core.strategy_engine import get_strategy_engine
            
            engine = get_strategy_engine()
            stats = engine.get_strategy_stats()
            
            self.assertIn('config', stats)
            self.assertIn('factor_library_stats', stats)
            self.assertIn('data_layer_stats', stats)
            
            logger.info(f"✅ 测试7通过：策略统计功能正常")
        except Exception as e:
            logger.error(f"❌ 测试7失败：{e}")
            self.fail(f"策略统计测试失败: {e}")


def run_all_tests():
    """运行所有测试"""
    logger.info("\n" + "=" * 80)
    logger.info("开始运行优化模块兼容性验证测试")
    logger.info("=" * 80 + "\n")
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestFactorLibrary))
    suite.addTests(loader.loadTestsFromTestCase(TestDataAccessLayer))
    suite.addTests(loader.loadTestsFromTestCase(TestStrategyEngine))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出测试结果
    logger.info("\n" + "=" * 80)
    logger.info("测试完成")
    logger.info(f"测试总数: {result.testsRun}")
    logger.info(f"通过: {result.testsRun - len(result.failures) - len(result.errors)}")
    logger.info(f"失败: {len(result.failures)}")
    logger.info(f"错误: {len(result.errors)}")
    logger.info("=" * 80 + "\n")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
