"""
Ana sayfa: özet kartlar + bugün + bu haftanın randevuları.
"""
from datetime import datetime, timedelta
import flet as ft

from services import customer_service, appointment_service
from ui import theme

DAYS_TR = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]


def _stat_card(label: str, value: str, sublabel: str = "") -> ft.Container:
    return theme.card(
        ft.Column(
            [
                ft.Text(label.upper(), size=10, color=theme.TEXT_MUTED,
                        weight=ft.FontWeight.W_500),
                ft.Container(height=12),
                ft.Text(value, size=36, weight=ft.FontWeight.W_300,
                        color=theme.TEXT, font_family=theme.FONT_FAMILY_DISPLAY),
                ft.Container(height=4),
                theme.caption(sublabel) if sublabel else ft.Container(),
            ],
            spacing=0,
        ),
        padding=28,
    )


def _appt_row(a, highlight: bool = False) -> ft.Container:
    when = a.appointment_at.strftime("%H:%M") if a.appointment_at else "—"
    status_colors = {
        "completed": theme.SUCCESS,
        "cancelled": theme.ERROR,
        "no_show":   theme.WARN,
    }
    status_color = status_colors.get(a.status, theme.TEXT_MUTED)

    return ft.Container(
        content=ft.Row(
            [
                ft.Container(
                    content=ft.Text(when, size=15, weight=ft.FontWeight.W_500,
                                    color=theme.ACCENT if highlight else theme.TEXT_MUTED,
                                    font_family=theme.FONT_FAMILY_DISPLAY),
                    width=64,
                ),
                ft.Column(
                    [
                        ft.Text(a.customer_name or "", size=13,
                                weight=ft.FontWeight.W_500, color=theme.TEXT),
                        theme.caption(a.service_name or "Hizmet belirtilmemiş"),
                    ],
                    spacing=2, expand=True,
                ),
                ft.Container(
                    content=ft.Text(a.status_label, size=10,
                                    color=theme.SURFACE if a.status != "scheduled" else theme.TEXT_MUTED,
                                    weight=ft.FontWeight.W_500),
                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                    bgcolor=status_color if a.status != "scheduled" else theme.SURFACE_ALT,
                    border_radius=2,
                ),
            ],
            spacing=12,
        ),
        padding=ft.padding.symmetric(vertical=11),
        border=ft.border.only(bottom=ft.BorderSide(1, theme.DIVIDER)),
    )


def build(page: ft.Page) -> ft.Control:
    cust  = customer_service.stats()
    now   = datetime.now()
    today = now.date()

    # Bu haftanın başı (Pazartesi) ve sonu (Pazar)
    week_start = today - timedelta(days=today.weekday())
    week_end   = week_start + timedelta(days=6)

    week_appts = appointment_service.list_appointments(
        start=datetime.combine(week_start, datetime.min.time()),
        end=datetime.combine(week_end,   datetime.max.time()),
    )

    today_appts = [a for a in week_appts if a.appointment_at and a.appointment_at.date() == today]
    upcoming    = [a for a in week_appts if a.appointment_at and a.appointment_at.date() > today]

    # ── Stat kartları (mobilde dikey) ────────────────────────────
    is_mobile = (page.width or 1200) < 768
    cards = [
        ft.Container(_stat_card("Toplam Müşteri", str(cust["total"]),
                                f"{cust['with_birthday']} doğum günü kayıtlı"),
                     expand=not is_mobile),
        ft.Container(_stat_card("İYS Onaylı", str(cust["iys"]),
                                "SMS gönderimine uygun"),
                     expand=not is_mobile),
        ft.Container(_stat_card("Bugün", str(len(today_appts)),
                                "randevu var"),
                     expand=not is_mobile),
        ft.Container(_stat_card("Bu Hafta", str(len(week_appts)),
                                f"{len(upcoming)} önünüzde"),
                     expand=not is_mobile),
    ]
    if is_mobile:
        stats_row = ft.Column(cards, spacing=10)
    else:
        stats_row = ft.Row(cards, spacing=16)

    # ── Bugünün listesi ──────────────────────────────────────────
    if today_appts:
        today_rows = [_appt_row(a, highlight=True) for a in today_appts]
    else:
        today_rows = [ft.Container(
            content=theme.body("Bugün planlı randevu yok.", muted=True),
            alignment=ft.alignment.center, padding=32,
        )]

    today_panel = theme.card(
        ft.Column(
            [theme.h3("Bugün — " + now.strftime("%d %B %Y")),
             ft.Container(height=8), *today_rows],
            spacing=0,
        )
    )

    # ── Bu haftanın geri kalanı ──────────────────────────────────
    week_controls: list[ft.Control] = []
    if upcoming:
        # Güne göre grupla
        from itertools import groupby
        for day_date, grp in groupby(upcoming, key=lambda a: a.appointment_at.date()):
            day_name = DAYS_TR[day_date.weekday()]
            day_label = f"{day_name}  {day_date.strftime('%d %B')}"
            week_controls.append(
                ft.Container(
                    content=theme.caption(day_label),
                    padding=ft.padding.only(top=16, bottom=4),
                )
            )
            for a in grp:
                week_controls.append(_appt_row(a))
    else:
        week_controls.append(ft.Container(
            content=theme.body("Bu hafta başka randevu yok.", muted=True),
            alignment=ft.alignment.center, padding=32,
        ))

    week_panel = theme.card(
        ft.Column(
            [theme.h3(f"Bu Hafta — {week_start.strftime('%d %b')} – {week_end.strftime('%d %b %Y')}"),
             ft.Container(height=4), *week_controls],
            spacing=0,
        )
    )

    # Selamlama
    hour = now.hour
    if hour < 12:
        greet = "Günaydın"
    elif hour < 18:
        greet = "İyi günler"
    else:
        greet = "İyi akşamlar"

    return ft.Column(
        [
            ft.Container(
                content=ft.Column(
                    [theme.caption(greet.upper()), theme.h1("Genel Bakış")],
                    spacing=4,
                ),
                padding=ft.padding.only(bottom=28),
            ),
            stats_row,
            ft.Container(height=24),
            today_panel,
            ft.Container(height=16),
            week_panel,
        ],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )
