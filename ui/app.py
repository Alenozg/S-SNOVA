"""
Ana uygulama — masaüstünde sidebar, mobilde drawer + AppBar.
Platform veya genişlik ile mobil tespiti yapılır.
"""
import flet as ft

from ui import theme
from ui.components import Sidebar
from ui.views import (
    dashboard_view, customers_view, staff_view, services_view,
    appointments_view, campaigns_view, sms_logs_view, settings_view,
    reports_view, inactive_customers_view,
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
    ("dashboard",    "Ana Sayfa",        ft.icons.DASHBOARD_OUTLINED),
    ("customers",    "Müşteriler",       ft.icons.PEOPLE_OUTLINE),
    ("appointments", "Randevular",       ft.icons.CALENDAR_MONTH_OUTLINED),
    ("campaigns",    "Kampanyalar",      ft.icons.CAMPAIGN_OUTLINED),
    ("staff",        "Personel",         ft.icons.BADGE_OUTLINED),
    ("services",     "Hizmetler",        ft.icons.DESIGN_SERVICES_OUTLINED),
    ("logs",         "SMS Geçmişi",      ft.icons.MAIL_OUTLINE),
    ("reports",      "Raporlar",         ft.icons.BAR_CHART_OUTLINED),
    ("inactive",     "Kayıp Müşteriler", ft.icons.PERSON_OFF_OUTLINED),
    ("settings",     "Ayarlar",          ft.icons.SETTINGS_OUTLINED),
]


def _is_mobile(page: ft.Page) -> bool:
    """Platform veya genişlikle mobil tespiti."""
    try:
        mobile_platforms = {ft.PagePlatform.ANDROID, ft.PagePlatform.IOS}
        if page.platform in mobile_platforms:
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


class SalonApp:
    def __init__(self, page: ft.Page, current_user: dict | None = None):
        self.page         = page
        self.current_user = current_user or {}
        self._active      = "dashboard"
        self._mobile      = _is_mobile(page)

        pad = ft.padding.symmetric(horizontal=14, vertical=16) if self._mobile \
              else ft.padding.symmetric(horizontal=48, vertical=40)

        self.content_area = ft.Container(expand=True, bgcolor=theme.BG, padding=pad)

    # ── mount ─────────────────────────────────────────────────
    def mount(self) -> None:
        if self._mobile:
            self._mount_mobile()
        else:
            self._mount_desktop()

    def _mount_desktop(self):
        sidebar = Sidebar(
            on_change=self.navigate,
            active="dashboard",
            current_user=self.current_user,
            on_logout=self._logout,
        )
        try:
            from ui.views import dashboard_view as _dv
            self.content_area.content = _dv.build(self.page)
        except Exception as _ex:
            self.content_area.content = ft.Container(
                content=ft.Text(str(_ex), color=theme.ERROR, size=12),
                padding=20,
            )
        self._active = "dashboard"
        self.page.add(ft.Row([sidebar, self.content_area], spacing=0, expand=True))
        self.page.update()

    def _mount_mobile(self):
        # Drawer
        drawer_tiles = []
        for key, label, icon in MENU_ITEMS:
            drawer_tiles.append(ft.ListTile(
                leading=ft.Icon(icon, size=20, color=theme.TEXT_MUTED),
                title=ft.Text(label, size=13, color=theme.TEXT),
                on_click=lambda e, k=key, l=label: self._drawer_nav(k, l),
            ))

        user_name = self.current_user.get("full_name", "Kullanıcı")
        drawer = ft.NavigationDrawer(
            bgcolor=theme.SURFACE,
            controls=[
                ft.Container(
                    content=ft.Column([
                        ft.Text("SISNOVA", size=18, weight=ft.FontWeight.W_300,
                                color=theme.TEXT,
                                font_family=theme.FONT_FAMILY_DISPLAY),
                        ft.Text("B E A U T Y", size=9, color=theme.TEXT_MUTED),
                        ft.Container(height=6),
                        ft.Text(user_name, size=12, color=theme.TEXT_MUTED),
                    ], spacing=2),
                    padding=ft.padding.only(left=20, top=32, right=20, bottom=12),
                ),
                ft.Divider(color=theme.DIVIDER, height=1),
                ft.Container(height=4),
                *drawer_tiles,
                ft.Divider(color=theme.DIVIDER, height=1),
                ft.ListTile(
                    leading=ft.Icon(ft.icons.LOGOUT_OUTLINED, size=18,
                                    color=theme.TEXT_MUTED),
                    title=ft.Text("Çıkış Yap", size=13, color=theme.TEXT_MUTED),
                    on_click=lambda e: self._logout(),
                ),
            ],
        )
        self.page.drawer = drawer

        # AppBar başlığı için referans
        self._appbar_title = ft.Text(
            "Ana Sayfa", size=16, color=theme.TEXT,
            weight=ft.FontWeight.W_400,
            font_family=theme.FONT_FAMILY_DISPLAY,
        )
        self.page.appbar = ft.AppBar(
            leading=ft.IconButton(
                icon=ft.icons.MENU,
                icon_color=theme.TEXT,
                on_click=lambda e: self._open_drawer(),
            ),
            leading_width=48,
            title=self._appbar_title,
            bgcolor=theme.SURFACE,
            elevation=0,
            center_title=False,
            actions=[
                ft.Container(
                    content=ft.Text(
                        user_name[:1].upper(),
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

        # İçeriği sayfaya eklemeden önce set et — boş beyaz ekran önlenir
        try:
            from ui.views import dashboard_view as _dv
            self.content_area.content = _dv.build(self.page)
        except Exception as _ex:
            self.content_area.content = ft.Container(
                content=ft.Text(str(_ex), color=theme.ERROR, size=12),
                padding=20,
            )
        self._active = "dashboard"
        self.page.add(self.content_area)
        self.page.update()

    def _open_drawer(self):
        try:
            self.page.drawer.open = True
            self.page.update()
        except Exception:
            pass

    def _drawer_nav(self, key: str, label: str):
        try:
            self.page.drawer.open = False
            self.page.update()
        except Exception:
            pass
        try:
            self._appbar_title.value = label
            self._appbar_title.update()
        except Exception:
            pass
        self.navigate(key)

    # ── navigate ──────────────────────────────────────────────
    def navigate(self, key: str) -> None:
        # mount sırasında dashboard zaten yüklendi, tekrar yükleme
        if key == self._active and key == "dashboard" and self.content_area.content:
            return
        builder = ROUTES.get(key)
        if not builder:
            return
        self._active = key
        try:
            view = builder(self.page)
            self.content_area.content = view
            self.page.update()
        except Exception as ex:
            import traceback
            self.content_area.content = ft.Container(
                content=ft.Column([
                    theme.h2("Bir şeyler ters gitti"),
                    ft.Container(height=8),
                    theme.body(str(ex), muted=True),
                    ft.Container(height=8),
                    ft.Text(traceback.format_exc()[:400], size=10,
                            color=theme.TEXT_MUTED, selectable=True),
                ]),
                padding=40,
            )
            self.page.update()

    # ── logout ────────────────────────────────────────────────
    def _logout(self):
        try:
            self.page.session.remove("current_user")
        except Exception:
            pass
        self.page.controls.clear()
        self.page.appbar = None
        self.page.drawer = None
        self.page.update()

        from ui.views.login_view import build_login

        def reload(user):
            self.page.controls.clear()
            self.page.appbar = None
            self.page.drawer = None
            self.page.update()
            new_app = SalonApp(self.page, current_user=user)
            new_app.mount()

        self.page.add(build_login(self.page, on_success=reload))
        self.page.update()
