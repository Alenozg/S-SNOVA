"""
Sol menü (sidebar) — kullanıcı bilgisi + çıkış butonu dahil.
"""
import flet as ft
from ui import theme


MENU_ITEMS = [
    ("dashboard",    "Ana Sayfa",   ft.icons.DASHBOARD_OUTLINED),
    ("customers",    "Müşteriler",  ft.icons.PEOPLE_OUTLINE),
    ("staff",        "Personel",    ft.icons.BADGE_OUTLINED),
    ("services",     "Hizmetler",   ft.icons.DESIGN_SERVICES_OUTLINED),
    ("appointments", "Randevular",  ft.icons.CALENDAR_MONTH_OUTLINED),
    ("campaigns",    "Kampanyalar", ft.icons.CAMPAIGN_OUTLINED),
    ("logs",         "SMS Geçmişi", ft.icons.MAIL_OUTLINE),
    ("settings",     "Ayarlar",     ft.icons.SETTINGS_OUTLINED),
]


class Sidebar(ft.Container):
    def __init__(self, on_change, active: str = "dashboard",
                 current_user: dict | None = None, on_logout=None):
        super().__init__()
        self.on_change    = on_change
        self.active       = active
        self.current_user = current_user or {}
        self.on_logout    = on_logout

        self.width   = 240
        self.bgcolor = theme.SURFACE
        self.padding = ft.padding.symmetric(horizontal=16, vertical=28)
        self.border  = ft.border.only(right=ft.BorderSide(1, theme.DIVIDER))

        self._items: dict[str, ft.Container] = {}
        self.content = self._build()

    def _build(self) -> ft.Column:
        logo = ft.Container(
            content=ft.Column([
                ft.Text("SISNOVA", size=20, weight=ft.FontWeight.W_300,
                        color=theme.TEXT, font_family=theme.FONT_FAMILY_DISPLAY),
                ft.Text("B E A U T Y", size=10, color=theme.TEXT_MUTED,
                        weight=ft.FontWeight.W_400),
            ], spacing=2),
            padding=ft.padding.only(left=12, bottom=28),
        )

        nav_items = [self._make_item(k, l, i) for k, l, i in MENU_ITEMS]

        # Kullanıcı bilgisi + çıkış
        user_name  = self.current_user.get("full_name", "Kullanıcı")
        user_email = self.current_user.get("email", "")
        user_role  = self.current_user.get("role", "user")
        role_label = "Admin" if user_role == "admin" else "Kullanıcı"

        user_panel = ft.Container(
            content=ft.Column([
                ft.Divider(color=theme.DIVIDER, height=1),
                ft.Container(height=12),
                ft.Row([
                    ft.Container(
                        content=ft.Text(
                            user_name[:1].upper(), size=13,
                            color=theme.SURFACE, weight=ft.FontWeight.W_600,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        width=32, height=32, border_radius=16,
                        bgcolor=theme.ACCENT,
                        alignment=ft.alignment.center,
                    ),
                    ft.Column([
                        ft.Text(user_name, size=12, color=theme.TEXT,
                                weight=ft.FontWeight.W_500,
                                overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Text(role_label, size=10, color=theme.TEXT_MUTED),
                    ], spacing=1, tight=True, expand=True),
                ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Container(height=8),
                ft.TextButton(
                    "Çıkış Yap",
                    icon=ft.icons.LOGOUT_OUTLINED,
                    on_click=lambda e: self.on_logout() if self.on_logout else None,
                    style=ft.ButtonStyle(
                        color=theme.TEXT_MUTED,
                        padding=ft.padding.symmetric(horizontal=4, vertical=4),
                    ),
                ),
            ], spacing=0, tight=True),
            padding=ft.padding.only(top=8),
        )

        return ft.Column([
            logo,
            *nav_items,
            ft.Container(expand=True),
            user_panel,
        ], spacing=4)

    def _make_item(self, key: str, label: str, icon) -> ft.Container:
        is_active = key == self.active
        item = ft.Container(
            content=ft.Row([
                ft.Icon(icon, size=18,
                        color=theme.ACCENT if is_active else theme.TEXT_MUTED),
                ft.Text(label, size=13,
                        weight=ft.FontWeight.W_500 if is_active else ft.FontWeight.W_400,
                        color=theme.TEXT if is_active else theme.TEXT_MUTED),
            ], spacing=14),
            padding=ft.padding.symmetric(horizontal=12, vertical=12),
            bgcolor=theme.SURFACE_ALT if is_active else None,
            border_radius=2,
            ink=True,
            on_click=lambda e, k=key: self._select(k),
            data=key,
        )
        self._items[key] = item
        return item

    def _select(self, key: str) -> None:
        if key == self.active:
            return
        prev, self.active = self.active, key
        for k in (prev, key):
            if k not in self._items:
                continue
            is_active = k == key
            c = self._items[k]
            row: ft.Row = c.content
            row.controls[0].color = theme.ACCENT if is_active else theme.TEXT_MUTED
            row.controls[1].color = theme.TEXT   if is_active else theme.TEXT_MUTED
            row.controls[1].weight = ft.FontWeight.W_500 if is_active else ft.FontWeight.W_400
            c.bgcolor = theme.SURFACE_ALT if is_active else None
        self.update()
        if self.on_change:
            self.on_change(key)
