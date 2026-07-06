#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NOIR MARKET — Telegram Mini App магазин цифровых товаров.

Бэкенд на чистой стандартной библиотеке Python (без зависимостей):
  * ThreadingHTTPServer — статика мини-аппа + JSON API
  * SQLite — товары, категории, заказы, склад ключей, промокоды, юзеры
  * Валидация Telegram WebApp initData (HMAC-SHA256)
  * Crypto Pay API (@CryptoBot) — инвойсы и проверка оплаты
  * Админ-панель прямо в мини-аппе (доступ по ADMIN_IDS из .env)

Запуск:  python3 server.py
"""

import json
import os
import re
import ssl
import sys
import hmac
import time
import hashlib
import sqlite3
import threading
import mimetypes
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEBAPP_DIR = os.path.join(BASE_DIR, 'webapp')
DATA_DIR = os.path.join(BASE_DIR, 'data')
DB_PATH = os.path.join(DATA_DIR, 'shop.db')


# ---------------------------------------------------------------------------
# Конфигурация из .env
# ---------------------------------------------------------------------------

def load_env():
    path = os.path.join(BASE_DIR, '.env')
    if not os.path.exists(path):
        return
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, value = line.split('=', 1)
            os.environ.setdefault(key.strip(), value.strip())


load_env()

BOT_TOKEN = os.environ.get('BOT_TOKEN', '')
CRYPTO_TOKEN = os.environ.get('CRYPTOBOT_TOKEN', '')
CRYPTO_API = os.environ.get('CRYPTOBOT_API', 'https://pay.crypt.bot/api').rstrip('/')
ADMIN_IDS = {int(x) for x in os.environ.get('ADMIN_IDS', '').replace(' ', '').split(',') if x}
CURRENCY = os.environ.get('CURRENCY', 'USD')
PORT = int(os.environ.get('PORT', '8877'))
DEV_MODE = os.environ.get('DEV_MODE', '0') == '1'

INVOICE_TTL = 1800          # время жизни инвойса, сек
AUTH_MAX_AGE = 86400        # initData не старше суток

DELIVER_LOCK = threading.Lock()


def now_iso():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


# ---------------------------------------------------------------------------
# База данных
# ---------------------------------------------------------------------------

def db():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA foreign_keys=ON')
    return conn


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY,
    username    TEXT,
    first_name  TEXT,
    photo_url   TEXT,
    is_banned   INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL,
    last_seen   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS categories (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    name  TEXT NOT NULL,
    icon  TEXT NOT NULL DEFAULT 'folder',
    sort  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS products (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id   INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    name          TEXT NOT NULL,
    subtitle      TEXT NOT NULL DEFAULT '',
    description   TEXT NOT NULL DEFAULT '',
    price         REAL NOT NULL,
    old_price     REAL,
    icon          TEXT NOT NULL DEFAULT 'package',
    badge         TEXT NOT NULL DEFAULT '',
    delivery_type TEXT NOT NULL DEFAULT 'text',   -- 'text' | 'keys'
    content       TEXT NOT NULL DEFAULT '',
    active        INTEGER NOT NULL DEFAULT 1,
    sort          INTEGER NOT NULL DEFAULT 0,
    sales         INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS stock (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id    INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    content       TEXT NOT NULL,
    sold_order_id INTEGER
);

CREATE TABLE IF NOT EXISTS orders (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL,
    items_json   TEXT NOT NULL,
    subtotal     REAL NOT NULL,
    discount     REAL NOT NULL DEFAULT 0,
    total        REAL NOT NULL,
    promo_code   TEXT,
    status       TEXT NOT NULL DEFAULT 'pending', -- pending | paid | expired
    invoice_id   INTEGER,
    pay_url      TEXT,
    delivery_json TEXT,
    created_at   TEXT NOT NULL,
    paid_at      TEXT
);

CREATE TABLE IF NOT EXISTS promos (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    code     TEXT NOT NULL UNIQUE,
    percent  INTEGER NOT NULL,
    max_uses INTEGER NOT NULL DEFAULT 0,          -- 0 = без лимита
    used     INTEGER NOT NULL DEFAULT 0,
    active   INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

DEFAULT_SETTINGS = {
    'shop_name': 'NOIR MARKET',
    'tagline': 'цифровые товары · мгновенная выдача',
    'currency_symbol': '$',
    'support': '@sdefgsdfsdfdsfbot',
    # Публичный HTTPS-адрес мини-аппа — для кнопки в ответе на /start.
    # Заполняется через админку, scripts/setup_bot.py или WEBAPP_URL в .env.
    'webapp_url': os.environ.get('WEBAPP_URL', ''),
}

SEED_CATEGORIES = [
    ('Подписки', 'sparkles', 0),
    ('Ключи и лицензии', 'key-round', 1),
    ('Аккаунты', 'user-round', 2),
    ('Софт', 'terminal', 3),
    ('VPN и приватность', 'shield', 4),
    ('Гайды', 'book-open', 5),
]

SEED_PRODUCTS = [
    # (category idx, name, subtitle, description, price, old_price, icon, badge, delivery_type, content, keys)
    (0, 'Telegram Premium · 3 мес', 'Официальный gift на ваш аккаунт',
     'Подарочная подписка Telegram Premium на 3 месяца. После оплаты пришлём gift-ссылку на активацию — она появится прямо в заказе.\n\n• Активация за 1–5 минут\n• Работает в любой стране\n• Гарантия на весь срок',
     11.99, 16.99, 'send', 'ХИТ', 'keys', '', ['TG-PREM-3M-DEMO-0001', 'TG-PREM-3M-DEMO-0002', 'TG-PREM-3M-DEMO-0003']),
    (0, 'Spotify Premium · 12 мес', 'Индивидуальный план, апгрейд вашего аккаунта',
     'Апгрейд вашего личного аккаунта Spotify до Premium на 12 месяцев. Слушайте без рекламы и офлайн.\n\n• Ваш аккаунт, ваши плейлисты\n• Выдача инструкции моментально',
     24.00, 39.00, 'audio-lines', '-38%', 'text',
     'Инструкция по активации Spotify Premium:\n1) Напишите в поддержку логин от аккаунта\n2) Активация в течение 30 минут\nКод заказа укажите в сообщении.', []),
    (1, 'Windows 11 Pro · ключ', 'Retail-ключ с моментальной выдачей',
     'Лицензионный retail-ключ активации Windows 11 Pro. Привязывается к вашей учётной записи Microsoft.\n\n• Онлайн-активация\n• Пожизненная лицензия\n• Ключ выдаётся сразу после оплаты',
     7.50, 12.00, 'app-window', '', 'keys', '', ['W11P-DEMO-AAAA-BBBB-0001', 'W11P-DEMO-AAAA-BBBB-0002', 'W11P-DEMO-AAAA-BBBB-0003', 'W11P-DEMO-AAAA-BBBB-0004', 'W11P-DEMO-AAAA-BBBB-0005']),
    (1, 'Office 2021 Pro Plus', 'Бессрочная лицензия, привязка к аккаунту',
     'Ключ Microsoft Office 2021 Professional Plus: Word, Excel, PowerPoint, Outlook и другие приложения. Бессрочно.\n\n• Онлайн-активация\n• 1 ПК',
     9.90, None, 'file-text', '', 'keys', '', ['OFF21-DEMO-CCCC-DDDD-0001', 'OFF21-DEMO-CCCC-DDDD-0002']),
    (2, 'ChatGPT Plus · аккаунт', 'Готовый аккаунт с подпиской на 1 мес',
     'Готовый аккаунт с активной подпиской ChatGPT Plus. Данные для входа выдаются мгновенно.\n\n• Полный доступ к GPT-моделям\n• Смена пароля разрешена\n• Гарантия 30 дней',
     17.00, 20.00, 'bot', 'NEW', 'keys', '', ['chatgpt_demo_login_1:password_1', 'chatgpt_demo_login_2:password_2']),
    (3, 'Adobe CC · All Apps · 1 мес', 'Photoshop, Premiere, After Effects и ещё 20+',
     'Подписка Adobe Creative Cloud All Apps на ваш аккаунт: Photoshop, Illustrator, Premiere Pro, After Effects и другие.\n\n• Активация на вашу почту Adobe\n• 100 ГБ облака',
     14.50, 54.99, 'pen-tool', '-74%', 'text',
     'Активация Adobe CC:\n1) Отправьте в поддержку e-mail вашего Adobe ID\n2) Примите приглашение в команду\n3) Подписка активна — проверьте в Creative Cloud.', []),
    (4, 'VPN Unlim · 6 мес', 'WireGuard-конфиг, безлимитный трафик',
     'Личный VPN на 6 месяцев: WireGuard-конфигурация, безлимитный трафик, скорость до 1 Гбит/с, локации EU/US.\n\n• Конфиг выдаётся сразу\n• До 3 устройств\n• Без логов',
     8.00, None, 'shield-check', 'ХИТ', 'keys', '', ['wg-demo-config-0001.conf :: https://example.com/wg/demo0001', 'wg-demo-config-0002.conf :: https://example.com/wg/demo0002', 'wg-demo-config-0003.conf :: https://example.com/wg/demo0003']),
    (5, 'Гайд: арбитраж крипты', 'PDF, 120 страниц + чек-листы',
     'Практический гайд по межбиржевому арбитражу криптовалют: связки, сканеры, риск-менеджмент, налоги.\n\n• 120 страниц PDF\n• Обновления бесплатно\n• Ссылка выдаётся мгновенно',
     5.00, 15.00, 'trending-up', '-66%', 'text',
     'Ваша ссылка на гайд: https://example.com/guides/crypto-arbitrage-demo.pdf\nПароль архива: noir2026', []),
]


def init_db():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = db()
    conn.executescript(SCHEMA)
    for key, value in DEFAULT_SETTINGS.items():
        conn.execute('INSERT OR IGNORE INTO settings(key, value) VALUES(?, ?)', (key, value))
    if conn.execute('SELECT COUNT(*) c FROM products').fetchone()['c'] == 0:
        cat_ids = []
        for name, icon, sort in SEED_CATEGORIES:
            cur = conn.execute('INSERT INTO categories(name, icon, sort) VALUES(?, ?, ?)', (name, icon, sort))
            cat_ids.append(cur.lastrowid)
        for i, (ci, name, subtitle, descr, price, old, icon, badge, dtype, content, keys) in enumerate(SEED_PRODUCTS):
            cur = conn.execute(
                'INSERT INTO products(category_id, name, subtitle, description, price, old_price, icon, badge,'
                ' delivery_type, content, active, sort, sales, created_at)'
                ' VALUES(?,?,?,?,?,?,?,?,?,?,1,?,?,?)',
                (cat_ids[ci], name, subtitle, descr, price, old, icon, badge, dtype, content, i,
                 (7 - i) * 3, now_iso()))
            for key in keys:
                conn.execute('INSERT INTO stock(product_id, content) VALUES(?, ?)', (cur.lastrowid, key))
        conn.execute("INSERT OR IGNORE INTO promos(code, percent, max_uses) VALUES('START10', 10, 0)")
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Внешние API: Telegram Bot API и Crypto Pay API
# ---------------------------------------------------------------------------

def make_ssl_context():
    """SSL-контекст с системными CA (у Python на macOS их часто нет из коробки)."""
    ctx = ssl.create_default_context()
    for cafile in ('/etc/ssl/cert.pem', '/usr/local/etc/openssl/cert.pem'):
        if os.path.exists(cafile):
            try:
                ctx.load_verify_locations(cafile)
            except Exception:
                pass
    try:
        import certifi
        ctx.load_verify_locations(certifi.where())
    except Exception:
        pass
    return ctx


SSL_CTX = make_ssl_context()


def http_json(url, payload=None, headers=None, timeout=15):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, headers={
        'Content-Type': 'application/json',
        'User-Agent': 'NoirMarket/1.0',  # Cloudflare режет дефолтный UA urllib
        **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as resp:
        return json.loads(resp.read().decode())


def crypto_api(method, params=None):
    """Вызов Crypto Pay API (https://help.crypt.bot/crypto-pay-api)."""
    try:
        data = http_json(f'{CRYPTO_API}/{method}', params or {},
                         {'Crypto-Pay-API-Token': CRYPTO_TOKEN})
    except urllib.error.HTTPError as e:
        try:
            data = json.loads(e.read().decode())
        except Exception:
            raise ApiError(502, f'CryptoBot HTTP {e.code}')
    if not data.get('ok'):
        err = data.get('error') or {}
        raise ApiError(502, f"CryptoBot: {err.get('name', err)}")
    return data['result']


def tg_api(method, params=None, timeout=15):
    try:
        return http_json(f'https://api.telegram.org/bot{BOT_TOKEN}/{method}', params or {},
                         timeout=timeout)
    except Exception as e:
        return {'ok': False, 'error': str(e)}


def notify_admins(text):
    def run():
        for admin_id in ADMIN_IDS:
            tg_api('sendMessage', {'chat_id': admin_id, 'text': text, 'parse_mode': 'HTML'})
    threading.Thread(target=run, daemon=True).start()


# ---------------------------------------------------------------------------
# Бот: единственная задача — по /start прислать кнопку открытия мини-аппа
# ---------------------------------------------------------------------------

def send_welcome(chat_id, user_id):
    conn = db()
    try:
        settings = get_settings(conn)
    finally:
        conn.close()
    url = (settings.get('webapp_url') or '').strip()
    text = (f"▪ <b>{settings.get('shop_name', 'NOIR MARKET')}</b>\n"
            f"{settings.get('tagline', '')}\n\n"
            "▪ Каталог, корзина, оплата и выдача — всё в мини-аппе\n"
            "▪ Оплата криптой через @CryptoBot (USDT, TON, BTC…)\n"
            "▪ Товар приходит мгновенно после оплаты")
    params = {'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'}
    if url.startswith('https://'):
        params['reply_markup'] = {'inline_keyboard': [[
            {'text': '🛍 Открыть магазин', 'web_app': {'url': url}}]]}
        params['text'] += '\n\nЖми кнопку ниже 👇'
    elif user_id in ADMIN_IDS:
        params['text'] += ('\n\n⚙️ <i>Кнопка мини-аппа появится, когда укажешь публичный '
                           'HTTPS-адрес: админка → Настройки → URL мини-аппа '
                           '(или scripts/setup_bot.py).</i>')
    else:
        params['text'] += '\n\n⏳ Магазин скоро откроется — загляни чуть позже.'
    resp = tg_api('sendMessage', params)
    if not resp.get('ok') and 'reply_markup' in params:
        # например, невалидный web_app URL — шлём без кнопки, чтобы юзер не остался без ответа
        params.pop('reply_markup')
        tg_api('sendMessage', params)


def handle_update(update):
    msg = update.get('message') or {}
    chat = msg.get('chat') or {}
    sender = msg.get('from') or {}
    if chat.get('type') != 'private' or not sender.get('id'):
        return
    # регистрируем в базе — попадёт в рассылки и статистику ещё до первой покупки
    conn = db()
    try:
        upsert_user(conn, {'id': sender['id'], 'username': sender.get('username', ''),
                           'first_name': sender.get('first_name', ''), 'photo_url': ''})
        conn.commit()
    finally:
        conn.close()
    # бот отвечает одним и тем же на любое сообщение: вся жизнь — в мини-аппе
    send_welcome(chat['id'], sender['id'])


def bot_loop():
    tg_api('deleteWebhook', {'drop_pending_updates': False})
    offset = 0
    print('[bot] long-polling запущен: жду /start', flush=True)
    while True:
        resp = tg_api('getUpdates', {'offset': offset, 'timeout': 25,
                                     'allowed_updates': ['message']}, timeout=35)
        if not resp.get('ok'):
            time.sleep(3)
            continue
        for update in resp.get('result', []):
            offset = update['update_id'] + 1
            try:
                handle_update(update)
            except Exception as e:
                sys.stderr.write(f'[bot] ошибка обработки апдейта: {e}\n')


# ---------------------------------------------------------------------------
# Авторизация: Telegram WebApp initData
# ---------------------------------------------------------------------------

class ApiError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


def validate_init_data(raw):
    """Проверка подписи initData по алгоритму Telegram (HMAC-SHA256)."""
    if not raw:
        return None
    try:
        pairs = urllib.parse.parse_qsl(raw, keep_blank_values=True)
    except Exception:
        return None
    data = dict(pairs)
    received_hash = data.pop('hash', None)
    if not received_hash:
        return None
    check_string = '\n'.join(f'{k}={v}' for k, v in sorted(data.items()))
    secret = hmac.new(b'WebAppData', BOT_TOKEN.encode(), hashlib.sha256).digest()
    calc_hash = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calc_hash, received_hash):
        return None
    try:
        if time.time() - int(data.get('auth_date', '0')) > AUTH_MAX_AGE:
            return None
        user = json.loads(data.get('user', '{}'))
        return user if user.get('id') else None
    except Exception:
        return None


def resolve_user(init_data):
    user = validate_init_data(init_data)
    if user is None and DEV_MODE and not init_data:
        # Демо-режим для обычного браузера: даём первого админа
        dev_id = next(iter(ADMIN_IDS), 1)
        user = {'id': dev_id, 'first_name': 'Dev', 'username': 'dev_mode', 'photo_url': ''}
    if user is None:
        raise ApiError(401, 'Невалидная авторизация Telegram')
    return user


def upsert_user(conn, user):
    now = now_iso()
    conn.execute(
        'INSERT INTO users(id, username, first_name, photo_url, created_at, last_seen)'
        ' VALUES(?,?,?,?,?,?)'
        ' ON CONFLICT(id) DO UPDATE SET username=excluded.username,'
        ' first_name=excluded.first_name, photo_url=excluded.photo_url, last_seen=excluded.last_seen',
        (user['id'], user.get('username', ''), user.get('first_name', ''),
         user.get('photo_url', ''), now, now))


def check_banned(conn, user_id):
    row = conn.execute('SELECT is_banned FROM users WHERE id=?', (user_id,)).fetchone()
    if row and row['is_banned']:
        raise ApiError(403, 'Вы заблокированы в этом магазине')


def require_admin(user):
    if user['id'] not in ADMIN_IDS:
        raise ApiError(403, 'Доступ только для администратора')


