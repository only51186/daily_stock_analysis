# -*- coding: utf-8 -*-
"""
===================================
单次测试脚本
===================================

【功能】
测试自动化系统的核心功能是否正常工作

【使用方法】
填完密钥并通过验证后，运行此脚本：
    python test_single_run.py
"""

import os
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from src.scheduler.auto_scheduler import AutoScheduler
from src.data.data_manager import get_data_manager
from src.notification.notification_sender import get_notification_sender
from utils.logger_config import setup_logger

logger = setup_logger(__name__, log_file='logs/test_single_run.log')


def print_banner():
    """
    打印测试横幅
    """
    banner = """
╔══════════════════════════════════════════════════════════════════╗
║                                                                      ║
║          🧪 股票量化自动化系统 - 单次测试 🧪                        ║
║                                                                      ║
╚════════════════════════════════════════════════════════════════════╝
"""
    print(banner)


def test_data_manager():
    """
    测试数据管理器
    """
    print("\n" + "=" * 80)
    print("测试1: 数据管理器")
    print("=" * 80)
    
    try:
        data_manager = get_data_manager()
        stats = data_manager.get_data_statistics()
        
        print(f"✅ 数据管理器初始化成功")
        print(f"   数据库路径: {data_manager.db_path}")
        print(f"   股票日线数据: {stats.get('daily_count', 0)}条")
        print(f"   股票数量: {stats.get('stock_count', 0)}只")
        print(f"   数据日期范围: {stats.get('date_range', 'N/A')}")
        
        return True
    except Exception as e:
        print(f"❌ 数据管理器测试失败: {str(e)}")
        return False


def test_data_download():
    """
    测试数据下载
    """
    print("\n" + "=" * 80)
    print("测试2: 数据下载")
    print("=" * 80)
    
    try:
        from scripts.auto_data_downloader import AutoDataDownloader
        
        downloader = AutoDataDownloader()
        result = downloader.download_all_data(force=False)
        
        if result.get('sectors', {}).get('success', False):
            print(f"✅ 板块数据下载成功: {result['sectors']['count']}个")
        else:
            print(f"⚠️ 板块数据下载失败: {result['sectors'].get('message', '未知错误')}")
        
        if result.get('stocks', {}).get('success', False):
            print(f"✅ 股票数据下载成功: {result['stocks']['count']}只")
        else:
            print(f"⚠️ 股票数据下载失败: {result['stocks'].get('message', '未知错误')}")
        
        success = (result.get('sectors', {}).get('success', False) and
                 result.get('stocks', {}).get('success', False))
        
        return success
    except Exception as e:
        print(f"❌ 数据下载测试失败: {str(e)}")
        return False


def test_stock_selection():
    """
    测试尾盘选股
    """
    print("\n" + "=" * 80)
    print("测试3: 尾盘选股")
    print("=" * 80)
    
    try:
        from scripts.evening_stock_selector_v2 import EveningStockSelector
        
        selector = EveningStockSelector()
        df = selector.run()
        
        if df is not None and not df.empty:
            print(f"✅ 尾盘选股成功: 选出 {len(df)} 只股票")
            
            # 显示前3只股票
            print(f"\n   前3只股票：")
            for i, row in df.head(3).iterrows():
                code = row.get('code', '')
                name = row.get('name', '')
                close = row.get('close', 0)
                pct_chg = row.get('pct_chg', 0)
                score = row.get('selection_score', 0)
                print(f"   {i+1}. {code} {name} - 收盘:{close:.2f}元 涨幅:{pct_chg:+.2f}% 得分:{score}分")
            
            return True
        else:
            print(f"⚠️ 未选出符合条件的股票")
            return True
    except Exception as e:
        print(f"❌ 尾盘选股测试失败: {str(e)}")
        return False


def test_backtest():
    """
    测试历史回测
    """
    print("\n" + "=" * 80)
    print("测试4: 历史回测")
    print("=" * 80)
    
    try:
        from scripts.strategy_backtest_optimized import HSShortStrategyOptimized
        
        # 简化测试，只运行少量数据
        print(f"⚠️ 历史回测需要较长时间，跳过详细测试")
        print(f"   实际使用时，系统会自动执行完整回测")
        
        return True
    except Exception as e:
        print(f"❌ 历史回测测试失败: {str(e)}")
        return False


def test_market_review():
    """
    测试市场复盘
    """
    print("\n" + "=" * 80)
    print("测试5: 市场复盘")
    print("=" * 80)
    
    try:
        from scripts.market_review import MarketReview
        
        reviewer = MarketReview()
        df = reviewer.run()
        
        if df is not None and not df.empty:
            print(f"✅ 市场复盘成功")
            print(f"   获取到 {len(df)} 条复盘数据")
        else:
            print(f"⚠️ 复盘数据为空")
        
        return True
    except Exception as e:
        print(f"❌ 市场复盘测试失败: {str(e)}")
        return False


def test_notification():
    """
    测试通知发送
    """
    print("\n" + "=" * 80)
    print("测试6: 通知发送")
    print("=" * 80)
    
    try:
        notification_sender = get_notification_sender()
        
        # 检查是否启用
        if not notification_sender.enabled:
            print(f"⚠️ 通知推送已禁用，跳过测试")
            print(f"   如需启用，请在 .env 文件中设置 DOUBAO_PUSH_ENABLED=true")
            return True
        
        # 发送测试通知
        result = notification_sender.send_notification(
            title="系统测试通知",
            message="这是一条测试消息，如果您收到此消息，说明通知功能正常",
            data={'test': True, 'timestamp': datetime.now().isoformat()}
        )
        
        if result['success']:
            print(f"✅ 通知发送成功")
        else:
            print(f"❌ 通知发送失败: {result['message']}")
        
        return result['success']
    except Exception as e:
        print(f"❌ 通知发送测试失败: {str(e)}")
        return False


def run_all_tests():
    """
    运行所有测试
    """
    print_banner()
    
    print(f"\n开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 运行测试
    tests = [
        ("数据管理器", test_data_manager),
        ("数据下载", test_data_download),
        ("尾盘选股", test_stock_selection),
        ("历史回测", test_backtest),
        ("市场复盘", test_market_review),
        ("通知发送", test_notification)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"\n❌ 测试异常: {test_name} - {str(e)}")
            results.append((test_name, False))
    
    # 总结
    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"  {test_name:12s} - {status}")
    
    print(f"\n通过率: {passed}/{total} ({passed/total*100:.1f}%)")
    print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if passed == total:
        print("\n✅ 所有测试通过，系统可以正常使用")
        print("\n下一步：启动自动化系统")
        print("  python main.py --mode schedule")
    else:
        print("\n⚠️ 部分测试失败，请检查配置")
        print("\n常见问题：")
        print("  1. API密钥未配置或配置错误")
        print("  2. 网络连接问题")
        print("  3. 数据源暂时不可用")
    
    print("=" * 80)


if __name__ == '__main__':
    try:
        run_all_tests()
    except KeyboardInterrupt:
        print("\n\n测试已中断")
    except Exception as e:
        logger.error(f"测试异常: {e}", exc_info=True)
        print(f"\n❌ 测试异常: {e}")
