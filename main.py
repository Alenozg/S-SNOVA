"""
Uygulama giriş noktası.

Çalıştırma:
    python main.py                 # masaüstü modu (varsayılan)
    FLET_MODE=web python main.py   # web modu (yerel test)
    Railway/üretim:                # PORT env değişkeni varsa otomatik web modu

Railway / bulut dağıtımı:
    - PORT env değişkeni Railway tarafından otomatik set edilir.
    - Web modunda ft.WEB_BROWSER ve host="0.0.0.0" kullanılır.
"""
import atexit
import logging
import os
import sys

import flet as ft

import config
from database import init_database
from services import scheduler_service
from ui import SalonApp, theme


# ---------- Loglama ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("salon_crm")


# ---------- Ortam tespiti ----------
def _is_web_mode() -> bool:
    """Web modunda çalışıyor muyuz?
    Railway/Heroku gibi platformlar PORT env'ını set eder.
    FLET_MODE=web ile manuel zorlanabilir."""
    if os.environ.get("FLET_MODE", "").lower() == "web":
        return True
    if os.environ.get("PORT"):   # Railway, Heroku, Render, vb.
        return True
    return False


IS_WEB = _is_web_mode()


# ---------- Sayfa main fonksiyonu ----------
def main(page: ft.Page) -> None:
    page.title = config.APP_NAME

    # Pencere ayarları sadece masaüstünde geçerli.
    # Web modunda page.window None olabilir veya set edilmesi hata verir.
    if not IS_WEB:
        try:
            page.window.width = 1280
            page.window.height = 820
            page.window.min_width = 1080
            page.window.min_height = 720
        except Exception as e:
            log.debug("Pencere ayarlari uygulanamadi: %s", e)

    theme.apply(page)

    # Uygulamayı monte et
    app = SalonApp(page)
    app.mount()


# ---------- Bootstrap: DB + scheduler ----------
def bootstrap() -> None:
    log.info("Veritabani baslatiliyor: %s", config.DATABASE_PATH)
    init_database()

    log.info("SMS saglayici: %s", config.SMS_PROVIDER)

    # Scheduler sadece masaüstünde çalışsın.
    # Web/bulut ortamında (Railway gibi) container ephemeral olduğu için
    # scheduler'ın kalıcı bir faydası yok; ayrıca hem worker hem request
    # thread'i tek process'te çalıştığından APScheduler beklenmedik
    # davranabilir. Gerekirse production'da ayrı bir worker kur.
    if IS_WEB:
        log.info("Web modu: zamanlayici atlaniyor (ephemeral ortam).")
        return

    try:
        log.info("Zamanlayici baslatiliyor...")
        scheduler_service.start()
        atexit.register(scheduler_service.shutdown)
    except Exception as e:
        log.warning("Zamanlayici baslatilamadi: %s", e)


# ---------- Giriş noktası ----------
if __name__ == "__main__":
    bootstrap()

    if IS_WEB:
        # Railway / bulut: web tarayıcıda erişilebilir sunucu
        port = int(os.environ.get("PORT", 8080))
        log.info("Web modu: host=0.0.0.0, port=%d", port)

        # Flet 0.24, 0.25, 0.26+ arasında WEB_BROWSER sabiti farklı yerlerde:
        #   - 0.24:   ft.WEB_BROWSER        (module-level constant)
        #   - 0.25+:  ft.AppView.WEB_BROWSER (enum)
        # En uyumlu yol: string kullanmak. Flet'in her sürümü bunu kabul eder.
        web_view = "web_browser"
        # Mümkünse enum kullan (daha type-safe), olmazsa string'de kal
        try:
            web_view = ft.AppView.WEB_BROWSER
        except AttributeError:
            try:
                web_view = ft.WEB_BROWSER
            except AttributeError:
                pass  # string fallback kalır

        ft.app(
            target=main,
            view=web_view,
            host="0.0.0.0",
            port=port,
        )
    else:
        # Masaüstü: normal Flet penceresi
        log.info("Masaustu modu")
        ft.app(target=main)
