# -*- coding: utf-8 -*-
"""
Simple one-time notification test
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.notification.notification_sender import get_notification_sender

print("Sending ONE notification to Doubao...")

sender = get_notification_sender()

# Disable retries for this test
sender.retry_times = 1

result = sender.send_notification(
    title="豆包通知测试",
    message="这是一条测试通知！如果您看到这条消息，说明豆包推送功能正常工作。",
    data={'test': 'success'},
    retry=1
)

print(f"Result: {result}")

if result.get('success'):
    print("✅ 通知发送成功！")
else:
    print("❌ 通知发送失败")
