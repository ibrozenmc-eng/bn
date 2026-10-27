"""ارسال خودکار + اتصال حساب تلگرام. باید روی سروری اجرا بشه که به تلگرام دسترسی داره."""
import time, traceback
from datetime import datetime
from sqlalchemy import select, update
from db import SessionLocal, User, Product, Order
import telegram as tg

offset = 0

def poll_bot():
    global offset
    for u in tg.updates(offset):
        offset = u["update_id"] + 1
        m = u.get("message") or {}
        text = (m.get("text") or "").strip()
        frm = m.get("from") or {}
        if not text.startswith("/start") or not frm.get("id"): continue
        code = text.split(maxsplit=1)[1] if " " in text else ""
        with SessionLocal() as db:
            user = db.scalar(select(User).where(User.link_code == code)) if code else None
            if not user:
                tg.send_message(frm["id"], "سلام! برای اتصال، از داخل پروفایل سایت Brozen روی «اتصال تلگرام» بزن.")
                continue
            taken = db.scalar(select(User).where(User.tg_id == frm["id"], User.id != user.id))
            if taken:
                tg.send_message(frm["id"], "این تلگرام قبلاً به حساب دیگری وصل شده.")
                continue
            user.tg_id, user.tg_name, user.link_code = frm["id"], frm.get("first_name"), None
            db.commit()
            tg.send_message(frm["id"], f"✅ حساب {user.username} به تلگرام وصل شد.")

def deliver_paid():
    with SessionLocal() as db:
        ids = db.scalars(select(Order.id).where(Order.status == "paid").order_by(Order.id).limit(20)).all()
    for oid in ids:
        with SessionLocal() as db:
            # قفل اتمیک: فقط یک بار می‌تونه از paid به sending بره (جلوگیری از ارسال دوباره)
            if db.execute(update(Order).where(Order.id == oid, Order.status == "paid").values(status="sending")).rowcount != 1:
                continue
            db.commit()
            o = db.get(Order, oid); u = db.get(User, o.user_id); p = db.get(Product, o.product_id)
            try:
                if not u.tg_id: raise RuntimeError("تلگرام کاربر وصل نیست")
                if p.kind == "gift": tg.send_gift(u.tg_id, p.ref, "Brozen")
                else: tg.gift_premium(u.tg_id, int(p.ref))
                o.status, o.delivered_at = "delivered", datetime.utcnow()
                try: tg.send_message(u.tg_id, f"🎁 سفارش #{o.id} ارسال شد.")
                except Exception: pass
            except Exception as ex:
                o.status, o.error = "failed", str(ex)[:300]
            db.commit()

if __name__ == "__main__":
    print("worker started")
    while True:
        for fn in (poll_bot, deliver_paid):
            try: fn()
            except Exception: traceback.print_exc(); time.sleep(3)
        time.sleep(1)
