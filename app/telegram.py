import httpx
import config as C

class TgError(Exception): pass

def call(method, **params):
    r = httpx.post(f"{C.TG_API}/bot{C.BOT_TOKEN}/{method}", json=params, timeout=40)
    d = r.json()
    if not d.get("ok"): raise TgError(d.get("description", "unknown error"))
    return d["result"]

def available_gifts(): return call("getAvailableGifts")["gifts"]
def send_gift(user_id, gift_id, text=""): return call("sendGift", user_id=user_id, gift_id=gift_id, text=text[:128])
def gift_premium(user_id, months):
    return call("giftPremiumSubscription", user_id=user_id, month_count=months,
                star_count=C.PREMIUM_STARS[months])
def send_message(chat_id, text): return call("sendMessage", chat_id=chat_id, text=text)
def updates(offset): return call("getUpdates", offset=offset, timeout=20, allowed_updates=["message"])
