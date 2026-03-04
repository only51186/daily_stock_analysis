# -*- coding: utf-8 -*-
"""
完整系统测试脚本
按顺序运行所有关键程序进行测试
"""

import sys
import os
import time
import subprocess
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def run_command(command, description):
    """运行命令并返回结果"""
    print(f"\n{'='*60}")
    print(f"🚀 开始执行: {description}")
    print(f"命令: {command}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        
        duration = time.time() - start_time
        
        if result.returncode == 0:
            print(f"✅ {description} 执行成功 (耗时: {duration:.2f}秒)")
            
            # 显示关键输出（最多显示10行）
            output_lines = result.stdout.strip().split('\n')
            if output_lines:
                print("关键输出:")
                for line in output_lines[-10:]:  # 显示最后10行
                    if line.strip():
                        print(f"   {line}")
        else:
            print(f"❌ {description} 执行失败 (耗时: {duration:.2f}秒)")
            print(f"错误信息: {result.stderr}")
        
        return result.returncode == 0, result.stdout, result.stderr
        
    except Exception as e:
        print(f"❌ {description} 执行异常: {e}")
        return False, "", str(e)

def main():
    """主测试函数"""
    print("🎯 开始完整系统测试")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    test_results = {}
    
    # 1. 测试数据下载程序
    test_results['data_download'] = run_command(
        'python scripts/auto_data_downloader.py',
        '数据下载程序测试'
    )
    
    # 2. 测试智能尾盘选股程序
    test_results['smart_selector'] = run_command(
        'python scripts/smart_evening_stock_selector.py',
        '智能尾盘选股程序测试'
    )
    
    # 3. 测试智能数据管理器
    test_results['smart_data_manager'] = run_command(
        'python test_smart_data.py',
        '智能数据管理器测试'
    )
    
    # 4. 测试因子计算程序
    test_results['factor_calculation'] = run_command(
        'python scripts/strategy_backtest.py --test',
        '因子计算和回测程序测试'
    )
    
    # 5. 测试市场复盘程序
    test_results['market_review'] = run_command(
        'python scripts/market_review.py --test',
        '市场复盘程序测试'
    )
    
    # 6. 测试自动化任务链
    test_results['auto_scheduler'] = run_command(
        'python src/scheduler/auto_scheduler.py --test',
        '自动化调度器测试'
    )
    
    # 7. 测试数据完整性
    test_results['data_integrity'] = run_command(
        'python scripts/check_db.py',
        '数据库完整性检查'
    )
    
    # 汇总测试结果
    print(f"\n{'='*80}")
    print("📊 测试结果汇总")
    print(f"{'='*80}")
    
    success_count = 0
    total_count = len(test_results)
    
    for test_name, (success, stdout, stderr) in test_results.items():
        status = "✅ 成功" if success else "❌ 失败"
        print(f"{test_name:20} {status}")
        if success:
            success_count += 1
    
    print(f"\n🎯 测试完成率: {success_count}/{total_count} ({success_count/total_count*100:.1f}%)")
    
    if success_count == total_count:
        print("🎉 所有测试通过！系统运行正常")
    else:
        print(f"⚠️ 有 {total_count - success_count} 个测试失败，需要检查")

if __name__ == "__main__":
    main()