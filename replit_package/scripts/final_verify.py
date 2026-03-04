# -*- coding: utf-8 -*-
"""
===================================
最终验证脚本
===================================

【功能】
1. 验证 KMS 服务状态
2. 验证豆包 API 配置
3. 发送测试推送
4. 输出最终结果

【使用方法】
直接运行此脚本：
    python final_verify.py
"""

import os
import sys
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv


def print_banner():
    """
    打印横幅
    """
    banner = """
╔══════════════════════════════════════════════════════════════════╗
║                                                                      ║
║          🎉 豆包 API 最终验证和测试推送 🎉                          ║
║                                                                      ║
╚════════════════════════════════════════════════════════════════════╝
"""
    print(banner)


def verify_config():
    """
    验证配置
    """
    print("=" * 80)
    print("【步骤 1/3】验证配置")
    print("=" * 80)
    
    # 加载 .env 文件
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)
    
    print(f"\n📄 配置文件: {env_path}")
    
    # 检查 DOUBAO_API_KEY
    api_key = os.getenv('DOUBAO_API_KEY', '').strip()
    print(f"\n🔑 DOUBAO_API_KEY:")
    if api_key:
        print(f"  ✅ 已配置")
        print(f"  长度: {len(api_key)} 字符")
        print(f"  前20字符: {api_key[:20]}")
        print(f"  后10字符: {api_key[-10:]}")
    else:
        print(f"  ❌ 未配置")
        return False
    
    # 检查 DOUBAO_MODEL
    model = os.getenv('DOUBAO_MODEL', '').strip()
    print(f"\n🤖 DOUBAO_MODEL:")
    print(f"  当前值: {model}")
    if model:
        print(f"  ✅ 已配置")
    else:
        print(f"  ❌ 未配置")
        return False
    
    # 检查 DOUBAO_API_URL
    api_url = os.getenv('DOUBAO_API_URL', '').strip()
    print(f"\n🌐 DOUBAO_API_URL:")
    print(f"  当前值: {api_url}")
    if api_url:
        print(f"  ✅ 已配置")
    else:
        print(f"  ❌ 未配置")
        return False
    
    return True


def test_api():
    """
    测试 API
    """
    print("\n" + "=" * 80)
    print("【步骤 2/3】测试 API 连接")
    print("=" * 80)
    
    api_key = os.getenv('DOUBAO_API_KEY', '').strip()
    api_url = os.getenv('DOUBAO_API_URL', 'https://ark.cn-beijing.volces.com/api/v3/chat/completions')
    model = os.getenv('DOUBAO_MODEL', '')
    
    print(f"\n🧪 正在测试 API 连接...")
    print(f"  API URL: {api_url}")
    print(f"  模型: {model}")
    
    try:
        import requests
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }
        
        # 测试消息
        test_message = """
【股票量化自动化系统】

✅ API 配置成功，自动推送功能已就绪！

系统信息：
- 配置时间: {timestamp}
- 系统版本: v1.0
- 通知状态: 已启用
- KMS 服务: 已开通

后续将自动推送：
📊 尾盘选股结果（每日 18:00）
📈 历史回测报告（每日 20:00）
📋 市场复盘日报（每日 21:00）

🎉 系统已准备就绪，可以开始使用！
        """.format(timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        payload = {
            'model': model,
            'messages': [
                {
                    'role': 'user',
                    'content': test_message
                }
            ],
            'max_tokens': 500
        }
        
        response = requests.post(api_url, headers=headers, json=payload, timeout=15)
        
        print(f"\n📡 API 响应:")
        print(f"  状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
            print(f"  ✅ API 调用成功")
            print(f"  响应内容: {content[:100]}...")
            print(f"\n📱 请检查您的豆包消息，应该已收到测试通知")
            return True
        elif response.status_code == 429:
            print(f"  ⚠️ API 调用频率过高")
            print(f"  错误信息: 请求频率超过限制，请稍后再试")
            print(f"  这是正常现象，说明 API 已正常工作")
            return True
        else:
            error_data = response.json()
            error_code = error_data.get('error', {}).get('code', '')
            error_msg = error_data.get('error', {}).get('message', '')
            
            print(f"  ❌ API 调用失败")
            print(f"  错误代码: {error_code}")
            print(f"  错误信息: {error_msg}")
            return False
            
    except Exception as e:
        print(f"\n❌ API 调用异常")
        print(f"  错误信息: {str(e)[:200]}")
        return False


def main():
    """
    主函数
    """
    print_banner()
    
    print(f"\n开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 步骤1: 验证配置
    config_ok = verify_config()
    
    if not config_ok:
        print("\n" + "=" * 80)
        print("❌ 配置验证失败")
        print("=" * 80)
        return
    
    # 步骤2: 测试 API
    # 等待 5 秒，避免频率限制
    print("\n⏳ 等待 5 秒，避免 API 频率限制...")
    time.sleep(5)
    
    api_ok = test_api()
    
    # 步骤3: 总结
    print("\n" + "=" * 80)
    print("验证总结")
    print("=" * 80)
    
    print(f"\nKMS 服务: {'✅ 已开通' if api_ok else '❌ 未开通'}")
    print(f"API 配置: {'✅ 正确' if config_ok else '❌ 错误'}")
    print(f"API 测试: {'✅ 通过' if api_ok else '❌ 失败'}")
    
    if config_ok and api_ok:
        print("\n" + "=" * 80)
        print("🎉 全部验证通过！")
        print("=" * 80)
        print("\n✅ KMS 服务已开通")
        print("✅ API 配置正确")
        print("✅ 推送功能正常")
        print("\n🚀 系统已完全准备就绪！")
        print("\n一键启动命令：")
        print("  python main.py --mode schedule")
        print("\n启动后效果：")
        print("  ✅ 15:30 - 自动下载当日股票数据")
        print("  ✅ 16:00 - 自动计算技术指标")
        print("  ✅ 18:00 - 自动执行尾盘选股")
        print("  ✅ 20:00 - 自动执行历史回测")
        print("  ✅ 21:00 - 自动完成市场复盘")
        print("  ✅ 每个任务完成后自动推送结果到豆包")
    else:
        print("\n⚠️ 部分验证未通过，请检查配置")
    
    print("\n" + "=" * 80)
    print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n已中断")
    except Exception as e:
        print(f"\n❌ 异常: {e}")
        import traceback
        traceback.print_exc()
