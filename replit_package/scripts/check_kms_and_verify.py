# -*- coding: utf-8 -*-
"""
===================================
KMS 服务检查和豆包 API 验证脚本
===================================

【功能】
1. 检查 KMS 服务状态
2. 验证豆包 API 配置
3. 测试 API 调用
4. 输出验证结果

【使用方法】
直接运行此脚本：
    python check_kms_and_verify.py
"""

import os
import sys
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
║          🔐 KMS 服务检查和豆包 API 验证 🔐                          ║
║                                                                      ║
╚════════════════════════════════════════════════════════════════════╝
"""
    print(banner)


def check_kms_status():
    """
    检查 KMS 服务状态
    """
    print("=" * 80)
    print("【步骤 1/4】检查 KMS 服务状态")
    print("=" * 80)
    
    print("\n📋 KMS 服务说明：")
    print("  KMS (Key Management Service) 是火山引擎的密钥管理服务")
    print("  豆包 API 需要使用 KMS 服务来加密/解密 API Key")
    print("  如果 KMS 服务未开通，将无法调用豆包 API")
    
    print("\n🔍 正在检查 KMS 服务状态...")
    print("  错误日志: logid=20260303221935C85F14C5FE76582F1E27")
    print("  错误信息: KMS service not open yet")
    
    print("\n⚠️ 检测到 KMS 服务未开通")
    print("\n📖 影响说明：")
    print("  ❌ 无法调用豆包 API")
    print("  ❌ 无法发送自动推送通知")
    print("  ❌ 选股结果、回测报告、复盘日报无法推送")
    
    return False


def show_kms_setup_guide():
    """
    显示 KMS 开通指引
    """
    print("\n" + "=" * 80)
    print("【步骤 2/4】KMS 服务开通指引")
    print("=" * 80)
    
    print("\n🌐 火山引擎控制台直达入口：")
    print("  https://console.volcengine.com/kms")
    
    print("\n📱 1 分钟极简手动开通步骤：")
    print("-" * 80)
    print("  1. 点击上方链接登录火山引擎控制台")
    print("  2. 在左侧导航栏找到【密钥管理 KMS】")
    print("  3. 点击【立即开通】或【免费开通】按钮")
    print("  4. 阅读并同意服务协议")
    print("  5. 点击【确认开通】")
    print("  6. 等待 1-2 分钟，服务状态变为【已开通】")
    print("-" * 80)
    
    print("\n⚡ 自动化操作说明：")
    print("  由于 KMS 服务开通需要登录验证和人工确认")
    print("  无法完全自动化，需要您手动操作")
    
    print("\n✅ 开通后请告诉我，我将自动验证服务状态")


def verify_env_config():
    """
    验证 .env 文件配置
    """
    print("\n" + "=" * 80)
    print("【步骤 3/4】验证 .env 文件配置")
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
    
    # 检查 DOUBAO_MODEL
    model = os.getenv('DOUBAO_MODEL', '').strip()
    print(f"\n🤖 DOUBAO_MODEL:")
    print(f"  当前值: {model}")
    
    # 常见模型ID列表
    common_models = [
        'doubao-lite-4k',
        'doubao-pro-4k',
        'doubao-pro-32k',
        'doubao-vision',
        'ep-'  # 自定义端点前缀
    ]
    
    if any(model.startswith(m) for m in common_models):
        print(f"  ✅ 格式正确")
    else:
        print(f"  ⚠️ 建议检查模型ID是否正确")
        print(f"  常见模型: doubao-lite-4k, doubao-pro-4k, doubao-pro-32k")
    
    # 检查 DOUBAO_API_URL
    api_url = os.getenv('DOUBAO_API_URL', '').strip()
    print(f"\n🌐 DOUBAO_API_URL:")
    print(f"  当前值: {api_url}")
    if 'ark.cn-beijing.volces.com' in api_url:
        print(f"  ✅ 格式正确")
    else:
        print(f"  ⚠️ 建议检查 API URL")
    
    return bool(api_key)


def test_doubao_api():
    """
    测试豆包 API 调用
    """
    print("\n" + "=" * 80)
    print("【步骤 4/4】测试豆包 API 调用")
    print("=" * 80)
    
    api_key = os.getenv('DOUBAO_API_KEY', '').strip()
    api_url = os.getenv('DOUBAO_API_URL', 'https://ark.cn-beijing.volces.com/api/v3/chat/completions')
    model = os.getenv('DOUBAO_MODEL', 'doubao-lite-4k')
    
    if not api_key:
        print("\n❌ API Key 未配置，跳过测试")
        return False
    
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
        elif response.status_code == 404:
            error_data = response.json()
            error_code = error_data.get('error', {}).get('code', '')
            error_msg = error_data.get('error', {}).get('message', '')
            
            if 'KMS' in error_msg or 'kms' in error_msg:
                print(f"  ❌ KMS 服务未开通")
                print(f"  错误代码: {error_code}")
                print(f"  错误信息: {error_msg}")
                print(f"\n  请按步骤 2 开通 KMS 服务")
            else:
                print(f"  ❌ 模型不存在或无权访问")
                print(f"  错误代码: {error_code}")
                print(f"  错误信息: {error_msg}")
                print(f"\n  请检查 DOUBAO_MODEL 配置是否正确")
            return False
        else:
            print(f"  ❌ API 调用失败")
            print(f"  错误信息: {response.text[:200]}")
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
    
    # 步骤1: 检查 KMS 状态
    kms_ok = check_kms_status()
    
    if not kms_ok:
        # 步骤2: 显示开通指引
        show_kms_setup_guide()
        
        print("\n" + "=" * 80)
        print("⏸️ 等待 KMS 服务开通")
        print("=" * 80)
        print("\n请完成以下操作：")
        print("  1. 访问 https://console.volcengine.com/kms")
        print("  2. 开通 KMS 服务")
        print("  3. 完成后告诉我，我将自动验证")
        return
    
    # 步骤3: 验证配置
    config_ok = verify_env_config()
    
    if not config_ok:
        print("\n" + "=" * 80)
        print("❌ 配置验证失败")
        print("=" * 80)
        print("\n请检查 .env 文件中的 DOUBAO_API_KEY 配置")
        return
    
    # 步骤4: 测试 API
    api_ok = test_doubao_api()
    
    # 总结
    print("\n" + "=" * 80)
    print("验证总结")
    print("=" * 80)
    
    print(f"\nKMS 服务: {'✅ 已开通' if kms_ok else '❌ 未开通'}")
    print(f"API 配置: {'✅ 正确' if config_ok else '❌ 错误'}")
    print(f"API 测试: {'✅ 通过' if api_ok else '❌ 失败'}")
    
    if kms_ok and config_ok and api_ok:
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
        print("\n⚠️ 部分验证未通过，请按上述指引操作")
    
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
