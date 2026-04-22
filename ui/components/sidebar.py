"""
Sol menü (sidebar). Seçim değiştiğinde on_change callback'ini çağırır.
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
    def __init__(self, on_change, active: str = "dashboard"):
        super().__init__()
        self.on_change = on_change
        self.active = active

        self.width = 240
        self.bgcolor = theme.SURFACE
        self.padding = ft.padding.symmetric(horizontal=16, vertical=28)
        self.border = ft.border.only(right=ft.BorderSide(1, theme.DIVIDER))

        self._items: dict[str, ft.Container] = {}
        self.content = self._build()

    def _build(self) -> ft.Column:
        logo = ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        "SISNOVA",
                        size=20,
                        weight=ft.FontWeight.W_300,
                        color=theme.TEXT,
                        font_family=theme.FONT_FAMILY_DISPLAY,
                    ),
                    # letter_spacing yerine harf aralarına boşluk koyarak
                    # aynı "geniş aralıklı" görünüm - tüm Flet sürümlerinde çalışır
                    ft.Text(
                        "B E A U T Y",
                        size=10,
                        color=theme.TEXT_MUTED,
                        weight=ft.FontWeight.W_400,
                    ),
                ],
                spacing=2,
            ),
            padding=ft.padding.only(left=12, bottom=28),
        )

        nav_items = []
        for key, label, icon in MENU_ITEMS:
            nav_items.append(self._make_item(key, label, icon))

        return ft.Column(
            [
                logo,
                *nav_items,
                ft.Container(expand=True),
                theme.caption("v1.0"),
            ],
            spacing=4,
        )

    def _make_item(self, key: str, label: str, icon) -> ft.Container:
        is_active = key == self.active
        item = ft.Container(
            content=ft.Row(
                [
                    ft.Icon(
                        icon,
                        size=18,
                        color=theme.ACCENT if is_active else theme.TEXT_MUTED,
                    ),
                    ft.Text(
                        label,
                        size=13,
                        weight=ft.FontWeight.W_500 if is_active else ft.FontWeight.W_400,
                        color=theme.TEXT if is_active else theme.TEXT_MUTED,
                    ),
                ],
                spacing=14,
            ),
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
        prev = self.active
        self.active = key

        # Eski ve yeni öğenin görünümünü güncelle
        for k in (prev, key):
            if k not in self._items:
                continue
            is_active = k == key
            container = self._items[k]
            row: ft.Row = container.content  # type: ignore
            icon: ft.Icon = row.controls[0]  # type: ignore
            text: ft.Text = row.controls[1]  # type: ignore
            icon.color = theme.ACCENT if is_active else theme.TEXT_MUTED
            text.color = theme.TEXT if is_active else theme.TEXT_MUTED
            text.weight = ft.FontWeight.W_500 if is_active else ft.FontWeight.W_400
            container.bgcolor = theme.SURFACE_ALT if is_active else None

        self.update()
        if self.on_change:
            self.on_change(key)
