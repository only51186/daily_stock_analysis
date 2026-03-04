# -*- coding: utf-8 -*-
"""
===================================
豆包 API 直接测试脚本
===================================

【功能】
直接测试豆包 API 调用，验证 KMS 服务是否已开通

【使用方法】
直接运行此脚本：
    python test_doubao_api.py
"""

import os
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv


def test_api():
    """
    测试豆包 API
    """
    print("=" * 80)
    print("豆包 API 直接测试")
    print("=" * 80)
    
    # 加载 .env 文件
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)
    
    api_key = os.getenv('DOUBAO_API_KEY', '').strip()
    api_url = os.getenv('DOUBAO_API_URL', 'https://ark.cn-beijing.volces.com/api/v3/chat/completions')
    model = os.getenv('DOUBAO_MODEL', 'doubao-lite-4k')
    
    print(f"\n配置信息:")
    print(f"  API Key: {api_key[:20]}...{api_key[-10:]}")
    print(f"  API URL: {api_url}")
    print(f"  Model: {model}")
    
    print(f"\n正在测试 API 调用...")
    
    try:
        import requests
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }
        
        payload = {
            'model': model,
            'messages': [
                {
                    'role': 'user',
                    'content': '测试连接，请回复"KMS服务已开通，API调用成功"'
                }
            ],
            'max_tokens': 50
        }
        
        response = requests.post(api_url, headers=headers, json=payload, timeout=15)
        
        print(f"\n响应状态: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
            print(f"✅ API 调用成功！")
            print(f"响应内容: {content}")
            return True
        else:
            error_data = response.json()
            error_code = error_data.get('error', {}).get('code', '')
            error_msg = error_data.get('error', {}).get('message', '')
            
            print(f"❌ API 调用失败")
            print(f"错误代码: {error_code}")
            print(f"错误信息: {error_msg}")
            
            if 'KMS' in error_msg or 'kms' in error_msg:
                print(f"\n⚠️ KMS 服务可能尚未完全生效，请等待 2-3 分钟后重试")
            
            return False
            
    except Exception as e:
        print(f"❌ 异常: {str(e)}")
        return False


if __name__ == '__main__':
    success = test_api()
    
    if success:
        print("\n" + "=" * 80)
        print("🎉 KMS 服务已开通，API 调用成功！")
        print("=" * 80)
        print("\n系统已完全准备就绪！")
        print("\n一键启动命令：")
        print("  python main.py --mode schedule")
    else:
        print("\n" + "=" * 80)
        print("❌ API 调用失败")
        print("=" * 80)
        print("\n请检查：")
        print("  1. KMS 服务是否已完全开通（可能需要等待 2-3 分钟）")
        print("  2. API Key 是否正确")
        print("  3. 模型 ID 是否正确")
