"""
Giriş / Kayıt ekranı — Flet 0.25.2 web uyumlu.
"""
import flet as ft
from ui import theme
from services import auth_service


def build_login(page: ft.Page, on_success) -> ft.Control:
    """
    on_success(user_dict) → giriş başarılı olduğunda çağrılır.
    """
    # ── state ──
    mode = {"v": "login"}   # "login" | "register"

    # ── alanlar ──
    f_name  = ft.TextField(
        label="Ad Soyad", border_color=theme.DIVIDER,
        focused_border_color=theme.ACCENT, bgcolor=theme.SURFACE,
        border_radius=2, text_style=ft.TextStyle(color=theme.TEXT, size=14),
        label_style=ft.TextStyle(color=theme.TEXT_MUTED, size=12),
        content_padding=ft.padding.symmetric(horizontal=14, vertical=16),
        visible=False,
    )
    f_email = ft.TextField(
        label="E-posta", border_color=theme.DIVIDER,
        focused_border_color=theme.ACCENT, bgcolor=theme.SURFACE,
        border_radius=2, text_style=ft.TextStyle(color=theme.TEXT, size=14),
        label_style=ft.TextStyle(color=theme.TEXT_MUTED, size=12),
        content_padding=ft.padding.symmetric(horizontal=14, vertical=16),
        keyboard_type=ft.KeyboardType.EMAIL,
    )
    f_pass  = ft.TextField(
        label="Şifre", password=True, can_reveal_password=True,
        border_color=theme.DIVIDER, focused_border_color=theme.ACCENT,
        bgcolor=theme.SURFACE, border_radius=2,
        text_style=ft.TextStyle(color=theme.TEXT, size=14),
        label_style=ft.TextStyle(color=theme.TEXT_MUTED, size=12),
        content_padding=ft.padding.symmetric(horizontal=14, vertical=16),
    )
    f_pass2 = ft.TextField(
        label="Şifre Tekrar", password=True, can_reveal_password=True,
        border_color=theme.DIVIDER, focused_border_color=theme.ACCENT,
        bgcolor=theme.SURFACE, border_radius=2,
        text_style=ft.TextStyle(color=theme.TEXT, size=14),
        label_style=ft.TextStyle(color=theme.TEXT_MUTED, size=12),
        content_padding=ft.padding.symmetric(horizontal=14, vertical=16),
        visible=False,
    )
    err_text  = ft.Text("", color=theme.ERROR, size=13, text_align=ft.TextAlign.CENTER)
    title_txt = ft.Text("Giriş Yap", size=28, weight=ft.FontWeight.W_300,
                        color=theme.TEXT, font_family=theme.FONT_FAMILY_DISPLAY,
                        text_align=ft.TextAlign.CENTER)
    btn_main  = theme.primary_button("Giriş Yap")
    toggle_btn = ft.TextButton(
        "Hesabın yok mu? Kayıt ol",
        style=ft.ButtonStyle(color=theme.TEXT_MUTED),
    )

    form_col = ft.Column(
        [f_name, f_email, f_pass, f_pass2, err_text],
        spacing=12, tight=True,
    )

    def switch_mode(e=None):
        err_text.value = ""
        if mode["v"] == "login":
            mode["v"] = "register"
            title_txt.value = "Kayıt Ol"
            btn_main.text   = "Kayıt Ol"
            f_name.visible  = True
            f_pass2.visible = True
            toggle_btn.text = "Zaten hesabın var mı? Giriş yap"
        else:
            mode["v"] = "login"
            title_txt.value = "Giriş Yap"
            btn_main.text   = "Giriş Yap"
            f_name.visible  = False
            f_pass2.visible = False
            toggle_btn.text = "Hesabın yok mu? Kayıt ol"
        page.update()

    def submit(e=None):
        err_text.value = ""
        email    = (f_email.value or "").strip()
        password = (f_pass.value  or "").strip()

        if mode["v"] == "login":
            user = auth_service.login(email, password)
            if user:
                on_success(user)
            else:
                err_text.value = "E-posta veya şifre hatalı."
                page.update()
        else:
            name = (f_name.value or "").strip()
            p2   = (f_pass2.value or "").strip()
            if password != p2:
                err_text.value = "Şifreler eşleşmiyor."
                page.update()
                return
            ok, msg = auth_service.register(email, password, name)
            if ok:
                err_text.value = ""
                # Otomatik giriş
                user = auth_service.login(email, password)
                if user:
                    on_success(user)
            else:
                err_text.value = msg
                page.update()

    btn_main.on_click   = submit
    toggle_btn.on_click = switch_mode

    # Enter tuşu ile submit
    f_pass.on_submit  = submit
    f_pass2.on_submit = submit
    f_email.on_submit = submit

    card = ft.Container(
        content=ft.Column(
            [
                ft.Container(height=8),
                title_txt,
                ft.Container(height=4),
                ft.Text("Sisnova Beauty CRM", size=12, color=theme.TEXT_MUTED,
                        text_align=ft.TextAlign.CENTER),
                ft.Container(height=24),
                form_col,
                ft.Container(height=16),
                btn_main,
                ft.Container(height=4),
                toggle_btn,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            tight=True, spacing=0,
        ),
        width=380,
        bgcolor=theme.SURFACE,
        border=ft.border.all(1, theme.DIVIDER),
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=36, vertical=32),
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
