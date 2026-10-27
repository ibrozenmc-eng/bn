import math, re, secrets, time
from datetime import datetime
from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy import select
import config as C, telegram as tg, zarinpal as zp
from db import *

Base.metadata.create_all(engine)
with SessionLocal() as _db:
    if not _db.scalar(select(Product).where(Product.kind == "premium")):
        for m, s in C.PREMIUM_STARS.items():
            _db.add(Product(kind="premium", ref=str(m), title=f"پریمیوم تلگرام {m} ماهه", stars=s))
        _db.commit()

app = FastAPI(docs_url=None, redoc_url=None)
app.add_middleware(SessionMiddleware, secret_key=C.SECRET_KEY, same_site="lax",
                   https_only=C.SITE_URL.startswith("https"), max_age=14 * 86400)
app.mount("/static", StaticFiles(directory="static"), name="static")
T = Jinja2Templates(directory="templates")
_tries: dict = {}

def price(stars): return int(math.ceil(stars * C.STAR_PRICE_TOMAN * (1 + C.MARGIN) / 1000) * 1000)

def current(request, db):
    uid = request.session.get("uid")
    return db.get(User, uid) if uid else None

def page(request, name, user=None, **ctx):
    return T.TemplateResponse(request, name, {"user": user, "price": price, "admins": C.ADMINS,
                                              "flash": request.session.pop("flash", None), "bot": C.BOT_USERNAME, **ctx})

def go(request, url, msg=None):
    if msg: request.session["flash"] = msg
    return RedirectResponse(url, status_code=303)

def throttle(request):
    ip = request.client.host if request.client else "x"
    hits = [t for t in _tries.get(ip, []) if time.time() - t < 300]
    _tries[ip] = hits + [time.time()]
    return len(hits) >= 10

@app.get("/")
def index(request: Request, db=Depends(get_db)):
    prods = db.scalars(select(Product).where(Product.active == True).order_by(Product.stars)).all()
    return page(request, "index.html", current(request, db),
                premium=[p for p in prods if p.kind == "premium"], gifts=[p for p in prods if p.kind == "gift"])

@app.api_route("/register", methods=["GET", "POST"])
async def register(request: Request, db=Depends(get_db)):
    if request.method == "GET": return page(request, "auth.html", mode="register")
    f = await request.form(); u, p = (f.get("username") or "").strip(), f.get("password") or ""
    if throttle(request): return go(request, "/register", "تلاش زیاد؛ چند دقیقه بعد دوباره امتحان کن.")
    if not re.fullmatch(r"[A-Za-z0-9_]{3,24}", u) or len(p) < 8:
        return go(request, "/register", "نام کاربری ۳ تا ۲۴ حرف انگلیسی/عدد و رمز حداقل ۸ کاراکتر باشد.")
    if db.scalar(select(User).where(User.username == u)): return go(request, "/register", "این نام کاربری گرفته شده.")
    user = User(username=u, pw=hash_pw(p)); db.add(user); db.commit()
    request.session["uid"] = user.id
    return go(request, "/dashboard", "ثبت‌نام انجام شد. حالا تلگرامت را وصل کن.")

@app.api_route("/login", methods=["GET", "POST"])
async def login(request: Request, db=Depends(get_db)):
    if request.method == "GET": return page(request, "auth.html", mode="login")
    f = await request.form()
    if throttle(request): return go(request, "/login", "تلاش زیاد؛ چند دقیقه بعد دوباره امتحان کن.")
    user = db.scalar(select(User).where(User.username == (f.get("username") or "").strip()))
    if not user or not check_pw(f.get("password") or "", user.pw): return go(request, "/login", "نام کاربری یا رمز اشتباه است.")
    request.session["uid"] = user.id
    return go(request, "/dashboard")

@app.get("/logout")
def logout(request: Request):
    request.session.clear(); return go(request, "/")

@app.get("/dashboard")
def dashboard(request: Request, db=Depends(get_db)):
    user = current(request, db)
    if not user: return go(request, "/login")
    if not user.tg_id and not user.link_code:
        user.link_code = secrets.token_urlsafe(12); db.commit()
    rows = db.execute(select(Order, Product).join(Product, Product.id == Order.product_id)
                      .where(Order.user_id == user.id).order_by(Order.id.desc())).all()
    return page(request, "dashboard.html", user, rows=rows)

@app.post("/buy/{pid}")
def buy(pid: int, request: Request, db=Depends(get_db)):
    user = current(request, db)
    if not user: return go(request, "/login", "اول وارد شو.")
    if not user.tg_id: return go(request, "/dashboard", "قبل از خرید، تلگرامت را وصل کن.")
    p = db.get(Product, pid)
    if not p or not p.active: return go(request, "/", "این محصول موجود نیست.")
    o = Order(user_id=user.id, product_id=p.id, amount=price(p.stars)); db.add(o); db.commit()
    try:
        o.authority = zp.start(o.amount, f"{p.title} - سفارش {o.id}", f"{C.SITE_URL}/pay/callback")
        db.commit()
    except Exception as ex:
        o.status, o.error = "failed", str(ex)[:200]; db.commit()
        return go(request, "/dashboard", "اتصال به درگاه ناموفق بود. دوباره تلاش کن.")
    return RedirectResponse(zp.pay_url(o.authority), status_code=303)

@app.get("/pay/callback")
def callback(request: Request, Authority: str = "", Status: str = "", db=Depends(get_db)):
    o = db.scalar(select(Order).where(Order.authority == Authority)) if Authority else None
    if not o: return go(request, "/")
    msg = None
    if o.status == "pending":
        if Status == "OK":
            try:
                o.ref_id = str(zp.verify(o.amount, Authority)); o.status, o.paid_at = "paid", datetime.utcnow()
                msg = "پرداخت تأیید شد؛ ارسال خودکار شروع شد."
            except Exception as ex:
                o.error = str(ex)[:200]; msg = "تأیید پرداخت انجام نشد. اگر پول کم شده، تا چند دقیقه بعد خودکار برگشت می‌خورد."
        else:
            o.status, msg = "cancelled", "پرداخت لغو شد."
        db.commit()
    return go(request, "/dashboard", msg)

def admin(request, db):
    u = current(request, db)
    return u if u and u.username in C.ADMINS else None

@app.get("/admin")
def admin_home(request: Request, db=Depends(get_db)):
    u = admin(request, db)
    if not u: return go(request, "/")
    rows = db.execute(select(Order, Product, User).join(Product).join(User, User.id == Order.user_id)
                      .order_by(Order.id.desc()).limit(100)).all()
    return page(request, "admin.html", u, rows=rows, prods=db.scalars(select(Product).order_by(Product.kind, Product.stars)).all())

@app.post("/admin/sync")
def sync(request: Request, db=Depends(get_db)):
    if not admin(request, db): return go(request, "/")
    try:
        n = 0
        for g in tg.available_gifts():
            p = db.scalar(select(Product).where(Product.kind == "gift", Product.ref == g["id"]))
            title = f"{(g.get('sticker') or {}).get('emoji', '🎁')} گیفت {g['star_count']} استارزی"
            if p: p.stars, p.title = g["star_count"], title
            else: db.add(Product(kind="gift", ref=g["id"], title=title, stars=g["star_count"])); n += 1
        db.commit(); return go(request, "/admin", f"{n} گیفت جدید اضافه شد.")
    except Exception as ex:
        return go(request, "/admin", f"خطا (این سرور به تلگرام وصل است؟): {ex}")

@app.post("/admin/retry/{oid}")
def retry(oid: int, request: Request, db=Depends(get_db)):
    if not admin(request, db): return go(request, "/")
    o = db.get(Order, oid)
    if o and o.status == "failed" and o.paid_at:  # فقط سفارش پرداخت‌شده
        o.status, o.error = "paid", None; db.commit()
    return go(request, "/admin")

@app.post("/admin/toggle/{pid}")
def toggle(pid: int, request: Request, db=Depends(get_db)):
    if not admin(request, db): return go(request, "/")
    p = db.get(Product, pid)
    if p: p.active = not p.active; db.commit()
    return go(request, "/admin")
