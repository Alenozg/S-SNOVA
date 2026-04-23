"""
Giriş ekranı — mobil uyumlu, kayıt özelliği yok.
"""
import flet as ft
from ui import theme
from services import auth_service


def build_login(page: ft.Page, on_success) -> ft.Control:
    is_mobile = (page.width or 1200) < 768

    f_user = ft.TextField(
        label="Kullanıcı Adı",
        border_color=theme.DIVIDER,
        focused_border_color=theme.ACCENT,
        bgcolor=theme.SURFACE,
        border_radius=2,
        text_style=ft.TextStyle(color=theme.TEXT, size=14),
        label_style=ft.TextStyle(color=theme.TEXT_MUTED, size=12),
        content_padding=ft.padding.symmetric(horizontal=14, vertical=16),
        autofocus=not is_mobile,  # mobilde autofocus klavyeyi tetikler
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
    err_text = ft.Text("", color=theme.ERROR, size=13,
                       text_align=ft.TextAlign.CENTER)
    btn_login = ft.ElevatedButton(
        text="Giriş Yap",
        style=ft.ButtonStyle(
            bgcolor=theme.ACCENT,
            color="#FFFFFF",
            shape=ft.RoundedRectangleBorder(radius=2),
            padding=ft.padding.symmetric(horizontal=24, vertical=18),
            text_style=ft.TextStyle(weight=ft.FontWeight.W_400, size=13),
        ),
        width=9999,  # tam genişlik — mobilde buton kaymasın
    )

    def submit(e=None):
        err_text.value = ""
        username = (f_user.value or "").strip()
        password = (f_pass.value or "").strip()

        if not username or not password:
            err_text.value = "Kullanıcı adı ve şifre zorunludur."
            page.update()
            return

        user = auth_service.login(username, password)
        if user:
            on_success(user)
        else:
            err_text.value = "Kullanıcı adı veya şifre hatalı."
            f_pass.value = ""
            page.update()

    btn_login.on_click = submit
    f_user.on_submit   = submit
    f_pass.on_submit   = submit

    # Mobilde padding küçük, kart tam genişlik
    h_pad = 20 if is_mobile else 36
    v_pad = 28 if is_mobile else 32

    card = ft.Container(
        content=ft.Column(
            [
                ft.Container(height=8),
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
                ft.Container(height=8),
                f_pass,
                ft.Container(height=4),
                err_text,
                ft.Container(height=16),
                btn_login,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            tight=True, spacing=0,
        ),
        # Mobilde genişlik sınırı yok (ekran genişliğini kullan)
        width=None if is_mobile else 380,
        bgcolor=theme.SURFACE,
        border=ft.border.all(1, theme.DIVIDER),
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=h_pad, vertical=v_pad),
    )

    # Mobilde kart tam ekran genişliğinde, ortada
    if is_mobile:
        return ft.Container(
            content=ft.Column(
                [
                    ft.Container(expand=True),
                    ft.Container(
                        content=card,
                        padding=ft.padding.symmetric(horizontal=16),
                    ),
                    ft.Container(expand=True),
                ],
                expand=True,
            ),
            expand=True,
            bgcolor=theme.BG,
        )

    return ft.Container(
        content=ft.Column(
            [card],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True,
        ),
        expand=True,
        bgcolor=theme.BG,
        alignment=ft.alignment.center,
    )
