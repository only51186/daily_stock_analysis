# -*- coding: utf-8 -*-
"""
简化系统测试脚本
只测试核心功能，避免复杂依赖
"""

import sys
import os
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_data_download():
    """测试数据下载程序"""
    print("=" * 60)
    print("测试数据下载程序")
    print("=" * 60)
    
    try:
        from scripts.auto_data_downloader import AutoDataDownloader
        downloader = AutoDataDownloader()
        result = downloader.download_all_data(force=False)
        
        print(f"股票数据: {result.get('stocks', {}).get('count', 0)}只")
        print(f"板块数据: {result.get('sectors', {}).get('count', 0)}个")
        
        if result.get('stocks', {}).get('success', False):
            print("数据下载测试: 成功")
            return True
        else:
            print("数据下载测试: 失败")
            return False
            
    except Exception as e:
        print(f"数据下载测试异常: {e}")
        return False

def test_smart_data_manager():
    """测试智能数据管理器"""
    print("\n" + "=" * 60)
    print("测试智能数据管理器")
    print("=" * 60)
    
    try:
        from src.data.smart_data_manager import SmartDataManager
        smart_dm = SmartDataManager()
        
        # 测试时间判断
        should_download = smart_dm._should_download_today_data()
        target_date = smart_dm._get_target_date()
        
        print(f"当前时间判断: {'需要下载当天数据' if should_download else '使用昨天数据'}")
        print(f"目标日期: {target_date}")
        
        # 测试数据获取
        data = smart_dm.get_smart_stock_daily(limit=5)
        print(f"获取数据条数: {len(data)}")
        
        if not data.empty:
            print(f"数据日期: {data['date'].iloc[0]}")
            print("智能数据管理器测试: 成功")
            return True
        else:
            print("智能数据管理器测试: 失败")
            return False
            
    except Exception as e:
        print(f"智能数据管理器测试异常: {e}")
        return False

def test_database_integrity():
    """测试数据库完整性"""
    print("\n" + "=" * 60)
    print("测试数据库完整性")
    print("=" * 60)
    
    try:
        import sqlite3
        from pathlib import Path
        
        project_root = Path(__file__).parent
        db_path = project_root / 'data' / 'stock_data.db'
        
        if not db_path.exists():
            print("数据库文件不存在")
            return False
        
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # 检查表结构
        tables = ['stock_daily', 'factor_data', 'selection_results', 'backtest_results', 'review_data']
        
        for table in tables:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if cursor.fetchone():
                print(f"表 {table}: 存在")
            else:
                print(f"表 {table}: 不存在")
        
        # 检查数据量
        cursor.execute("SELECT COUNT(*) FROM stock_daily")
        stock_count = cursor.fetchone()[0]
        print(f"股票数据条数: {stock_count}")
        
        conn.close()
        
        if stock_count > 0:
            print("数据库完整性测试: 成功")
            return True
        else:
            print("数据库完整性测试: 失败")
            return False
            
    except Exception as e:
        print(f"数据库完整性测试异常: {e}")
        return False

def test_auto_scheduler():
    """测试自动化调度器"""
    print("\n" + "=" * 60)
    print("测试自动化调度器")
    print("=" * 60)
    
    try:
        from src.scheduler.auto_scheduler import AutoScheduler
        scheduler = AutoScheduler()
        
        # 测试数据存在性检查
        data_check = scheduler._check_today_data_exists()
        
        print(f"数据存在性检查: {data_check['message']}")
        print(f"数据存在: {data_check['exists']}")
        print(f"数据有效: {data_check['valid']}")
        
        print("自动化调度器测试: 成功")
        return True
        
    except Exception as e:
        print(f"自动化调度器测试异常: {e}")
        return False

def main():
    """主测试函数"""
    print("开始简化系统测试")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    test_results = {}
    
    # 运行测试
    test_results['data_download'] = test_data_download()
    test_results['smart_data_manager'] = test_smart_data_manager()
    test_results['database_integrity'] = test_database_integrity()
    test_results['auto_scheduler'] = test_auto_scheduler()
    
    # 汇总结果
    print("\n" + "=" * 80)
    print("测试结果汇总")
    print("=" * 80)
    
    success_count = 0
    for test_name, success in test_results.items():
        status = "成功" if success else "失败"
        print(f"{test_name:20} {status}")
        if success:
            success_count += 1
    
    print(f"\n测试完成率: {success_count}/{len(test_results)} ({success_count/len(test_results)*100:.1f}%)")
    
    if success_count == len(test_results):
        print("所有核心功能测试通过！")
    else:
        print(f"有 {len(test_results) - success_count} 个测试失败")

if __name__ == "__main__":
    main()