# ---------------------------------------------------------------------------
# Бизнес-логика: заказы, доставка, оплата
# ---------------------------------------------------------------------------

def get_settings(conn):
    return {r['key']: r['value'] for r in conn.execute('SELECT key, value FROM settings')}


def stock_left(conn, product_id):
    return conn.execute(
        'SELECT COUNT(*) c FROM stock WHERE product_id=? AND sold_order_id IS NULL',
        (product_id,)).fetchone()['c']


def product_public(conn, row, with_content=False):
    p = dict(row)
    p['stock_left'] = stock_left(conn, p['id']) if p['delivery_type'] == 'keys' else None
    if not with_content:
        p.pop('content', None)
    return p


def find_promo(conn, code):
    if not code:
        return None
    promo = conn.execute('SELECT * FROM promos WHERE code=? COLLATE NOCASE AND active=1',
                         (code.strip(),)).fetchone()
    if not promo:
        raise ApiError(400, 'Промокод не найден')
    if promo['max_uses'] and promo['used'] >= promo['max_uses']:
        raise ApiError(400, 'Промокод исчерпан')
    return promo


def create_order(conn, user, body):
    items_req = body.get('items') or []
    if not items_req:
        raise ApiError(400, 'Корзина пуста')
    items, subtotal = [], 0.0
    for it in items_req:
        product = conn.execute('SELECT * FROM products WHERE id=? AND active=1',
                               (int(it.get('id', 0)),)).fetchone()
        if not product:
            raise ApiError(400, 'Товар недоступен')
        qty = max(1, min(int(it.get('qty', 1)), 50))
        if product['delivery_type'] == 'text':
            qty = 1
        elif stock_left(conn, product['id']) < qty:
            raise ApiError(400, f'«{product["name"]}»: недостаточно на складе')
        items.append({'id': product['id'], 'name': product['name'], 'price': product['price'],
                      'qty': qty, 'icon': product['icon'], 'delivery_type': product['delivery_type']})
        subtotal += product['price'] * qty

    promo = find_promo(conn, body.get('promo'))
    percent = promo['percent'] if promo else 0
    subtotal = round(subtotal, 2)
    discount = round(subtotal * percent / 100, 2)
    total = round(subtotal - discount, 2)

    cur = conn.execute(
        'INSERT INTO orders(user_id, items_json, subtotal, discount, total, promo_code, status, created_at)'
        " VALUES(?,?,?,?,?,?,'pending',?)",
        (user['id'], json.dumps(items, ensure_ascii=False), subtotal, discount, total,
         promo['code'] if promo else None, now_iso()))
    order_id = cur.lastrowid

    if total <= 0:
        # 100% промокод — выдаём сразу без инвойса
        conn.commit()
        order = conn.execute('SELECT * FROM orders WHERE id=?', (order_id,)).fetchone()
        deliver_order(conn, order)
        return order_row(conn.execute('SELECT * FROM orders WHERE id=?', (order_id,)).fetchone())

    settings = get_settings(conn)
    invoice = crypto_api('createInvoice', {
        'currency_type': 'fiat',
        'fiat': CURRENCY,
        'amount': f'{total:.2f}',
        'description': f"{settings.get('shop_name', 'Shop')} — заказ #{order_id}"[:1024],
        'payload': str(order_id),
        'expires_in': INVOICE_TTL,
    })
    pay_url = (invoice.get('mini_app_invoice_url') or invoice.get('bot_invoice_url')
               or invoice.get('pay_url'))
    conn.execute('UPDATE orders SET invoice_id=?, pay_url=? WHERE id=?',
                 (invoice['invoice_id'], pay_url, order_id))
    conn.commit()
    return order_row(conn.execute('SELECT * FROM orders WHERE id=?', (order_id,)).fetchone())


