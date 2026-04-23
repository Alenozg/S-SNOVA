"""
Giriş ekranı — mobil + masaüstü uyumlu.
"""
import flet as ft
from ui import theme
from services import auth_service


def build_login(page: ft.Page, on_success) -> ft.Control:

    f_user = ft.TextField(
        label="Kullanıcı Adı",
        border_color=theme.DIVIDER,
        focused_border_color=theme.ACCENT,
        bgcolor=theme.SURFACE,
        border_radius=2,
        text_style=ft.TextStyle(color=theme.TEXT, size=14),
        label_style=ft.TextStyle(color=theme.TEXT_MUTED, size=12),
        content_padding=ft.padding.symmetric(horizontal=14, vertical=16),
    )
    f_pass = ft.TextField(
        label="Şifre",
        password=True,
        can_reveal_password=True,
        border_color=theme.DIVIDER,
        focused_border_color=theme.ACCENT,
        bgcolor=theme.SURFACE,
        border_radius=2,
        text_style=ft.TextStyle(color=theme.TEXT, size=14),
        label_style=ft.TextStyle(color=theme.TEXT_MUTED, size=12),
        content_padding=ft.padding.symmetric(horizontal=14, vertical=16),
    )
    err_text = ft.Text(
        "", color=theme.ERROR, size=13,
        text_align=ft.TextAlign.CENTER,
    )

    btn_login = ft.ElevatedButton(
        text="Giriş Yap",
        style=ft.ButtonStyle(
            bgcolor=theme.ACCENT,
            color="#FFFFFF",
            shape=ft.RoundedRectangleBorder(radius=2),
            padding=ft.padding.symmetric(horizontal=24, vertical=18),
            text_style=ft.TextStyle(weight=ft.FontWeight.W_400, size=14),
        ),
    )

    def submit(e=None):
        err_text.value = ""
        try:
            page.update()
        except Exception:
            pass

        username = (f_user.value or "").strip()
        password = (f_pass.value or "").strip()

        if not username or not password:
            err_text.value = "Kullanıcı adı ve şifre zorunludur."
            try:
                page.update()
            except Exception:
                pass
            return

        try:
            user = auth_service.login(username, password)
        except Exception as ex:
            err_text.value = f"Bağlantı hatası: {ex}"
            try:
                page.update()
            except Exception:
                pass
            return

        if user:
            try:
                on_success(user)
            except Exception as ex:
                err_text.value = f"Yükleme hatası: {ex}"
                try:
                    page.update()
                except Exception:
                    pass
        else:
            err_text.value = "Kullanıcı adı veya şifre hatalı."
            f_pass.value = ""
            try:
                page.update()
            except Exception:
                pass

    btn_login.on_click = submit
    f_user.on_submit   = submit
    f_pass.on_submit   = submit

    # Kart — sabit genişlik yok, padding ile responsive
    card = ft.Container(
        content=ft.Column(
            [
                ft.Text(
                    "Giriş Yap", size=26, weight=ft.FontWeight.W_300,
                    color=theme.TEXT, font_family=theme.FONT_FAMILY_DISPLAY,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Container(height=4),
                ft.Text(
                    "Sisnova Beauty CRM", size=12, color=theme.TEXT_MUTED,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Container(height=24),
                f_user,
                ft.Container(height=10),
                f_pass,
                ft.Container(height=8),
                err_text,
                ft.Container(height=16),
                ft.Row(
                    [btn_login],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            tight=True,
            spacing=0,
        ),
        bgcolor=theme.SURFACE,
        border=ft.border.all(1, theme.DIVIDER),
        border_radius=10,
        padding=ft.padding.symmetric(horizontal=28, vertical=32),
    )

    # Dış kapsayıcı: ortalar + scroll (mobil klavye için)
    return ft.Container(
        content=ft.Column(
            [
                ft.Container(expand=True),
                ft.Container(
                    content=card,
                    # Max genişlik 400, kenarlar 20px padding
                    padding=ft.padding.symmetric(horizontal=20),
                    alignment=ft.alignment.center,
                ),
                ft.Container(expand=True),
            ],
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        ),
        expand=True,
        bgcolor=theme.BG,
    )
