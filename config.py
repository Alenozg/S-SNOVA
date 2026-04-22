"""
Uygulama genelinde kullanılan ayarlar.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# ── Veritabanı yolu ──────────────────────────────────────────────
# Öncelik sırası:
# 1. DATABASE_PATH env var (Railway Volume için: /data/salon.db)
# 2. Railway ortamı otomatik algıla → /data/salon.db
# 3. Lokal geliştirme → proje klasöründe salon.db
_db_env = os.getenv("DATABASE_PATH", "").strip()

if _db_env:
    DATABASE_PATH = Path(_db_env)
elif os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_PROJECT_ID"):
    # Railway üzerindeyiz → Volume /data'ya mount edilmiş beklenir
    DATABASE_PATH = Path("/data/salon.db")
elif os.getenv("PORT"):
    # Başka bir cloud ortamı
    DATABASE_PATH = Path("/data/salon.db")
else:
    # Lokal
    DATABASE_PATH = BASE_DIR / "salon.db"

# Klasörün var olduğundan emin ol (Volume mount edilmişse /data zaten var)
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

# ── Uygulama ────────────────────────────────────────────────────
APP_NAME    = os.getenv("APP_NAME", "Sisnova Beauty")
APP_VERSION = "1.2.0"
SALON_NAME  = os.getenv("SALON_NAME", "Sisnova Beauty")

# ── SMS Sağlayıcı ────────────────────────────────────────────────
SMS_PROVIDER       = os.getenv("SMS_PROVIDER", "mock")
NETGSM_USERCODE    = os.getenv("NETGSM_USERCODE", "")
NETGSM_PASSWORD    = os.getenv("NETGSM_PASSWORD", "")
NETGSM_HEADER      = os.getenv("NETGSM_HEADER", "")
GENERIC_SMS_URL    = os.getenv("GENERIC_SMS_URL", "")
GENERIC_SMS_API_KEY = os.getenv("GENERIC_SMS_API_KEY", "")
GENERIC_SMS_SENDER  = os.getenv("GENERIC_SMS_SENDER", "")

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
