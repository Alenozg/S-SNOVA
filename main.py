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
        page.session.set(SESSION_KEY, user)
        page.controls.clear()
        app = SalonApp(page, current_user=user)
        app.mount()

    def show_login():
        page.controls.clear()
        login_ctrl = build_login(page, on_success=load_app)
        page.add(login_ctrl)

    # Oturum yoksa login göster
    show_login()


def bootstrap() -> None:
    log.info("Veritabani baslatiliyor: %s", config.DATABASE_PATH)
    init_database()
    seed_admin()
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

        ft.app(target=main, view=web_view, host="0.0.0.0", port=port)
    else:
        log.info("Masaustu modu")
        ft.app(target=main)
