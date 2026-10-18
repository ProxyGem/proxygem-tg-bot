# ============================================================
#   ProxyGem Telegram Bot — Single File Edition
#   Python 3.12+ / aiogram 3.x / SQLite
#   Без python-dotenv: свой мини-парсер .env
#   Навигация — в ОДНОМ сообщении (edit_caption / edit_text)
#   Консольные команды: restart | stop | start | status | help | exit
# ============================================================

import asyncio
import json
import logging
import os
import secrets
import string
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

# ============================================================
# РУЧНАЯ ЗАГРУЗКА .env (без python-dotenv)
# ============================================================
def _load_dotenv_manual(path: str = ".env"):
    """Простой парсер .env — без внешних библиотек."""
    if not os.path.exists(path):
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
    except Exception as e:
        print(f"⚠️ Не удалось прочитать .env: {e}")

_load_dotenv_manual()
# ============================================================

import aiosqlite
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    Message,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiohttp import ClientSession, ClientTimeout

# ============================================================
# KEEP_ALIVE (для Render / UptimeRobot)
# ============================================================
try:
    from keep_alive import keep_alive
    _HAS_KEEP_ALIVE = True
except ImportError:
    _HAS_KEEP_ALIVE = False
    def keep_alive():
        pass

# ============================================================
# CONFIG — БЕРЁТСЯ ИЗ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_IDS: List[int] = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()]

CHANNEL_USERNAME = "proxy_gem777"
CHANNEL_URL = "https://t.me/proxy_gem777"
SUPPORT_URL = "https://t.me/proxygem_support_bot"
SITE_URL = "https://proxygem.github.io/site/"
HOWTO_URL = "https://t.me/proxy_gem777/7"
DOWNLOAD_URL = "https://t.me/proxy_gem777/8"
DB_PATH = "proxygem.db"
LOG_LEVEL = "INFO"

IMG_MAIN = "images/glavnaia.png"
IMG_PREMIUM = "images/premium.png"

PROXY_URL = "tg://proxy?server=tg.taxivse.ru&port=25035&secret=eec3a80805cd5ee5d245ccea60ff27a3576170692d6d6170732e79616e6465782e7275"

WORKER_API        = os.getenv("WORKER_API", "https://proxygem.proxygem777.workers.dev").rstrip("/")
WORKER_TOKEN      = os.getenv("WORKER_TOKEN", "").strip()
PREMIUM_CODES_URL = os.getenv("PREMIUM_CODES_URL", "").strip()

GITHUB_OWNER      = os.getenv("GITHUB_OWNER", "ProxyGem")
GITHUB_REPO       = os.getenv("GITHUB_REPO", "X3-qW8-zR5-")
GITHUB_FILE_PATH  = os.getenv("GITHUB_FILE_PATH", "proxygem_sub.txt")
PREMIUM_FILE_PATH = os.getenv("PREMIUM_FILE_PATH", "premium_codes.json")

EXTRA_SERVICES = {
    "white": {"price": 59.0, "folder": "sub_white_list", "src": "white_list.txt", "name": "Белые списки"},
}

REF_BONUS_PER_FRIEND = 15.0
BONUS_MIN_ORDER      = 50.0

LINKS = {
    "incy_ios":     "https://apps.apple.com/ru/app/incy/id6756943388",
    "incy_android": "https://play.google.com/store/search?q=INCY&c=apps&hl=ru",
    "happ_android": "https://play.google.com/store/apps/details?id=com.happproxy&hl=ru",
    "happ_windows": "https://github.com/Happ-proxy/happ-desktop/releases/latest/download/setup-Happ.x64.exe",
}

if not BOT_TOKEN:
    print("❌ BOT_TOKEN не найден. Установи переменную окружения BOT_TOKEN.")
    sys.exit(1)

if not ADMIN_IDS:
    print("⚠️ ADMIN_IDS не задан — админ-панель будет недоступна никому.")

# ============================================================
# ANSI COLORS + BANNER
# ============================================================

def _enable_ansi():
    if os.name == "nt":
        os.system("")
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except Exception:
            pass


class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    BG_PINK = "\033[105m"
    BLACK = "\033[30m"
    BRIGHT_BLACK = "\033[90m"
    WHITE = "\033[97m"
    PINK_TEXT = "\033[95m"
    CYAN = "\033[96m"
    YELLOW = "\033[93m"
    GREEN = "\033[92m"
    RED = "\033[91m"


BANNER = r"""
    ██████╗ ██████╗  ██████╗ ██╗  ██╗██╗   ██╗     ██████╗ ███████╗███╗   ███╗
    ██╔══██╗██╔══██╗██╔═══██╗╚██╗██╔╝╚██╗ ██╔╝    ██╔════╝ ██╔════╝████╗ ████║
    ██████╔╝██████╔╝██║   ██║ ╚███╔╝  ╚████╔╝     ██║  ███╗█████╗  ██╔████╔██║
    ██╔═══╝ ██╔══██╗██║   ██║ ██╔██╗   ╚██╔╝      ██║   ██║██╔══╝  ██║╚██╔╝██║
    ██║     ██║  ██║╚██████╔╝██╔╝ ██╗   ██║       ╚██████╔╝███████╗██║ ╚═╝ ██║
    ╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝   ╚═╝        ╚═════╝ ╚══════╝╚═╝     ╚═╝

    ███████╗███████╗██████╗ ██╗   ██╗███████╗██████╗ ███████╗
    ██╔════╝██╔════╝██╔══██╗██║   ██║██╔════╝██╔══██╗██╔════╝
    ███████╗█████╗  ██████╔╝██║   ██║█████╗  ██████╔╝███████╗
    ╚════██║██╔══╝  ██╔══██╗╚██╗ ██╔╝██╔══╝  ██╔══██╗╚════██║
    ███████║███████╗██║  ██║ ╚████╔╝ ███████╗██║  ██║███████║
    ╚══════╝╚══════╝╚═╝  ╚═╝  ╚═══╝  ╚══════╝╚═╝  ╚═╝╚══════╝
"""


def print_banner():
    _enable_ansi()
    print()
    print(f"{C.PINK_TEXT}{C.BOLD}{BANNER}{C.RESET}")
    print()
    print(f"{C.CYAN}{C.BOLD}    PROXYGEM{C.RESET}")
    print(f"{C.CYAN}{C.BOLD}    TG BOT SERVERS{C.RESET}")
    print()
    header = f"{C.BG_PINK}{C.BLACK}{C.BOLD}" + " " * 64 + f"{C.RESET}"
    print(header)
    print("  ProxyGem Bot · Telegram · aiogram 3.x")
    print("  консоль управления — введите 'help'")
    print(header)
    print()


def print_help():
    print(f"{C.CYAN}{'═' * 64}{C.RESET}")
    print(f"{C.BOLD}{C.WHITE}  КОНСОЛЬ УПРАВЛЕНИЯ PROXYGEM BOT{C.RESET}")
    print(f"{C.CYAN}{'═' * 64}{C.RESET}")
    print(f"  {C.YELLOW}restart{C.RESET}   — перезапустить бота")
    print(f"  {C.YELLOW}stop{C.RESET}      — остановить бота")
    print(f"  {C.YELLOW}start{C.RESET}     — возобновить polling")
    print(f"  {C.YELLOW}status{C.RESET}    — статус")
    print(f"  {C.YELLOW}help{C.RESET}      — справка")
    print(f"  {C.YELLOW}exit{C.RESET}      — выход")
    print(f"{C.CYAN}{'═' * 64}{C.RESET}")
    print()


logging.basicConfig(
    level=LOG_LEVEL,
    format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
log = logging.getLogger("proxygem")

CONTROL = {"stop": False, "restart": False, "exit": False}
bot: Optional[Bot] = None
_http: Optional[ClientSession] = None

# ============================================================
# DATABASE
# ============================================================

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    language TEXT DEFAULT 'ru',
    is_admin INTEGER DEFAULT 0,
    is_banned INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    plan TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    folder TEXT,
    custom_name TEXT,
    raw_url TEXT,
    device_limit TEXT DEFAULT 'Безлимит',
    traffic_limit TEXT DEFAULT 'Безлимит'
);
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    plan TEXT NOT NULL,
    amount REAL NOT NULL,
    currency TEXT DEFAULT 'RUB',
    provider TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    external_id TEXT,
    order_id TEXT,
    bonus_used REAL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS referrals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    referrer_id INTEGER NOT NULL,
    referred_id INTEGER NOT NULL UNIQUE,
    bonus REAL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS bonuses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    reason TEXT DEFAULT '',
    ref_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS languages (code TEXT PRIMARY KEY, title TEXT NOT NULL);
INSERT OR IGNORE INTO languages (code, title) VALUES
('ru','Русский'),('en','English'),('tr','Türkçe');
"""


class DB:
    def __init__(self, path: str):
        self.path = path
        self._conn: Optional[aiosqlite.Connection] = None

    async def connect(self):
        self._conn = await aiosqlite.connect(self.path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.executescript(SCHEMA)
        await self._migrate()
        await self._conn.commit()
        log.info("DB connected: %s", self.path)

    async def _migrate(self):
        migrations = [
            ("payments",      "order_id",     "TEXT"),
            ("payments",      "external_id",  "TEXT"),
            ("payments",      "bonus_used",   "REAL DEFAULT 0"),
            ("users",         "is_admin",     "INTEGER DEFAULT 0"),
            ("users",         "is_banned",    "INTEGER DEFAULT 0"),
            ("users",         "language",     "TEXT DEFAULT 'ru'"),
            ("referrals",     "bonus",        "REAL DEFAULT 0"),
            ("subscriptions", "folder",       "TEXT"),
            ("subscriptions", "custom_name",  "TEXT"),
            ("subscriptions", "raw_url",      "TEXT"),
            ("subscriptions", "device_limit", "TEXT DEFAULT 'Безлимит'"),
            ("subscriptions", "traffic_limit","TEXT DEFAULT 'Безлимит'"),
        ]
        for table, column, coltype in migrations:
            try:
                async with self.c.execute(f"PRAGMA table_info({table})") as cur:
                    cols = [row["name"] for row in await cur.fetchall()]
                if column not in cols:
                    await self.c.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}")
                    log.info("Migration: added %s.%s", table, column)
            except Exception as e:
                log.warning("Migration %s.%s failed: %s", table, column, e)

    async def close(self):
        if self._conn:
            await self._conn.close()

    @property
    def c(self) -> aiosqlite.Connection:
        assert self._conn is not None
        return self._conn

    async def get_user(self, uid: int) -> Optional[Dict[str, Any]]:
        async with self.c.execute("SELECT * FROM users WHERE id=?", (uid,)) as cur:
            r = await cur.fetchone()
            return dict(r) if r else None

    async def upsert_user(self, uid: int, username: str, first_name: str, last_name: str = ""):
        await self.c.execute(
            "INSERT INTO users (id, username, first_name, last_name) VALUES (?,?,?,?) "
            "ON CONFLICT(id) DO UPDATE SET username=excluded.username, "
            "first_name=excluded.first_name, last_name=excluded.last_name",
            (uid, username, first_name, last_name),
        )
        await self.c.commit()

    async def set_language(self, uid: int, lang: str):
        await self.c.execute("UPDATE users SET language=? WHERE id=?", (lang, uid))
        await self.c.commit()

    async def get_language(self, uid: int) -> str:
        u = await self.get_user(uid)
        return (u or {}).get("language", "ru")

    async def count_users(self) -> int:
        async with self.c.execute("SELECT COUNT(*) AS c FROM users") as cur:
            return (await cur.fetchone())["c"]

    async def count_new_users_today(self) -> int:
        async with self.c.execute(
            "SELECT COUNT(*) AS c FROM users WHERE date(created_at)=date('now')"
        ) as cur:
            return (await cur.fetchone())["c"]

    async def all_user_ids(self) -> List[int]:
        async with self.c.execute("SELECT id FROM users") as cur:
            return [r["id"] for r in await cur.fetchall()]

    async def create_subscription(self, uid: int, plan: str, days: int,
                                  folder: Optional[str] = None,
                                  raw_url: Optional[str] = None,
                                  custom_name: Optional[str] = None,
                                  device_limit: str = "Безлимит",
                                  traffic_limit: str = "Безлимит") -> int:
        expires = (datetime.utcnow() + timedelta(days=days)).isoformat()
        cur = await self.c.execute(
            "INSERT INTO subscriptions "
            "(user_id, plan, expires_at, folder, raw_url, custom_name, device_limit, traffic_limit) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (uid, plan, expires, folder, raw_url, custom_name, device_limit, traffic_limit),
        )
        await self.c.commit()
        return cur.lastrowid

    async def get_subscription(self, sub_id: int, uid: Optional[int] = None) -> Optional[Dict[str, Any]]:
        if uid is not None:
            async with self.c.execute(
                "SELECT * FROM subscriptions WHERE id=? AND user_id=?", (sub_id, uid)
            ) as cur:
                r = await cur.fetchone()
        else:
            async with self.c.execute(
                "SELECT * FROM subscriptions WHERE id=?", (sub_id,)
            ) as cur:
                r = await cur.fetchone()
        return dict(r) if r else None

    async def user_subscriptions(self, uid: int) -> List[Dict[str, Any]]:
        async with self.c.execute(
            "SELECT * FROM subscriptions WHERE user_id=? ORDER BY id DESC", (uid,)
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]

    async def active_subscription(self, uid: int) -> Optional[Dict[str, Any]]:
        async with self.c.execute(
            "SELECT * FROM subscriptions WHERE user_id=? AND status='active' "
            "AND expires_at > ? ORDER BY expires_at DESC LIMIT 1",
            (uid, datetime.utcnow().isoformat()),
        ) as cur:
            r = await cur.fetchone()
            return dict(r) if r else None

    async def count_active_subs(self) -> int:
        async with self.c.execute(
            "SELECT COUNT(*) AS c FROM subscriptions WHERE status='active' AND expires_at > ?",
            (datetime.utcnow().isoformat(),),
        ) as cur:
            return (await cur.fetchone())["c"]

    async def rename_subscription(self, sub_id: int, uid: int, new_name: str):
        await self.c.execute(
            "UPDATE subscriptions SET custom_name=? WHERE id=? AND user_id=?",
            (new_name, sub_id, uid),
        )
        await self.c.commit()

    async def delete_subscription(self, sub_id: int, uid: Optional[int] = None):
        if uid is None:
            await self.c.execute("DELETE FROM subscriptions WHERE id=?", (sub_id,))
        else:
            await self.c.execute(
                "DELETE FROM subscriptions WHERE id=? AND user_id=?", (sub_id, uid)
            )
        await self.c.commit()

    async def create_payment(self, uid: int, plan: str, amount: float, provider: str,
                             order_id: Optional[str] = None, bonus_used: float = 0.0) -> int:
        cur = await self.c.execute(
            "INSERT INTO payments (user_id, plan, amount, provider, order_id, bonus_used) "
            "VALUES (?,?,?,?,?,?)",
            (uid, plan, amount, provider, order_id, bonus_used),
        )
        await self.c.commit()
        return cur.lastrowid

    async def mark_payment_success(self, order_id: str):
        await self.c.execute(
            "UPDATE payments SET status='success' WHERE order_id=?", (order_id,)
        )
        await self.c.commit()

    async def pending_payments(self) -> List[Dict[str, Any]]:
        async with self.c.execute(
            "SELECT * FROM payments WHERE status='pending' AND provider='platega'"
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]

    async def add_referral(self, ref_id: int, new_id: int) -> bool:
        try:
            await self.c.execute(
                "INSERT INTO referrals (referrer_id, referred_id, bonus) VALUES (?,?,?)",
                (ref_id, new_id, REF_BONUS_PER_FRIEND),
            )
            await self.c.execute(
                "INSERT INTO bonuses (user_id, amount, reason, ref_id) VALUES (?,?,?,?)",
                (ref_id, REF_BONUS_PER_FRIEND, "referral", new_id),
            )
            await self.c.commit()
            return True
        except aiosqlite.IntegrityError:
            return False

    async def ref_count(self, uid: int) -> int:
        async with self.c.execute(
            "SELECT COUNT(*) AS c FROM referrals WHERE referrer_id=?", (uid,)
        ) as cur:
            return (await cur.fetchone())["c"]

    async def ref_bonus(self, uid: int) -> float:
        async with self.c.execute(
            "SELECT COALESCE(SUM(bonus),0) AS s FROM referrals WHERE referrer_id=?", (uid,)
        ) as cur:
            return float((await cur.fetchone())["s"])

    async def count_refs_total(self) -> int:
        async with self.c.execute("SELECT COUNT(*) AS c FROM referrals") as cur:
            return (await cur.fetchone())["c"]

    async def get_balance(self, uid: int) -> float:
        async with self.c.execute(
            "SELECT COALESCE(SUM(amount),0) AS s FROM bonuses WHERE user_id=?", (uid,)
        ) as cur:
            return float((await cur.fetchone())["s"])

    async def add_bonus(self, uid: int, amount: float, reason: str = "", ref_id: Optional[int] = None):
        await self.c.execute(
            "INSERT INTO bonuses (user_id, amount, reason, ref_id) VALUES (?,?,?,?)",
            (uid, amount, reason, ref_id),
        )
        await self.c.commit()

    async def spend_bonus(self, uid: int, amount: float, reason: str = "subscription"):
        if amount <= 0:
            return True
        bal = await self.get_balance(uid)
        if bal + 0.001 < amount:
            return False
        await self.c.execute(
            "INSERT INTO bonuses (user_id, amount, reason) VALUES (?,?,?)",
            (uid, -abs(amount), reason),
        )
        await self.c.commit()
        return True


db = DB(DB_PATH)

# ============================================================
# I18N
# ============================================================

T: Dict[str, Dict[str, str]] = {
    "ru": {
        "subscribe_required": "⊘ Для использования бота необходимо подписаться на канал ProxyGem.\n\nПосле подписки нажмите кнопку ниже.",
        "subscribe_btn": "▸ Подписаться",
        "check_sub_btn": "✓ Проверить подписку",
        "not_subscribed": "✕ Вы ещё не подписались на канал!",
        "choose_language": "◍ Выберите язык / Choose language:",
        "language_saved": "✓ Язык сохранён!",
        "main_menu": "◆ Добро пожаловать в главное меню!\n\n▸ Как пользоваться ProxyGem?\n{howto}\n\n◍ Наш сайт:\n{site}\n\n❯ Выберите действие:",
        "btn_buy":     "▣ Купить",
        "btn_my_subs": "◆ Подключиться",
        "btn_invite":  "✦ Пригласить друга",
        "btn_profile": "◉ Мой профиль",
        "btn_proxy":   "◇ Прокси для Telegram",
        "btn_support": "⚙ Не работает ProxyGem",
        "btn_download":"⤓ Скачать",
        "btn_back":    "❮ Назад",
        "btn_admin":   "⛨ Админ-панель",
        "btn_change_lang": "◍ Сменить язык",
        "btn_pay":     "▦ Оплатить",
        "btn_site":    "◍ Сайт",
        "btn_support_chat": "✉ Поддержка",
        "download_title": (
            "⤓ Скачать ProxyGem\n\n"
            "▸ На данный момент доступна версия только для Windows.\n"
            "▸ Версии для других устройств появятся позже.\n\n"
            "❯ Нажмите кнопку ниже, чтобы скачать:"
        ),
        "download_btn": "⤓ Скачать для Windows",
        "tariffs_title": "▣ Тарифы ProxyGem\n\n❯ Выберите подходящий план:",
        "buy_menu_title": "▣ Магазин ProxyGem\n\n❯ Выберите раздел:",
        "t1_name": "① 1 месяц", "t1_desc": "Быстрый доступ", "t1_feat": "• Безлимит устройств\n• Безлимит трафик\n• Все локации", "t1_price": "259 ₽",
        "t3_name": "② 3 месяца", "t3_desc": "Оптимально", "t3_feat": "• Безлимит устройств\n• Безлимит трафик\n• Все локации\n• Приоритет", "t3_price": "659 ₽",
        "t6_name": "③ 6 месяцев", "t6_desc": "Полгода без забот", "t6_feat": "• Безлимит устройств\n• Безлимит трафик\n• Все локации\n• Приоритет\n• Скидка 20%", "t6_price": "1 190 ₽",
        "tariff_details": "▤ {name}\n\n{desc}\n\nЧто входит:\n{feat}\n\n◎ Цена: {price}",
        "pay_choose": "▦ Выберите способ оплаты:",
        "pay_crypto": "◎ CryptoBot",
        "pay_stars": "☆ Telegram Stars",
        "pay_yookassa": "▦ ЮKassa",
        "pay_platega": "▦ Platega",
        "pay_stub": "⚠ Оплата через {provider} временно недоступна.\nОбратитесь в поддержку: {support}",
        "pay_created": "▦ Платёж создан.\n\n❯ Нажмите кнопку ниже для оплаты:",
        "pay_btn_go": "▦ Перейти к оплате",
        "pay_fail": "⚠ Не удалось создать платёж. Попробуйте позже.",
        "no_subs": "▤ У вас пока нет подписок.\n\n❯ Купите подписку в разделе «Купить» или активируйте ключ.",
        "subs_title": "▤ Ваши подписки\n\n❯ Выберите подписку:",
        "sub_info": "▤ Информация о подписке\n\n◉ Название: {name}\n○ Лимит устройств: {devices}\n◎ Действует до: {expires}\n○ Активирована: {started}\n● Статус: {status}\n○ Трафик обхода: {traffic}",
        "sub_active": "Активна",
        "sub_inactive": "Неактивна",
        "sub_expired": "Истекла",
        "btn_connect_vpn": "◆ Подключить VPN",
        "btn_rename":      "✎ Изменить название",
        "btn_delete":      "✕ Удалить подписку",
        "btn_iphone":      "▸ iPhone",
        "btn_android":     "▸ Android",
        "btn_windows":     "▸ Windows",
        "btn_macos":       "▸ macOS",
        "btn_back_subs":   "❮ К подпискам",
        "rename_prompt":   "✎ Введите новое название подписки.\n\nОтмена: /cancel",
        "rename_done":     "✓ Название изменено на «{name}».",
        "delete_confirm":  "⚠ Вы точно хотите удалить подписку?\n\nПосле удаления вы уже не сможете её активировать.",
        "delete_done":     "✓ Подписка удалена.",
        "vpn_title":       "◆ Подключение VPN\n\n❯ Выберите вашу платформу:",
        "android_choose":  "◆ Android\n\n❯ Выберите приложение:",
        "happ_btn":        "▸ Happ",
        "incy_btn":        "▸ Incy",
        "no_active": "⚠ Подписка неактивна или истекла. Продлите её, чтобы получить ссылку.",
        "ref_title": "✦ Приглашайте друзей!\n\nВаша ссылка:\n{link}\n\n◉ Приглашено: {friends}\n◎ Бонусов: {bonus} ₽\n★ Уровень: {level}\n\n▸ За каждого друга — +15 ₽.\n▸ Списать бонусы можно при оплате от 50 ₽.",
        "lv1": "① Новичок", "lv2": "② Друг", "lv3": "③ Партнёр", "lv4": "④ Легенда",
        "profile_title": "◉ Ваш профиль:\n\n▸ ID: {id}\n▸ Username: {username}\n▸ Имя: {name}\n▸ Язык: {language}\n▸ Регистрация: {created}\n▸ Приглашено: {friends}\n▸ Бонусов: {bonus} ₽\n▸ Подписка: {sub_status}",
        "no_username": "не указан",
        "vpn_help": "⚙ Если возникли проблемы с ProxyGem:\n\n1. Перезапустите приложение.\n2. Проверьте интернет.\n3. Обновите конфигурацию.\n4. Попробуйте другой сервер.",
        "support_text": "✉ Поддержка: {support}\n◍ Сайт: {site}",
        "proxy_title": "◇ Прокси для Telegram\n\n▸ Бесплатный MTProto-прокси для обхода блокировок.\n▸ Работает в России и других регионах.\n▸ Не требует VPN-приложения — работает прямо в Telegram.\n\n❯ Нажмите «Подключиться», чтобы активировать прокси.",
        "proxy_connect": "◆ Подключиться",
        "proxy_hint": "▸ Если прокси не работает — попробуйте позже или напишите в поддержку.",
        "admin_title": "⛨ Админ-панель",
        "admin_users": "◉ Пользователи",
        "admin_stats": "▦ Статистика",
        "admin_broadcast": "✉ Рассылка",
        "admin_subs": "▤ Подписки",
        "admin_refs": "✦ Рефералы",
        "admin_conv": "◆ Конверсии",
        "admin_stats_text": "▦ Статистика ProxyGem\n\n◉ Всего пользователей: {users}\n✦ Новых за день: {new_today}\n▤ Активных подписок: {subs}\n◆ Всего рефералов: {refs}",
        "admin_users_text": "◉ Последние {n} пользователей:\n\n{list}",
        "broadcast_prompt": "✉ Отправьте текст рассылки.\n\nОтмена: /cancel",
        "broadcast_done": "✓ Рассылка завершена.\nОтправлено: {sent}\nОшибок: {failed}",
        "broadcast_cancel": "✕ Рассылка отменена.",
        "not_admin": "⛔ У вас нет доступа.",
        "antispam": "⏳ Слишком много запросов. Подождите немного.",
        "error": "⚠ Произошла ошибка. Попробуйте позже.",
        "btn_tariffs":  "▣ Подписки ProxyGem",
        "btn_key_act":  "✎ Активировать ключ",
        "key_prompt":   "✎ Введите ключ активации.\n\nОтмена: /cancel",
        "key_not_found": "✕ Ключ не найден.",
        "key_used":     "✕ Ключ уже использован.",
        "key_bad_type": "✕ Этот ключ не активируется в боте.",
        "key_limit":    "✕ Достигнут лимит активаций для этого ключа.",
        "key_ok":       "✓ Ключ активирован!\n\n▸ Тариф: {duration}\n▸ Дней: {days}\n▸ Название: {name}\n▸ Папка: {folder}\n\n❯ Перейдите в «Подключиться», чтобы получить ссылку.",
        "key_ok_no_url": "✓ Ключ активирован, но ссылка не создалась. Напишите в поддержку: {support}",
"extra_details": "◇ {name}\n\n◎ Цена: {price:.0f} ₽\n▸ Срок: навсегда",
        "extra_pay_btn": "▦ Оплатить {price:.0f} ₽",
        "extra_not_found": "⚠ Услуга не найдена",
        "pay_success_key": "✓ Оплата получена!\n\n▸ Ваш ключ: `{key}`\n▸ Тариф: {duration}\n\nАктивируйте его: «Купить» → «Активировать ключ».",
        "pay_no_keys": "⚠ Оплата прошла, но свободные ключи закончились. Напишите в поддержку: {support}",
        "pay_success_extra": "✓ Оплата получена!\n\n▸ {name}\n{link_line}",
        "sub_link_line": "\n▸ Ваша подписка: {url}",
        "bonus_offer": "◎ У вас есть бонусные {bal:.0f} ₽.\n\nСписать бонусы при оплате этого заказа?",
        "bonus_btn_use_all": "✓ Списать {bal:.0f} ₽",
        "bonus_btn_use_partial": "✎ Списать часть",
        "bonus_btn_skip": "✕ Не списывать",
        "bonus_partial_prompt": "✎ Введите сумму бонусов для списания (от 1 до {max:.0f} ₽).\n\nЗаказ: {price:.0f} ₽\n\nОтмена: /cancel",
        "bonus_applied": "✓ Бонусы применены.\n\n▸ Сумма заказа: {price:.0f} ₽\n▸ Списано бонусами: {bonus:.0f} ₽\n▸ К оплате: {to_pay:.0f} ₽",
        "bonus_min_order": "⚠ Списать бонусы можно только при сумме заказа от {min:.0f} ₽.",
        "bonus_not_enough": "✕ Недостаточно бонусов.",
        "bonus_bad_amount": "✕ Некорректная сумма.",
    },
    "en": {
        "subscribe_required": "⊘ Subscribe to ProxyGem channel first.",
        "subscribe_btn": "▸ Subscribe",
        "check_sub_btn": "✓ Check",
        "not_subscribed": "✕ Not subscribed!",
        "choose_language": "◍ Choose language:",
        "language_saved": "✓ Saved!",
        "main_menu": "◆ Main menu!\n\n▸ How to use?\n{howto}\n\n◍ Site:\n{site}\n\n❯ Choose:",
        "btn_buy": "▣ Buy", "btn_my_subs": "◆ Connect", "btn_invite": "✦ Invite",
        "btn_profile": "◉ Profile", "btn_proxy": "◇ Proxy", "btn_support": "⚙ Support",
        "btn_download": "⤓ Download", "btn_back": "❮ Back", "btn_admin": "⛨ Admin",
        "btn_change_lang": "◍ Language", "btn_pay": "▦ Pay", "btn_site": "◍ Site",
        "btn_support_chat": "✉ Support",
        "download_title": "⤓ Download ProxyGem",
        "download_btn": "⤓ Download",
        "tariffs_title": "▣ Tariffs",
        "buy_menu_title": "▣ Shop",
        "t1_name": "① 1 month", "t1_desc": "Fast", "t1_feat": "• Unlimited devices\n• Unlimited traffic", "t1_price": "259 ₽",
        "t3_name": "② 3 months", "t3_desc": "Best", "t3_feat": "• Unlimited devices\n• Unlimited traffic", "t3_price": "659 ₽",
        "t6_name": "③ 6 months", "t6_desc": "Half-year", "t6_feat": "• Unlimited devices\n• Unlimited traffic", "t6_price": "1 190 ₽",
        "tariff_details": "▤ {name}\n\n{desc}\n\n{feat}\n\n◎ {price}",
        "pay_choose": "▦ Payment method:",
        "pay_crypto": "◎ CryptoBot", "pay_stars": "☆ Stars", "pay_yookassa": "▦ YooKassa", "pay_platega": "▦ Platega",
        "pay_stub": "⚠ {provider} unavailable. {support}",
        "pay_created": "▦ Payment created. ❯ Press below:",
        "pay_btn_go": "▦ Go to payment",
        "pay_fail": "⚠ Failed.",
        "no_subs": "▤ No subscriptions.",
        "subs_title": "▤ Subscriptions\n\n❯ Choose:",
        "sub_info": "▤ Sub info\n\n◉ Name: {name}\n○ Devices: {devices}\n◎ Expires: {expires}\n○ Activated: {started}\n● Status: {status}\n○ Traffic: {traffic}",
        "sub_active": "Active", "sub_inactive": "Inactive", "sub_expired": "Expired",
        "btn_connect_vpn": "◆ Connect VPN", "btn_rename": "✎ Rename", "btn_delete": "✕ Delete",
        "btn_iphone": "▸ iPhone", "btn_android": "▸ Android", "btn_windows": "▸ Windows", "btn_macos": "▸ macOS",
        "btn_back_subs": "❮ Back",
        "rename_prompt": "✎ New name:",
        "rename_done": "✓ Renamed to «{name}».",
        "delete_confirm": "⚠ Delete subscription?",
        "delete_done": "✓ Deleted.",
        "vpn_title": "◆ VPN\n\n❯ Platform:",
        "android_choose": "◆ Android\n\n❯ App:",
        "happ_btn": "▸ Happ", "incy_btn": "▸ Incy",
        "no_active": "⚠ Not active.",
        "ref_title": "✦ Invite friends!\n\n{link}\n\n◉ {friends}\n◎ {bonus} ₽\n★ {level}",
        "lv1": "① Rookie", "lv2": "② Friend", "lv3": "③ Partner", "lv4": "④ Legend",
        "profile_title": "◉ Profile\n\n▸ {id}\n▸ {username}\n▸ {name}\n▸ {language}\n▸ {created}\n▸ {friends}\n▸ {bonus} ₽\n▸ {sub_status}",
        "no_username": "n/a",
        "vpn_help": "⚙ Issues?",
        "support_text": "✉ {support}\n◍ {site}",
        "proxy_title": "◇ Proxy",
        "proxy_connect": "◆ Connect",
        "proxy_hint": "▸ Try later.",
        "admin_title": "⛨ Admin",
        "admin_users": "◉ Users", "admin_stats": "▦ Stats", "admin_broadcast": "✉ Broadcast",
        "admin_subs": "▤ Subs", "admin_refs": "✦ Refs", "admin_conv": "◆ Conv",
        "admin_stats_text": "▦ Stats\n\n◉ {users}\n✦ {new_today}\n▤ {subs}\n◆ {refs}",
        "admin_users_text": "◉ Last {n}:\n\n{list}",
        "broadcast_prompt": "✉ Broadcast text:",
        "broadcast_done": "✓ Sent: {sent}, Failed: {failed}",
        "broadcast_cancel": "✕ Cancelled.",
        "not_admin": "⛔ Denied.",
        "antispam": "⏳ Too many requests.",
        "error": "⚠ Error.",
        "btn_tariffs": "▣ Tariffs",
        "btn_key_act": "✎ Activate key",
        "key_prompt": "✎ Enter key:",
        "key_not_found": "✕ Not found.",
        "key_used": "✕ Used.",
        "key_bad_type": "✕ Cannot.",
        "key_limit": "✕ Limit.",
        "key_ok": "✓ Activated!\n\n▸ {duration}\n▸ {days}\n▸ {name}\n▸ {folder}\n\n❯ «Connect» for link.",
        "key_ok_no_url": "✓ Activated, no link. {support}",
        "extra_details": "◇ {name}\n\n◎ Price: {price:.0f} ₽\n▸ Term: forever",
        "extra_pay_btn": "▦ {price:.0f} ₽",
        "extra_not_found": "⚠ Not found",
        "pay_success_key": "✓ Paid!\n\n▸ {key}\n▸ {duration}\n\n«Buy» → «Activate».",
        "pay_no_keys": "⚠ No keys. {support}",
        "pay_success_extra": "✓ Paid!\n\n▸ {name}\n{link_line}",
        "sub_link_line": "\n▸ {url}",
        "bonus_offer": "◎ {bal:.0f} ₽ bonus. Use?",
        "bonus_btn_use_all": "✓ Use {bal:.0f} ₽",
        "bonus_btn_use_partial": "✎ Partial",
        "bonus_btn_skip": "✕ Skip",
        "bonus_partial_prompt": "✎ Amount (1-{max:.0f} ₽):",
        "bonus_applied": "✓ Applied.\n\n▸ {price:.0f}\n▸ {bonus:.0f}\n▸ {to_pay:.0f}",
        "bonus_min_order": "⚠ Min {min:.0f} ₽.",
        "bonus_not_enough": "✕ Not enough.",
        "bonus_bad_amount": "✕ Bad.",
    },
    "tr": {
        "subscribe_required": "⊘ ProxyGem kanalına abone olun.",
        "subscribe_btn": "▸ Abone ol",
        "check_sub_btn": "✓ Kontrol",
        "not_subscribed": "✕ Abone değilsiniz!",
        "choose_language": "◍ Dil:",
        "language_saved": "✓ Kaydedildi!",
        "main_menu": "◆ Ana menü!\n\n▸ {howto}\n\n◍ {site}\n\n❯ Seçin:",
        "btn_buy": "▣ Satın al", "btn_my_subs": "◆ Bağlan", "btn_invite": "✦ Davet",
        "btn_profile": "◉ Profil", "btn_proxy": "◇ Proxy", "btn_support": "⚙ Destek",
        "btn_download": "⤓ İndir", "btn_back": "❮ Geri", "btn_admin": "⛨ Yönetici",
        "btn_change_lang": "◍ Dil", "btn_pay": "▦ Öde", "btn_site": "◍ Site",
        "btn_support_chat": "✉ Destek",
        "download_title": "⤓ İndir",
        "download_btn": "⤓ İndir",
        "tariffs_title": "▣ Tarifeler",
        "buy_menu_title": "▣ Mağaza",
        "t1_name": "① 1 ay", "t1_desc": "Hızlı", "t1_feat": "• Sınırsız", "t1_price": "259 ₽",
        "t3_name": "② 3 ay", "t3_desc": "En iyi", "t3_feat": "• Sınırsız", "t3_price": "659 ₽",
        "t6_name": "③ 6 ay", "t6_desc": "Yarım yıl", "t6_feat": "• Sınırsız", "t6_price": "1 190 ₽",
        "tariff_details": "▤ {name}\n\n{desc}\n\n{feat}\n\n◎ {price}",
        "pay_choose": "▦ Ödeme:",
        "pay_crypto": "◎ CryptoBot", "pay_stars": "☆ Stars", "pay_yookassa": "▦ YooKassa", "pay_platega": "▦ Platega",
        "pay_stub": "⚠ {provider} yok. {support}",
        "pay_created": "▦ Oluşturuldu. ❯:",
        "pay_btn_go": "▦ Ödemeye git",
        "pay_fail": "⚠ Hata.",
        "no_subs": "▤ Abonelik yok.",
        "subs_title": "▤ Abonelikler\n\n❯ Seçin:",
        "sub_info": "▤ Bilgi\n\n◉ {name}\n○ {devices}\n◎ {expires}\n○ {started}\n● {status}\n○ {traffic}",
        "sub_active": "Aktif", "sub_inactive": "Pasif", "sub_expired": "Süresi doldu",
        "btn_connect_vpn": "◆ VPN Bağlan", "btn_rename": "✎ Yeniden ad", "btn_delete": "✕ Sil",
        "btn_iphone": "▸ iPhone", "btn_android": "▸ Android", "btn_windows": "▸ Windows", "btn_macos": "▸ macOS",
        "btn_back_subs": "❮ Geri",
        "rename_prompt": "✎ Yeni ad:",
        "rename_done": "✓ «{name}».",
        "delete_confirm": "⚠ Silinsin mi?",
        "delete_done": "✓ Silindi.",
        "vpn_title": "◆ VPN\n\n❯ Platform:",
        "android_choose": "◆ Android\n\n❯ Uygulama:",
        "happ_btn": "▸ Happ", "incy_btn": "▸ Incy",
        "no_active": "⚠ Pasif.",
        "ref_title": "✦ Davet!\n\n{link}\n\n◉ {friends}\n◎ {bonus} ₽\n★ {level}",
        "lv1": "① Çaylak", "lv2": "② Arkadaş", "lv3": "③ Ortak", "lv4": "④ Efsane",
        "profile_title": "◉ Profil\n\n▸ {id}\n▸ {username}\n▸ {name}\n▸ {language}\n▸ {created}\n▸ {friends}\n▸ {bonus} ₽\n▸ {sub_status}",
        "no_username": "yok",
        "vpn_help": "⚙ Sorunlar?",
        "support_text": "✉ {support}\n◍ {site}",
        "proxy_title": "◇ Proxy",
        "proxy_connect": "◆ Bağlan",
        "proxy_hint": "▸ Sonra deneyin.",
        "admin_title": "⛨ Yönetici",
        "admin_users": "◉ Kullanıcılar", "admin_stats": "▦ İstatistik", "admin_broadcast": "✉ Yayın",
        "admin_subs": "▤ Abonelik", "admin_refs": "✦ Ref", "admin_conv": "◆ Dönüşüm",
        "admin_stats_text": "▦\n\n◉ {users}\n✦ {new_today}\n▤ {subs}\n◆ {refs}",
        "admin_users_text": "◉ {n}:\n\n{list}",
        "broadcast_prompt": "✉ Metin:",
        "broadcast_done": "✓ {sent}, ✕ {failed}",
        "broadcast_cancel": "✕ İptal.",
        "not_admin": "⛔ Yok.",
        "antispam": "⏳ Bekleyin.",
        "error": "⚠ Hata.",
        "btn_tariffs": "▣ Tarifeler",
        "btn_key_act": "✎ Anahtar",
        "key_prompt": "✎ Anahtar:",
        "key_not_found": "✕ Yok.",
        "key_used": "✕ Kullanılmış.",
        "key_bad_type": "✕ Olamaz.",
        "key_limit": "✕ Limit.",
        "key_ok": "✓ Etkinleştirildi!\n\n▸ {duration}\n▸ {days}\n▸ {name}\n▸ {folder}\n\n❯ «Bağlan» link.",
        "key_ok_no_url": "✓ Etkinleştirildi. {support}",
        "extra_details": "◇ {name}\n\n◎ Fiyat: {price:.0f} ₽\n▸ Süre: sonsuza kadar",
        "extra_pay_btn": "▦ {price:.0f} ₽",
        "extra_not_found": "⚠ Yok",
        "pay_success_key": "✓ Ödendi!\n\n▸ {key}\n▸ {duration}",
        "pay_no_keys": "⚠ {support}",
        "pay_success_extra": "✓ Ödendi!\n\n▸ {name}\n{link_line}",
        "sub_link_line": "\n▸ {url}",
        "bonus_offer": "◎ {bal:.0f} ₽?",
        "bonus_btn_use_all": "✓ {bal:.0f} ₽",
        "bonus_btn_use_partial": "✎ Kısmi",
        "bonus_btn_skip": "✕ Hayır",
        "bonus_partial_prompt": "✎ 1-{max:.0f} ₽:",
        "bonus_applied": "✓\n\n▸ {price:.0f}\n▸ {bonus:.0f}\n▸ {to_pay:.0f}",
        "bonus_min_order": "⚠ Min {min:.0f} ₽.",
        "bonus_not_enough": "✕ Yetersiz.",
        "bonus_bad_amount": "✕ Geçersiz.",
    },
}


def t(lang: str, key: str, **kw) -> str:
    lang = lang if lang in T else "ru"
    txt = T[lang].get(key) or T["ru"].get(key, key)
    try:
        return txt.format(**kw)
    except Exception:
        return txt


TARIFFS = {
    "1m": {"days": 30,  "price": 259.0,  "name": "t1_name", "desc": "t1_desc", "feat": "t1_feat", "price_key": "t1_price", "duration": "1_month"},
    "3m": {"days": 90,  "price": 659.0,  "name": "t3_name", "desc": "t3_desc", "feat": "t3_feat", "price_key": "t3_price", "duration": "3_month"},
    "6m": {"days": 180, "price": 1190.0, "name": "t6_name", "desc": "t6_desc", "feat": "t6_feat", "price_key": "t6_price", "duration": "6_month"},
}

# ============================================================
# HTTP CLIENT / WORKER
# ============================================================

async def http() -> ClientSession:
    global _http
    if _http is None or _http.closed:
        _http = ClientSession(timeout=ClientTimeout(total=30))
    return _http


async def worker_post(path: str, payload: dict) -> dict:
    h = await http()
    headers = {"Content-Type": "application/json"}
    if WORKER_TOKEN:
        headers["Authorization"] = f"Bearer {WORKER_TOKEN}"
    try:
        async with h.post(f"{WORKER_API}{path}", json=payload, headers=headers) as r:
            txt = await r.text()
            try:
                return {"ok": r.status < 400, "status": r.status, "data": json.loads(txt)}
            except Exception:
                return {"ok": r.status < 400, "status": r.status, "data": {"raw": txt}}
    except Exception as e:
        log.error("worker_post %s failed: %s", path, e)
        return {"ok": False, "status": 0, "data": {"error": str(e)}}


# ============================================================
# PLATEGA
# ============================================================

async def platega_create_payment(uid: int, amount: float, description: str, plan: str,
                                 bonus_used: float = 0.0) -> Optional[str]:
    order_id = f"{uid}-{plan}-{int(time.time())}"
    payload = {
        "action": "create_payment", "amount": amount, "currency": "RUB",
        "description": description, "order_id": order_id,
        "success_url": "https://t.me/proxy_gem777", "fail_url": "https://t.me/proxy_gem777",
        "metadata": {"user_id": uid, "plan": plan, "bonus_used": bonus_used},
    }
    res = await worker_post("/platega/payment", payload)
    if not res["ok"]:
        log.error("Platega failed: %s", res)
        return None
    data = res["data"] or {}
    inner = data.get("data") or data.get("result") or {}
    url = (data.get("url") or data.get("payment_url") or data.get("paymentUrl")
           or data.get("redirectUrl") or inner.get("url"))
    if not url:
        return None
    await db.create_payment(uid, plan, amount, "platega", order_id=order_id, bonus_used=bonus_used)
    return url


async def platega_check_payment(order_id: str) -> str:
    res = await worker_post("/platega/status", {"action": "check_payment", "order_id": order_id})
    if not res["ok"]:
        return "pending"
    data = res["data"] or {}
    return (data.get("status") or "pending").lower()


# ============================================================
# PREMIUM CODES
# ============================================================

async def fetch_premium_codes() -> List[dict]:
    res = await worker_post("/premium/mark", {"action": "read"})
    if res["ok"] and isinstance(res["data"], dict) and res["data"].get("codes"):
        return res["data"]["codes"]
    if PREMIUM_CODES_URL:
        try:
            h = await http()
            async with h.get(PREMIUM_CODES_URL) as r:
                if r.status == 200:
                    raw = await r.json()
                    if isinstance(raw, list):
                        return raw
                    if isinstance(raw, dict) and isinstance(raw.get("codes"), list):
                        return raw["codes"]
        except Exception:
            pass
    return []


async def pick_unused_code(duration: str) -> Optional[dict]:
    res = await worker_post("/premium/mark", {"action": "pick_unused", "duration": duration})
    if res["ok"] and isinstance(res["data"], dict) and res["data"].get("code"):
        return res["data"]["code"]
    codes = await fetch_premium_codes()
    for c in codes:
        if c.get("used") is True or c.get("gived") is True:
            continue
        if (c.get("type") or "").upper() == "PROXYGEM":
            continue
        if c.get("duration") != duration:
            continue
        if (c.get("used_count") or 0) >= (c.get("max_activations") or 1):
            continue
        return c
    return None


async def mark_code_gived(code_key: str) -> bool:
    res = await worker_post("/premium/mark", {"action": "mark_gived", "key": code_key})
    return res["ok"]


async def mark_code_used(code_key: str, device_id: Optional[str] = None) -> bool:
    res = await worker_post("/premium/mark", {"action": "mark_used", "key": code_key, "device_id": device_id})
    return res["ok"]


async def consume_premium_code(uid: int, plan_code: str) -> Optional[dict]:
    tf = TARIFFS.get(plan_code)
    if not tf:
        return None
    code = await pick_unused_code(tf["duration"])
    if not code:
        return None
    key = code.get("id") or code.get("key")
    if not key:
        return None
    if not await mark_code_gived(key):
        return None
    return code


# ============================================================
# GITHUB SUB FOLDERS
# ============================================================

ALPHABET = string.ascii_letters + string.digits


def random_suffix(n: int = 10) -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(n))


async def create_sub_folder_with_expire(kind: str, days: int) -> Optional[tuple]:
    if kind == "sub":
        folder, src = "sub", GITHUB_FILE_PATH
    else:
        cfg = EXTRA_SERVICES[kind]
        folder, src = cfg["folder"], cfg["src"]

    suffix = random_suffix(10)
    dest = f"{folder}/{suffix}.txt"

    now_ms = int(time.time() * 1000)
    expire_ms = now_ms + days * 24 * 60 * 60 * 1000
    d = datetime.utcfromtimestamp(expire_ms / 1000)
    announce = (f"✅ Подписка активна до {d.strftime('%d.%m.%Y')} | "
                f"Обязательно подпишитесь на @proxy_gem777 в Телеграме!")

    payload = {
        "action": "copy_with_expire",
        "owner": GITHUB_OWNER, "repo": GITHUB_REPO,
        "src_path": src, "dest_path": dest,
        "expire_ms": expire_ms, "announce_text": announce,
    }
    res = await worker_post("/github/copy_with_expire", payload)
    if not res["ok"]:
        log.error("copy_with_expire failed: %s", res)
        return None
    data = res["data"] or {}
    raw = data.get("raw_url") or f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/main/{dest}"
    return (folder, raw)


async def create_sub_folder(kind: str) -> Optional[str]:
    if kind == "sub":
        folder, src = "sub", GITHUB_FILE_PATH
    else:
        cfg = EXTRA_SERVICES[kind]
        folder, src = cfg["folder"], cfg["src"]
    suffix = random_suffix(10)
    dest = f"{folder}/{suffix}.txt"
    payload = {
        "action": "copy", "owner": GITHUB_OWNER, "repo": GITHUB_REPO,
        "src_path": src, "dest_path": dest, "commit_message": f"create {dest}",
    }
    res = await worker_post("/github/copy", payload)
    if not res["ok"]:
        return None
    data = res["data"] or {}
    return data.get("raw_url") or f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/main/{dest}"


async def sync_sub_folders():
    while not CONTROL["exit"]:
        try:
            await worker_post("/github/sync", {
                "action": "sync", "owner": GITHUB_OWNER, "repo": GITHUB_REPO,
                "folder": EXTRA_SERVICES["white"]["folder"],
                "source": EXTRA_SERVICES["white"]["src"],
            })
        except Exception as e:
            log.warning("sync_sub_folders: %s", e)
        await asyncio.sleep(300)


# ============================================================
# PAYMENTS POLLING
# ============================================================

async def on_payment_success(uid: int, plan: str, order_id: str):
    await db.mark_payment_success(order_id)

    if plan.startswith("extra_"):
        kind = plan.split("_", 1)[1]
        svc = EXTRA_SERVICES.get(kind, {})
        url = await create_sub_folder(kind)
        link_line = t("ru", "sub_link_line", url=url) if url else ""
        try:
            await bot.send_message(uid, t("ru", "pay_success_extra", name=svc.get("name", kind), link_line=link_line))
        except Exception:
            pass
        return

    code = await consume_premium_code(uid, plan)
    if not code:
        try:
            await bot.send_message(uid, t("ru", "pay_no_keys", support=SUPPORT_URL))
        except Exception:
            pass
        return

    key = code.get("id") or code.get("key")
    try:
        await bot.send_message(uid, t("ru", "pay_success_key", key=key, duration=code.get("duration")))
    except Exception:
        pass


async def poll_payments():
    while not CONTROL["exit"]:
        try:
            for row in await db.pending_payments():
                oid = row.get("order_id")
                if not oid:
                    continue
                st = await platega_check_payment(oid)
                if st in ("success", "paid", "completed"):
                    await on_payment_success(row["user_id"], row["plan"], oid)
        except Exception as e:
            log.warning("poll_payments: %s", e)
        await asyncio.sleep(30)


# ============================================================
# KEYBOARDS
# ============================================================

def kb_subscribe() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=T["ru"]["subscribe_btn"], url=CHANNEL_URL)
    b.button(text=T["ru"]["check_sub_btn"], callback_data="check_sub")
    b.adjust(1, 1)
    return b.as_markup()


def kb_language() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🇷🇺 Русский", callback_data="lang:ru")
    b.button(text="🇺🇸 English", callback_data="lang:en")
    b.button(text="🇹🇷 Türkçe",  callback_data="lang:tr")
    b.adjust(1)
    return b.as_markup()


def kb_main(lang: str, is_admin: bool = False) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=t(lang, "btn_my_subs"), callback_data="menu:subs")
    b.button(text=t(lang, "btn_buy"),     callback_data="menu:buy")
    b.button(text=t(lang, "btn_download"),callback_data="menu:download")
    b.button(text=t(lang, "btn_invite"),  callback_data="menu:ref")
    b.button(text=t(lang, "btn_support"), callback_data="menu:support")
    b.button(text=t(lang, "btn_proxy"),   callback_data="menu:proxy")
    b.button(text=t(lang, "btn_profile"), callback_data="menu:profile")
    if is_admin:
        b.button(text=t(lang, "btn_admin"), callback_data="admin:panel")
        b.adjust(2, 1, 1, 1, 1, 2)
    else:
        b.adjust(2, 1, 1, 1, 1, 1)
    return b.as_markup()


def kb_buy_menu(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=t(lang, "btn_tariffs"), callback_data="menu:tariffs")
    b.button(text="◇ Белые списки — 59 ₽", callback_data="extra:white")
    b.button(text=t(lang, "btn_key_act"),   callback_data="key:activate")
    b.button(text=t(lang, "btn_back"),      callback_data="back:main")
    b.adjust(1)
    return b.as_markup()


def kb_extra_details(lang: str, kind: str) -> InlineKeyboardMarkup:
    svc = EXTRA_SERVICES[kind]
    b = InlineKeyboardBuilder()
    b.button(text=t(lang, "extra_pay_btn", price=svc["price"]), callback_data=f"extra_pay:{kind}")
    b.button(text=t(lang, "btn_back"), callback_data="menu:buy")
    b.adjust(1)
    return b.as_markup()


def kb_download(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=t(lang, "download_btn"), url=DOWNLOAD_URL)
    b.button(text=t(lang, "btn_back"),     callback_data="back:main")
    b.adjust(1)
    return b.as_markup()


def kb_tariffs(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for code, tf in TARIFFS.items():
        b.button(text=f"{t(lang, tf['name'])} — {t(lang, tf['price_key'])}", callback_data=f"tariff:{code}")
    b.button(text=t(lang, "btn_back"), callback_data="menu:buy")
    b.adjust(1)
    return b.as_markup()


def kb_tariff_details(lang: str, code: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=t(lang, "btn_pay"),  callback_data=f"pay:{code}")
    b.button(text=t(lang, "btn_back"), callback_data="menu:tariffs")
    b.adjust(1)
    return b.as_markup()


def kb_payment_methods(lang: str, code: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=t(lang, "pay_platega"),  callback_data=f"pm:platega:{code}")
    b.button(text=t(lang, "pay_crypto"),   callback_data=f"pm:crypto:{code}")
    b.button(text=t(lang, "pay_stars"),    callback_data=f"pm:stars:{code}")
    b.button(text=t(lang, "pay_yookassa"), callback_data=f"pm:yookassa:{code}")
    b.button(text=t(lang, "btn_back"),     callback_data=f"tariff:{code}")
    b.adjust(1)
    return b.as_markup()


def kb_bonus_offer(lang: str, code: str, bal: float) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=t(lang, "bonus_btn_use_all", bal=bal), callback_data=f"bonus:all:{code}")
    b.button(text=t(lang, "bonus_btn_use_partial"),       callback_data=f"bonus:part:{code}")
    b.button(text=t(lang, "bonus_btn_skip"),              callback_data=f"bonus:skip:{code}")
    b.adjust(1)
    return b.as_markup()


def kb_support(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=t(lang, "btn_support_chat"), url=SUPPORT_URL)
    b.button(text=t(lang, "btn_site"),         url=SITE_URL)
    b.button(text=t(lang, "btn_back"),         callback_data="back:main")
    b.adjust(1)
    return b.as_markup()


def kb_proxy(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=t(lang, "proxy_connect"), url=PROXY_URL)
    b.button(text=t(lang, "btn_back"),      callback_data="back:main")
    b.adjust(1)
    return b.as_markup()


def kb_profile(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=t(lang, "btn_change_lang"), callback_data="profile:lang")
    b.button(text=t(lang, "btn_back"),        callback_data="back:main")
    b.adjust(1)
    return b.as_markup()


def kb_admin(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=t(lang, "admin_users"),     callback_data="admin:users")
    b.button(text=t(lang, "admin_stats"),     callback_data="admin:stats")
    b.button(text="✎ Управление подписками",  callback_data="admin:manage")
    b.button(text="✉ Сообщение пользователю", callback_data="admin:dm")
    b.button(text=t(lang, "admin_broadcast"), callback_data="admin:broadcast")
    b.button(text=t(lang, "admin_subs"),      callback_data="admin:subs")
    b.button(text=t(lang, "admin_refs"),      callback_data="admin:refs")
    b.button(text=t(lang, "admin_conv"),      callback_data="admin:conv")
    b.button(text=t(lang, "btn_back"),        callback_data="back:main")
    b.adjust(1)
    return b.as_markup()


def kb_back_only(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="back:main")
    ]])


def kb_user_subs_list(subs: List[dict], lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for s in subs:
        name = s.get("custom_name") or f"Key {s['id']}"
        icon = "●" if s["status"] == "active" else "○"
        b.button(text=f"{icon} {name}", callback_data=f"sub:open:{s['id']}")
    b.button(text=t(lang, "btn_back"), callback_data="back:main")
    b.adjust(1)
    return b.as_markup()


def kb_sub_card(lang: str, sub_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=t(lang, "btn_connect_vpn"), callback_data=f"sub:vpn:{sub_id}")
    b.button(text=t(lang, "btn_rename"),      callback_data=f"sub:rename:{sub_id}")
    b.button(text=t(lang, "btn_delete"),      callback_data=f"sub:del:{sub_id}")
    b.button(text=t(lang, "btn_back_subs"),   callback_data="menu:subs")
    b.adjust(1)
    return b.as_markup()


def kb_vpn_platform(lang: str, sub_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=t(lang, "btn_iphone"),  callback_data=f"sub:dev:iphone:{sub_id}")
    b.button(text=t(lang, "btn_android"), callback_data=f"sub:dev:android:{sub_id}")
    b.button(text=t(lang, "btn_windows"), callback_data=f"sub:dev:windows:{sub_id}")
    b.button(text=t(lang, "btn_macos"),   callback_data=f"sub:dev:macos:{sub_id}")
    b.button(text=t(lang, "btn_back"),    callback_data=f"sub:open:{sub_id}")
    b.adjust(1)
    return b.as_markup()


def kb_android_apps(lang: str, sub_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=t(lang, "happ_btn"), callback_data=f"sub:app:happ:{sub_id}")
    b.button(text=t(lang, "incy_btn"), callback_data=f"sub:app:incy:{sub_id}")
    b.button(text=t(lang, "btn_back"), callback_data=f"sub:vpn:{sub_id}")
    b.adjust(1)
    return b.as_markup()


def kb_delete_confirm(lang: str, sub_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✓ Да, удалить", callback_data=f"sub:del_yes:{sub_id}")
    b.button(text="✕ Отмена",     callback_data=f"sub:open:{sub_id}")
    b.adjust(1)
    return b.as_markup()


def kb_admin_manage(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="▸ Выдать подписку",  callback_data="admin:give")
    b.button(text="▸ Забрать подписку", callback_data="admin:take")
    b.button(text=t(lang, "btn_back"),  callback_data="admin:panel")
    b.adjust(1)
    return b.as_markup()


def kb_admin_give_plans() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="① 1 месяц (30 дней)",   callback_data="admin:give_plan:1m")
    b.button(text="② 3 месяца (90 дней)",  callback_data="admin:give_plan:3m")
    b.button(text="③ 6 месяцев (180 дней)",callback_data="admin:give_plan:6m")
    b.button(text="④ Навсегда (3650 дней)",callback_data="admin:give_plan:forever")
    b.button(text="❮ Отмена",              callback_data="admin:manage")
    b.adjust(1)
    return b.as_markup()


def kb_admin_take_list(subs: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for s in subs:
        name = s.get("custom_name") or f"Key {s['id']}"
        b.button(text=f"✕ {name} (sub #{s['id']})",
                 callback_data=f"admin:take_pick:{s['id']}")
    b.button(text="❮ Отмена", callback_data="admin:manage")
    b.adjust(1)
    return b.as_markup()


def kb_admin_take_confirm(sub_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✓ Да, забрать", callback_data=f"admin:take_yes:{sub_id}")
    b.button(text="✕ Отмена",      callback_data="admin:manage")
    b.adjust(1)
    return b.as_markup()


def kb_admin_broadcast_mode() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="▸ Просто текст",          callback_data="admin:bc_text")
    b.button(text="▸ Текст + inline-кнопки", callback_data="admin:bc_textbtns")
    b.button(text="❮ Назад",                 callback_data="admin:panel")
    b.adjust(1)
    return b.as_markup()


# ============================================================
# STATES
# ============================================================

class BroadcastSG(StatesGroup):
    waiting_text = State()
    waiting_buttons = State()


class KeySG(StatesGroup):
    waiting = State()


class BonusSG(StatesGroup):
    waiting_amount = State()


class RenameSG(StatesGroup):
    waiting_name = State()


class AdminGiveSG(StatesGroup):
    waiting_user_id = State()
    waiting_plan = State()


class AdminTakeSG(StatesGroup):
    waiting_user_id = State()


class AdminDMSG(StatesGroup):
    waiting_user_id = State()
    waiting_text = State()


# ============================================================
# MIDDLEWARES
# ============================================================

class AntiSpamMW:
    def __init__(self):
        self._last: Dict[int, float] = {}

    async def __call__(self, handler, event, data):
        uid = None
        if isinstance(event, Message) and event.from_user:
            uid = event.from_user.id
        elif isinstance(event, CallbackQuery) and event.from_user:
            uid = event.from_user.id
        if uid:
            now = time.time()
            if now - self._last.get(uid, 0) < 0.5:
                if isinstance(event, CallbackQuery):
                    try:
                        await event.answer(t("ru", "antispam"), show_alert=False)
                    except Exception:
                        pass
                return
            self._last[uid] = now
        return await handler(event, data)


class SubscriptionMW:
    def __init__(self, bot_: Bot):
        self.bot = bot_

    async def is_subscribed(self, uid: int) -> bool:
        try:
            member = await self.bot.get_chat_member(f"@{CHANNEL_USERNAME}", uid)
            return member.status in ("creator", "administrator", "member", "restricted")
        except Exception as e:
            log.warning("is_subscribed check failed for %s: %s", uid, e)
            return True

    async def __call__(self, handler, event, data):
        if isinstance(event, Message) and event.text and event.text.startswith("/start"):
            return await handler(event, data)
        if isinstance(event, CallbackQuery) and (event.data or "").startswith(("check_sub", "lang:")):
            return await handler(event, data)

        uid = None
        if isinstance(event, Message) and event.from_user:
            uid = event.from_user.id
        elif isinstance(event, CallbackQuery) and event.from_user:
            uid = event.from_user.id

        if uid and uid in ADMIN_IDS:
            return await handler(event, data)

        if uid and not await self.is_subscribed(uid):
            text = t("ru", "subscribe_required")
            if isinstance(event, Message):
                await event.answer(text, reply_markup=kb_subscribe())
            else:
                try:
                    await event.message.edit_text(text, reply_markup=kb_subscribe())
                except TelegramBadRequest:
                    await event.message.answer(text, reply_markup=kb_subscribe())
            return
        return await handler(event, data)


# ============================================================
# UNIVERSAL EDIT
# ============================================================

async def show_screen(target: CallbackQuery, caption: str,
                      reply_markup: InlineKeyboardMarkup,
                      image_path: Optional[str] = None):
    msg = target.message
    has_photo = bool(msg.photo)
    want_photo = bool(image_path and os.path.exists(image_path))

    if has_photo and want_photo:
        try:
            media = InputMediaPhoto(media=FSInputFile(image_path), caption=caption)
            await msg.edit_media(media=media, reply_markup=reply_markup)
            return
        except TelegramBadRequest as e:
            if "message is not modified" in str(e).lower():
                try:
                    await msg.edit_reply_markup(reply_markup=reply_markup)
                except Exception:
                    pass
                return

    if has_photo and not want_photo:
        try:
            await msg.edit_caption(caption=caption, reply_markup=reply_markup)
            return
        except TelegramBadRequest:
            pass

    if not has_photo and not want_photo:
        try:
            await msg.edit_text(caption, reply_markup=reply_markup, disable_web_page_preview=True)
            return
        except TelegramBadRequest as e:
            if "message is not modified" in str(e).lower():
                try:
                    await msg.edit_reply_markup(reply_markup=reply_markup)
                except Exception:
                    pass
                return

    if not has_photo and want_photo:
        try:
            await msg.delete()
        except Exception:
            pass
        try:
            await msg.answer_photo(photo=FSInputFile(image_path), caption=caption,
                                   reply_markup=reply_markup)
            return
        except Exception:
            pass

    try:
        await msg.answer(caption, reply_markup=reply_markup, disable_web_page_preview=True)
    except Exception:
        pass


async def show_main_menu(target, uid: int, edit: bool = False):
    lang = await db.get_language(uid)
    is_admin = uid in ADMIN_IDS
    text = t(lang, "main_menu", howto=HOWTO_URL, site=SITE_URL)
    kb = kb_main(lang, is_admin)

    if isinstance(target, CallbackQuery):
        await show_screen(target, text, kb, IMG_MAIN)
    else:
        try:
            if os.path.exists(IMG_MAIN):
                await target.answer_photo(photo=FSInputFile(IMG_MAIN), caption=text, reply_markup=kb)
            else:
                await target.answer(text, reply_markup=kb, disable_web_page_preview=True)
        except Exception:
            pass


# ============================================================
# ROUTER
# ============================================================

router = Router()


@router.message(CommandStart(deep_link=True))
async def cmd_start_deeplink(msg: Message, command: CommandObject, bot: Bot):
    await handle_start(msg, bot, command.args)


@router.message(CommandStart())
async def cmd_start(msg: Message, bot: Bot):
    await handle_start(msg, bot, None)


async def handle_start(msg: Message, bot: Bot, payload: Optional[str]):
    u = msg.from_user
    is_new = await db.get_user(u.id) is None
    await db.upsert_user(u.id, u.username or "", u.first_name or "", u.last_name or "")

    if payload and payload.isdigit() and is_new:
        ref_id = int(payload)
        if ref_id != u.id and await db.add_referral(ref_id, u.id):
            try:
                await bot.send_message(
                    ref_id,
                    f"✦ По вашей ссылке зарегистрировался новый пользователь!\n"
                    f"◎ Вам начислено +{REF_BONUS_PER_FRIEND:.0f} ₽ бонусом."
                )
            except Exception:
                pass

    sub_mw = SubscriptionMW(bot)
    if not await sub_mw.is_subscribed(u.id) and u.id not in ADMIN_IDS:
        await msg.answer(t("ru", "subscribe_required"), reply_markup=kb_subscribe())
        return

    user = await db.get_user(u.id)
    if not user or not user.get("language"):
        await msg.answer(t("ru", "choose_language"), kb_language())
        return

    await show_main_menu(msg, u.id)


@router.callback_query(F.data == "check_sub")
async def cb_check_sub(cb: CallbackQuery, bot: Bot):
    sub_mw = SubscriptionMW(bot)
    if await sub_mw.is_subscribed(cb.from_user.id):
        await cb.answer(t("ru", "language_saved"), show_alert=False)
        user = await db.get_user(cb.from_user.id)
        if not user or not user.get("language"):
            await show_screen(cb, t("ru", "choose_language"), kb_language())
        else:
            await show_main_menu(cb, cb.from_user.id)
    else:
        await cb.answer(t("ru", "not_subscribed"), show_alert=True)


@router.callback_query(F.data.startswith("lang:"))
async def cb_lang(cb: CallbackQuery):
    lang = cb.data.split(":")[1]
    await db.set_language(cb.from_user.id, lang)
    await cb.answer(t(lang, "language_saved"))
    await show_main_menu(cb, cb.from_user.id)


@router.callback_query(F.data == "back:main")
async def cb_back_main(cb: CallbackQuery):
    await show_main_menu(cb, cb.from_user.id)


@router.callback_query(F.data == "menu:buy")
async def cb_buy(cb: CallbackQuery):
    lang = await db.get_language(cb.from_user.id)
    await show_screen(cb, t(lang, "buy_menu_title"), kb_buy_menu(lang))


@router.callback_query(F.data == "menu:tariffs")
async def cb_tariffs(cb: CallbackQuery):
    lang = await db.get_language(cb.from_user.id)
    await show_screen(cb, t(lang, "tariffs_title"), kb_tariffs(lang))


@router.callback_query(F.data == "menu:download")
async def cb_download(cb: CallbackQuery):
    lang = await db.get_language(cb.from_user.id)
    await show_screen(cb, t(lang, "download_title"), kb_download(lang))


@router.callback_query(F.data.startswith("tariff:"))
async def cb_tariff(cb: CallbackQuery):
    code = cb.data.split(":")[1]
    tf = TARIFFS.get(code)
    if not tf:
        await cb.answer(t("ru", "error"), show_alert=True)
        return
    lang = await db.get_language(cb.from_user.id)
    text = t(lang, "tariff_details",
             name=t(lang, tf["name"]), desc=t(lang, tf["desc"]),
             feat=t(lang, tf["feat"]), price=t(lang, tf["price_key"]))
    await show_screen(cb, text, kb_tariff_details(lang, code))


@router.callback_query(F.data.startswith("pay:"))
async def cb_pay(cb: CallbackQuery):
    code = cb.data.split(":")[1]
    lang = await db.get_language(cb.from_user.id)
    await show_screen(cb, t(lang, "pay_choose"), kb_payment_methods(lang, code))


@router.callback_query(F.data.startswith("pm:"))
async def cb_payment_method(cb: CallbackQuery):
    _, provider, code = cb.data.split(":")
    lang = await db.get_language(cb.from_user.id)
    tf = TARIFFS.get(code)
    if not tf:
        await cb.answer(t(lang, "error"), show_alert=True)
        return

    if provider != "platega":
        await db.create_payment(cb.from_user.id, code, tf["price"], provider)
        provider_name = {"crypto": "CryptoBot", "stars": "Telegram Stars", "yookassa": "ЮKassa"}.get(provider, provider)
        await show_screen(cb, t(lang, "pay_stub", provider=provider_name, support=SUPPORT_URL),
                          kb_tariff_details(lang, code))
        return

    price = float(tf["price"])
    bal = await db.get_balance(cb.from_user.id)
    if bal >= 1.0 and price >= BONUS_MIN_ORDER:
        await show_screen(cb, t(lang, "bonus_offer", bal=bal),
                          kb_bonus_offer(lang, code, bal))
        return

    await _start_platega_payment(cb, code, bonus=0.0)


async def _start_platega_payment(cb: CallbackQuery, code: str, bonus: float = 0.0):
    lang = await db.get_language(cb.from_user.id)
    tf = TARIFFS.get(code)
    if not tf:
        await cb.answer(t(lang, "error"), show_alert=True)
        return

    price = float(tf["price"])
    bonus = min(bonus, price)
    to_pay = max(0.0, price - bonus)

    if bonus > 0 and not await db.spend_bonus(cb.from_user.id, bonus, reason=f"order {code}"):
        await cb.answer(t(lang, "bonus_not_enough"), show_alert=True)
        return

    url = await platega_create_payment(cb.from_user.id, to_pay, f"ProxyGem {code}", code, bonus_used=bonus)
    if not url:
        if bonus > 0:
            await db.add_bonus(cb.from_user.id, bonus, reason="rollback")
        await cb.answer(t(lang, "pay_fail"), show_alert=True)
        return

    header = t(lang, "bonus_applied", price=price, bonus=bonus, to_pay=to_pay) if bonus > 0 \
             else t(lang, "pay_created")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "pay_btn_go"), url=url)],
        [InlineKeyboardButton(text=t(lang, "btn_back"), callback_data=f"tariff:{code}")],
    ])
    await show_screen(cb, header + "\n\n" + t(lang, "pay_created"), kb)


@router.callback_query(F.data.startswith("bonus:"))
async def cb_bonus(cb: CallbackQuery, state: FSMContext):
    _, action, code = cb.data.split(":")
    lang = await db.get_language(cb.from_user.id)
    tf = TARIFFS.get(code)
    if not tf:
        await cb.answer(t(lang, "error"), show_alert=True)
        return

    price = float(tf["price"])
    bal = await db.get_balance(cb.from_user.id)

    if action == "all":
        await _start_platega_payment(cb, code, bonus=min(bal, price))
    elif action == "skip":
        await _start_platega_payment(cb, code, bonus=0.0)
    elif action == "part":
        await state.set_state(BonusSG.waiting_amount)
        await state.update_data(code=code)
        await show_screen(cb, t(lang, "bonus_partial_prompt", max=min(bal, price), price=price),
                          kb_back_only(lang))


@router.message(BonusSG.waiting_amount)
async def do_bonus_partial(msg: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    code = data.get("code")
    await state.clear()
    lang = await db.get_language(msg.from_user.id)
    tf = TARIFFS.get(code)
    if not tf:
        await msg.answer(t(lang, "error"))
        await show_main_menu(msg, msg.from_user.id)
        return
    try:
        amount = float((msg.text or "").replace(",", ".").strip())
    except Exception:
        await msg.answer(t(lang, "bonus_bad_amount"))
        await show_main_menu(msg, msg.from_user.id)
        return

    price = float(tf["price"])
    bal = await db.get_balance(msg.from_user.id)
    amount = min(max(amount, 1.0), min(bal, price))

    if amount < 1.0:
        await msg.answer(t(lang, "bonus_bad_amount"))
        await show_main_menu(msg, msg.from_user.id)
        return

    to_pay = max(0.0, price - amount)
    if amount > 0 and not await db.spend_bonus(msg.from_user.id, amount, reason=f"order {code}"):
        await msg.answer(t(lang, "bonus_not_enough"))
        await show_main_menu(msg, msg.from_user.id)
        return

    url = await platega_create_payment(msg.from_user.id, to_pay, f"ProxyGem {code}", code, bonus_used=amount)
    if not url:
        if amount > 0:
            await db.add_bonus(msg.from_user.id, amount, reason="rollback")
        await msg.answer(t(lang, "pay_fail"))
        await show_main_menu(msg, msg.from_user.id)
        return

    header = t(lang, "bonus_applied", price=price, bonus=amount, to_pay=to_pay)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "pay_btn_go"), url=url)],
        [InlineKeyboardButton(text=t(lang, "btn_back"), callback_data=f"tariff:{code}")],
    ])
    await msg.answer(header + "\n\n" + t(lang, "pay_created"), reply_markup=kb)


@router.callback_query(F.data.startswith("extra:"))
async def cb_extra(cb: CallbackQuery):
    kind = cb.data.split(":")[1]
    svc = EXTRA_SERVICES.get(kind)
    if not svc:
        await cb.answer(t("ru", "extra_not_found"), show_alert=True)
        return
    lang = await db.get_language(cb.from_user.id)
    text = t(lang, "extra_details", name=svc["name"], folder=svc["folder"],
             src=svc["src"], price=svc["price"])
    await show_screen(cb, text, kb_extra_details(lang, kind))


@router.callback_query(F.data.startswith("extra_pay:"))
async def cb_extra_pay(cb: CallbackQuery):
    kind = cb.data.split(":")[1]
    svc = EXTRA_SERVICES.get(kind)
    if not svc:
        await cb.answer(t("ru", "extra_not_found"), show_alert=True)
        return
    lang = await db.get_language(cb.from_user.id)
    url = await platega_create_payment(cb.from_user.id, svc["price"],
                                       f"ProxyGem {svc['name']}", f"extra_{kind}")
    if not url:
        await cb.answer(t(lang, "pay_fail"), show_alert=True)
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "pay_btn_go"), url=url)],
        [InlineKeyboardButton(text=t(lang, "btn_back"), callback_data=f"extra:{kind}")],
    ])
    await show_screen(cb, t(lang, "pay_created"), kb)


@router.callback_query(F.data == "key:activate")
async def cb_key_activate(cb: CallbackQuery, state: FSMContext):
    lang = await db.get_language(cb.from_user.id)
    await state.set_state(KeySG.waiting)
    await show_screen(cb, t(lang, "key_prompt"), kb_back_only(lang))


@router.message(KeySG.waiting)
async def do_activate_key(msg: Message, state: FSMContext, bot: Bot):
    await state.clear()
    lang = await db.get_language(msg.from_user.id)
    key = (msg.text or "").strip()

    codes = await fetch_premium_codes()
    found = None
    for c in codes:
        if (c.get("id") or c.get("key")) == key:
            found = c
            break

    if not found:
        await msg.answer(t(lang, "key_not_found"))
        await show_main_menu(msg, msg.from_user.id)
        return
    if found.get("used") is True and (found.get("used_count") or 0) >= (found.get("max_activations") or 1):
        await msg.answer(t(lang, "key_used"))
        await show_main_menu(msg, msg.from_user.id)
        return
    if (found.get("type") or "").upper() == "PROXYGEM":
        await msg.answer(t(lang, "key_bad_type"))
        await show_main_menu(msg, msg.from_user.id)
        return

    duration = found.get("duration", "1_month")
    days_map = {"1_month": 30, "3_month": 90, "6_month": 180, "forever": 3650}
    days = days_map.get(duration, 30)

    if not await mark_code_used(key, device_id=f"DEV-{msg.from_user.id}"):
        await msg.answer(t(lang, "key_limit"))
        await show_main_menu(msg, msg.from_user.id)
        return

    result = await create_sub_folder_with_expire("sub", days)
    if not result:
        await msg.answer(t(lang, "key_ok_no_url", support=SUPPORT_URL))
        await show_main_menu(msg, msg.from_user.id)
        return
    folder, raw_url = result

    existing = await db.user_subscriptions(msg.from_user.id)
    custom_name = f"Key {len(existing) + 1}"

    await db.create_subscription(msg.from_user.id, duration, days,
                                 folder=folder, raw_url=raw_url, custom_name=custom_name)
    await msg.answer(t(lang, "key_ok", duration=duration, days=days, name=custom_name, folder=folder))
    await show_main_menu(msg, msg.from_user.id)


@router.callback_query(F.data == "menu:subs")
async def cb_subs(cb: CallbackQuery):
    lang = await db.get_language(cb.from_user.id)
    subs = await db.user_subscriptions(cb.from_user.id)
    if not subs:
        await show_screen(cb, t(lang, "no_subs"), kb_back_only(lang), IMG_PREMIUM)
        return
    await show_screen(cb, t(lang, "subs_title"), kb_user_subs_list(subs, lang), IMG_PREMIUM)


@router.callback_query(F.data.startswith("sub:open:"))
async def cb_sub_open(cb: CallbackQuery):
    sub_id = int(cb.data.split(":")[2])
    lang = await db.get_language(cb.from_user.id)
    sub = await db.get_subscription(sub_id, cb.from_user.id)
    if not sub:
        await cb.answer("⚠ Подписка не найдена", show_alert=True)
        return

    try:
        expires = datetime.fromisoformat(sub["expires_at"])
        started = datetime.fromisoformat(sub["started_at"])
    except Exception:
        expires, started = datetime.utcnow(), datetime.utcnow()

    if expires > datetime.utcnow() and sub["status"] == "active":
        status_text = t(lang, "sub_active")
    elif sub["status"] == "expired" or expires <= datetime.utcnow():
        status_text = t(lang, "sub_expired")
    else:
        status_text = t(lang, "sub_inactive")

    name = sub.get("custom_name") or f"Key {sub['id']}"
    text = t(lang, "sub_info",
             name=name,
             devices=sub.get("device_limit") or "Безлимит",
             expires=expires.strftime("%Y-%m-%d"),
             started=started.strftime("%Y-%m-%d"),
             status=status_text,
             traffic=sub.get("traffic_limit") or "Безлимит")
    await show_screen(cb, text, kb_sub_card(lang, sub_id), IMG_PREMIUM)


@router.callback_query(F.data.startswith("sub:rename:"))
async def cb_sub_rename(cb: CallbackQuery, state: FSMContext):
    sub_id = int(cb.data.split(":")[2])
    sub = await db.get_subscription(sub_id, cb.from_user.id)
    if not sub:
        await cb.answer("⚠", show_alert=True)
        return
    lang = await db.get_language(cb.from_user.id)
    await state.set_state(RenameSG.waiting_name)
    await state.update_data(sub_id=sub_id)
    await show_screen(cb, t(lang, "rename_prompt"), kb_back_only(lang))


@router.message(RenameSG.waiting_name)
async def do_rename_sub(msg: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    sub_id = data.get("sub_id")
    await state.clear()
    lang = await db.get_language(msg.from_user.id)
    new_name = (msg.text or "").strip()[:32]
    if not new_name:
        await msg.answer("✕ Название не может быть пустым.")
        await show_main_menu(msg, msg.from_user.id)
        return
    await db.rename_subscription(sub_id, msg.from_user.id, new_name)
    await msg.answer(t(lang, "rename_done", name=new_name))
    await show_main_menu(msg, msg.from_user.id)


@router.callback_query(F.data.startswith("sub:del:"))
async def cb_sub_del(cb: CallbackQuery):
    if cb.data.startswith("sub:del_yes:"):
        return
    sub_id = int(cb.data.split(":")[2])
    sub = await db.get_subscription(sub_id, cb.from_user.id)
    if not sub:
        await cb.answer("⚠", show_alert=True)
        return
    lang = await db.get_language(cb.from_user.id)
    await show_screen(cb, t(lang, "delete_confirm"), kb_delete_confirm(lang, sub_id), IMG_PREMIUM)


@router.callback_query(F.data.startswith("sub:del_yes:"))
async def cb_sub_del_yes(cb: CallbackQuery):
    sub_id = int(cb.data.split(":")[2])
    lang = await db.get_language(cb.from_user.id)
    sub = await db.get_subscription(sub_id, cb.from_user.id)
    if not sub:
        await cb.answer("⚠", show_alert=True)
        return
    await db.delete_subscription(sub_id, cb.from_user.id)
    await cb.answer(t(lang, "delete_done"), show_alert=False)
    await cb_subs(cb)


@router.callback_query(F.data.startswith("sub:vpn:"))
async def cb_sub_vpn(cb: CallbackQuery):
    sub_id = int(cb.data.split(":")[2])
    lang = await db.get_language(cb.from_user.id)
    sub = await db.get_subscription(sub_id, cb.from_user.id)
    if not sub:
        await cb.answer("⚠", show_alert=True)
        return
    try:
        expires = datetime.fromisoformat(sub["expires_at"])
        active = expires > datetime.utcnow() and sub["status"] == "active"
    except Exception:
        active = False

    if not active:
        await cb.answer(t(lang, "no_active"), show_alert=True)
        return

    await show_screen(cb, t(lang, "vpn_title"), kb_vpn_platform(lang, sub_id))


@router.callback_query(F.data.startswith("sub:dev:iphone:"))
async def cb_sub_dev_iphone(cb: CallbackQuery):
    sub_id = int(cb.data.split(":")[3])
    sub = await db.get_subscription(sub_id, cb.from_user.id)
    if not sub:
        await cb.answer("⚠", show_alert=True)
        return
    deeplink = f"incy://add/{sub['raw_url']}"
    text = (
        "Выполните несколько простых шагов для подключения:\n\n"
        "1️⃣ ✅ Установите приложение 👉 INCY\n"
        f"{LINKS['incy_ios']}\n\n"
        "2️⃣ 🔗 Пройдите по ссылке:\n"
        f"({deeplink})\n\n"
        f"Подключиться — {deeplink}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◆ Подключиться", url=deeplink)],
        [InlineKeyboardButton(text="❮ Назад", callback_data=f"sub:vpn:{sub_id}")],
    ])
    await show_screen(cb, text, kb, IMG_PREMIUM)


@router.callback_query(F.data.startswith("sub:dev:macos:"))
async def cb_sub_dev_macos(cb: CallbackQuery):
    sub_id = int(cb.data.split(":")[3])
    sub = await db.get_subscription(sub_id, cb.from_user.id)
    if not sub:
        await cb.answer("⚠", show_alert=True)
        return
    deeplink = f"incy://add/{sub['raw_url']}"
    text = (
        "Выполните несколько простых шагов для подключения:\n\n"
        "1️⃣ ✅ Установите приложение 👉 INCY\n"
        f"{LINKS['incy_ios']}\n\n"
        "2️⃣ 🔗 Пройдите по ссылке:\n"
        f"({deeplink})\n\n"
        f"Подключиться — {deeplink}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◆ Подключиться", url=deeplink)],
        [InlineKeyboardButton(text="❮ Назад", callback_data=f"sub:vpn:{sub_id}")],
    ])
    await show_screen(cb, text, kb, IMG_PREMIUM)


@router.callback_query(F.data.startswith("sub:dev:android:"))
async def cb_sub_dev_android(cb: CallbackQuery):
    sub_id = int(cb.data.split(":")[3])
    lang = await db.get_language(cb.from_user.id)
    sub = await db.get_subscription(sub_id, cb.from_user.id)
    if not sub:
        await cb.answer("⚠", show_alert=True)
        return
    await show_screen(cb, t(lang, "android_choose"), kb_android_apps(lang, sub_id), IMG_PREMIUM)


@router.callback_query(F.data.startswith("sub:app:happ:"))
async def cb_sub_app_happ(cb: CallbackQuery):
    sub_id = int(cb.data.split(":")[3])
    sub = await db.get_subscription(sub_id, cb.from_user.id)
    if not sub:
        await cb.answer("⚠", show_alert=True)
        return
    deeplink = f"happ://add/{sub['raw_url']}"
    text = (
        "Выполните несколько простых шагов для подключения:\n\n"
        "1️⃣ ✅ Установите приложение 👉 HAPP\n"
        f"{LINKS['happ_android']}\n\n"
        "2️⃣ 🔗 Пройдите по ссылке:\n"
        f"({deeplink})\n\n"
        f"Подключиться — {deeplink}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◆ Подключиться", url=deeplink)],
        [InlineKeyboardButton(text="❮ Назад", callback_data=f"sub:dev:android:{sub_id}")],
    ])
    await show_screen(cb, text, kb, IMG_PREMIUM)


@router.callback_query(F.data.startswith("sub:app:incy:"))
async def cb_sub_app_incy(cb: CallbackQuery):
    sub_id = int(cb.data.split(":")[3])
    sub = await db.get_subscription(sub_id, cb.from_user.id)
    if not sub:
        await cb.answer("⚠", show_alert=True)
        return
    deeplink = f"incy://add/{sub['raw_url']}"
    text = (
        "Выполните несколько простых шагов для подключения:\n\n"
        "1️⃣ ✅ Установите приложение 👉 INCY\n"
        f"{LINKS['incy_android']}\n\n"
        "2️⃣ 🔗 Пройдите по ссылке:\n"
        f"({deeplink})\n\n"
        f"Подключиться — {deeplink}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◆ Подключиться", url=deeplink)],
        [InlineKeyboardButton(text="❮ Назад", callback_data=f"sub:dev:android:{sub_id}")],
    ])
    await show_screen(cb, text, kb, IMG_PREMIUM)


@router.callback_query(F.data.startswith("sub:dev:windows:"))
async def cb_sub_dev_windows(cb: CallbackQuery):
    sub_id = int(cb.data.split(":")[3])
    sub = await db.get_subscription(sub_id, cb.from_user.id)
    if not sub:
        await cb.answer("⚠", show_alert=True)
        return
    deeplink = f"happ://add/{sub['raw_url']}"
    text = (
        "Выполните несколько простых шагов для подключения:\n\n"
        "1️⃣ ✅ Установите приложение 👉 Happ\n"
        f"{LINKS['happ_windows']}\n\n"
        "2️⃣ 🔗 Пройдите по ссылке:\n"
        f"({deeplink})\n\n"
        f"Подключиться — {deeplink}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◆ Подключиться", url=deeplink)],
        [InlineKeyboardButton(text="❮ Назад", callback_data=f"sub:vpn:{sub_id}")],
    ])
    await show_screen(cb, text, kb, IMG_PREMIUM)


@router.callback_query(F.data == "menu:ref")
async def cb_ref(cb: CallbackQuery, bot: Bot):
    lang = await db.get_language(cb.from_user.id)
    uid = cb.from_user.id
    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start={uid}"
    friends = await db.ref_count(uid)
    bonus = await db.get_balance(uid)
    if friends >= 100:
        level = t(lang, "lv4")
    elif friends >= 30:
        level = t(lang, "lv3")
    elif friends >= 10:
        level = t(lang, "lv2")
    else:
        level = t(lang, "lv1")
    text = t(lang, "ref_title", link=link, friends=friends, bonus=f"{bonus:.0f}", level=level)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✦ Поделиться", url=f"https://t.me/share/url?url={link}")],
        [InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="back:main")],
    ])
    await show_screen(cb, text, kb)


@router.callback_query(F.data == "menu:profile")
async def cb_profile(cb: CallbackQuery):
    lang = await db.get_language(cb.from_user.id)
    u = await db.get_user(cb.from_user.id) or {}
    sub = await db.active_subscription(cb.from_user.id)
    friends = await db.ref_count(cb.from_user.id)
    bonus = await db.get_balance(cb.from_user.id)
    username = f"@{u.get('username')}" if u.get("username") else t(lang, "no_username")
    name = (u.get("first_name") or "") + (" " + u["last_name"] if u.get("last_name") else "")
    sub_status = t(lang, "sub_active") if sub else t(lang, "sub_inactive")
    text = t(lang, "profile_title",
             id=u.get("id"), username=username, name=name or "—",
             language=u.get("language", lang),
             created=(u.get("created_at") or "")[:10],
             friends=friends, bonus=f"{bonus:.0f}", sub_status=sub_status)
    await show_screen(cb, text, kb_profile(lang))


@router.callback_query(F.data == "profile:lang")
async def cb_profile_lang(cb: CallbackQuery):
    await show_screen(cb, t("ru", "choose_language"), kb_language())


@router.callback_query(F.data == "menu:support")
async def cb_support(cb: CallbackQuery):
    lang = await db.get_language(cb.from_user.id)
    text = t(lang, "vpn_help") + "\n\n" + t(lang, "support_text", support=SUPPORT_URL, site=SITE_URL)
    await show_screen(cb, text, kb_support(lang))


@router.callback_query(F.data == "menu:proxy")
async def cb_proxy(cb: CallbackQuery):
    lang = await db.get_language(cb.from_user.id)
    text = t(lang, "proxy_title") + "\n\n" + t(lang, "proxy_hint")
    await show_screen(cb, text, kb_proxy(lang))


@router.callback_query(F.data == "admin:panel")
async def cb_admin_panel(cb: CallbackQuery):
    if cb.from_user.id not in ADMIN_IDS:
        await cb.answer(t("ru", "not_admin"), show_alert=True)
        return
    lang = await db.get_language(cb.from_user.id)
    await show_screen(cb, t(lang, "admin_title"), kb_admin(lang))


@router.callback_query(F.data == "admin:stats")
async def cb_admin_stats(cb: CallbackQuery):
    if cb.from_user.id not in ADMIN_IDS:
        await cb.answer(t("ru", "not_admin"), show_alert=True)
        return
    lang = await db.get_language(cb.from_user.id)
    text = t(lang, "admin_stats_text",
             users=await db.count_users(),
             new_today=await db.count_new_users_today(),
             subs=await db.count_active_subs(),
             refs=await db.count_refs_total())
    await show_screen(cb, text, kb_admin(lang))


@router.callback_query(F.data == "admin:users")
async def cb_admin_users(cb: CallbackQuery):
    if cb.from_user.id not in ADMIN_IDS:
        await cb.answer(t("ru", "not_admin"), show_alert=True)
        return
    lang = await db.get_language(cb.from_user.id)
    async with db.c.execute("SELECT * FROM users ORDER BY created_at DESC LIMIT 20") as cur:
        rows = [dict(r) for r in await cur.fetchall()]
    lines = []
    for r in rows:
        uname = f"@{r['username']}" if r.get("username") else "—"
        lines.append(f"▸ {r['id']} {uname} — {r.get('first_name') or ''} ({r.get('language') or 'ru'})")
    text = t(lang, "admin_users_text", n=len(rows), list="\n".join(lines) or "—")
    await show_screen(cb, text, kb_admin(lang))


@router.callback_query(F.data == "admin:subs")
async def cb_admin_subs(cb: CallbackQuery):
    if cb.from_user.id not in ADMIN_IDS:
        await cb.answer(t("ru", "not_admin"), show_alert=True)
        return
    lang = await db.get_language(cb.from_user.id)
    async with db.c.execute("SELECT * FROM subscriptions ORDER BY started_at DESC LIMIT 20") as cur:
        rows = [dict(r) for r in await cur.fetchall()]
    lines = []
    for r in rows:
        name = r.get("custom_name") or f"Key {r['id']}"
        lines.append(f"▸ {r['user_id']} — {name} → {r['expires_at'][:10]} [{r['status']}]")
    text = f"▤ Активных: {await db.count_active_subs()}\n\n" + ("\n".join(lines) or "—")
    await show_screen(cb, text, kb_admin(lang))


@router.callback_query(F.data == "admin:refs")
async def cb_admin_refs(cb: CallbackQuery):
    if cb.from_user.id not in ADMIN_IDS:
        await cb.answer(t("ru", "not_admin"), show_alert=True)
        return
    lang = await db.get_language(cb.from_user.id)
    async with db.c.execute(
        "SELECT referrer_id, COUNT(*) AS c FROM referrals GROUP BY referrer_id ORDER BY c DESC LIMIT 20"
    ) as cur:
        rows = [dict(r) for r in await cur.fetchall()]
    lines = [f"▸ {r['referrer_id']} → {r['c']} приглашено" for r in rows]
    text = f"✦ Всего рефералов: {await db.count_refs_total()}\n\n" + ("\n".join(lines) or "—")
    await show_screen(cb, text, kb_admin(lang))


@router.callback_query(F.data == "admin:conv")
async def cb_admin_conv(cb: CallbackQuery):
    if cb.from_user.id not in ADMIN_IDS:
        await cb.answer(t("ru", "not_admin"), show_alert=True)
        return
    lang = await db.get_language(cb.from_user.id)
    total = await db.count_users()
    subs = await db.count_active_subs()
    conv = (subs / total * 100) if total else 0
    async with db.c.execute("SELECT COUNT(*) AS c FROM payments") as cur:
        pays = (await cur.fetchone())["c"]
    text = (f"◆ Конверсии\n\n"
            f"▸ Пользователей: {total}\n"
            f"▸ Активных подписок: {subs}\n"
            f"▸ Конверсия: {conv:.2f}%\n"
            f"▸ Платежей: {pays}")
    await show_screen(cb, text, kb_admin(lang))


@router.callback_query(F.data == "admin:manage")
async def cb_admin_manage(cb: CallbackQuery):
    if cb.from_user.id not in ADMIN_IDS:
        await cb.answer(t("ru", "not_admin"), show_alert=True)
        return
    text = ("✎ Управление подписками\n\n"
            "▸ Выдать подписку — создастся файл в GitHub и запись в БД.\n"
            "▸ Забрать подписку — удалит подписку у пользователя.")
    await show_screen(cb, text, kb_admin_manage("ru"))


@router.callback_query(F.data == "admin:give")
async def cb_admin_give(cb: CallbackQuery, state: FSMContext):
    if cb.from_user.id not in ADMIN_IDS:
        await cb.answer(t("ru", "not_admin"), show_alert=True)
        return
    await state.set_state(AdminGiveSG.waiting_user_id)
    await show_screen(cb, "✎ Введите Telegram ID пользователя, которому выдать подписку.\n\nОтмена: /cancel",
                      kb_back_only("ru"))


@router.message(AdminGiveSG.waiting_user_id)
async def do_admin_give_uid(msg: Message, state: FSMContext, bot: Bot):
    if msg.from_user.id not in ADMIN_IDS:
        return
    raw = (msg.text or "").strip()
    if not raw.isdigit():
        await msg.answer("✕ ID должен быть числом. /cancel — отмена.")
        return

    target_uid = int(raw)
    target = await db.get_user(target_uid)
    if not target:
        await msg.answer(f"✕ Пользователь {target_uid} не найден в БД.\n"
                         f"Он должен хотя бы раз нажать /start в боте.")
        await state.clear()
        await show_main_menu(msg, msg.from_user.id)
        return

    await state.update_data(target_uid=target_uid)
    await state.set_state(AdminGiveSG.waiting_plan)

    name = (target.get("first_name") or "")
    if target.get("username"):
        name += f" @{target['username']}"
    await msg.answer(f"▸ Пользователь: {target_uid} {name}\n\n❯ Выберите тариф:",
                     reply_markup=kb_admin_give_plans())


@router.callback_query(F.data.startswith("admin:give_plan:"))
async def cb_admin_give_plan(cb: CallbackQuery, state: FSMContext, bot: Bot):
    if cb.from_user.id not in ADMIN_IDS:
        await cb.answer(t("ru", "not_admin"), show_alert=True)
        return

    plan_code = cb.data.split(":")[2]
    data = await state.get_data()
    target_uid = data.get("target_uid")
    if not target_uid:
        await cb.answer("⚠ Сначала введите ID.", show_alert=True)
        return

    days_map = {"1m": 30, "3m": 90, "6m": 180, "forever": 3650}
    dur_map  = {"1m": "1_month", "3m": "3_month", "6m": "6_month", "forever": "forever"}
    days = days_map.get(plan_code, 30)
    duration = dur_map.get(plan_code, "1_month")

    await cb.answer("Создаю…")

    result = await create_sub_folder_with_expire("sub", days)
    if not result:
        await cb.message.answer("✕ Не удалось создать файл в GitHub.")
        await state.clear()
        return
    folder, raw_url = result

    existing = await db.user_subscriptions(target_uid)
    custom_name = f"Premium {len(existing) + 1}"

    await db.create_subscription(target_uid, duration, days,
                                 folder=folder, raw_url=raw_url, custom_name=custom_name)

    await cb.message.answer(
        f"✓ Подписка выдана пользователю {target_uid}\n\n"
        f"▸ Название: {custom_name}\n"
        f"▸ Тариф: {duration}\n"
        f"▸ Дней: {days}\n"
        f"▸ Папка: {folder}\n"
        f"▸ Ссылка: {raw_url}"
    )

    try:
        await bot.send_message(
            target_uid,
            f"✓ Вам выдана подписка «{custom_name}».\n\n"
            f"▸ Тариф: {duration}\n"
            f"▸ Действует до: {(datetime.utcnow() + timedelta(days=days)).strftime('%d.%m.%Y')}\n\n"
            f"❯ Перейдите в «Подключиться», чтобы подключиться."
        )
    except Exception as e:
        log.warning("notify user about admin gift: %s", e)

    await state.clear()
    await show_main_menu(cb.message, cb.from_user.id)


@router.callback_query(F.data == "admin:take")
async def cb_admin_take(cb: CallbackQuery, state: FSMContext):
    if cb.from_user.id not in ADMIN_IDS:
        await cb.answer(t("ru", "not_admin"), show_alert=True)
        return
    await state.set_state(AdminTakeSG.waiting_user_id)
    await show_screen(cb, "✎ Введите Telegram ID пользователя, у которого забрать подписки.\n\nОтмена: /cancel",
                      kb_back_only("ru"))


@router.message(AdminTakeSG.waiting_user_id)
async def do_admin_take_uid(msg: Message, state: FSMContext, bot: Bot):
    if msg.from_user.id not in ADMIN_IDS:
        return
    raw = (msg.text or "").strip()
    if not raw.isdigit():
        await msg.answer("✕ ID должен быть числом. /cancel — отмена.")
        return

    target_uid = int(raw)
    subs = await db.user_subscriptions(target_uid)
    if not subs:
        await msg.answer(f"✕ У пользователя {target_uid} нет подписок.")
        await state.clear()
        await show_main_menu(msg, msg.from_user.id)
        return

    await state.update_data(target_uid=target_uid)
    text = f"▤ Подписки пользователя {target_uid}:\n\n❯ Выберите, что забрать:"
    await msg.answer(text, reply_markup=kb_admin_take_list(subs))


@router.callback_query(F.data.startswith("admin:take_pick:"))
async def cb_admin_take_pick(cb: CallbackQuery, state: FSMContext):
    if cb.from_user.id not in ADMIN_IDS:
        await cb.answer(t("ru", "not_admin"), show_alert=True)
        return
    sub_id = int(cb.data.split(":")[2])
    sub = await db.get_subscription(sub_id)
    if not sub:
        await cb.answer("⚠ Подписка не найдена", show_alert=True)
        return
    name = sub.get("custom_name") or f"Key {sub['id']}"
    text = (f"⚠ Забрать подписку?\n\n"
            f"▸ Пользователь: {sub['user_id']}\n"
            f"▸ Название: {name}\n"
            f"▸ Тариф: {sub['plan']}\n"
            f"▸ До: {sub['expires_at'][:10]}\n\n"
            f"Пользователь получит уведомление.")
    await show_screen(cb, text, kb_admin_take_confirm(sub_id))


@router.callback_query(F.data.startswith("admin:take_yes:"))
async def cb_admin_take_yes(cb: CallbackQuery, state: FSMContext, bot: Bot):
    if cb.from_user.id not in ADMIN_IDS:
        await cb.answer(t("ru", "not_admin"), show_alert=True)
        return
    sub_id = int(cb.data.split(":")[2])
    sub = await db.get_subscription(sub_id)
    if not sub:
        await cb.answer("⚠ Подписка не найдена", show_alert=True)
        return

    name = sub.get("custom_name") or f"Key {sub['id']}"
    target_uid = sub["user_id"]

    await db.delete_subscription(sub_id)
    await cb.message.answer(f"✓ Подписка «{name}» удалена у пользователя {target_uid}.")

    try:
        await bot.send_message(
            target_uid,
            f"⚠ Ваша подписка «{name}» была отозвана администратором.\n\n"
            f"❯ Обратитесь в поддержку: {SUPPORT_URL}"
        )
    except Exception as e:
        log.warning("notify user about admin take: %s", e)

    await state.clear()
    await show_main_menu(cb.message, cb.from_user.id)


@router.callback_query(F.data == "admin:dm")
async def cb_admin_dm(cb: CallbackQuery, state: FSMContext):
    if cb.from_user.id not in ADMIN_IDS:
        await cb.answer(t("ru", "not_admin"), show_alert=True)
        return
    await state.set_state(AdminDMSG.waiting_user_id)
    await show_screen(
        cb,
        "✉ Отправка сообщения пользователю.\n\n"
        "▸ Введите Telegram ID получателя.\n\nОтмена: /cancel",
        kb_back_only("ru")
    )


@router.message(AdminDMSG.waiting_user_id)
async def do_admin_dm_uid(msg: Message, state: FSMContext, bot: Bot):
    if msg.from_user.id not in ADMIN_IDS:
        return
    raw = (msg.text or "").strip()
    if not raw.isdigit():
        await msg.answer("✕ ID должен быть числом. /cancel — отмена.")
        return

    target_uid = int(raw)
    target = await db.get_user(target_uid)
    if not target:
        await msg.answer(f"✕ Пользователь {target_uid} не найден в БД.")
        return

    await state.update_data(target_uid=target_uid)
    await state.set_state(AdminDMSG.waiting_text)
    await msg.answer(
        f"✎ Введите текст сообщения для пользователя {target_uid}.\n\n"
        f"Он получит его как обычное сообщение от бота.\n\nОтмена: /cancel"
    )


@router.message(AdminDMSG.waiting_text)
async def do_admin_dm_text(msg: Message, state: FSMContext, bot: Bot):
    if msg.from_user.id not in ADMIN_IDS:
        return
    data = await state.get_data()
    target_uid = data.get("target_uid")
    text = (msg.text or msg.caption or "").strip()
    if not text:
        await msg.answer("✕ Пустое сообщение отменено.")
        await state.clear()
        await show_main_menu(msg, msg.from_user.id)
        return

    try:
        await bot.send_message(target_uid, text)
        await msg.answer(f"✓ Сообщение доставлено пользователю {target_uid}.")
    except TelegramForbiddenError:
        await msg.answer(f"✕ Пользователь {target_uid} заблокировал бота.")
    except Exception as e:
        await msg.answer(f"✕ Ошибка доставки: {e}")

    await state.clear()
    await show_main_menu(msg, msg.from_user.id)


@router.callback_query(F.data == "admin:broadcast")
async def cb_admin_broadcast(cb: CallbackQuery, state: FSMContext):
    if cb.from_user.id not in ADMIN_IDS:
        await cb.answer(t("ru", "not_admin"), show_alert=True)
        return
    await show_screen(
        cb,
        "✉ Глобальная рассылка.\n\n❯ Выберите режим:",
        kb_admin_broadcast_mode()
    )


@router.callback_query(F.data == "admin:bc_text")
async def cb_admin_bc_text(cb: CallbackQuery, state: FSMContext):
    if cb.from_user.id not in ADMIN_IDS:
        await cb.answer(t("ru", "not_admin"), show_alert=True)
        return
    await state.set_state(BroadcastSG.waiting_text)
    await state.update_data(with_buttons=False)
    await show_screen(cb, "✉ Отправьте текст рассылки.\n\nОтмена: /cancel", kb_back_only("ru"))


@router.callback_query(F.data == "admin:bc_textbtns")
async def cb_admin_bc_textbtns(cb: CallbackQuery, state: FSMContext):
    if cb.from_user.id not in ADMIN_IDS:
        await cb.answer(t("ru", "not_admin"), show_alert=True)
        return
    await state.set_state(BroadcastSG.waiting_text)
    await state.update_data(with_buttons=True)
    await show_screen(
        cb,
        "✉ Отправьте текст рассылки.\n\n"
        "После текста бот попросит кнопки.\n"
        "Формат каждой строки: `Текст кнопки | https://ссылка`\n\n"
        "Отмена: /cancel",
        kb_back_only("ru")
    )


@router.message(BroadcastSG.waiting_text)
async def do_broadcast_text(msg: Message, state: FSMContext, bot: Bot):
    if msg.from_user.id not in ADMIN_IDS:
        return
    data = await state.get_data()
    with_buttons = data.get("with_buttons", False)
    text = msg.text or msg.caption or ""
    await state.update_data(broadcast_text=text)

    if with_buttons:
        await state.set_state(BroadcastSG.waiting_buttons)
        await msg.answer(
            "✎ Отправьте кнопки (по одной на строку).\n\n"
            "Формат: `Текст кнопки | https://ссылка`\n\n"
            "Пример:\n"
            "`Перейти на сайт | https://proxygem.github.io/site/`\n"
            "`Поддержка | https://t.me/proxygem_support_bot`\n\n"
            "Отмена: /cancel",
            parse_mode=None,
        )
        return

    await _do_broadcast_send(msg, state, bot, text, buttons=None)


@router.message(BroadcastSG.waiting_buttons)
async def do_broadcast_buttons(msg: Message, state: FSMContext, bot: Bot):
    if msg.from_user.id not in ADMIN_IDS:
        return
    data = await state.get_data()
    text = data.get("broadcast_text", "")
    raw = msg.text or ""

    buttons: List[List[InlineKeyboardButton]] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line or "|" not in line:
            continue
        label, url = line.split("|", 1)
        label = label.strip()
        url = url.strip()
        if not label or not url.startswith(("http://", "https://", "tg://")):
            continue
        buttons.append([InlineKeyboardButton(text=label, url=url)])

    await _do_broadcast_send(msg, state, bot, text, buttons=buttons or None)


async def _do_broadcast_send(msg: Message, state: FSMContext, bot: Bot,
                             text: str, buttons: Optional[List[List[InlineKeyboardButton]]]):
    await state.clear()
    lang = await db.get_language(msg.from_user.id)
    kb = InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None
    sent, failed = 0, 0
    for uid in await db.all_user_ids():
        try:
            await bot.send_message(uid, text, reply_markup=kb,
                                   disable_web_page_preview=True)
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1
    await msg.answer(t(lang, "broadcast_done", sent=sent, failed=failed))
    await show_main_menu(msg, msg.from_user.id)


@router.message(Command("cancel"))
async def cmd_cancel(msg: Message, state: FSMContext):
    if await state.get_state():
        await state.clear()
        lang = await db.get_language(msg.from_user.id)
        await msg.answer(t(lang, "broadcast_cancel"))
        await show_main_menu(msg, msg.from_user.id)


@router.message()
async def fallback(msg: Message):
    await show_main_menu(msg, msg.from_user.id)


# ============================================================
# CONSOLE
# ============================================================

def console_listener():
    while True:
        try:
            cmd = input().strip().lower()
        except (EOFError, KeyboardInterrupt):
            break
        if not cmd:
            continue
        if cmd in ("exit", "quit", "q"):
            print(f"{C.YELLOW}[console]{C.RESET} Выход…")
            CONTROL["exit"] = True
            os._exit(0)
        elif cmd == "stop":
            print(f"{C.YELLOW}[console]{C.RESET} Остановка…")
            CONTROL["stop"] = True
            time.sleep(0.5)
            os._exit(0)
        elif cmd == "start":
            if CONTROL["stop"]:
                print(f"{C.GREEN}[console]{C.RESET} Запуск polling…")
                CONTROL["stop"] = False
            else:
                print(f"{C.YELLOW}[console]{C.RESET} Уже работает.")
        elif cmd == "restart":
            print(f"{C.YELLOW}[console]{C.RESET} Перезапуск…")
            CONTROL["restart"] = True
            try:
                subprocess.Popen([sys.executable] + sys.argv, cwd=os.getcwd(), close_fds=True)
            except Exception as e:
                print(f"{C.RED}[console]{C.RESET} Ошибка: {e}")
            time.sleep(0.5)
            os._exit(0)
        elif cmd == "status":
            state = "ОСТАНОВЛЕН" if CONTROL["stop"] else "РАБОТАЕТ"
            color = C.RED if CONTROL["stop"] else C.GREEN
            print(f"{color}[console]{C.RESET} Состояние: {color}{state}{C.RESET}")
            print(f"{C.YELLOW}[console]{C.RESET} PID: {os.getpid()}")
        elif cmd in ("help", "?"):
            print_help()
        else:
            print(f"{C.RED}[console]{C.RESET} Неизвестная команда: {cmd}.")


# ============================================================
# MAIN
# ============================================================

async def main():
    global bot
    print_banner()
    print_help()
    print(f"{C.YELLOW}[console]{C.RESET} Введите 'help' для списка команд.\n")

    if _HAS_KEEP_ALIVE:
        try:
            keep_alive()
            log.info("keep_alive запущен")
        except Exception as e:
            log.warning("keep_alive: %s", e)

    await db.connect()
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=None))
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except Exception as e:
        log.warning("delete_webhook: %s", e)

    dp = Dispatcher(storage=MemoryStorage())

    @dp.error()
    async def on_error(event):
        log.warning("Unhandled error: %s", event.exception)
        return True

    dp.message.middleware(AntiSpamMW())
    dp.callback_query.middleware(AntiSpamMW())
    dp.message.middleware(SubscriptionMW(bot))
    dp.callback_query.middleware(SubscriptionMW(bot))

    dp.include_router(router)

    me = await bot.get_me()
    log.info("Bot started as @%s", me.username)

    asyncio.create_task(poll_payments())
    asyncio.create_task(sync_sub_folders())

    threading.Thread(target=console_listener, daemon=True).start()

    polling_task = asyncio.create_task(
        dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    )

    try:
        while not CONTROL["exit"]:
            if CONTROL["stop"]:
                await asyncio.sleep(0.3)
                if CONTROL["restart"] or CONTROL["exit"]:
                    break
                continue
            await asyncio.sleep(0.3)
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass

    try:
        await dp.stop_polling()
    except Exception:
        pass
    try:
        polling_task.cancel()
        await polling_task
    except Exception:
        pass

    await db.close()
    await bot.session.close()
    if _http and not _http.closed:
        await _http.close()

    if CONTROL["restart"]:
        print(f"{C.YELLOW}[console]{C.RESET} Перезапуск…")
        os._exit(0)

    print(f"{C.GREEN}[console]{C.RESET} Бот остановлен.")


if __name__ == "__main__":
    try:
        keep_alive()
        asyncio.run(main()) # Запуск бота
    except (KeyboardInterrupt, SystemExit):
        print(f"\n{C.YELLOW}[console]{C.RESET} Остановлено пользователем.")
