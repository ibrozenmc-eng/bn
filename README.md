# Brozen: راه‌اندازی روی سرور

1. روی سرور Ubuntu: `curl -fsSL https://get.docker.com | sh`
2. فایل‌ها را روی سرور بریز، بعد `cp .env.example .env` و `nano .env` (همه مقادیر را پر کن).
3. دامنه .ir را با رکورد A به IP سرور وصل کن، بعد `docker compose up -d --build`
4. با ثبت‌نام در سایت وارد شو (نام کاربری باید در ADMIN_USERNAMES باشد)، در /admin «همگام‌سازی گیفت‌ها» را بزن.
5. ربات را در @BotFather بساز، موجودی استارز ربات را شارژ کن، با یک سفارش کوچک تست کن.

قبل از تست پرداخت واقعی: ZARINPAL_SANDBOX=1 بگذار.
بک‌آپ: پوشه data/ را روزانه کپی کن. لاگ‌ها: `docker compose logs -f worker`
