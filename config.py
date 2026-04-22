"""
Uygulama genelinde kullanılan ayarlar.
Üretim ortamında hassas bilgileri .env dosyasına taşıyın.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# .env varsa yükle
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# --- Veritabanı ---
DATABASE_PATH = BASE_DIR / "salon.db"

# --- Uygulama ---
APP_NAME = "Sisnova Beauty"
APP_VERSION = "1.1.0"

# --- SMS Sağlayıcı ---
# Desteklenen: "netgsm", "generic_rest", "mock"
# "mock" gerçek SMS göndermez; geliştirme için log yazar.
SMS_PROVIDER = os.getenv("SMS_PROVIDER", "mock")

# Netgsm ayarları
NETGSM_USERCODE = os.getenv("NETGSM_USERCODE", "")
NETGSM_PASSWORD = os.getenv("NETGSM_PASSWORD", "")
NETGSM_HEADER = os.getenv("NETGSM_HEADER", "")  # Onaylı SMS başlığı (gönderici adı)

# Generic REST ayarları (ör. İletimerkezi, Mutlucell vb.)
GENERIC_SMS_URL = os.getenv("GENERIC_SMS_URL", "")
GENERIC_SMS_API_KEY = os.getenv("GENERIC_SMS_API_KEY", "")
GENERIC_SMS_SENDER = os.getenv("GENERIC_SMS_SENDER", "")

# --- Otomasyon ---
# Randevu hatırlatması kaç saat önce gönderilsin
REMINDER_HOURS_BEFORE = 24
# Arka plan zamanlayıcı kontrol aralığı (dakika)
SCHEDULER_CHECK_INTERVAL_MINUTES = 15
# Doğum günü SMS'lerinin gönderileceği saat (00-23)
BIRTHDAY_SEND_HOUR = 10

# --- Mesaj Şablonları ---
# {name} değişkeni müşterinin adıyla değiştirilir.
# {date}, {time}, {service} randevu değişkenleri.
MESSAGE_TEMPLATES = {
    "appointment_reminder": (
        "Merhaba {name}, yarın {time} randevunuzu hatirlatmak isteriz. "
        "Gorusmek uzere. {salon}"
    ),
    "birthday": (
        "Sevgili {name}, dogum gununuz kutlu olsun! "
        "Size ozel surprizimiz icin bekleriz. {salon}"
    ),
}

SALON_NAME = os.getenv("SALON_NAME", "Sisnova Beauty")
