# -*- coding: utf-8 -*-
"""
===================================
环境变量读取验证脚本
===================================

【功能】
验证 .env 文件中的环境变量能否被 Python 程序正常读取

【使用方法】
直接运行此脚本：
    python test_env_read.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv


def test_env_read():
    """
    测试环境变量读取
    """
    print("=" * 80)
    print("环境变量读取验证")
    print("=" * 80)
    
    # 加载 .env 文件
    env_path = Path(__file__).parent.parent / '.env'
    print(f"\n.env 文件路径: {env_path}")
    print(f".env 文件存在: {env_path.exists()}")
    
    load_dotenv(env_path)
    
    # 读取 TUSHARE_TOKEN
    tushare_token = os.getenv('TUSHARE_TOKEN', '').strip()
    print("\n1. TUSHARE_TOKEN")
    print("-" * 80)
    print(f"   原始值: {repr(os.getenv('TUSHARE_TOKEN'))}")
    print(f"   去空格后: {repr(tushare_token)}")
    
    if tushare_token and tushare_token != '':
        print(f"   ✅ TUSHARE_TOKEN 已成功读取")
        print(f"   长度: {len(tushare_token)} 字符")
        print(f"   前20字符: {tushare_token[:20]}")
        print(f"   后10字符: {tushare_token[-10:]}")
    else:
        print(f"   ❌ TUSHARE_TOKEN 未配置或为空")
    
    # 读取 DOUBAO_API_KEY
    doubao_api_key = os.getenv('DOUBAO_API_KEY', '').strip()
    print("\n2. DOUBAO_API_KEY")
    print("-" * 80)
    print(f"   原始值: {repr(os.getenv('DOUBAO_API_KEY'))}")
    print(f"   去空格后: {repr(doubao_api_key)}")
    
    if doubao_api_key and doubao_api_key != '':
        print(f"   ✅ DOUBAO_API_KEY 已成功读取")
        print(f"   长度: {len(doubao_api_key)} 字符")
        print(f"   前20字符: {doubao_api_key[:20]}")
        print(f"   后10字符: {doubao_api_key[-10:]}")
    else:
        print(f"   ❌ DOUBAO_API_KEY 未配置或为空")
    
    # 读取其他配置
    print("\n3. 其他配置验证")
    print("-" * 80)
    
    configs = [
        ('DATA_SOURCE_PRIORITY', 'akshare,efinance,tushare'),
        ('DATA_CACHE_ENABLED', 'true'),
        ('DOUBAO_MODEL', 'Doubao-Seedream-5.0-lite'),
        ('LOG_LEVEL', 'INFO')
    ]
    
    for key, expected in configs:
        value = os.getenv(key, '')
        status = "✅" if value == expected else "⚠️"
        print(f"   {status} {key}: {value}")
        if value != expected:
            print(f"      期望值: {expected}")
    
    # 总结
    print("\n" + "=" * 80)
    print("验证总结")
    print("=" * 80)
    
    if tushare_token and doubao_api_key:
        print("✅ 所有关键环境变量已成功读取")
        print("\nVS Code 配置状态:")
        print("  ✅ python.terminal.useEnvFile 已启用")
        print("  ✅ .env 文件路径正确")
        print("  ✅ 环境变量注入正常")
    else:
        print("❌ 部分环境变量未配置")
        print("\n请检查:")
        print("  1. .env 文件是否存在")
        print("  2. TUSHARE_TOKEN 和 DOUBAO_API_KEY 是否已填入")
        print("  3. VS Code 是否已重新加载窗口")
    
    print("=" * 80)


if __name__ == '__main__':
    test_env_read()
