import httpx
import config as C

BASE = "https://sandbox.zarinpal.com" if C.ZP_SANDBOX else "https://payment.zarinpal.com"
class ZPError(Exception): pass

def _post(path, body):
    r = httpx.post(f"{BASE}/pg/v4/payment/{path}.json", json=body, timeout=30,
                   headers={"Accept": "application/json"})
    j = r.json()
    d = j.get("data")
    return d if isinstance(d, dict) and d else {"code": (j.get("errors") or {}).get("code", -1)}

def start(amount_toman, desc, callback):
    d = _post("request", {"merchant_id": C.ZP_MERCHANT, "amount": amount_toman * 10,
                          "callback_url": callback, "description": desc})
    if d.get("code") != 100: raise ZPError(f"request code={d.get('code')}")
    return d["authority"]

def pay_url(authority): return f"{BASE}/pg/StartPay/{authority}"

def verify(amount_toman, authority):
    d = _post("verify", {"merchant_id": C.ZP_MERCHANT, "amount": amount_toman * 10, "authority": authority})
    if d.get("code") not in (100, 101): raise ZPError(f"verify code={d.get('code')}")
    return d.get("ref_id")