def deliver_order(conn, order):
    """Отметить заказ оплаченным и выдать цифровой товар. Потокобезопасно."""
    with DELIVER_LOCK:
        fresh = conn.execute('SELECT status FROM orders WHERE id=?', (order['id'],)).fetchone()
        if not fresh or fresh['status'] != 'pending':
            return
        delivery = []
        for it in json.loads(order['items_json']):
            product = conn.execute('SELECT * FROM products WHERE id=?', (it['id'],)).fetchone()
            if it['delivery_type'] == 'keys':
                rows = conn.execute(
                    'SELECT id, content FROM stock WHERE product_id=? AND sold_order_id IS NULL LIMIT ?',
                    (it['id'], it['qty'])).fetchall()
                for r in rows:
                    conn.execute('UPDATE stock SET sold_order_id=? WHERE id=?', (order['id'], r['id']))
                content = [r['content'] for r in rows]
                if len(rows) < it['qty']:
                    content.append('⚠️ Часть позиций закончилась — напишите в поддержку, укажите номер заказа.')
            else:
                content = [(product['content'] if product else '') or 'Свяжитесь с поддержкой для получения товара.']
            conn.execute('UPDATE products SET sales=sales+? WHERE id=?', (it['qty'], it['id']))
            delivery.append({'product_id': it['id'], 'name': it['name'], 'qty': it['qty'],
                             'icon': it['icon'], 'content': content})
        conn.execute("UPDATE orders SET status='paid', paid_at=?, delivery_json=? WHERE id=?",
                     (now_iso(), json.dumps(delivery, ensure_ascii=False), order['id']))
        if order['promo_code']:
            conn.execute('UPDATE promos SET used=used+1 WHERE code=? COLLATE NOCASE', (order['promo_code'],))
        conn.commit()

    buyer = conn.execute('SELECT username, first_name FROM users WHERE id=?', (order['user_id'],)).fetchone()
    who = ('@' + buyer['username']) if buyer and buyer['username'] else (buyer['first_name'] if buyer else order['user_id'])
    names = ', '.join(f"{d['name']} ×{d['qty']}" for d in delivery)
    notify_admins(f'💰 <b>Оплачен заказ #{order["id"]}</b>\n'
                  f'Сумма: <b>${order["total"]:.2f}</b>\nПокупатель: {who}\nСостав: {names}')


def check_order_payment(conn, order):
    """Опрос Crypto Pay API по pending-заказу; при оплате — выдача."""
    if order['status'] != 'pending' or not order['invoice_id']:
        return order
    try:
        result = crypto_api('getInvoices', {'invoice_ids': str(order['invoice_id'])})
    except ApiError:
        return order
    invoices = result.get('items', result) if isinstance(result, dict) else result
    if not invoices:
        return order
    status = invoices[0].get('status')
    if status == 'paid':
        deliver_order(conn, order)
    elif status == 'expired':
        conn.execute("UPDATE orders SET status='expired' WHERE id=? AND status='pending'", (order['id'],))
        conn.commit()
    return conn.execute('SELECT * FROM orders WHERE id=?', (order['id'],)).fetchone()


def order_row(row, include_user=False, conn=None):
    o = dict(row)
    o['items'] = json.loads(o.pop('items_json') or '[]')
    o['delivery'] = json.loads(o.pop('delivery_json') or 'null')
    if include_user and conn is not None:
        u = conn.execute('SELECT username, first_name FROM users WHERE id=?', (o['user_id'],)).fetchone()
        o['username'] = (u['username'] or u['first_name']) if u else str(o['user_id'])
    return o


# ---------------------------------------------------------------------------
# API-маршруты
# ---------------------------------------------------------------------------

def api_auth(conn, user, body, m):
    upsert_user(conn, user)
    conn.commit()
    check_banned(conn, user['id'])
    return {'user': {'id': user['id'], 'first_name': user.get('first_name', ''),
                     'username': user.get('username', ''), 'photo_url': user.get('photo_url', '')},
            'is_admin': user['id'] in ADMIN_IDS,
            'settings': get_settings(conn)}


def api_shop(conn, user, body, m):
    check_banned(conn, user['id'])
    categories = [dict(r) for r in conn.execute(
        'SELECT c.*, (SELECT COUNT(*) FROM products p WHERE p.category_id=c.id AND p.active=1) AS count'
        ' FROM categories c ORDER BY sort, id')]
    products = [product_public(conn, r) for r in conn.execute(
        'SELECT * FROM products WHERE active=1 ORDER BY sort, id DESC')]
    return {'categories': categories, 'products': products, 'settings': get_settings(conn)}


def api_promo_check(conn, user, body, m):
    promo = find_promo(conn, body.get('code'))
    if not promo:
        raise ApiError(400, 'Укажите промокод')
    return {'code': promo['code'], 'percent': promo['percent']}


def api_order_create(conn, user, body, m):
    upsert_user(conn, user)
    check_banned(conn, user['id'])
    return create_order(conn, user, body)


def api_order_get(conn, user, body, m):
    order = conn.execute('SELECT * FROM orders WHERE id=? AND user_id=?',
                         (int(m.group(1)), user['id'])).fetchone()
    if not order:
        raise ApiError(404, 'Заказ не найден')
    order = check_order_payment(conn, order)
    return order_row(order)


def api_my_orders(conn, user, body, m):
    rows = conn.execute('SELECT * FROM orders WHERE user_id=? ORDER BY id DESC LIMIT 100',
                        (user['id'],)).fetchall()
    return {'orders': [order_row(r) for r in rows]}


# --- админ ---

def api_admin_overview(conn, user, body, m):
    require_admin(user)
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    q = lambda sql, *a: conn.execute(sql, a).fetchone()[0]
    recent = [order_row(r, include_user=True, conn=conn) for r in conn.execute(
        'SELECT * FROM orders ORDER BY id DESC LIMIT 8')]
    top = [dict(r) for r in conn.execute(
        'SELECT name, icon, sales, price FROM products WHERE sales>0 ORDER BY sales DESC LIMIT 5')]
    return {
        'revenue_total': q("SELECT COALESCE(SUM(total),0) FROM orders WHERE status='paid'"),
        'revenue_today': q("SELECT COALESCE(SUM(total),0) FROM orders WHERE status='paid' AND paid_at LIKE ?", today + '%'),
        'orders_paid': q("SELECT COUNT(*) FROM orders WHERE status='paid'"),
        'orders_pending': q("SELECT COUNT(*) FROM orders WHERE status='pending'"),
        'users_count': q('SELECT COUNT(*) FROM users'),
        'products_count': q('SELECT COUNT(*) FROM products'),
        'stock_total': q('SELECT COUNT(*) FROM stock WHERE sold_order_id IS NULL'),
        'top_products': top,
        'recent_orders': recent,
    }


def api_admin_products(conn, user, body, m):
    require_admin(user)
    return {'products': [product_public(conn, r, with_content=True) for r in conn.execute(
        'SELECT * FROM products ORDER BY sort, id DESC')]}


PRODUCT_FIELDS = ('name', 'subtitle', 'description', 'price', 'old_price', 'icon', 'badge',
                  'delivery_type', 'content', 'active', 'sort', 'category_id')


def clean_product(body):
    name = (body.get('name') or '').strip()
    if not name:
        raise ApiError(400, 'Название обязательно')
    try:
        price = round(float(body.get('price', 0)), 2)
    except (TypeError, ValueError):
        raise ApiError(400, 'Некорректная цена')
    if price <= 0:
        raise ApiError(400, 'Цена должна быть больше нуля')
    old_price = body.get('old_price')
    try:
        old_price = round(float(old_price), 2) if old_price not in (None, '', 0) else None
    except (TypeError, ValueError):
        old_price = None
    dtype = body.get('delivery_type')
    if dtype not in ('text', 'keys'):
        dtype = 'text'
    cat = body.get('category_id')
    return {
        'name': name[:120],
        'subtitle': (body.get('subtitle') or '').strip()[:160],
        'description': (body.get('description') or '').strip()[:4000],
        'price': price, 'old_price': old_price,
        'icon': ((body.get('icon') or 'package').strip() or 'package')[:80],
        'badge': (body.get('badge') or '').strip()[:20],
        'delivery_type': dtype,
        'content': (body.get('content') or '').strip()[:8000],
        'active': 1 if body.get('active', True) else 0,
        'sort': int(body.get('sort') or 0),
        'category_id': int(cat) if cat else None,
    }


def api_admin_product_create(conn, user, body, m):
    require_admin(user)
    p = clean_product(body)
    cur = conn.execute(
        'INSERT INTO products(name, subtitle, description, price, old_price, icon, badge, delivery_type,'
        ' content, active, sort, category_id, created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
        (*[p[f] for f in PRODUCT_FIELDS], now_iso()))
    conn.commit()
    return product_public(conn, conn.execute('SELECT * FROM products WHERE id=?', (cur.lastrowid,)).fetchone(), True)


def api_admin_product_update(conn, user, body, m):
    require_admin(user)
    pid = int(m.group(1))
    if not conn.execute('SELECT id FROM products WHERE id=?', (pid,)).fetchone():
        raise ApiError(404, 'Товар не найден')
    p = clean_product(body)
    conn.execute(f"UPDATE products SET {', '.join(f'{f}=?' for f in PRODUCT_FIELDS)} WHERE id=?",
                 (*[p[f] for f in PRODUCT_FIELDS], pid))
    conn.commit()
    return product_public(conn, conn.execute('SELECT * FROM products WHERE id=?', (pid,)).fetchone(), True)


def api_admin_product_delete(conn, user, body, m):
    require_admin(user)
    conn.execute('DELETE FROM products WHERE id=?', (int(m.group(1)),))
    conn.commit()
    return {'ok': True}


def api_admin_stock_add(conn, user, body, m):
    require_admin(user)
    pid = int(m.group(1))
    if not conn.execute('SELECT id FROM products WHERE id=?', (pid,)).fetchone():
        raise ApiError(404, 'Товар не найден')
    keys = [k.strip() for k in (body.get('keys') or []) if k and k.strip()]
    if not keys:
        raise ApiError(400, 'Нет ключей для добавления')
    for key in keys:
        conn.execute('INSERT INTO stock(product_id, content) VALUES(?, ?)', (pid, key))
    conn.commit()
    return {'added': len(keys), 'stock_left': stock_left(conn, pid)}


def api_admin_categories_create(conn, user, body, m):
    require_admin(user)
    name = (body.get('name') or '').strip()
    if not name:
        raise ApiError(400, 'Название обязательно')
    conn.execute('INSERT INTO categories(name, icon, sort) VALUES(?,?,?)',
                 (name[:60], (body.get('icon') or 'folder').strip()[:80], int(body.get('sort') or 0)))
    conn.commit()
    return {'ok': True}


def api_admin_categories_update(conn, user, body, m):
    require_admin(user)
    conn.execute('UPDATE categories SET name=?, icon=?, sort=? WHERE id=?',
                 ((body.get('name') or '').strip()[:60], (body.get('icon') or 'folder').strip()[:80],
                  int(body.get('sort') or 0), int(m.group(1))))
    conn.commit()
    return {'ok': True}


def api_admin_categories_delete(conn, user, body, m):
    require_admin(user)
    conn.execute('DELETE FROM categories WHERE id=?', (int(m.group(1)),))
    conn.commit()
    return {'ok': True}


def api_admin_orders(conn, user, body, m):
    require_admin(user)
    return {'orders': [order_row(r, include_user=True, conn=conn) for r in conn.execute(
        'SELECT * FROM orders ORDER BY id DESC LIMIT 200')]}


def api_admin_order_check(conn, user, body, m):
    require_admin(user)
    order = conn.execute('SELECT * FROM orders WHERE id=?', (int(m.group(1)),)).fetchone()
    if not order:
        raise ApiError(404, 'Заказ не найден')
    return order_row(check_order_payment(conn, order), include_user=True, conn=conn)


def api_admin_promos(conn, user, body, m):
    require_admin(user)
    return {'promos': [dict(r) for r in conn.execute('SELECT * FROM promos ORDER BY id DESC')]}


def api_admin_promo_create(conn, user, body, m):
    require_admin(user)
    code = (body.get('code') or '').strip().upper()
    percent = int(body.get('percent') or 0)
    if not re.fullmatch(r'[A-Z0-9_-]{2,32}', code):
        raise ApiError(400, 'Код: 2–32 символа, латиница/цифры')
    if not 1 <= percent <= 100:
        raise ApiError(400, 'Скидка: от 1 до 100%')
    try:
        conn.execute('INSERT INTO promos(code, percent, max_uses) VALUES(?,?,?)',
                     (code, percent, int(body.get('max_uses') or 0)))
    except sqlite3.IntegrityError:
        raise ApiError(400, 'Такой код уже существует')
    conn.commit()
    return {'ok': True}


def api_admin_promo_update(conn, user, body, m):
    require_admin(user)
    conn.execute('UPDATE promos SET active=? WHERE id=?',
                 (1 if body.get('active') else 0, int(m.group(1))))
    conn.commit()
    return {'ok': True}


def api_admin_promo_delete(conn, user, body, m):
    require_admin(user)
    conn.execute('DELETE FROM promos WHERE id=?', (int(m.group(1)),))
    conn.commit()
    return {'ok': True}


def api_admin_users(conn, user, body, m):
    require_admin(user)
    rows = conn.execute(
        'SELECT u.*, COUNT(o.id) AS orders_count, COALESCE(SUM(o.total), 0) AS spent'
        " FROM users u LEFT JOIN orders o ON o.user_id=u.id AND o.status='paid'"
        ' GROUP BY u.id ORDER BY spent DESC, u.last_seen DESC LIMIT 500').fetchall()
    return {'users': [dict(r) for r in rows]}


def api_admin_user_ban(conn, user, body, m):
    require_admin(user)
    uid = int(m.group(1))
    if uid in ADMIN_IDS:
        raise ApiError(400, 'Нельзя забанить администратора')
    conn.execute('UPDATE users SET is_banned=? WHERE id=?', (1 if body.get('banned') else 0, uid))
    conn.commit()
    return {'ok': True}


def api_admin_broadcast(conn, user, body, m):
    require_admin(user)
    text = (body.get('text') or '').strip()
    if not text:
        raise ApiError(400, 'Пустое сообщение')
    ids = [r['id'] for r in conn.execute('SELECT id FROM users WHERE is_banned=0')]

    def run():
        sent = 0
        for uid in ids:
            if tg_api('sendMessage', {'chat_id': uid, 'text': text, 'parse_mode': 'HTML'}).get('ok'):
                sent += 1
            time.sleep(0.06)
        notify_admins(f'📣 Рассылка завершена: доставлено {sent} из {len(ids)}')
    threading.Thread(target=run, daemon=True).start()
    return {'started': True, 'recipients': len(ids)}


def api_admin_settings_get(conn, user, body, m):
    require_admin(user)
    return get_settings(conn)


def api_admin_settings_put(conn, user, body, m):
    require_admin(user)
    for key in DEFAULT_SETTINGS:
        if key in body:
            conn.execute('INSERT INTO settings(key, value) VALUES(?, ?)'
                         ' ON CONFLICT(key) DO UPDATE SET value=excluded.value',
                         (key, str(body[key]).strip()[:300]))
    conn.commit()
    return get_settings(conn)


ROUTES = [
    ('POST', r'/api/auth$', api_auth),
    ('GET', r'/api/shop$', api_shop),
    ('POST', r'/api/promo/check$', api_promo_check),
    ('POST', r'/api/orders$', api_order_create),
    ('GET', r'/api/orders/(\d+)$', api_order_get),
    ('GET', r'/api/my/orders$', api_my_orders),
    ('GET', r'/api/admin/overview$', api_admin_overview),
    ('GET', r'/api/admin/products$', api_admin_products),
    ('POST', r'/api/admin/products$', api_admin_product_create),
    ('PUT', r'/api/admin/products/(\d+)$', api_admin_product_update),
    ('DELETE', r'/api/admin/products/(\d+)$', api_admin_product_delete),
    ('POST', r'/api/admin/products/(\d+)/stock$', api_admin_stock_add),
    ('POST', r'/api/admin/categories$', api_admin_categories_create),
    ('PUT', r'/api/admin/categories/(\d+)$', api_admin_categories_update),
    ('DELETE', r'/api/admin/categories/(\d+)$', api_admin_categories_delete),
    ('GET', r'/api/admin/orders$', api_admin_orders),
    ('POST', r'/api/admin/orders/(\d+)/check$', api_admin_order_check),
    ('GET', r'/api/admin/promos$', api_admin_promos),
    ('POST', r'/api/admin/promos$', api_admin_promo_create),
    ('PUT', r'/api/admin/promos/(\d+)$', api_admin_promo_update),
    ('DELETE', r'/api/admin/promos/(\d+)$', api_admin_promo_delete),
    ('GET', r'/api/admin/users$', api_admin_users),
    ('POST', r'/api/admin/users/(\d+)/ban$', api_admin_user_ban),
    ('POST', r'/api/admin/broadcast$', api_admin_broadcast),
    ('GET', r'/api/admin/settings$', api_admin_settings_get),
    ('PUT', r'/api/admin/settings$', api_admin_settings_put),
]


# ---------------------------------------------------------------------------
# HTTP-сервер
# ---------------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    server_version = 'NoirMarket/1.0'

    def log_message(self, fmt, *args):
        sys.stderr.write('[%s] %s\n' % (datetime.now().strftime('%H:%M:%S'), fmt % args))

    # --- ответы ---

    def send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, path):
        try:
            with open(path, 'rb') as f:
                body = f.read()
        except OSError:
            self.send_json({'error': 'Not found'}, 404)
            return
        ctype = mimetypes.guess_type(path)[0] or 'application/octet-stream'
        if ctype.startswith('text/') or ctype in ('application/javascript', 'application/json'):
            ctype += '; charset=utf-8'
        self.send_response(200)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    # --- обработка ---

    def handle_api(self, method):
        parsed = urllib.parse.urlparse(self.path)
        body = {}
        if method in ('POST', 'PUT'):
            length = int(self.headers.get('Content-Length') or 0)
            if length:
                try:
                    body = json.loads(self.rfile.read(length).decode())
                except Exception:
                    raise ApiError(400, 'Некорректный JSON')
        for route_method, pattern, func in ROUTES:
            if route_method != method:
                continue
            match = re.match(pattern, parsed.path)
            if match:
                user = resolve_user(self.headers.get('X-Init-Data', ''))
                conn = db()
                try:
                    result = func(conn, user, body, match)
                finally:
                    conn.close()
                self.send_json(result)
                return
        raise ApiError(404, 'Неизвестный метод API')

    def handle_static(self):
        path = urllib.parse.urlparse(self.path).path
        if path in ('/', '/index.html'):
            path = '/index.html'
        target = os.path.normpath(os.path.join(WEBAPP_DIR, path.lstrip('/')))
        if not target.startswith(WEBAPP_DIR):
            self.send_json({'error': 'Forbidden'}, 403)
            return
        if not os.path.isfile(target):
            # SPA-фолбэк: любые пути отдают index.html
            target = os.path.join(WEBAPP_DIR, 'index.html')
        self.send_file(target)

    def dispatch(self, method):
        try:
            if urllib.parse.urlparse(self.path).path.startswith('/api/'):
                self.handle_api(method)
            elif method == 'GET':
                self.handle_static()
            else:
                self.send_json({'error': 'Method not allowed'}, 405)
        except ApiError as e:
            self.send_json({'error': e.message}, e.status)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:
            sys.stderr.write(f'[ERROR] {type(e).__name__}: {e}\n')
            self.send_json({'error': 'Внутренняя ошибка сервера'}, 500)

    def do_GET(self):
        self.dispatch('GET')

    def do_POST(self):
        self.dispatch('POST')

    def do_PUT(self):
        self.dispatch('PUT')

    def do_DELETE(self):
        self.dispatch('DELETE')


def main():
    if not BOT_TOKEN or not CRYPTO_TOKEN:
        sys.exit('Заполни BOT_TOKEN и CRYPTOBOT_TOKEN в .env')
    init_db()
    threading.Thread(target=bot_loop, daemon=True).start()
    server = ThreadingHTTPServer(('0.0.0.0', PORT), Handler)
    print(f'╔══════════════════════════════════════════╗')
    print(f'║  NOIR MARKET · http://localhost:{PORT}     ║')
    print(f'║  Админы: {", ".join(map(str, sorted(ADMIN_IDS))):<32}║')
    print(f'║  DEV_MODE: {"ON (браузер = админ!)" if DEV_MODE else "off":<30}║')
    print(f'╚══════════════════════════════════════════╝', flush=True)
    server.serve_forever()


if __name__ == '__main__':
    main()
