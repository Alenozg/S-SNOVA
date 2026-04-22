"""
SMS gönderim geçmişi (tüm tipler).
"""
from datetime import datetime
import flet as ft

from database import fetch_all
from ui import theme


TYPE_LABELS = {
    "campaign":  "Kampanya",
    "reminder":  "Hatırlatma",
    "birthday":  "Doğum Günü",
}
TYPE_COLORS = {
    "campaign":  theme.ACCENT,
    "reminder":  theme.SUCCESS,
    "birthday":  theme.WARN,
}


def build(page: ft.Page) -> ft.Control:
    logs = fetch_all(
        """SELECT l.*, c.first_name || ' ' || c.last_name AS customer_name
           FROM sms_logs l
           LEFT JOIN customers c ON c.id = l.customer_id
           ORDER BY l.created_at DESC
           LIMIT 500"""
    )

    header = ft.Container(
        content=ft.Row(
            [
                ft.Container(
                    content=ft.Text("ZAMAN", size=10, color=theme.TEXT_MUTED,
                                    weight=ft.FontWeight.W_500),
                    width=140,
                ),
                ft.Container(
                    content=ft.Text("TİP", size=10, color=theme.TEXT_MUTED,
                                    weight=ft.FontWeight.W_500),
                    width=110,
                ),
                ft.Container(
                    content=ft.Text("ALICI", size=10, color=theme.TEXT_MUTED,
                                    weight=ft.FontWeight.W_500),
                    width=200,
                ),
                ft.Container(
                    content=ft.Text("MESAJ", size=10, color=theme.TEXT_MUTED,
                                    weight=ft.FontWeight.W_500),
                    expand=True,
                ),
                ft.Container(
                    content=ft.Text("DURUM", size=10, color=theme.TEXT_MUTED,
                                    weight=ft.FontWeight.W_500),
                    width=90,
                ),
            ],
            spacing=16,
        ),
        padding=ft.padding.symmetric(horizontal=24, vertical=14),
        bgcolor=theme.SURFACE_ALT,
        border=ft.border.only(bottom=ft.BorderSide(1, theme.DIVIDER)),
    )

    rows: list[ft.Control] = [header]
    if not logs:
        rows.append(ft.Container(
            content=theme.body("Henüz gönderilmiş SMS yok.", muted=True),
            padding=40, alignment=ft.alignment.center,
        ))
    else:
        for log in logs:
            ts = log.get("created_at") or ""
            if ts:
                try:
                    ts = datetime.fromisoformat(ts).strftime("%d.%m.%Y %H:%M")
                except Exception:
                    pass

            stype = log.get("sms_type", "")
            type_chip = ft.Container(
                content=ft.Text(
                    TYPE_LABELS.get(stype, stype), size=10,
                    color=theme.SURFACE, weight=ft.FontWeight.W_500),
                padding=ft.padding.symmetric(horizontal=8, vertical=4),
                bgcolor=TYPE_COLORS.get(stype, theme.TEXT_MUTED),
                border_radius=2,
            )
            ok = log.get("status") == "sent"
            status_icon = ft.Icon(
                ft.icons.CHECK_CIRCLE_OUTLINE if ok else ft.icons.ERROR_OUTLINE,
                size=16, color=theme.SUCCESS if ok else theme.ERROR,
            )
            rows.append(ft.Container(
                content=ft.Row(
                    [
                        ft.Container(content=theme.caption(str(ts)), width=140),
                        ft.Container(content=type_chip, width=110),
                        ft.Container(
                            content=ft.Column(
                                [
                                    ft.Text(log.get("customer_name") or "—",
                                            size=13, color=theme.TEXT),
                                    theme.caption(log.get("phone", "")),
                                ],
                                spacing=1,
                            ),
                            width=200,
                        ),
                        ft.Container(
                            content=ft.Text(
                                (log.get("message") or "")[:120],
                                size=12, color=theme.TEXT_MUTED,
                                no_wrap=False, max_lines=2,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            expand=True,
                        ),
                        ft.Container(
                            content=ft.Row([status_icon], alignment=ft.MainAxisAlignment.START),
                            width=90,
                        ),
                    ],
                    spacing=16,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
                padding=ft.padding.symmetric(horizontal=24, vertical=14),
                border=ft.border.only(bottom=ft.BorderSide(1, theme.DIVIDER)),
            ))

    header_block = ft.Container(
        content=ft.Column(
            [theme.caption("GÜNLÜK"), theme.h1("SMS Geçmişi")],
            spacing=4,
        ),
        padding=ft.padding.only(bottom=28),
    )

    return ft.Column(
        [header_block, theme.card(ft.Column(rows, spacing=0), padding=0)],
        scroll=ft.ScrollMode.AUTO, expand=True,
    )
