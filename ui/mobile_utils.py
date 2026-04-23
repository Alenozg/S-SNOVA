"""
Mobil yardımcı fonksiyonlar.
"""
import flet as ft
from ui import theme


def is_mobile(page: ft.Page) -> bool:
    try:
        if page.platform in {ft.PagePlatform.ANDROID, ft.PagePlatform.IOS}:
            return True
    except Exception:
        pass
    try:
        w = page.width
        if w and w > 0:
            return w < 768
    except Exception:
        pass
    return False


def mobile_card_row(*items) -> ft.Container:
    """
    Mobil için kompakt kart satırı.
    items: (label, value) tuple'ları
    """
    rows = []
    for label, value in items:
        if value and value != "—":
            rows.append(ft.Row([
                ft.Text(label, size=10, color=theme.TEXT_MUTED, width=90),
                ft.Text(str(value), size=12, color=theme.TEXT, expand=True,
                        no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS),
            ], spacing=8))
    return ft.Column(rows, spacing=4)
