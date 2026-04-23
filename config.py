"""
Uygulama genelinde kullanılan ayarlar.
"""
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

log = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# ── Veritabanı yolu ──────────────────────────────────────────────
# Öncelik:
# 1. DATABASE_PATH env var (Dockerfile'da /data/salon.db olarak set edildi)
# 2. Lokal geliştirme → proje klasöründe salon.db
_db_env = os.getenv("DATABASE_PATH", "").strip()
if _db_env:
    DATABASE_PATH = Path(_db_env)
else:
    DATABASE_PATH = BASE_DIR / "salon.db"

# Klasörü garantile
try:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
except Exception:
    pass

# ── Uygulama ────────────────────────────────────────────────────
APP_NAME    = os.getenv("APP_NAME", "Sisnova Beauty")
APP_VERSION = "1.2.0"
SALON_NAME  = os.getenv("SALON_NAME", "Sisnova Beauty")

# ── SMS Sağlayıcı ────────────────────────────────────────────────
SMS_PROVIDER        = os.getenv("SMS_PROVIDER", "mock")
NETGSM_USERCODE     = os.getenv("NETGSM_USERCODE", "")
NETGSM_PASSWORD     = os.getenv("NETGSM_PASSWORD", "")
NETGSM_HEADER       = os.getenv("NETGSM_HEADER", "")
GENERIC_SMS_URL     = os.getenv("GENERIC_SMS_URL", "")
GENERIC_SMS_API_KEY = os.getenv("GENERIC_SMS_API_KEY", "")
GENERIC_SMS_SENDER  = os.getenv("GENERIC_SMS_SENDER", "")

# ── SMS Maliyet ──────────────────────────────────────────────────
# Segment başına maliyet (€). .env'de SMS_COST_PER_SEGMENT=0.02 ile override edilebilir.
SMS_COST_PER_SEGMENT = float(os.getenv("SMS_COST_PER_SEGMENT", "0.02"))

# ── Otomasyon ────────────────────────────────────────────────────
REMINDER_HOURS_BEFORE            = int(os.getenv("REMINDER_HOURS_BEFORE", "24"))
SCHEDULER_CHECK_INTERVAL_MINUTES = int(os.getenv("SCHEDULER_CHECK_INTERVAL_MINUTES", "15"))
BIRTHDAY_SEND_HOUR               = int(os.getenv("BIRTHDAY_SEND_HOUR", "10"))

MESSAGE_TEMPLATES = {
    "appointment_reminder": (
        "Merhaba {name}, yarin {time} randevunuzu hatirlatmak isteriz. "
        "Gorusmek uzere. {salon}"
    ),
    "birthday": (
        "Sevgili {name}, dogum gununuz kutlu olsun! "
        "Size ozel surprizimiz icin bekleriz. {salon}"
    ),
}
