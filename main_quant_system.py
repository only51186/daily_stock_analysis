# -*- coding: utf-8 -*-
"""
===================================
A-Share Quantitative Trading System
===================================

[Complete System]
Data Layer → Factor Layer → Strategy Layer → Backtest Layer → Report Layer

[Features]
- Multi-source data with automatic fallback
- Comprehensive technical analysis
- 50+ factors with auto-selection
- 5 ultra-short-term strategies
- Enhanced backtesting system
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.data_layer import get_enhanced_data_manager
from src.market_analysis import get_market_analyzer
from src.factor_layer import get_factor_library
from src.backtest_layer import get_enhanced_backtester
from src.strategies import get_all_strategies, get_strategy_optimizer
from utils.trae_memory import get_memory


class AShareQuantSystem:
    """
    Complete A-Share Quantitative Trading System
    """
    
    def __init__(self):
        self.data_manager = get_enhanced_data_manager()
        self.market_analyzer = get_market_analyzer()
        self.factor_library = get_factor_library()
        self.backtester = get_enhanced_backtester(initial_capital=100000.0)
        self.strategy_optimizer = get_strategy_optimizer()
        self.memory = get_memory()
        
        logger.info("=" * 80)
        logger.info("A-SHARE QUANTITATIVE TRADING SYSTEM")
        logger.info("=" * 80)
    
    def run_complete_analysis(
        self,
        symbol: str = '000001.SZ',
        start_date: str = None,
        end_date: str = None
    ):
        """
        Run complete analysis pipeline
        
        Args:
            symbol: Stock code
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
        """
        logger.info(f"\n[Step 1] Fetching data for {symbol}...")
        
        df, source = self.data_manager.get_stock_data(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date
        )
        
        if df is None or df.empty:
            logger.error("Failed to fetch data from any source")
            return None
        
        logger.info(f"Data fetched from: {source}")
        logger.info(f"Data shape: {df.shape}")
        
        logger.info(f"\n[Step 2] Market analysis...")
        analysis = self.market_analyzer.analyze(df)
        self.market_analyzer.print_analysis(analysis)
        
        logger.info(f"\n[Step 3] Calculating factors...")
        df_with_factors = self.factor_library.calculate_all_factors(df)
        logger.info(f"Calculated {len(df_with_factors.columns) - len(df.columns)} factors")
        
        if 'close' in df_with_factors.columns:
            logger.info(f"\n[Step 4] Evaluating factors...")
            factor_eval = self.factor_library.evaluate_factors(df_with_factors, forward_period=5)
            logger.info(f"Effective factors: {factor_eval.get('effective_factors', [])}")
        
        logger.info(f"\n[Step 5] Testing all strategies...")
        results = self.strategy_optimizer.test_all_strategies(df, initial_capital=100000.0)
        
        self.strategy_optimizer.print_strategy_comparison()
        
        top_strategies = self.strategy_optimizer.get_top_strategies(n=3)
        
        logger.info(f"\n[Step 6] Top 3 Strategies:")
        for i, (name, result) in enumerate(top_strategies, 1):
            logger.info(f"\n{i}. {name}")
            logger.info(f"   Win Rate: {result.win_rate:.2%}")
            logger.info(f"   Total Return: {result.total_return:.2%}")
            logger.info(f"   Sharpe Ratio: {result.sharpe_ratio:.2f}")
            logger.info(f"   Max Drawdown: {result.max_drawdown:.2%}")
        
        logger.info(f"\n[Step 7] Data source health report:")
        self.data_manager.print_health_report()
        
        return {
            'symbol': symbol,
            'data': df,
            'data_with_factors': df_with_factors,
            'market_analysis': analysis,
            'strategy_results': results,
            'top_strategies': top_strategies
        }
    
    def print_system_guide(self):
        """Print system usage guide"""
        print("\n" + "=" * 80)
        print("SYSTEM USAGE GUIDE")
        print("=" * 80)
        
        print("\n[1] QUICK START")
        print("  from main_quant_system import AShareQuantSystem")
        print("  system = AShareQuantSystem()")
        print("  system.run_complete_analysis('000001.SZ')")
        
        print("\n[2] TRADING RULES")
        print("  - Market: Shanghai/Shenzhen Main Board")
        print("  - Style: Ultra-short-term (1-5 days)")
        print("  - Operation: Full position in/out")
        print("  - Goal: High win rate + High return")
        
        print("\n[3] AVAILABLE STRATEGIES")
        strategies = get_all_strategies()
        for i, s in enumerate(strategies, 1):
            print(f"  {i}. {s.name}")
        
        print("\n[4] DATA SOURCES (Priority)")
        print("  1. OpenBB (Primary)")
        print("  2. AkShare (Backup 1)")
        print("  3. Tushare (Backup 2)")
        print("  4. EastMoney (Backup 3)")
        print("  5. TongHuaShun (Backup 4)")
        print("  6. Local Cache (Fallback)")
        
        print("\n" + "=" * 80)


def main():
    """Main function"""
    print("\n" + "=" * 80)
    print("A-SHARE QUANTITATIVE TRADING SYSTEM - MAIN")
    print("=" * 80)
    
    system = AShareQuantSystem()
    system.print_system_guide()
    
    test_symbol = '000001.SZ'
    print(f"\nTesting system with {test_symbol}...")
    
    try:
        results = system.run_complete_analysis(
            symbol=test_symbol,
            start_date=(datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d'),
            end_date=datetime.now().strftime('%Y-%m-%d')
        )
        
        if results:
            print("\n✅ System test completed successfully!")
        else:
            print("\n⚠️ System test completed with issues")
            
    except Exception as e:
        logger.error(f"System test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
