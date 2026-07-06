import os
from dotenv import load_dotenv
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CRYPTOPAY_TOKEN = os.getenv("CRYPTOPAY_TOKEN")
CRYPTOPAY_API = os.getenv("CRYPTOPAY_API", "https://testnet-pay.crypt.bot/api")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./shop.db")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://example.com/")
INIT_DATA_MAX_AGE = 86400  # 24 часа