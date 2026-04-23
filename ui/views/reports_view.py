"""
Raporlar: Gelir • Personel Performansı • Hizmet İstatistikleri
"""
from datetime import datetime
import flet as ft

from services import analytics_service
from ui import theme

MONTHS_TR = {
    "01": "Oca", "02": "Şub", "03": "Mar", "04": "Nis",
    "05": "May", "06": "Haz", "07": "Tem", "08": "Ağu",
    "09": "Eyl", "10": "Eki", "11": "Kas", "12": "Ara",
}


def _fmt_tl(val) -> str:
    try:
        return f"{float(val):,.0f} ₺".replace(",", ".")
    except Exception:
        return "— ₺"


def _pct(part, total) -> str:
    try:
        return f"%{int(part / total * 100)}" if total else "%0"
    except Exception:
        return "%0"


# ── Mini bar chart (SVG-free, Flet container yığını) ──────────────
def _bar_chart(rows: list[dict], value_key: str, label_key: str,
               color: str, max_val: float | None = None) -> ft.Control:
    if not rows:
        return theme.body("Veri yok.", muted=True)
    mv = max_val or max((float(r.get(value_key) or 0) for r in rows), default=1) or 1
    bars = []
    for r in rows:
        val  = float(r.get(value_key) or 0)
        pct  = val / mv
        label = str(r.get(label_key, ""))
        # Ay kodu ise Türkçe ay kısaltmasına çevir (ör. "2026-04" → "Nis 26")
        if len(label) == 7 and label[4] == "-":
            mm, yy = label[5:7], label[2:4]
            label = f"{MONTHS_TR.get(mm, mm)} '{yy}"

        bars.append(
            ft.Column(
                [
                    ft.Text(_fmt_tl(val) if value_key == "revenue" else str(int(val)),
                            size=9, color=theme.TEXT_MUTED,
                            text_align=ft.TextAlign.CENTER),
                    ft.Container(
                        height=max(4, int(80 * pct)),
                        width=36,
                        bgcolor=color,
                        border_radius=ft.border_radius.only(top_left=3, top_right=3),
                    ),
                    ft.Text(label, size=9, color=theme.TEXT_MUTED,
                            text_align=ft.TextAlign.CENTER, no_wrap=False),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=4,
            )
        )
    return ft.Container(
        content=ft.Row(bars, alignment=ft.MainAxisAlignment.START,
                       vertical_alignment=ft.CrossAxisAlignment.END, spacing=8,
                       scroll=ft.ScrollMode.AUTO),
        height=140,
    )


# ── Tek satır istatistik ──────────────────────────────────────────
def _stat_row(label: str, value: str, sub: str = "",
              value_color: str | None = None) -> ft.Container:
    return ft.Container(
        content=ft.Row(
            [
                ft.Container(content=theme.body(label, muted=True), expand=True),
                ft.Column(
                    [
                        ft.Text(value, size=14, weight=ft.FontWeight.W_600,
                                color=value_color or theme.TEXT),
                        theme.caption(sub) if sub else ft.Container(height=0),
                    ],
                    spacing=1,
                    horizontal_alignment=ft.CrossAxisAlignment.END,
                ),
            ],
            spacing=16,
        ),
        padding=ft.padding.symmetric(vertical=11),
        border=ft.border.only(bottom=ft.BorderSide(1, theme.DIVIDER)),
    )


def build(page: ft.Page) -> ft.Control:
    # ── Veri ─────────────────────────────────────────────────────
    summary      = analytics_service.revenue_summary()
    monthly      = analytics_service.revenue_last_6_months()
    staff_perf   = analytics_service.staff_performance()
    svc_stats    = analytics_service.service_stats()
    status_breakdown = analytics_service.appointment_status_breakdown()

    this_month  = float(summary.get("this_month") or 0)
    last_month  = float(summary.get("last_month") or 0)
    this_year   = float(summary.get("this_year") or 0)
    appt_month  = int(summary.get("appt_this_month") or 0)

    diff = this_month - last_month
    diff_color = theme.SUCCESS if diff >= 0 else theme.ERROR
    diff_sign  = "▲" if diff >= 0 else "▼"
    diff_txt   = f"{diff_sign} {_fmt_tl(abs(diff))} geçen aya göre"

    # ── Stat kartları ─────────────────────────────────────────────
    def big_card(label, val, sub, color=None):
        return ft.Container(
            content=ft.Column([
                theme.caption(label),
                ft.Container(height=8),
                ft.Text(val, size=28, weight=ft.FontWeight.W_300,
                        color=color or theme.TEXT,
                        font_family=theme.FONT_FAMILY_DISPLAY),
                ft.Container(height=4),
                theme.caption(sub),
            ], spacing=0),
            padding=ft.padding.all(24),
            bgcolor=theme.SURFACE,
            border=ft.border.all(1, theme.DIVIDER),
            border_radius=8,
            expand=True,
        )

    is_mobile = (page.width or 1200) < 768
    _summary_cards = [
        big_card("BU AY GELİR",   _fmt_tl(this_month),  diff_txt, diff_color),
        big_card("GEÇEN AY GELİR", _fmt_tl(last_month), "karşılaştırma"),
        big_card("BU YIL TOPLAM", _fmt_tl(this_year),   "tamamlanan randevular"),
        big_card("BU AY RANDEVU", str(appt_month),       "toplam kayıt"),
    ]
    if is_mobile:
        summary_row = ft.Column(_summary_cards, spacing=10)
    else:
        summary_row = ft.Row(_summary_cards, spacing=12)

    # ── Durum dağılımı ────────────────────────────────────────────
    total_appts = sum(status_breakdown.values()) or 1
    status_labels = {
        "scheduled": ("Planlandı",      theme.ACCENT),
        "completed": ("Tamamlandı",     theme.SUCCESS),
        "cancelled": ("İptal",          theme.ERROR),
        "no_show":   ("Gelmedi",        theme.WARN),
    }
    status_pills = []
    for k, (lbl, col) in status_labels.items():
        cnt = status_breakdown.get(k, 0)
        status_pills.append(ft.Container(
            content=ft.Column([
                ft.Text(str(cnt), size=20, weight=ft.FontWeight.W_300,
                        color=col, font_family=theme.FONT_FAMILY_DISPLAY),
                ft.Text(lbl, size=10, color=theme.TEXT_MUTED),
                ft.Text(_pct(cnt, total_appts), size=10, color=col,
                        weight=ft.FontWeight.W_500),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2),
            padding=ft.padding.symmetric(horizontal=20, vertical=14),
            bgcolor=theme.SURFACE, border=ft.border.all(1, theme.DIVIDER),
            border_radius=8, expand=True,
        ))

    # ── Aylık gelir grafiği ───────────────────────────────────────
    revenue_chart = _bar_chart(monthly, "revenue", "month",
                               color=theme.ACCENT)
    appt_chart    = _bar_chart(monthly, "completed", "month",
                               color=theme.SUCCESS)

    revenue_card = theme.card(ft.Column([
        theme.h3("Aylık Gelir (Son 6 Ay)"),
        ft.Container(height=12),
        revenue_chart,
        ft.Container(height=16),
        theme.h3("Aylık Tamamlanan Randevu"),
        ft.Container(height=12),
        appt_chart,
    ], spacing=0))

    # ── Personel performansı ──────────────────────────────────────
    staff_rows: list[ft.Control] = [
        ft.Container(
            content=ft.Row([
                ft.Container(ft.Text("PERSONEL", size=10, color=theme.TEXT_MUTED,
                                     weight=ft.FontWeight.W_500), expand=True),
                ft.Container(ft.Text("RANDEVU", size=10, color=theme.TEXT_MUTED,
                                     weight=ft.FontWeight.W_500), width=80,
                             alignment=ft.alignment.center),
                ft.Container(ft.Text("TAMAMLANDI", size=10, color=theme.TEXT_MUTED,
                                     weight=ft.FontWeight.W_500), width=100,
                             alignment=ft.alignment.center),
                ft.Container(ft.Text("GELİR", size=10, color=theme.TEXT_MUTED,
                                     weight=ft.FontWeight.W_500), width=110,
                             alignment=ft.alignment.center_right),
            ], spacing=12),
            padding=ft.padding.symmetric(horizontal=20, vertical=12),
            bgcolor=theme.SURFACE_ALT,
            border=ft.border.only(bottom=ft.BorderSide(1, theme.DIVIDER)),
        )
    ]
    for s in staff_perf:
        total    = int(s.get("total") or 0)
        done     = int(s.get("completed") or 0)
        revenue  = float(s.get("revenue") or 0)
        rate_txt = _pct(done, total) if total else "—"
        color    = s.get("color") or theme.ACCENT

        staff_rows.append(ft.Container(
            content=ft.Row([
                ft.Row([
                    ft.Container(width=10, height=10, bgcolor=color,
                                 border_radius=5),
                    ft.Text(s.get("name", "—"), size=13, color=theme.TEXT,
                            weight=ft.FontWeight.W_500),
                ], spacing=8, expand=True),
                ft.Container(
                    ft.Text(str(total), size=13, color=theme.TEXT_MUTED,
                            text_align=ft.TextAlign.CENTER),
                    width=80, alignment=ft.alignment.center),
                ft.Container(
                    ft.Column([
                        ft.Text(str(done), size=13, color=theme.SUCCESS,
                                text_align=ft.TextAlign.CENTER,
                                weight=ft.FontWeight.W_500),
                        ft.Text(rate_txt, size=10, color=theme.TEXT_MUTED,
                                text_align=ft.TextAlign.CENTER),
                    ], spacing=1, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    width=100, alignment=ft.alignment.center),
                ft.Container(
                    ft.Text(_fmt_tl(revenue), size=13, color=theme.TEXT,
                            weight=ft.FontWeight.W_600,
                            text_align=ft.TextAlign.RIGHT),
                    width=110, alignment=ft.alignment.center_right),
            ], spacing=12),
            padding=ft.padding.symmetric(horizontal=20, vertical=14),
            border=ft.border.only(bottom=ft.BorderSide(1, theme.DIVIDER)),
        ))

    if len(staff_rows) == 1:
        staff_rows.append(ft.Container(
            content=theme.body("Henüz personel atamalı randevu yok.", muted=True),
            padding=32, alignment=ft.alignment.center,
        ))

    staff_card = theme.card(ft.Column([
        ft.Row([
            ft.Icon(ft.icons.BADGE_OUTLINED, size=18, color=theme.ACCENT),
            theme.h3("Personel Performansı"),
        ], spacing=8),
        ft.Container(height=12),
        ft.Column(staff_rows, spacing=0),
    ], spacing=0), padding=0)

    # ── Hizmet istatistikleri ─────────────────────────────────────
    svc_rows: list[ft.Control] = [
        ft.Container(
            content=ft.Row([
                ft.Container(ft.Text("HİZMET", size=10, color=theme.TEXT_MUTED,
                                     weight=ft.FontWeight.W_500), expand=True),
                ft.Container(ft.Text("RANDEVU", size=10, color=theme.TEXT_MUTED,
                                     weight=ft.FontWeight.W_500), width=80,
                             alignment=ft.alignment.center),
                ft.Container(ft.Text("TAMAMLANDI", size=10, color=theme.TEXT_MUTED,
                                     weight=ft.FontWeight.W_500), width=100,
                             alignment=ft.alignment.center),
                ft.Container(ft.Text("TOPLAM GELİR", size=10, color=theme.TEXT_MUTED,
                                     weight=ft.FontWeight.W_500), width=120,
                             alignment=ft.alignment.center_right),
            ], spacing=12),
            padding=ft.padding.symmetric(horizontal=20, vertical=12),
            bgcolor=theme.SURFACE_ALT,
            border=ft.border.only(bottom=ft.BorderSide(1, theme.DIVIDER)),
        )
    ]

    max_total = max((int(s.get("total") or 0) for s in svc_stats), default=1) or 1
    for sv in svc_stats:
        total   = int(sv.get("total") or 0)
        done    = int(sv.get("completed") or 0)
        revenue = float(sv.get("revenue") or 0)
        bar_w   = max(4, int(120 * total / max_total))

        svc_rows.append(ft.Container(
            content=ft.Row([
                ft.Column([
                    ft.Text(sv.get("name", "—"), size=13, color=theme.TEXT,
                            weight=ft.FontWeight.W_500),
                    ft.Container(
                        width=bar_w, height=3,
                        bgcolor=theme.ACCENT,
                        border_radius=2,
                    ),
                ], spacing=4, expand=True),
                ft.Container(
                    ft.Text(str(total), size=13, color=theme.TEXT_MUTED,
                            text_align=ft.TextAlign.CENTER),
                    width=80, alignment=ft.alignment.center),
                ft.Container(
                    ft.Text(str(done), size=13, color=theme.SUCCESS,
                            weight=ft.FontWeight.W_500,
                            text_align=ft.TextAlign.CENTER),
                    width=100, alignment=ft.alignment.center),
                ft.Container(
                    ft.Text(_fmt_tl(revenue), size=13, color=theme.TEXT,
                            weight=ft.FontWeight.W_600,
                            text_align=ft.TextAlign.RIGHT),
                    width=120, alignment=ft.alignment.center_right),
            ], spacing=12),
            padding=ft.padding.symmetric(horizontal=20, vertical=14),
            border=ft.border.only(bottom=ft.BorderSide(1, theme.DIVIDER)),
        ))

    if len(svc_rows) == 1:
        svc_rows.append(ft.Container(
            content=theme.body("Henüz hizmet verisi yok.", muted=True),
            padding=32, alignment=ft.alignment.center,
        ))

    svc_card = theme.card(ft.Column([
        ft.Row([
            ft.Icon(ft.icons.DESIGN_SERVICES_OUTLINED, size=18, color=theme.ACCENT),
            theme.h3("Hizmet İstatistikleri"),
        ], spacing=8),
        ft.Container(height=12),
        ft.Column(svc_rows, spacing=0),
    ], spacing=0), padding=0)

    _pill_row = ft.Column(
        [ft.Container(c) for c in status_pills], spacing=8
    ) if is_mobile else ft.Row(
        [ft.Container(c, expand=True) for c in status_pills], spacing=12
    )

    return ft.Column(
        [
            ft.Container(
                content=ft.Column([
                    theme.caption("ANALİTİK"),
                    theme.h1("Raporlar"),
                ], spacing=4),
                padding=ft.padding.only(bottom=24),
            ),
            summary_row,
            ft.Container(height=12),
            _pill_row,
            ft.Container(height=16),
            revenue_card,
            ft.Container(height=16),
            staff_card,
            ft.Container(height=16),
            svc_card,
        ],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )
