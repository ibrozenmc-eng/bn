import os, hashlib, hmac
from datetime import datetime
from sqlalchemy import create_engine, String, Integer, BigInteger, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
import config as C

kw = {"connect_args": {"timeout": 30}} if C.DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(C.DATABASE_URL, **kw)
SessionLocal = sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase): pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(32), unique=True)
    pw: Mapped[str] = mapped_column(String(200))
    tg_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, nullable=True)
    tg_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    link_code: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    created: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Product(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(10))   # gift | premium
    ref: Mapped[str] = mapped_column(String(64))    # gift_id یا تعداد ماه
    title: Mapped[str] = mapped_column(String(100))
    stars: Mapped[int] = mapped_column(Integer)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class Order(Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    amount: Mapped[int] = mapped_column(Integer)            # تومان
    # pending → paid → sending → delivered | failed | cancelled
    status: Mapped[str] = mapped_column(String(12), default="pending", index=True)
    authority: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    ref_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

def hash_pw(p, salt=None):
    salt = salt or os.urandom(16).hex()
    h = hashlib.pbkdf2_hmac("sha256", p.encode(), bytes.fromhex(salt), 200_000).hex()
    return f"{salt}${h}"

def check_pw(p, stored):
    salt, h = stored.split("$")
    return hmac.compare_digest(hash_pw(p, salt).split("$")[1], h)

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()
