#!/usr/bin/env python3
"""
推送模块 — WxPusher + Telegram + 飞书自定义机器人 + 飞书应用机器人
通知内容精简版
"""

import os
import json
import hmac
import time
import base64
import hashlib
import requests
import logging

logger = logging.getLogger(__name__)


# --- WxPusher ---

def push_wxpusher(content: str, title: str = "书香门第签到") -> bool:
    spt = os.environ.get("WXPUSHER_SPT", "").strip()
    if not spt:
        return False

    full_content = f"{title}\n\n{content}"
    url = f"https://wxpusher.zjiecode.com/api/send/message/{spt}/{full_content}"

    for attempt in range(5):
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200:
                return True
        except requests.exceptions.RequestException as e:
            print(f"❌ WxPusher 失败({attempt + 1}/5): {e}")
            if attempt < 4:
                time.sleep(3 + attempt * 2)
    return False


# --- Telegram ---

TELEGRAM_API_BASE = "https://api.telegram.org"


def push_telegram(content: str, title: str = "书香门第签到") -> bool:
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

    if not bot_token or not chat_id:
        return False

    message = f"*{title}*\n{content}"
    url = f"{TELEGRAM_API_BASE}/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
    }

    for attempt in range(3):
        try:
            resp = requests.post(url, json=payload, timeout=15)
            if resp.status_code == 200 and resp.json().get("ok"):
                return True
        except requests.exceptions.RequestException as e:
            print(f"❌ Telegram 失败({attempt + 1}/3): {e}")
            if attempt < 2:
                time.sleep(3 + attempt * 2)
    return False


# --- 飞书自定义机器人（群机器人）---

def push_feishu(content: str, title: str = "书香门第签到") -> bool:
    """飞书自定义机器人推送（群机器人 Webhook）"""
    webhook = os.environ.get("FEISHU_WEBHOOK", "").strip()
    if not webhook:
        return False

    secret = os.environ.get("FEISHU_SECRET", "").strip()

    if secret:
        # 开启签名校验模式
        timestamp = str(int(time.time()))
        string_to_sign = f"{timestamp}\n{secret}"
        sign = base64.b64encode(
            hmac.new(secret.encode("utf-8"), string_to_sign.encode("utf-8"), hashlib.sha256).digest()
        ).decode("utf-8")
        payload = {
            "timestamp": timestamp,
            "sign": sign,
            "msg_type": "interactive",
            "card": {
                "header": {"title": {"tag": "plain_text", "content": title}},
                "elements": [{"tag": "markdown", "content": content}],
            },
        }
    else:
        # 无签名模式
        text = f"**{title}**\n\n{content}"
        payload = {"msg_type": "text", "content": {"text": text}}

    for attempt in range(3):
        try:
            resp = requests.post(webhook, json=payload, timeout=15, headers={"Content-Type": "application/json"})
            data = resp.json()
            if data.get("code") == 0 or data.get("StatusCode") == 0:
                print(f"📤 飞书机器人 推送成功")
                return True
            print(f"❌ 飞书机器人 推送失败: {data}")
        except Exception as e:
            print(f"❌ 飞书机器人 推送异常({attempt + 1}/3): {e}")
            if attempt < 2:
                time.sleep(3 + attempt * 2)
    return False


# --- 飞书应用机器人（企业应用）---

def push_feishu_app(content: str, title: str = "书香门第签到") -> bool:
    """飞书企业应用推送"""
    app_id = os.environ.get("FEISHU_APP_ID", "").strip()
    app_secret = os.environ.get("FEISHU_APP_SECRET", "").strip()
    receive_id = os.environ.get("FEISHU_APP_RECEIVE_ID", "").strip()
    receive_type = os.environ.get("FEISHU_APP_RECEIVE_TYPE", "open_id").strip()

    if not app_id or not app_secret or not receive_id:
        return False

    # 1. 获取 tenant_access_token
    try:
        resp = requests.post(
            "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            json={"app_id": app_id, "app_secret": app_secret},
            timeout=15,
        )
        tenant_token = resp.json().get("tenant_access_token")
        if not tenant_token:
            print(f"❌ 飞书应用 获取token失败: {resp.text[:200]}")
            return False
    except Exception as e:
        print(f"❌ 飞书应用 获取token异常: {e}")
        return False

    # 2. 发送消息
    send_url = f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type={receive_type}"
    text = f"{title}\n\n{content}"
    payload = {
        "receive_id": receive_id,
        "msg_type": "text",
        "content": json.dumps({"text": text}),
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {tenant_token}",
    }

    for attempt in range(3):
        try:
            resp = requests.post(send_url, json=payload, headers=headers, timeout=15)
            data = resp.json()
            if data.get("code") == 0:
                print(f"📤 飞书应用 推送成功")
                return True
            print(f"❌ 飞书应用 推送失败: {data}")
        except Exception as e:
            print(f"❌ 飞书应用 推送异常({attempt + 1}/3): {e}")
            if attempt < 2:
                time.sleep(3 + attempt * 2)
    return False


# --- 统一接口 ---

def push_success(content: str) -> bool:
    wx = push_wxpusher(content, title="✅ 已签到")
    tg = push_telegram(content, title="✅ 已签到")
    fs = push_feishu(content, title="✅ 已签到")
    fa = push_feishu_app(content, title="✅ 已签到")
    return wx or tg or fs or fa


def push_failure(content: str) -> bool:
    wx = push_wxpusher(content, title="❌ 签到失败")
    tg = push_telegram(content, title="❌ 签到失败")
    fs = push_feishu(content, title="❌ 签到失败")
    fa = push_feishu_app(content, title="❌ 签到失败")
    return wx or tg or fs or fa
