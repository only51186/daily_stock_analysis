# -*- coding: utf-8 -*-
"""
===================================
API密钥自动验证和全流程测试脚本
===================================

【功能】
1. 自动验证 TUSHARE_TOKEN 和 DOUBAO_API_KEY 是否有效
2. 测试 API 接口调用是否正常
3. 执行系统全流程测试（数据获取、选股、结果推送）
4. 输出测试结果

【使用方法】
填完密钥后，直接运行此脚本：
    python auto_verify_and_test.py
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
║          🔑 API密钥自动验证和全流程测试 🔑                          ║
║                                                                      ║
╚════════════════════════════════════════════════════════════════════╝
"""
    print(banner)


def verify_tushare_token():
    """
    验证 Tushare Token
    """
    print("\n" + "=" * 80)
    print("【步骤 1/5】验证 Tushare Token")
    print("=" * 80)
    
    # 加载 .env 文件
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)
    
    tushare_token = os.getenv('TUSHARE_TOKEN', '').strip()
    
    print(f"\nToken 状态检查...")
    print(f"  原始值: {repr(os.getenv('TUSHARE_TOKEN'))}")
    print(f"  去空格后: {repr(tushare_token)}")
    
    if not tushare_token or tushare_token == '':
        print(f"\n❌ Tushare Token 未配置")
        print(f"\n请按以下步骤获取 Token：")
        print(f"  1. 点击官方链接: https://tushare.pro/register")
        print(f"  2. 注册账号并登录")
        print(f"  3. 点击右上角头像 → 用户中心")
        print(f"  4. 在'接口TOKEN'页面复制Token")
        print(f"  5. 粘贴到 .env 文件第24行 TUSHARE_TOKEN= 后面")
        return False
    
    print(f"\n✅ Tushare Token 已配置")
    print(f"  长度: {len(tushare_token)} 字符")
    print(f"  前20字符: {tushare_token[:20]}")
    print(f"  后10字符: {tushare_token[-10:]}")
    
    # 测试连接
    print(f"\n正在测试 Tushare API 连接...")
    try:
        import tushare as ts
        pro = ts.pro_api(tushare_token)
        
        # 获取交易日历
        df = pro.trade_cal(exchange='SSE', start_date='20260301', end_date='20260303')
        
        print(f"✅ Tushare API 连接成功")
        print(f"  获取到 {len(df)} 条交易日数据")
        print(f"  数据示例: {df.head(1).to_dict('records')[0] if not df.empty else '无数据'}")
        return True
        
    except Exception as e:
        print(f"❌ Tushare API 连接失败")
        print(f"  错误信息: {str(e)[:200]}")
        print(f"\n可能原因：")
        print(f"  1. Token 不正确或已过期")
        print(f"  2. 网络连接问题")
        print(f"  3. Tushare 服务暂时不可用")
        return False


def verify_doubao_api_key():
    """
    验证豆包 API Key
    """
    print("\n" + "=" * 80)
    print("【步骤 2/5】验证豆包 API Key")
    print("=" * 80)
    
    # 加载 .env 文件
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)
    
    doubao_api_key = os.getenv('DOUBAO_API_KEY', '').strip()
    
    print(f"\nAPI Key 状态检查...")
    print(f"  原始值: {repr(os.getenv('DOUBAO_API_KEY'))}")
    print(f"  去空格后: {repr(doubao_api_key)}")
    
    if not doubao_api_key or doubao_api_key == '':
        print(f"\n❌ 豆包 API Key 未配置")
        print(f"\n请按以下步骤获取 API Key：")
        print(f"  1. 点击官方链接: https://console.volcengine.com/ark")
        print(f"  2. 登录火山引擎账号")
        print(f"  3. 创建应用（如已有可跳过）")
        print(f"  4. 在应用详情页获取API Key")
        print(f"  5. 粘贴到 .env 文件第31行 DOUBAO_API_KEY= 后面")
        return False
    
    print(f"\n✅ 豆包 API Key 已配置")
    print(f"  长度: {len(doubao_api_key)} 字符")
    print(f"  前20字符: {doubao_api_key[:20]}")
    print(f"  后10字符: {doubao_api_key[-10:]}")
    
    # 测试连接
    print(f"\n正在测试豆包 API 连接...")
    try:
        import requests
        
        api_url = os.getenv('DOUBAO_API_URL', 'https://ark.cn-beijing.volces.com/api/v3/chat/completions')
        model = os.getenv('DOUBAO_MODEL', 'Doubao-Seedream-5.0-lite')
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {doubao_api_key}'
        }
        
        payload = {
            'model': model,
            'messages': [
                {
                    'role': 'user',
                    'content': '测试连接，请回复"连接成功"'
                }
            ],
            'max_tokens': 10
        }
        
        response = requests.post(api_url, headers=headers, json=payload, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 豆包 API 连接成功")
            print(f"  响应状态: {response.status_code}")
            print(f"  模型: {model}")
            print(f"  响应内容: {result.get('choices', [{}])[0].get('message', {}).get('content', 'N/A')}")
            return True
        else:
            print(f"❌ 豆包 API 连接失败")
            print(f"  响应状态: {response.status_code}")
            print(f"  错误信息: {response.text[:200]}")
            print(f"\n可能原因：")
            print(f"  1. API Key 不正确")
            print(f"  2. API Key 已过期或额度不足")
            print(f"  3. 网络连接问题")
            return False
            
    except Exception as e:
        print(f"❌ 豆包 API 连接失败")
        print(f"  错误信息: {str(e)[:200]}")
        return False


def test_data_download():
    """
    测试数据下载
    """
    print("\n" + "=" * 80)
    print("【步骤 3/5】测试数据下载")
    print("=" * 80)
    
    try:
        from scripts.auto_data_downloader import AutoDataDownloader
        
        print(f"\n正在下载数据...")
        downloader = AutoDataDownloader()
        result = downloader.download_all_data(force=False)
        
        print(f"\n下载结果：")
        
        if result.get('sectors', {}).get('success', False):
            print(f"  ✅ 板块数据: {result['sectors']['count']}个")
        else:
            print(f"  ⚠️ 板块数据: {result['sectors'].get('message', '失败')}")
        
        if result.get('stocks', {}).get('success', False):
            print(f"  ✅ 股票数据: {result['stocks']['count']}只")
        else:
            print(f"  ⚠️ 股票数据: {result['stocks'].get('message', '失败')}")
        
        success = (result.get('sectors', {}).get('success', False) and
                 result.get('stocks', {}).get('success', False))
        
        if success:
            print(f"\n✅ 数据下载成功")
        else:
            print(f"\n⚠️ 数据下载部分失败")
        
        return success
        
    except Exception as e:
        print(f"\n❌ 数据下载失败")
        print(f"  错误信息: {str(e)[:200]}")
        return False


def test_stock_selection():
    """
    测试选股
    """
    print("\n" + "=" * 80)
    print("【步骤 4/5】测试选股")
    print("=" * 80)
    
    try:
        from scripts.evening_stock_selector_v2 import EveningStockSelector
        
        print(f"\n正在执行选股...")
        selector = EveningStockSelector()
        df = selector.run()
        
        if df is not None and not df.empty:
            print(f"\n✅ 选股成功")
            print(f"  选出股票: {len(df)} 只")
            
            print(f"\n前5只股票：")
            for i, row in df.head(5).iterrows():
                code = row.get('code', '')
                name = row.get('name', '')
                close = row.get('close', 0)
                pct_chg = row.get('pct_chg', 0)
                score = row.get('selection_score', 0)
                logic = row.get('selection_logic', '')
                print(f"  {i+1}. {code} {name}")
                print(f"     收盘:{close:.2f}元 涨幅:{pct_chg:+.2f}% 得分:{score}分")
                print(f"     逻辑:{logic}")
            
            return True
        else:
            print(f"\n⚠️ 未选出符合条件的股票")
            print(f"  这可能是正常的，取决于当前市场行情")
            return True
            
    except Exception as e:
        print(f"\n❌ 选股失败")
        print(f"  错误信息: {str(e)[:200]}")
        return False


def test_notification():
    """
    测试结果推送
    """
    print("\n" + "=" * 80)
    print("【步骤 5/5】测试结果推送")
    print("=" * 80)
    
    try:
        from src.notification.notification_sender import get_notification_sender
        
        notification_sender = get_notification_sender()
        
        # 检查是否启用
        if not notification_sender.enabled:
            print(f"\n⚠️ 通知推送已禁用")
            print(f"  当前配置: DOUBAO_PUSH_ENABLED=false")
            print(f"  如需启用，请在 .env 文件中设置 DOUBAO_PUSH_ENABLED=true")
            return True
        
        print(f"\n正在发送测试通知...")
        
        # 发送测试通知
        result = notification_sender.send_notification(
            title="系统测试通知",
            message="这是一条测试消息，如果您收到此消息，说明通知功能正常",
            data={
                'test': True,
                'timestamp': datetime.now().isoformat(),
                'message': '全流程测试完成'
            }
        )
        
        if result['success']:
            print(f"\n✅ 通知发送成功")
            print(f"  请检查您的豆包消息")
        else:
            print(f"\n❌ 通知发送失败")
            print(f"  错误信息: {result['message']}")
        
        return result['success']
        
    except Exception as e:
        print(f"\n❌ 通知发送失败")
        print(f"  错误信息: {str(e)[:200]}")
        return False


def run_full_test():
    """
    运行完整测试流程
    """
    print_banner()
    
    print(f"\n开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\n本脚本将自动执行以下步骤：")
    print(f"  1. 验证 Tushare Token")
    print(f"  2. 验证豆包 API Key")
    print(f"  3. 测试数据下载")
    print(f"  4. 测试选股功能")
    print(f"  5. 测试结果推送")
    
    input("\n按 Enter 键开始测试...")
    
    # 步骤1: 验证 Tushare Token
    tushare_ok = verify_tushare_token()
    if not tushare_ok:
        print("\n" + "=" * 80)
        print("测试终止")
        print("=" * 80)
        print("\n请先配置 TUSHARE_TOKEN 后再运行此脚本")
        print("获取地址: https://tushare.pro/register")
        return
    
    time.sleep(1)
    
    # 步骤2: 验证豆包 API Key
    doubao_ok = verify_doubao_api_key()
    if not doubao_ok:
        print("\n" + "=" * 80)
        print("测试终止")
        print("=" * 80)
        print("\n请先配置 DOUBAO_API_KEY 后再运行此脚本")
        print("获取地址: https://console.volcengine.com/ark")
        return
    
    time.sleep(1)
    
    # 步骤3: 测试数据下载
    data_ok = test_data_download()
    time.sleep(1)
    
    # 步骤4: 测试选股
    selection_ok = test_stock_selection()
    time.sleep(1)
    
    # 步骤5: 测试通知
    notification_ok = test_notification()
    
    # 总结
    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)
    
    tests = [
        ("Tushare Token", tushare_ok),
        ("豆包 API Key", doubao_ok),
        ("数据下载", data_ok),
        ("选股功能", selection_ok),
        ("结果推送", notification_ok)
    ]
    
    for test_name, success in tests:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"  {test_name:12s} - {status}")
    
    passed = sum(1 for _, success in tests if success)
    total = len(tests)
    
    print(f"\n通过率: {passed}/{total} ({passed/total*100:.1f}%)")
    print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if passed == total:
        print("\n" + "=" * 80)
        print("🎉 恭喜！所有测试通过！")
        print("=" * 80)
        print("\n系统已准备就绪，可以开始使用自动化系统")
        print("\n下一步：启动定时自动化系统")
        print("  命令: python main.py --mode schedule")
        print("\n启动后效果：")
        print("  ✅ 15:30 - 自动下载当日股票数据")
        print("  ✅ 16:00 - 自动计算技术指标")
        print("  ✅ 18:00 - 自动执行尾盘选股")
        print("  ✅ 20:00 - 自动执行历史回测")
        print("  ✅ 21:00 - 自动完成市场复盘")
        print("  ✅ 每个任务完成后自动推送结果到豆包")
        print("=" * 80)
    else:
        print("\n⚠️ 部分测试失败，请检查配置")
        print("\n常见问题：")
        print("  1. API密钥未配置或配置错误")
        print("  2. 网络连接问题")
        print("  3. 数据源暂时不可用")


if __name__ == '__main__':
    try:
        run_full_test()
    except KeyboardInterrupt:
        print("\n\n测试已中断")
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
