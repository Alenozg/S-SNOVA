"""
Sisnova Beauty CRM — giriş noktası.
"""
import atexit
import logging
import os
import sys

import flet as ft

import config
from database import init_database
from services import scheduler_service
from services.auth_service import seed_admin
from ui import SalonApp, theme
from ui.views.login_view import build_login

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("salon_crm")


def _is_web_mode() -> bool:
    if os.environ.get("FLET_MODE", "").lower() == "web":
        return True
    if os.environ.get("PORT"):
        return True
    return False


IS_WEB = _is_web_mode()

# Aktif kullanıcı session (page session key)
SESSION_KEY = "current_user"


def main(page: ft.Page) -> None:
    page.title = config.APP_NAME
    page.bgcolor = theme.BG
    page.padding = 0

    if not IS_WEB:
        try:
            page.window.width = 1280
            page.window.height = 820
            page.window.min_width = 1080
            page.window.min_height = 720
        except Exception:
            pass

    try:
        page.theme = ft.Theme(
            color_scheme_seed=theme.ACCENT,
            font_family=theme.FONT_FAMILY_BODY,
            use_material3=True,
        )
    except Exception:
        page.theme = ft.Theme(color_scheme_seed=theme.ACCENT)

    def load_app(user: dict):
        """Giriş başarılıysa ana uygulamayı yükle."""
        try:
            page.session.set(SESSION_KEY, user)
        except Exception:
            pass
        page.controls.clear()
        page.appbar = None
        page.drawer = None
        page.update()
        app = SalonApp(page, current_user=user)
        app.mount()

    def show_login():
        page.controls.clear()
        page.appbar = None
        page.drawer = None
        page.update()
        login_ctrl = build_login(page, on_success=load_app)
        page.add(login_ctrl)
        page.update()

    # Oturum yoksa login göster
    show_login()


def bootstrap() -> None:
    import os as _os
    from database.db_manager import _USE_PG

    if _USE_PG:
        log.info("Veritabani modu: POSTGRESQL — veriler kalici olarak saklanir.")
    else:
        db_path = config.DATABASE_PATH
        db_exists = db_path.exists()
        db_size   = db_path.stat().st_size if db_exists else 0
        log.info("Veritabani modu: SQLITE — %s (mevcut=%s, boyut=%d bytes)",
                 db_path, db_exists, db_size)

    init_database()
    seed_admin()

    # Başlangıç teşhisi — volume çalışıyor mu?
    try:
        from database.db_manager import fetch_one
        row = fetch_one("SELECT COUNT(*) as cnt FROM customers")
        cust_count = row["cnt"] if row else 0
        row2 = fetch_one("SELECT COUNT(*) as cnt FROM users")
        user_count = row2["cnt"] if row2 else 0
        new_size = db_path.stat().st_size if db_path.exists() else 0
        log.info("DB DURUM: musteriler=%d, kullanicilar=%d, dosya_boyutu=%d bytes",
                 cust_count, user_count, new_size)
        if cust_count == 0:
            log.warning("DB UYARI: Musteri bulunamadi. Volume mount edildi mi? (/data)")
        else:
            log.info("DB OK: Veriler korunuyor (%d musteri)", cust_count)
    except Exception as e:
        log.error("DB teşhis hatası: %s", e)
    log.info("SMS saglayici: %s", config.SMS_PROVIDER)

    if IS_WEB:
        log.info("Web modu: zamanlayici atlaniyor (ephemeral ortam).")
        return
    try:
        log.info("Zamanlayici baslatiliyor...")
        scheduler_service.start()
        atexit.register(scheduler_service.shutdown)
    except Exception as e:
        log.warning("Zamanlayici baslatilamadi: %s", e)


if __name__ == "__main__":
    bootstrap()

    if IS_WEB:
        port = int(os.environ.get("PORT", 8080))
        log.info("Web modu: host=0.0.0.0, port=%d", port)

        web_view = "web_browser"
        try:
            web_view = ft.AppView.WEB_BROWSER
        except AttributeError:
            try:
                web_view = ft.WEB_BROWSER
            except AttributeError:
                pass

        # FLET_SECRET_KEY env var olarak okunur (railway.toml'da set edildi)
        ft.app(
            target=main,
            view=web_view,
            host="0.0.0.0",
            port=port,
            upload_dir="/tmp/flet_uploads",
        )
    else:
        log.info("Masaustu modu")
        ft.app(target=main)
