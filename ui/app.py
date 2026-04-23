"""
Ana uygulama — masaüstünde sidebar, mobilde drawer + AppBar.
Breakpoint: 768 px altı = mobil.
"""
import flet as ft

from ui import theme
from ui.components import Sidebar
from ui.views import (
    dashboard_view,
    customers_view,
    staff_view,
    services_view,
    appointments_view,
    campaigns_view,
    sms_logs_view,
    settings_view,
    reports_view,
    inactive_customers_view,
)

ROUTES = {
    "dashboard":    dashboard_view.build,
    "customers":    customers_view.build,
    "staff":        staff_view.build,
    "services":     services_view.build,
    "appointments": appointments_view.build,
    "campaigns":    campaigns_view.build,
    "logs":         sms_logs_view.build,
    "settings":     settings_view.build,
    "reports":      reports_view.build,
    "inactive":     inactive_customers_view.build,
}

MENU_ITEMS = [
    ("dashboard",    "Ana Sayfa",         ft.icons.DASHBOARD_OUTLINED),
    ("customers",    "Müşteriler",         ft.icons.PEOPLE_OUTLINE),
    ("appointments", "Randevular",         ft.icons.CALENDAR_MONTH_OUTLINED),
    ("campaigns",    "Kampanyalar",        ft.icons.CAMPAIGN_OUTLINED),
    ("staff",        "Personel",           ft.icons.BADGE_OUTLINED),
    ("services",     "Hizmetler",          ft.icons.DESIGN_SERVICES_OUTLINED),
    ("logs",         "SMS Geçmişi",        ft.icons.MAIL_OUTLINE),
    ("reports",      "Raporlar",           ft.icons.BAR_CHART_OUTLINED),
    ("inactive",     "Kayıp Müşteriler",   ft.icons.PERSON_OFF_OUTLINED),
    ("settings",     "Ayarlar",            ft.icons.SETTINGS_OUTLINED),
]

MOBILE_BREAKPOINT = 768


class SalonApp:
    def __init__(self, page: ft.Page, current_user: dict | None = None):
        self.page          = page
        self.current_user  = current_user or {}
        self._active_route = "dashboard"

        # İçerik alanı — her iki modda da kullanılır
        self.content_area = ft.Container(
            expand=True,
            bgcolor=theme.BG,
            padding=self._content_padding(),
        )

        # Masaüstü sidebar
        self.sidebar = Sidebar(
            on_change=self.navigate,
            active="dashboard",
            current_user=self.current_user,
            on_logout=self._logout,
        )

        # Mobil: NavigationDrawer
        self._drawer = self._build_drawer()
        self.page.drawer = self._drawer

        # Mobil: AppBar
        self._appbar = self._build_appbar()

        # Resize dinleyicisi
        self.page.on_resized = self._on_resize

    # ── Yardımcılar ──────────────────────────────────────────────
    @property
    def _is_mobile(self) -> bool:
        try:
            return (self.page.width or 1200) < MOBILE_BREAKPOINT
        except Exception:
            return False

    def _content_padding(self):
        if self._is_mobile:
            return ft.padding.symmetric(horizontal=16, vertical=20)
        return ft.padding.symmetric(horizontal=48, vertical=40)

    # ── Mobil drawer ─────────────────────────────────────────────
    def _build_drawer(self) -> ft.NavigationDrawer:
        tiles = []
        for key, label, icon in MENU_ITEMS:
            tiles.append(ft.ListTile(
                leading=ft.Icon(icon, size=20, color=theme.TEXT_MUTED),
                title=ft.Text(label, size=13, color=theme.TEXT),
                on_click=lambda e, k=key: self._drawer_select(k),
                data=key,
            ))

        user_name = self.current_user.get("full_name", "Kullanıcı")
        header = ft.Container(
            content=ft.Column([
                ft.Text("SISNOVA", size=18, weight=ft.FontWeight.W_300,
                        color=theme.TEXT, font_family=theme.FONT_FAMILY_DISPLAY),
                ft.Text("B E A U T Y", size=9, color=theme.TEXT_MUTED),
                ft.Container(height=8),
                ft.Text(user_name, size=12, color=theme.TEXT_MUTED),
            ], spacing=2),
            padding=ft.padding.fromLTRB(20, 32, 20, 16),
        )

        logout_tile = ft.ListTile(
            leading=ft.Icon(ft.icons.LOGOUT_OUTLINED, size=18, color=theme.TEXT_MUTED),
            title=ft.Text("Çıkış Yap", size=13, color=theme.TEXT_MUTED),
            on_click=lambda e: self._logout(),
        )

        return ft.NavigationDrawer(
            bgcolor=theme.SURFACE,
            controls=[
                header,
                ft.Divider(color=theme.DIVIDER, height=1),
                ft.Container(height=8),
                *tiles,
                ft.Container(expand=True),
                ft.Divider(color=theme.DIVIDER, height=1),
                logout_tile,
            ],
        )

    def _drawer_select(self, key: str):
        self._drawer.open = False
        self.page.update()
        self.navigate(key)
        # AppBar başlığını güncelle
        label = next((l for k, l, _ in MENU_ITEMS if k == key), "")
        if self._appbar.title:
            self._appbar.title.value = label
            self.page.update()

    def _build_appbar(self) -> ft.AppBar:
        return ft.AppBar(
            leading=ft.IconButton(
                icon=ft.icons.MENU,
                icon_color=theme.TEXT,
                on_click=lambda e: self._open_drawer(),
            ),
            leading_width=48,
            title=ft.Text("Ana Sayfa", size=16, color=theme.TEXT,
                          weight=ft.FontWeight.W_400,
                          font_family=theme.FONT_FAMILY_DISPLAY),
            bgcolor=theme.SURFACE,
            elevation=0,
            center_title=False,
            actions=[
                ft.Container(
                    content=ft.Text(
                        self.current_user.get("full_name", "A")[:1].upper(),
                        size=13, color=theme.SURFACE,
                        weight=ft.FontWeight.W_600,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    width=32, height=32, border_radius=16,
                    bgcolor=theme.ACCENT,
                    alignment=ft.alignment.center,
                    margin=ft.margin.only(right=12),
                ),
            ],
        )

    def _open_drawer(self):
        self._drawer.open = True
        self.page.update()

    # ── Layout kurulumu ──────────────────────────────────────────
    def mount(self) -> None:
        self._apply_layout()
        self.navigate("dashboard")

    def _apply_layout(self):
        self.page.controls.clear()
        self.content_area.padding = self._content_padding()

        if self._is_mobile:
            self.page.appbar = self._appbar
            self.page.add(self.content_area)
        else:
            self.page.appbar = None
            layout = ft.Row(
                [self.sidebar, self.content_area],
                spacing=0, expand=True,
            )
            self.page.add(layout)

        self.page.update()

    def _on_resize(self, e):
        self._apply_layout()
        # Mevcut route'u yeniden render et
        self.navigate(self._active_route)

    # ── Navigasyon ───────────────────────────────────────────────
    def navigate(self, key: str) -> None:
        builder = ROUTES.get(key)
        if not builder:
            return
        self._active_route = key
        try:
            view = builder(self.page)
            self.content_area.content = view
            if self.content_area.page:
                self.content_area.update()
        except Exception as ex:
            self.content_area.content = ft.Container(
                content=ft.Column([
                    theme.h2("Bir şeyler ters gitti"),
                    ft.Container(height=8),
                    theme.body(f"{ex}", muted=True),
                ]),
                padding=40,
            )
            if self.content_area.page:
                self.content_area.update()
            raise

    # ── Çıkış ────────────────────────────────────────────────────
    def _logout(self):
        try:
            self.page.session.remove("current_user")
        except Exception:
            pass
        self.page.controls.clear()
        self.page.appbar = None
        self.page.drawer = None
        from ui.views.login_view import build_login
        def reload(user):
            self.page.controls.clear()
            app = SalonApp(self.page, current_user=user)
            app.mount()
        self.page.add(build_login(self.page, on_success=reload))
        self.page.update()
