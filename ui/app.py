"""
Ana uygulama sınıfı. Sidebar + içerik alanı, basit router.
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
}


class SalonApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.content_area = ft.Container(
            expand=True,
            bgcolor=theme.BG,
            padding=ft.padding.symmetric(horizontal=48, vertical=40),
        )
        self.sidebar = Sidebar(on_change=self.navigate, active="dashboard")

    def mount(self) -> None:
        layout = ft.Row(
            [self.sidebar, self.content_area],
            spacing=0, expand=True,
        )
        self.page.add(layout)
        self.navigate("dashboard")

    def navigate(self, key: str) -> None:
        builder = ROUTES.get(key)
        if not builder:
            return
        try:
            view = builder(self.page)
            self.content_area.content = view
            self.content_area.update()
        except Exception as ex:
            self.content_area.content = ft.Container(
                content=ft.Column(
                    [
                        theme.h2("Bir şeyler ters gitti"),
                        ft.Container(height=8),
                        theme.body(f"{ex}", muted=True),
                    ],
                ),
                padding=40,
            )
            self.content_area.update()
            raise
