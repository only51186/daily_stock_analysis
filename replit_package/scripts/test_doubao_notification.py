# -*- coding: utf-8 -*-
"""
Test Doubao notification
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.notification.notification_sender import get_notification_sender

print("Testing Doubao notification...")

sender = get_notification_sender()

print(f"Enabled: {sender.enabled}")
print(f"API Key: {'*' * len(sender.api_key) if sender.api_key else 'Not set'}")
print(f"Model: {sender.model}")

result = sender.send_notification(
    title="测试通知",
    message="豆包推送功能测试成功！如果您看到这条消息，说明通知功能正常工作。",
    data={'test': 'success'}
)

print(f"\nResult: {result}")

if result.get('success'):
    print("✅ 豆包推送功能正常！")
else:
    print("❌ 豆包推送功能失败")
