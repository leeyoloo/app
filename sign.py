#!/usr/bin/env python3
"""
书香门第 (txtnovel.vip) 每日自动签到脚本
Discuz 论坛 + dsu_paulsign 签到助手插件
"""

import re
import os
import sys
import time
import random
import logging
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from push import push_success, push_failure

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

BASE_URL = os.environ.get("TXNOVEL_URL", "http://www.txtnovel.vip").rstrip('/')
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

# dsu_paulsign 心情编码
MOODS = ["kx", "ng", "ym", "ch", "fd", "shuai", "yj", "dx"]
MESSAGES = [
    "签到打卡，天天向上！",
    "每日签到，习惯养成！",
    "今天也要加油鸭！",
    "签到签到，金币到手！",
    "坚持签到，贵在坚持！",
    "每日一签，好运连连！",
    "签到成功，继续努力！",
]


def build_session(cookie_str: str) -> requests.Session:
    """
    从 COOKIE_TXNOVEL 环境变量构建带 cookie 的 requests.Session。
    兼容两种 cookie 格式：
      1. "key=val; key2=val2"  （浏览器直接复制）
      2. Netscape cookie 格式（多行，tab 分隔）
    """
    s = requests.Session()
    s.headers.update({
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,*/*",
        "Accept-Language": "zh-CN,zh;q=0.9",
    })

    # 设置重试
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    s.mount("http://", HTTPAdapter(max_retries=retry))
    s.mount("https://", HTTPAdapter(max_retries=retry))

    parsed = urlparse(BASE_URL)
    base_domain = parsed.hostname  # e.g. "www.txtnovel.vip" or "txtnovel.vip"

    # 解析 cookie 字符串
    cookies_dict = {}
    lines = cookie_str.strip().splitlines()

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        # Netscape 格式: domain  TRUE  /  FALSE  0  name  value
        if "\t" in line:
            parts = line.split("\t")
            if len(parts) >= 7:
                name = parts[5].strip()
                value = parts[6].strip()
                cookies_dict[name] = value
            continue

        # 标准 "key=val; key2=val2" 格式
        for pair in line.split(";"):
            pair = pair.strip()
            if "=" in pair:
                name, _, value = pair.partition("=")
                name = name.strip()
                value = value.strip()
                if name:
                    cookies_dict[name] = value

    if not cookies_dict:
        logger.error("No cookies parsed from COOKIE_TXNOVEL")
        sys.exit(1)

    logger.info(f"Parsed {len(cookies_dict)} cookies: {list(cookies_dict.keys())}")

    # 设置 cookie，兼容 www 和非 www 域名
    for name, value in cookies_dict.items():
        s.cookies.set(name, value, domain=base_domain, path="/")
        # 同时设置另一个域名变体（www <-> 非 www）
        if base_domain.startswith("www."):
            alt_domain = base_domain[4:]  # txtnovel.vip
        else:
            alt_domain = "www." + base_domain
        s.cookies.set(name, value, domain=alt_domain, path="/")
        # 也设置无域名限制
        s.cookies.set(name, value, path="/")

    return s


def check_login(session: requests.Session) -> str | None:
    """检查登录状态，返回用户名"""
    logger.info("Checking login...")
    try:
        r = session.get(f"{BASE_URL}/forum.php", timeout=15, allow_redirects=True)
        body = decode_response(r)
    except Exception as e:
        logger.error(f"Request failed: {e}")
        return None

    # 调试：输出响应状态和关键信息
    logger.info(f"Response status: {r.status_code}, final URL: {r.url}")
    logger.info(f"Response length: {len(body)} chars")

    # 检查登录标记
    if "退出" in body or "注销" in body or "logging" in body:
        # 多种方式提取用户名
        # 方式1: <a ... title="xxx">xxx</a> 模式
        patterns = [
            r'<a[^>]*href="[^"]*space-uid-\d+[^"]*"[^>]*>([^<]+)</a>',
            r'title="([^"]+)"[^>]*class="[^"]*vwmy[^"]*"',
            r'<a[^>]*id="umenu"[^>]*>([^<]+)</a>',
            r'welcomemessage[^>]*>([^<]+)<',
            r'<em[^>]*>([^<]{2,20})</em>',
            r'title="[^"]*"[^>]*>([^<]+)<',
        ]
        for pat in patterns:
            m = re.search(pat, body)
            if m and m.group(1).strip():
                username = m.group(1).strip()
                logger.info(f"Logged in as: {username}")
                return username

        logger.info("Logged in (username not extracted)")
        return "unknown"

    # 输出调试信息帮助排查
    if len(body) < 500:
        logger.warning(f"Short response body: {body[:300]}")

    logger.warning("Cookie expired or invalid — no login markers found")
    return None


def get_formhash(session: requests.Session) -> str | None:
    """获取 Discuz formhash"""
    try:
        r = session.get(f"{BASE_URL}/forum.php", timeout=15)
        body = decode_response(r)
        m = re.search(r'name="formhash"\s+value="(\w+)"', body)
        if m:
            fh = m.group(1)
            logger.info(f"formhash: {fh}")
            return fh
    except Exception as e:
        logger.error(f"Failed to get formhash: {e}")
    logger.warning("formhash not found")
    return None


def decode_response(r: requests.Response) -> str:
    """智能解码响应：优先从 XML/HTML 声明检测编码"""
    raw = r.content

    # 尝试从 XML 声明提取编码
    m = re.search(rb'<\?xml[^>]+encoding=["\']([^"\']+)', raw[:200])
    if m:
        enc = m.group(1).decode("ascii", errors="ignore").lower()
        try:
            return raw.decode(enc)
        except (LookupError, UnicodeDecodeError):
            pass

    # 尝试从 Content-Type 提取
    ct = r.headers.get("Content-Type", "")
    m = re.search(r'charset=([^\s;]+)', ct, re.I)
    if m:
        enc = m.group(1).lower()
        try:
            return raw.decode(enc)
        except (LookupError, UnicodeDecodeError):
            pass

    # Discuz 论坛默认 GBK，优先尝试
    for enc in ("gbk", "gb2312", "gb18030", "utf-8"):
        try:
            text = raw.decode(enc)
            # 简单验证：如果包含常见中文且不包含 replacement char
            if "\ufffd" not in text[:500] or enc == "utf-8":
                return text
        except (UnicodeDecodeError, LookupError):
            continue

    return raw.decode("utf-8", errors="replace")


def extract_sign_stats(body: str) -> dict:
    """从签到页/签到响应中提取签到统计信息"""
    stats = {}
    
    logger.info("开始提取签到信息...")
    logger.info(f"响应内容长度: {len(body)}")
    logger.info(f"响应内容前3000字符: {body[:3000]}")

    # 连续签到天数
    patterns = [
        r'连续签到[：:]\s*(\d+)\s*天',
        r'连续[：:]\s*(\d+)',
        r'连续(\d+)天',
        r'lianday[^>]*>(\d+)',
        r'连续.*?(\d+)',
    ]
    for p in patterns:
        m = re.search(p, body)
        if m:
            stats["continuous"] = int(m.group(1))
            logger.info(f"提取到连续签到天数: {stats['continuous']}")
            break

    # 累计签到天数
    patterns = [
        r'累计签到[：:]\s*(\d+)\s*天',
        r'累计[：:]\s*(\d+)',
        r'累计(\d+)天',
        r'totaldays[^>]*>(\d+)',
        r'总签[：:]\s*(\d+)',
        r'累计.*?(\d+)',
        r'您累计已签到[：:]\s*(\d+)',
        r'累计已签到[：:]\s*(\d+)',
    ]
    for p in patterns:
        m = re.search(p, body)
        if m:
            stats["total"] = int(m.group(1))
            logger.info(f"提取到累计签到天数: {stats['total']}")
            break

    # 本月签到天数
    patterns = [
        r'本月已累计签到[：:]\s*(\d+)\s*天',
        r'本月签到[：:]\s*(\d+)\s*天',
        r'本月[：:]\s*(\d+)',
        r'本月.*?(\d+)天',
    ]
    for p in patterns:
        m = re.search(p, body)
        if m:
            stats["monthly"] = int(m.group(1))
            logger.info(f"提取到本月签到天数: {stats['monthly']}")
            break

    # 上次签到时间
    patterns = [
        r'上次签到时间[：:]\s*([^\s<]+)',
        r'上次签到[：:]\s*([^\s<]+)',
        r'上次.*?时间[：:]\s*([^\s<]+)',
    ]
    for p in patterns:
        m = re.search(p, body)
        if m:
            stats["last_sign_time"] = m.group(1).strip()
            logger.info(f"提取到上次签到时间: {stats['last_sign_time']}")
            break

    # 总奖励
    patterns = [
        r'总奖励为[：:][^,，]+?([\d]+)\s*枚',
        r'总奖励[：:][^,，]+?([\d]+)\s*枚',
        r'累计奖励[：:][^,，]+?([\d]+)\s*枚',
        r'您目前获得的总奖励为[：:][^,，]*?([\d]+)\s*枚',
        r'目前获得的总奖励[：:][^,，]*?([\d]+)\s*枚',
        r'总奖励[：:]\s*([\d]+)\s*枚',
        r'金币[：:]\s*([\d]+)',
        r'金币[^\d]*(\d+)',
    ]
    for p in patterns:
        m = re.search(p, body)
        if m:
            stats["total_reward"] = int(m.group(1))
            logger.info(f"提取到总奖励: {stats['total_reward']}")
            break

    # 上次奖励
    patterns = [
        r'上次获得的奖励为[：:][^,，]+?([\d]+)\s*枚',
        r'上次奖励[：:][^,，]+?([\d]+)\s*枚',
    ]
    for p in patterns:
        m = re.search(p, body)
        if m:
            stats["last_reward"] = int(m.group(1))
            logger.info(f"提取到上次奖励: {stats['last_reward']}")
            break

    # 等级
    patterns = [
        r'等级[：:]\s*([^\s<,，]+)',
        r'level[：:]\s*([^\s<,，]+)',
        r'级别[：:]\s*([^\s<,，]+)',
        r'等级.*?\[(.*?)\]',
        r'您目前的等级为[：:](.*?)(?:，|Tips|$)',
        r'目前的等级[：:](.*?)(?:，|Tips|$)',
    ]
    for p in patterns:
        m = re.search(p, body)
        if m:
            stats["level"] = m.group(1).strip()
            logger.info(f"提取到等级: {stats['level']}")
            break

    # 升级所需天数
    patterns = [
        r'再签到\s*(\d+)\s*天就可以提升',
        r'还需\s*(\d+)\s*天升级',
        r'升级还需\s*(\d+)\s*天',
        r'Tips.*?再签到\s*(\d+)',
    ]
    for p in patterns:
        m = re.search(p, body)
        if m:
            stats["upgrade_days"] = int(m.group(1))
            logger.info(f"提取到升级所需天数: {stats['upgrade_days']}")
            break

    # 奖励（金币/铜币/威望）
    patterns = [
        r'获得[^<]*?(\d+)\s*(?:个?)?(?:金币|铜币|威望)',
        r'奖励[^<]*?(\d+)\s*(?:个?)?(?:金币|铜币|威望)',
    ]
    for p in patterns:
        m = re.search(p, body)
        if m:
            stats["reward"] = m.group(0).strip()
            stats["coins"] = int(m.group(1))
            logger.info(f"提取到本次奖励: {stats['reward']}")
            break
    
    logger.info(f"最终提取到的统计信息: {stats}")

    return stats


def do_sign(session: requests.Session, formhash: str) -> tuple[bool, str, dict]:
    """dsu_paulsign 签到助手 POST 签到，返回 (成功, 消息, 统计信息)"""
    logger.info("Signing in...")
    sign_page = f"{BASE_URL}/plugin.php?id=dsu_paulsign:sign"

    try:
        r = session.get(sign_page, timeout=15, headers={
            "Referer": f"{BASE_URL}/forum.php",
        })
        page_body = decode_response(r)
    except Exception as e:
        return False, f"无法访问签到页面: {e}", {}

    if "今日已签" in page_body or "已经签到" in page_body:
        stats = extract_sign_stats(page_body)
        logger.info(f"已经签到, stats: {stats}")
        return True, "今日已签到", stats

    # 分析签到页面结构，寻找正确的签到 URL 和参数
    logger.info("分析签到页面结构...")
    
    # 输出页面的前2000个字符，帮助调试
    logger.info(f"签到页面前2000字符: {page_body[:2000]}")
    
    # 尝试从页面中提取签到表单信息
    form_pattern = re.search(r'<form[^>]*action="([^"]+)"[^>]*>', page_body)
    if form_pattern:
        action_url = form_pattern.group(1)
        if not action_url.startswith('http'):
            action_url = BASE_URL + action_url
        logger.info(f"从页面提取到表单 action: {action_url}")
    else:
        # 尝试不同的签到 URL
        action_urls = [
            f"{BASE_URL}/plugin.php?id=dsu_paulsign:sign&operation=qiandao",
            f"{BASE_URL}/plugin.php?id=dsu_paulsign:sign&operation=qiandao&infloat=1",
            f"{BASE_URL}/plugin.php?id=dsu_paulsign:sign&operation=qiandao&inajax=1",
            f"{BASE_URL}/plugin.php?id=dsu_paulsign:sign&operation=qiandao&infloat=1&inajax=1",
        ]
        logger.info(f"准备尝试多个签到 URL: {action_urls}")

    # 从签到页提取 formhash（如果传入的 formhash 无效）
    if not formhash:
        # 尝试多种方式提取 formhash
        patterns = [
            r'name="formhash"\s+value="(\w+)"',
            r'formhash"\s*:\s*"(\w+)"',
            r'formhash=(\w+)',
            r'value="(\w+)"\s+name="formhash"',
            r'formhash\s*=\s*["\']([^"\']+)["\']',
        ]
        
        for pattern in patterns:
            m = re.search(pattern, page_body)
            if m:
                formhash = m.group(1)
                logger.info(f"从签到页面获取 formhash: {formhash}")
                break
        
        # 即使没有找到 formhash，也尝试签到
        if not formhash:
            logger.warning("未找到 formhash，尝试不带 formhash 签到")
            formhash = ""

    # 从签到页提取可用的心情值
    mood_options = re.findall(r'name="qdxq"\s+value="(\w+)"', page_body)
    if not mood_options:
        mood_options = re.findall(r'qdxq.*?value="(\w+)"', page_body)
    if mood_options:
        logger.info(f"从页面获取可用心情: {mood_options}")
        moods = mood_options
    else:
        moods = MOODS
        logger.info(f"使用默认心情: {moods}")

    # 确定要使用的签到 URL
    if 'action_url' in locals():
        # 如果从页面提取到了 action_url，就使用它
        test_urls = [action_url]
    else:
        # 否则尝试多个可能的签到 URL
        test_urls = action_urls

    # 尝试不同的签到模式和 URL
    for qdmode in [1, 2, 3]:
        mood = random.choice(moods)
        msg = random.choice(MESSAGES)

        logger.info(f"尝试 qdmode={qdmode}, mood={mood}: {msg}")

        # 尝试每个 URL
        for action_url in test_urls:
            logger.info(f"尝试 URL: {action_url}")

            # 添加随机延迟，避免频率限制
            delay = random.uniform(2, 5)
            logger.info(f"添加 {delay:.2f} 秒延迟，避免频率限制")
            time.sleep(delay)

            try:
                # 准备 POST 数据 - 尝试不同的参数组合
                post_data = {
                    "qdxq": mood,
                    "qdmode": qdmode,
                    "todaysay": msg,
                    "fastreply": "0",
                    "submit": "true",
                }
                
                # 添加 formhash（如果有）
                if formhash:
                    post_data["formhash"] = formhash
                
                # 尝试不同的参数名
                if qdmode == 1:
                    post_data["qdmode"] = "1"
                elif qdmode == 2:
                    post_data["qdmode"] = "2"
                elif qdmode == 3:
                    post_data["qdmode"] = "3"

                # 发送请求
                r = session.post(action_url, data=post_data, headers={
                    "Referer": sign_page,
                    "Content-Type": "application/x-www-form-urlencoded",
                }, timeout=15)
                body = decode_response(r)
            except Exception as e:
                logger.error(f"签到请求失败: {e}")
                continue

            logger.info(f"响应 ({len(body)} 字符): {body[:500]}")

            # 检查频率限制
            if "频率刷新限制" in body or "访问速度过快" in body:
                logger.warning("遇到频率限制，添加额外延迟")
                time.sleep(5)
                continue

            if "今日已签" in body or "已经签到" in body:
                stats = extract_sign_stats(body)
                return True, "今日已签到", stats

            # 签到成功
            if "签到成功" in body or "恭喜" in body or "获得" in body:
                stats = extract_sign_stats(body)
                return True, "签到成功", stats

            # Discuz 签到弹窗：有"签到提示"标题 + hideWindow = 成功
            if "签到提示" in body and "hideWindow" in body:
                stats = extract_sign_stats(body)
                return True, "签到成功", stats

            # 检查其他成功标志
            if "success" in body.lower() or "ok" in body.lower() or "成功" in body:
                stats = extract_sign_stats(body)
                return True, "签到成功", stats

            if "不正确" in body or "请重新选择" in body:
                logger.info(f"心情 {mood} 被拒绝, 尝试下一个...")
                continue

            if "未登录" in body or "请先登录" in body:
                return False, "Cookie 已过期", {}

    return False, "所有心情尝试失败", {}


def notify(result: bool, message: str, username: str = "", stats: dict = None):
    """发送通知 — 书香门第签到模板"""
    if stats is None:
        stats = {}
    cst = timezone(timedelta(hours=8))
    now = datetime.now(cst)
    now_str = now.strftime("%Y-%m-%d %H:%M")

    # 提取项目名称
    project_name = urlparse(BASE_URL).hostname or "书香门第"

    print("")
    print("=" * 50)
    print(f"Time: {now.strftime('%Y-%m-%d %H:%M:%S')} (CST)  Result: {'✅' if result else '❌'} {message}")
    print(f"URL:  {BASE_URL}")
    if result:
        print(f"OK:   {message}")
    else:
        print(f"FAIL: {message}")
    print("=" * 50)

    gh_output = os.environ.get("GITHUB_OUTPUT")
    if gh_output:
        with open(gh_output, "a") as f:
            f.write(f"sign_result={'success' if result else 'failed'}\n")
            f.write(f"sign_message={message}\n")
            f.write(f"sign_time={now_str}\n")

    # --- 推送模板 ---
    if result:
        user_line = username if username and username != "unknown" else "未知用户"

        # 构建奖励行
        if stats.get("coins"):
            reward_line = f"获得 {stats['coins']} 金币"
        elif stats.get("reward"):
            reward_line = stats["reward"]
        else:
            reward_line = "签到成功"

        # 构建详细信息
        details = []
        details.append(f"项目: {project_name}")
        if stats.get("total"):
            details.append(f"累计已签到: {stats['total']} 天")
        if stats.get("monthly"):
            details.append(f"本月已累计签到: {stats['monthly']} 天")
        if stats.get("last_sign_time"):
            details.append(f"上次签到时间: {stats['last_sign_time']}")
        if stats.get("total_reward"):
            details.append(f"目前获得的总奖励: 金币 {stats['total_reward']} 枚")
        if stats.get("last_reward"):
            details.append(f"上次获得的奖励: 金币 {stats['last_reward']} 枚")
        if stats.get("level"):
            details.append(f"目前的等级: {stats['level']}")
        if stats.get("upgrade_days"):
            details.append(f"Tips: 只需再签到 {stats['upgrade_days']} 天就可以提升等级")

        # 构建统计行
        parts = []
        if stats.get("continuous"):
            parts.append(f"连续{stats['continuous']}天")
        if stats.get("total"):
            parts.append(f"累计{stats['total']}天")
        if stats.get("level"):
            parts.append(f"等级: {stats['level']}")
        stats_line = " | ".join(parts) if parts else ""

        # 构建推送内容
        summary = f"{user_line}\n{reward_line}\n签到时间: {now_str}"
        if stats_line:
            summary += f"\n{stats_line}"
        # 添加详细信息
        if details:
            summary += "\n\n详细信息:\n" + "\n".join(details)
        push_success(summary)
    else:
        summary = (
            f"签到失败\n"
            f"项目: {project_name}\n"
            f"原因: {message}\n"
            f"签到时间: {now_str}"
        )
        push_failure(summary)


def random_delay():
    """
    随机延迟后签到
    SIGN_MAX_DELAY 环境变量设定最大延迟秒数：
      未设置/空 → 默认0秒(立即签到)
      0         → 立即签到
      60        → 最多等60秒
      1800      → 最多等30分钟
    每天基于日期做种子，同一天延迟固定
    """
    max_delay_env = os.environ.get("SIGN_MAX_DELAY", "").strip()
    try:
        max_delay = int(max_delay_env) if max_delay_env else 0
    except ValueError:
        logger.warning(f"SIGN_MAX_DELAY 值无效: {max_delay_env!r}，使用默认 0 秒")
        max_delay = 0
    if max_delay < 0:
        max_delay = 0

    cst = timezone(timedelta(hours=8))
    today = datetime.now(cst).strftime("%Y-%m-%d")
    rng = random.Random(today)
    delay = rng.randint(0, max_delay)

    if delay == 0:
        print("⚡ 立即签到（延迟 0 秒）")
    else:
        minutes = delay // 60
        seconds = delay % 60
        print(f"⏳ 随机延迟 {minutes}分{seconds}秒（上限 {max_delay} 秒）")
    time.sleep(delay)


def main():
    sign_max = os.environ.get("SIGN_MAX_DELAY", "").strip()
    print("=" * 50)
    print("txtnovel auto sign-in")
    print(f"URL: {BASE_URL}")
    print(f"SIGN_MAX_DELAY: {sign_max or '0'}s")
    print("=" * 50)

    # 随机延迟 0~30 分钟
    random_delay()

    cookie_str = os.environ.get("COOKIE_TXNOVEL", "").strip()
    if not cookie_str:
        logger.error("COOKIE_TXNOVEL not set")
        notify(False, "COOKIE_TXNOVEL 环境变量未设置")
        sys.exit(1)

    session = build_session(cookie_str)

    username = check_login(session)
    if not username:
        notify(False, "Cookie 无效或已过期")
        sys.exit(1)

    formhash = get_formhash(session)
    if not formhash:
        logger.warning("无法从 forum.php 获取 formhash，将尝试从签到页面获取")

    success, message, stats = do_sign(session, formhash)
    notify(success, message, username, stats)

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
