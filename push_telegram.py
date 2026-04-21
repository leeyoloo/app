#!/usr/bin/env python3
"""
Telegram Bot 推送模块
通过 Bot API 发送签到结果通知
"""

import os
import time
import requests
import logging

logger = logging.getLogger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org"


def push_telegram(content: str, title: str = "书香门第签到") -> bool:
    """
    Telegram Bot 推送
    环境变量:
      TELEGRAM_BOT_TOKEN - Bot Token
      TELEGRAM_CHAT_ID   - 目标 Chat ID (个人或群组)
    """
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

    if not bot_token or not chat_id:
        logger.warning("Telegram Bot Token 或 Chat ID 未设置，跳过推送")
        print("ℹ️ 未设置 TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID，跳过 Telegram 推送")
        return False

    message = f"*{title}*\n\n{content}"
    url = f"{TELEGRAM_API_BASE}/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
    }

    attempts = 3
    for attempt in range(attempts):
        try:
            resp = requests.post(url, json=payload, timeout=15)
            logger.info("Telegram 响应: %s", resp.text[:200])
            print(f"📤 Telegram 推送结果: {resp.text[:150]}")
            if resp.status_code == 200 and resp.json().get("ok"):
                return True
            else:
                logger.error("Telegram 推送失败: %s", resp.text[:300])
        except requests.exceptions.RequestException as e:
            logger.error("Telegram 推送异常(%d/%d): %s", attempt + 1, attempts, e)
            print(f"❌ Telegram 推送失败({attempt + 1}/{attempts}): {e}")
            if attempt < attempts - 1:
                time.sleep(3 + attempt * 2)

    return False


def telegram_push_success(content: str) -> bool:
    """推送成功通知"""
    return push_telegram(content, title="✅ 书香门第签到成功")


def telegram_push_failure(content: str) -> bool:
    """推送失败通知"""
    return push_telegram(content, title="❌ 书香门第签到失败")
