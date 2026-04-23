"""
SMS gönderim geçmişi (tüm tipler) – maliyet sütunuyla.
"""
from datetime import datetime
import flet as ft

import config
from database import fetch_all
from services.sms_service import calculate_sms_cost, sms_segment_count
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


def _fmt_cost(cost: float) -> str:
    """0.40 TL formatında döndürür."""
    return f"{cost:.2f} TL"


def build(page: ft.Page) -> ft.Control:
    logs = fetch_all(
        """SELECT l.*, c.first_name || ' ' || c.last_name AS customer_name
           FROM sms_logs l
           LEFT JOIN customers c ON c.id = l.customer_id
           ORDER BY l.created_at DESC
           LIMIT 500"""
    )

    # ── Maliyet hesapla ──────────────────────────────────────────
    total_cost = 0.0
    total_sms  = len(logs)
    sent_count = 0
    for log in logs:
        msg = log.get("message") or ""
        log["_cost"] = calculate_sms_cost(msg)
        total_cost += log["_cost"]
        if log.get("status") == "sent":
            sent_count += 1

    # ── Özet kartları ────────────────────────────────────────────
    def summary_card(label: str, value: str, icon: str, color: str) -> ft.Control:
        return ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        content=ft.Icon(icon, size=20, color=color),
                        width=40, height=40,
                        bgcolor=f"{color}18",
                        border_radius=8,
                        alignment=ft.alignment.center,
                    ),
                    ft.Column(
                        [
                            ft.Text(value, size=18, weight=ft.FontWeight.W_700,
                                    color=theme.TEXT),
                            ft.Text(label, size=11, color=theme.TEXT_MUTED),
                        ],
                        spacing=2,
                    ),
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.symmetric(horizontal=20, vertical=14),
            bgcolor=theme.SURFACE,
            border_radius=10,
            border=ft.border.all(1, theme.DIVIDER),
            expand=True,
        )

    summary_row = ft.Row(
        [
            summary_card("Toplam SMS", str(total_sms),
                         ft.icons.SEND_OUTLINED, theme.ACCENT),
            summary_card("Başarıyla Gönderildi", str(sent_count),
                         ft.icons.CHECK_CIRCLE_OUTLINE, theme.SUCCESS),
            summary_card("Başarısız", str(total_sms - sent_count),
                         ft.icons.ERROR_OUTLINE, theme.ERROR),
            summary_card("Toplam Maliyet", _fmt_cost(total_cost),
                         ft.icons.CURRENCY_LIRA_OUTLINED, theme.WARN),
        ],
        spacing=12,
    )

    # ── Tablo başlık ─────────────────────────────────────────────
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
                ft.Container(
                    content=ft.Text("MALİYET", size=10, color=theme.TEXT_MUTED,
                                    weight=ft.FontWeight.W_500),
                    width=80,
                ),
            ],
            spacing=16,
        ),
        padding=ft.padding.symmetric(horizontal=24, vertical=14),
        bgcolor=theme.SURFACE_ALT,
        border=ft.border.only(bottom=ft.BorderSide(1, theme.DIVIDER)),
    )

    is_mob = (page.width or 1200) < 768
    rows: list[ft.Control] = [] if is_mob else [header]

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

            cost = log.get("_cost", 0.0)
            cost_text = ft.Text(
                _fmt_cost(cost),
                size=12,
                color=theme.TEXT if cost > 0 else theme.TEXT_MUTED,
                weight=ft.FontWeight.W_500,
            )

            if is_mob:
                rows.append(ft.Container(
                    content=ft.Row([
                        type_chip,
                        ft.Column([
                            ft.Text(log.get("customer_name") or "—",
                                    size=12, weight=ft.FontWeight.W_500, color=theme.TEXT),
                            ft.Text((log.get("message") or "")[:60], size=10,
                                    color=theme.TEXT_MUTED, max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(str(ts), size=10, color=theme.TEXT_FAINT),
                        ], spacing=2, expand=True),
                        ft.Column([
                            status_icon,
                            ft.Text(_fmt_cost(cost), size=10, color=theme.TEXT_MUTED),
                        ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=ft.padding.symmetric(horizontal=14, vertical=10),
                    border=ft.border.only(bottom=ft.BorderSide(1, theme.DIVIDER)),
                ))
            else:
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
                            content=ft.Row(
                                [status_icon],
                                alignment=ft.MainAxisAlignment.START,
                            ),
                            width=90,
                        ),
                        ft.Container(
                            content=cost_text,
                            width=80,
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
        padding=ft.padding.only(bottom=20),
    )

    return ft.Column(
        [
            header_block,
            summary_row,
            ft.Container(height=20),
            theme.card(ft.Column(rows, spacing=0), padding=0),
        ],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )
