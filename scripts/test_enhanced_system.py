# -*- coding: utf-8 -*-
"""
===================================
Test the Enhanced Quant System
===================================

[Tests]
1. Data manager test
2. Market analysis test
3. Factor library test
4. Backtester test
5. Strategies test
"""

import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_data_manager():
    """Test data manager"""
    print("\n" + "=" * 60)
    print("TEST 1: DATA MANAGER")
    print("=" * 60)
    
    try:
        from src.data_layer import get_enhanced_data_manager
        manager = get_enhanced_data_manager()
        
        df, source = manager.get_stock_data('000001.SZ')
        
        if df is not None and not df.empty:
            print(f"✅ Data fetched successfully from: {source}")
            print(f"✅ Data shape: {df.shape}")
            print(f"✅ Columns: {list(df.columns)}")
            manager.print_health_report()
            return True
        else:
            print("❌ Failed to fetch data")
            return False
    except Exception as e:
        print(f"❌ Data manager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_market_analyzer():
    """Test market analyzer"""
    print("\n" + "=" * 60)
    print("TEST 2: MARKET ANALYZER")
    print("=" * 60)
    
    try:
        from src.data_layer import get_enhanced_data_manager
        from src.market_analysis import get_market_analyzer
        
        manager = get_enhanced_data_manager()
        df, _ = manager.get_stock_data('000001.SZ')
        
        if df is None or df.empty:
            print("⚠️ Skipping: No data available")
            return False
        
        analyzer = get_market_analyzer()
        analysis = analyzer.analyze(df)
        
        if 'error' not in analysis:
            print("✅ Market analysis completed")
            print(f"✅ Sentiment: {analysis['sentiment']}")
            print(f"✅ Trend: {analysis['trend']['direction']}")
            print(f"✅ Signals: {analysis['signals']}")
            return True
        else:
            print(f"❌ Analysis error: {analysis['error']}")
            return False
    except Exception as e:
        print(f"❌ Market analyzer test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_factor_library():
    """Test factor library"""
    print("\n" + "=" * 60)
    print("TEST 3: FACTOR LIBRARY")
    print("=" * 60)
    
    try:
        from src.data_layer import get_enhanced_data_manager
        from src.factor_layer import get_factor_library
        
        manager = get_enhanced_data_manager()
        df, _ = manager.get_stock_data('000001.SZ')
        
        if df is None or df.empty:
            print("⚠️ Skipping: No data available")
            return False
        
        library = get_factor_library()
        df_with_factors = library.calculate_all_factors(df)
        
        factor_count = len(df_with_factors.columns) - len(df.columns)
        print(f"✅ Factor library loaded")
        print(f"✅ Calculated {factor_count} factors")
        
        if factor_count > 0:
            print(f"✅ Sample factors: {list(df_with_factors.columns)[-5:]}")
            return True
        else:
            print("⚠️ No factors calculated")
            return False
    except Exception as e:
        print(f"❌ Factor library test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_strategies():
    """Test strategies"""
    print("\n" + "=" * 60)
    print("TEST 4: STRATEGIES")
    print("=" * 60)
    
    try:
        from src.strategies import get_all_strategies
        
        strategies = get_all_strategies()
        
        print(f"✅ {len(strategies)} strategies loaded")
        for i, strategy in enumerate(strategies, 1):
            print(f"  {i}. {strategy.name}")
        
        return len(strategies) == 5
    except Exception as e:
        print(f"❌ Strategies test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_backtester():
    """Test backtester"""
    print("\n" + "=" * 60)
    print("TEST 5: BACKTESTER")
    print("=" * 60)
    
    try:
        from src.data_layer import get_enhanced_data_manager
        from src.backtest_layer import get_enhanced_backtester
        from src.strategies import VolumeBreakoutStrategy
        
        manager = get_enhanced_data_manager()
        df, _ = manager.get_stock_data('000001.SZ')
        
        if df is None or len(df) < 60:
            print("⚠️ Skipping: Insufficient data")
            return False
        
        backtester = get_enhanced_backtester(initial_capital=100000.0)
        strategy = VolumeBreakoutStrategy()
        
        print("✅ Running backtest...")
        result = backtester.run(df, strategy)
        
        print(f"✅ Backtest completed")
        print(f"✅ Total trades: {result.total_trades}")
        print(f"✅ Win rate: {result.win_rate:.2%}")
        print(f"✅ Total return: {result.total_return:.2%}")
        
        return True
    except Exception as e:
        print(f"❌ Backtester test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("ENHANCED QUANT SYSTEM - COMPLETE TEST SUITE")
    print("=" * 80)
    
    results = {}
    
    results['data_manager'] = test_data_manager()
    results['market_analyzer'] = test_market_analyzer()
    results['factor_library'] = test_factor_library()
    results['strategies'] = test_strategies()
    results['backtester'] = test_backtester()
    
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    for name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  {name:<20} {status}")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    print(f"\nTotal: {passed}/{total} tests passed")
    print("=" * 80)
    
    return passed == total


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
