"""
"Quiet luxury" tema tanımları.

Mat, dinlendirici, topraktan gelen renkler.
Ferforje altın yerine kumlu taş tonu, sıcak grilere kaçan nötrler.
"""
import flet as ft


# --- Palet ---
BG          = "#F5F2ED"   # kağıt bej — ana zemin
SURFACE     = "#FFFFFF"   # kart yüzeyi
SURFACE_ALT = "#EFEBE4"   # hafif kontrast zemin
TEXT        = "#2B2724"   # ana metin — yumuşak kömür
TEXT_MUTED  = "#8A827A"   # yardımcı metin — sıcak gri
TEXT_FAINT  = "#B4ADA4"   # placeholder
ACCENT      = "#A89078"   # mat taş bronzu
ACCENT_DARK = "#7D6752"   # üzerine gelme
DIVIDER     = "#E3DED5"   # ince ayırıcı
SUCCESS     = "#7A8471"   # adaçayı yeşili
ERROR       = "#9B6B5F"   # sönük kiremit
WARN        = "#C2A878"   # ılık altın uyarı

# Geçersiz / eksik kayıt satırı için — pastel gül kurusu tonları
# Göz yormayan, minimalist ruhu bozmayan uyarı vurguları
INVALID_BG  = "#F5EBE8"   # pastel gül kurusu zemin (çok hafif kırmızı ton)
INVALID_BAR = "#C89C94"   # mat somon/gül — sol bar aksan
INVALID_TXT = "#8B5D55"   # hatalı alan uyarı metni (koyu sönük bordo)


# --- Tipografi ---
FONT_FAMILY_BODY    = "Inter"
FONT_FAMILY_DISPLAY = "Cormorant Garamond"


def apply(page: ft.Page) -> None:
    """Page üzerinde global tema ayarlarını yapar.

    NOT: ft.ColorScheme tüm Flet sürümlerinde farklı parametreler kabul
    ediyor. Basit ve uyumlu kalmak için sadece color_scheme_seed ve
    font_family kullanıyoruz; geri kalanı Flet kendi çıkarsıyor.
    """
    page.bgcolor = BG
    page.padding = 0
    # Font'u online'dan çekmiyoruz - Railway dahil bazı ortamlarda
    # gstatic.com erişimi ya yavaş ya kısıtlı. Sistem font'u ile devam.
    try:
        page.theme = ft.Theme(
            color_scheme_seed=ACCENT,
            font_family=FONT_FAMILY_BODY,
            use_material3=True,
        )
    except Exception:
        # Flet sürümü Theme API'sini farklı kabul ediyorsa temel şekilde uygula
        page.theme = ft.Theme(color_scheme_seed=ACCENT)


# --- Tekrar kullanılabilir text stilleri ---
def h1(text: str) -> ft.Text:
    return ft.Text(
        text,
        size=32,
        weight=ft.FontWeight.W_300,
        color=TEXT,
        font_family=FONT_FAMILY_DISPLAY,
    )


def h2(text: str) -> ft.Text:
    return ft.Text(text, size=22, weight=ft.FontWeight.W_400, color=TEXT)


def h3(text: str) -> ft.Text:
    return ft.Text(text, size=16, weight=ft.FontWeight.W_500, color=TEXT)


def body(text: str, muted: bool = False) -> ft.Text:
    return ft.Text(
        text,
        size=14,
        color=TEXT_MUTED if muted else TEXT,
        weight=ft.FontWeight.W_400,
    )


def caption(text: str) -> ft.Text:
    return ft.Text(text, size=11, color=TEXT_FAINT, weight=ft.FontWeight.W_400)


# --- Bileşen yardımcıları ---
def card(content: ft.Control, padding: int = 24) -> ft.Container:
    """Temel kart; hafif border, gölge yok."""
    return ft.Container(
        content=content,
        bgcolor=SURFACE,
        padding=padding,
        border=ft.border.all(1, DIVIDER),
        border_radius=4,
    )


def divider() -> ft.Container:
    return ft.Container(height=1, bgcolor=DIVIDER)


def primary_button(text: str, on_click=None, icon: str | None = None) -> ft.FilledButton:
    return ft.FilledButton(
        text=text,
        icon=icon,
        on_click=on_click,
        style=ft.ButtonStyle(
            bgcolor=ACCENT,
            color="#FFFFFF",
            shape=ft.RoundedRectangleBorder(radius=2),
            padding=ft.padding.symmetric(horizontal=24, vertical=18),
            text_style=ft.TextStyle(
                weight=ft.FontWeight.W_400,
                size=13,
            ),
        ),
    )


def ghost_button(text: str, on_click=None, icon: str | None = None) -> ft.OutlinedButton:
    return ft.OutlinedButton(
        text=text,
        icon=icon,
        on_click=on_click,
        style=ft.ButtonStyle(
            color=TEXT,
            side=ft.BorderSide(1, DIVIDER),
            shape=ft.RoundedRectangleBorder(radius=2),
            padding=ft.padding.symmetric(horizontal=20, vertical=16),
            text_style=ft.TextStyle(
                weight=ft.FontWeight.W_400,
                size=13,
            ),
        ),
    )


def text_field(label: str, value: str = "", password: bool = False, multiline: bool = False,
               hint: str = "") -> ft.TextField:
    return ft.TextField(
        label=label,
        value=value,
        hint_text=hint,
        password=password,
        can_reveal_password=password,
        multiline=multiline,
        min_lines=3 if multiline else 1,
        max_lines=6 if multiline else 1,
        border_color=DIVIDER,
        focused_border_color=ACCENT,
        label_style=ft.TextStyle(color=TEXT_MUTED, size=12, weight=ft.FontWeight.W_400),
        text_style=ft.TextStyle(color=TEXT, size=14),
        cursor_color=ACCENT,
        bgcolor=SURFACE,
        border_radius=2,
        content_padding=ft.padding.symmetric(horizontal=14, vertical=16),
    )
