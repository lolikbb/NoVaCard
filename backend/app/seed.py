from .database import SessionLocal, Base, engine
from . import models

# Создаём таблицы
Base.metadata.create_all(bind=engine)
db = SessionLocal()

# Проверяем, есть ли уже данные
if not db.query(models.Category).first():
    print("🌱 Начинаем заполнение базы данных...")
    
    # === Категории с иконками ===
    c1 = models.Category(
        title="Подписки", 
        icon="clapperboard",  # иконка для кино/видео
        sort_order=1
    )
    c2 = models.Category(
        title="Игровые ключи", 
        icon="gamepad-2",  # иконка для игр
        sort_order=2
    )
    c3 = models.Category(
        title="Софт", 
        icon="monitor",  # иконка для софта
        sort_order=3
    )
    c4 = models.Category(
        title="Аккаунты", 
        icon="users",  # иконка для аккаунтов
        sort_order=4
    )
    c5 = models.Category(
        title="Крипто-товары", 
        icon="bitcoin",  # иконка для крипто
        sort_order=5
    )
    
    db.add_all([c1, c2, c3, c4, c5])
    db.commit()
    print("✅ Категории созданы")

    # === Товары с иконками ===
    
    # Подписки
    p1 = models.Product(
        category_id=c1.id, 
        title="Netflix Premium 1 месяц", 
        description="Доступ к аккаунту 4K UHD. До 5 устройств одновременно.",
        price=4.5, 
        asset="USDT", 
        type="subscription", 
        duration_days=30, 
        icon="tv"  # ← иконка телевизора
    )
    
    p2 = models.Product(
        category_id=c1.id, 
        title="Spotify Premium 3 месяца", 
        description="Музыка без рекламы, офлайн-режим, высокое качество.",
        price=7.99, 
        asset="USDT", 
        type="subscription", 
        duration_days=90, 
        icon="music"  # ← иконка музыки
    )
    
    p3 = models.Product(
        category_id=c1.id, 
        title="YouTube Premium 6 месяцев", 
        description="Видео без рекламы, фоновый режим, YouTube Music.",
        price=12.99, 
        asset="USDT", 
        type="subscription", 
        duration_days=180, 
        icon="youtube"  # ← иконка YouTube
    )
    
    # Игровые ключи
    p4 = models.Product(
        category_id=c2.id, 
        title="Steam Gift Card $10", 
        description="Ключ активации Steam для пополнения баланса.",
        price=11, 
        asset="USDT", 
        type="key", 
        icon="gamepad-2"  # ← иконка геймпада
    )
    
    p5 = models.Product(
        category_id=c2.id, 
        title="Xbox Game Pass Ultimate 1 месяц", 
        description="Доступ к сотням игр на Xbox и PC.",
        price=14.99, 
        asset="USDT", 
        type="key", 
        icon="controller"  # ← иконка контроллера
    )
    
    p6 = models.Product(
        category_id=c2.id, 
        title="PlayStation Plus 3 месяца", 
        description="Игры каждый месяц, онлайн-мультиплеер, скидки.",
        price=19.99, 
        asset="USDT", 
        type="key", 
        icon="play"  # ← иконка проигрывателя
    )
    
    # Софт
    p7 = models.Product(
        category_id=c3.id, 
        title="Windows 11 Pro Key", 
        description="Лицензионный ключ для Windows 11 Pro.",
        price=15, 
        asset="USDT", 
        type="key", 
        icon="monitor"  # ← иконка монитора
    )
    
    p8 = models.Product(
        category_id=c3.id, 
        title="Adobe Creative Cloud 1 месяц", 
        description="Photoshop, Premiere, After Effects и все приложения Adobe.",
        price=39.99, 
        asset="USDT", 
        type="subscription", 
        duration_days=30, 
        icon="palette"  # ← иконка палитры
    )
    
    p9 = models.Product(
        category_id=c3.id, 
        title="Microsoft Office 2021", 
        description="Word, Excel, PowerPoint, Outlook — постоянная лицензия.",
        price=29.99, 
        asset="USDT", 
        type="key", 
        icon="file-text"  # ← иконка документа
    )
    
    # Аккаунты
    p10 = models.Product(
        category_id=c4.id, 
        title="ChatGPT Plus аккаунт", 
        description="Доступ к GPT-4, быстрые ответы, приоритетное обслуживание.",
        price=12.99, 
        asset="USDT", 
        type="key", 
        icon="bot"  # ← иконка бота
    )
    
    p11 = models.Product(
        category_id=c4.id, 
        title="Instagram аккаунт 1000 подписчиков", 
        description="Готовый аккаунт с реальными подписчиками.",
        price=25.99, 
        asset="USDT", 
        type="key", 
        icon="instagram"  # ← иконка Instagram
    )
    
    # Крипто-товары
    p12 = models.Product(
        category_id=c5.id, 
        title="Крипто-кошелёк Trust Wallet", 
        description="Готовый кошелёк с seed-фразой. Мультивалютный.",
        price=5.99, 
        asset="USDT", 
        type="key", 
        icon="wallet"  # ← иконка кошелька
    )
    
    p13 = models.Product(
        category_id=c5.id, 
        title="VPN Премиум 1 год", 
        description="Безопасный доступ к интернету, обход блокировок.",
        price=49.99, 
        asset="USDT", 
        type="subscription", 
        duration_days=365, 
        icon="shield"  # ← иконка щита
    )
    
    p14 = models.Product(
        category_id=c5.id, 
        title="NFT коллекция 'CyberPunk'", 
        description="Уникальный NFT-токен. Ограниченный выпуск.",
        price=99.99, 
        asset="USDT", 
        type="key", 
        icon="image"  # ← иконка изображения
    )
    
    db.add_all([p1, p2, p3, p4, p5, p6, p7, p8, p9, p10, p11, p12, p13, p14])
    db.commit()
    print("✅ Товары созданы")

    # === Ключи для товаров с типом "key" ===
    keys_data = [
        (p4.id, "STEAM-XXXX-YYYY-ZZZZ"),
        (p4.id, "STEAM-AAAA-BBBB-CCCC"),
        (p4.id, "STEAM-1111-2222-3333"),
        (p5.id, "XBOX-1234-5678-9012"),
        (p5.id, "XBOX-3456-7890-1234"),
        (p6.id, "PSN-9999-8888-7777"),
        (p7.id, "WIN11-AAAA-BBBB-CCCC"),
        (p7.id, "WIN11-DDDD-EEEE-FFFF"),
        (p9.id, "OFFICE-1234-5678-9012"),
        (p10.id, "CHATGPT-ABCD-EFGH-IJKL"),
        (p11.id, "INSTA-USER-1234-5678"),
        (p12.id, "WALLET-SEED-12345-67890"),
        (p14.id, "NFT-CYBER-9876-5432"),
    ]
    
    for product_id, key_value in keys_data:
        db.add(models.ProductKey(product_id=product_id, value=key_value))
    
    db.commit()
    print("✅ Ключи добавлены")

    print("🎉 База данных успешно заполнена!")
else:
    print("ℹ️ База данных уже содержит данные. Для перезаполнения удалите файл shop.db")

db.close()