#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Привязка мини-аппа к боту.

Когда у тебя появится публичный HTTPS-адрес (ngrok / cloudflared / VPS),
запусти:

    python3 scripts/setup_bot.py https://your-domain.com

Скрипт установит кнопку меню бота (открывает мини-апп) и описание бота.
"""

import json
import os
import sqlite3
import ssl
import sys
import urllib.request

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'data', 'shop.db')


def make_ssl_context():
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


def load_env():
    with open(os.path.join(BASE_DIR, '.env'), encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())


def tg(method, params):
    token = os.environ['BOT_TOKEN']
    req = urllib.request.Request(
        f'https://api.telegram.org/bot{token}/{method}',
        data=json.dumps(params).encode(),
        headers={'Content-Type': 'application/json', 'User-Agent': 'NoirMarket/1.0'})
    with urllib.request.urlopen(req, timeout=15, context=SSL_CTX) as r:
        return json.loads(r.read())


def main():
    if len(sys.argv) < 2 or not sys.argv[1].startswith('https://'):
        sys.exit('Использование: python3 scripts/setup_bot.py https://your-public-url.com')
    url = sys.argv[1].rstrip('/')
    load_env()

    # URL в настройки магазина — бот сразу начнёт слать кнопку в ответ на /start
    if os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        conn.execute("INSERT INTO settings(key, value) VALUES('webapp_url', ?)"
                     ' ON CONFLICT(key) DO UPDATE SET value=excluded.value', (url,))
        conn.commit()
        conn.close()
        print('URL мини-аппа сохранён в настройках магазина.')

    print('Кнопка меню…', tg('setChatMenuButton', {
        'menu_button': {'type': 'web_app', 'text': 'Магазин',
                        'web_app': {'url': url}}}))
    print('Описание…', tg('setMyDescription', {
        'description': 'Магазин цифровых товаров. Жми кнопку «Магазин» внизу — всё внутри мини-аппа. Оплата криптой через @CryptoBot.'}))
    print('Короткое описание…', tg('setMyShortDescription', {
        'short_description': 'Цифровые товары · оплата криптой · мгновенная выдача'}))
    print('\nГотово! Открой бота и нажми кнопку «Магазин».')
    print('Совет: в @BotFather можно ещё включить Main Mini App (/mybots → Bot Settings → Main Mini App) с тем же URL.')


if __name__ == '__main__':
    main()
