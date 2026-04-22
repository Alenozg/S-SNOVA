"""
Ana sayfa: özet kartlar + bugünkü randevular.
"""
import flet as ft

from services import customer_service, appointment_service
from ui import theme


def _stat_card(label: str, value: str, sublabel: str = "") -> ft.Container:
    return theme.card(
        ft.Column(
            [
                ft.Text(
                    label.upper(),
                    size=10,
                    color=theme.TEXT_MUTED,
                    weight=ft.FontWeight.W_500,
                ),
                ft.Container(height=12),
                ft.Text(
                    value,
                    size=36,
                    weight=ft.FontWeight.W_300,
                    color=theme.TEXT,
                    font_family=theme.FONT_FAMILY_DISPLAY,
                ),
                ft.Container(height=4),
                theme.caption(sublabel) if sublabel else ft.Container(),
            ],
            spacing=0,
        ),
        padding=28,
    )


def build(page: ft.Page) -> ft.Control:
    cust = customer_service.stats()
    today = appointment_service.today_appointments()
    now_greet = "İyi günler"

    # --- İstatistik kartları
    stats_row = ft.Row(
        [
            ft.Container(_stat_card("Toplam Müşteri", str(cust["total"]),
                                    f"{cust['with_birthday']} doğum günü kayıtlı"),
                         expand=True),
            ft.Container(_stat_card("İYS Onaylı", str(cust["iys"]),
                                    "SMS gönderimine uygun"),
                         expand=True),
            ft.Container(_stat_card("Bugünün Randevuları", str(len(today)),
                                    "Planlı ve tamamlanan"),
                         expand=True),
        ],
        spacing=16,
    )

    # --- Bugünün randevu listesi
    if today:
        rows = []
        for a in today:
            when = a.appointment_at.strftime("%H:%M") if a.appointment_at else "—"
            rows.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Container(
                                content=ft.Text(
                                    when,
                                    size=16,
                                    weight=ft.FontWeight.W_400,
                                    color=theme.ACCENT,
                                    font_family=theme.FONT_FAMILY_DISPLAY,
                                ),
                                width=80,
                            ),
                            ft.Column(
                                [
                                    ft.Text(a.customer_name or "", size=14,
                                            weight=ft.FontWeight.W_500,
                                            color=theme.TEXT),
                                    theme.caption(a.service_name or "Hizmet belirtilmemiş"),
                                ],
                                spacing=2,
                                expand=True,
                            ),
                            ft.Container(
                                content=ft.Text(a.status_label, size=11,
                                                color=theme.TEXT_MUTED),
                                padding=ft.padding.symmetric(horizontal=10, vertical=5),
                                bgcolor=theme.SURFACE_ALT,
                                border_radius=2,
                            ),
                        ],
                        spacing=16,
                    ),
                    padding=ft.padding.symmetric(vertical=14),
                    border=ft.border.only(bottom=ft.BorderSide(1, theme.DIVIDER)),
                )
            )
        today_panel = theme.card(
            ft.Column(
                [
                    theme.h3("Bugünün Randevuları"),
                    ft.Container(height=8),
                    *rows,
                ],
                spacing=0,
            )
        )
    else:
        today_panel = theme.card(
            ft.Column(
                [
                    theme.h3("Bugünün Randevuları"),
                    ft.Container(height=16),
                    ft.Container(
                        content=theme.body("Bugün planlı randevu yok.", muted=True),
                        alignment=ft.alignment.center,
                        padding=40,
                    ),
                ]
            )
        )

    return ft.Column(
        [
            ft.Container(
                content=ft.Column(
                    [
                        theme.caption(now_greet.upper()),
                        theme.h1("Genel Bakış"),
                    ],
                    spacing=4,
                ),
                padding=ft.padding.only(bottom=28),
            ),
            stats_row,
            ft.Container(height=24),
            today_panel,
        ],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )
