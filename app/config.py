import os
e = os.getenv
BOT_TOKEN = e("BOT_TOKEN", "")
BOT_USERNAME = e("BOT_USERNAME", "")
DATABASE_URL = e("DATABASE_URL", "sqlite:////data/brozen.db")
SECRET_KEY = e("SECRET_KEY", "change-me")
SITE_URL = e("SITE_URL", "http://localhost:8000").rstrip("/")
ZP_MERCHANT = e("ZARINPAL_MERCHANT", "")
ZP_SANDBOX = e("ZARINPAL_SANDBOX", "0") == "1"
ADMINS = {x.strip() for x in e("ADMIN_USERNAMES", "").split(",") if x.strip()}
STAR_PRICE_TOMAN = float(e("STAR_PRICE_TOMAN", "1500"))
MARGIN = float(e("MARGIN", "0.12"))
TG_API = e("TG_API", "https://api.telegram.org")
PREMIUM_STARS = {3: 1000, 6: 1500, 12: 2500}  # طبق مستندات Bot API
