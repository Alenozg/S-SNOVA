"""
Müşteri profil ekranı (Plandok benzeri kapsamlı görünüm).

Büyük bir AlertDialog olarak açılır. İçerik:
  - Sol: temel bilgiler (ad, tel, e-posta, cinsiyet, doğum tarihi, İYS, notlar)
  - Sağ üst: 4 istatistik kartı (harcama, tamamlanan, iptal, gelmedi)
  - Alt: geçmiş randevular tablosu (tarih, hizmet, personel, durum, tutar)

Kullanım:
    open_customer_profile(page, customer_id=42)
"""
from datetime import datetime
from typing import Callable, Optional

import flet as ft

from services import customer_service, appointment_service
from ui import theme


STATUS_COLORS = {
    "scheduled": theme.ACCENT,
    "completed": theme.SUCCESS,
    "cancelled": theme.ERROR,
    "no_show":   theme.WARN,
}


def open_customer_profile(
    page: ft.Page,
    customer_id: int,
    on_edit: Optional[Callable[[int], None]] = None,
) -> None:
    """
    Büyük modal olarak profil ekranını açar.

    on_edit: kullanıcı "Düzenle" dediğinde çağrılır; genelde
             CustomersView.open_form(cid) bağlanır.
    """
    c = customer_service.get_customer(customer_id)
    if not c:
        page.snack_bar = ft.SnackBar(
            ft.Text("Müşteri bulunamadı."), bgcolor=theme.ERROR)
        page.snack_bar.open = True
        page.update()
        return

    stats = customer_service.customer_stats(customer_id)
    appointments = appointment_service.customer_appointments(customer_id)

    # ---------- SOL: temel bilgiler ----------
    def info_row(label: str, value: str) -> ft.Container:
        return ft.Container(
            content=ft.Column(
                [
                    ft.Text(label.upper(), size=10, color=theme.TEXT_MUTED,
                            weight=ft.FontWeight.W_500),
                    ft.Text(
                        value or "—", size=14, color=theme.TEXT,
                        weight=ft.FontWeight.W_400,
                        selectable=True,
                    ),
                ],
                spacing=4, tight=True,
            ),
            padding=ft.padding.symmetric(vertical=10),
            border=ft.border.only(bottom=ft.BorderSide(1, theme.DIVIDER)),
        )

    # Baş harfler - avatar
    initials = "".join([
        (c.first_name[:1] or "").upper(),
        (c.last_name[:1] or "").upper(),
    ]) or "—"

    avatar = ft.Container(
        content=ft.Text(
            initials, size=28,
            weight=ft.FontWeight.W_300,
            color=theme.SURFACE,
            font_family=theme.FONT_FAMILY_DISPLAY,
        ),
        width=72, height=72,
        bgcolor=theme.ACCENT,
        border_radius=36,
        alignment=ft.alignment.center,
    )

    # İYS rozet
    iys_badge = ft.Container(
        content=ft.Row(
            [
                ft.Icon(
                    ft.icons.CHECK_CIRCLE_OUTLINE if c.iys_consent
                    else ft.icons.REMOVE_CIRCLE_OUTLINE,
                    size=14,
                    color=theme.SUCCESS if c.iys_consent else theme.TEXT_MUTED,
                ),
                ft.Text(
                    "İYS Onaylı" if c.iys_consent else "İYS Onayı Yok",
                    size=11, color=theme.TEXT_MUTED,
                    weight=ft.FontWeight.W_500,
                ),
            ],
            spacing=6,
        ),
        padding=ft.padding.symmetric(horizontal=10, vertical=4),
        bgcolor=theme.SURFACE_ALT,
        border_radius=2,
    )

    left_panel = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [avatar,
                     ft.Column(
                         [
                             ft.Text(
                                 c.full_name, size=22,
                                 weight=ft.FontWeight.W_400,
                                 color=theme.TEXT,
                                 font_family=theme.FONT_FAMILY_DISPLAY,
                             ),
                             ft.Text(
                                 f"{c.age} yaş" if c.age else "yaş bilinmiyor",
                                 size=12, color=theme.TEXT_MUTED,
                             ),
                             iys_badge,
                         ],
                         spacing=4, tight=True,
                     )],
                    spacing=16, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Container(height=16),
                info_row("Telefon", c.display_phone),
                info_row("E-posta", c.email),
                info_row("Cinsiyet", c.gender_label),
                info_row(
                    "Doğum Tarihi",
                    c.birth_date.strftime("%d.%m.%Y") if c.birth_date else "—",
                ),
                info_row("Notlar", c.notes),
            ],
            spacing=0, scroll=ft.ScrollMode.AUTO,
        ),
        width=340,
        padding=ft.padding.only(right=24),
    )

    # ---------- SAĞ ÜST: 4 istatistik kartı ----------
    def stat_card(
        label: str, value: str, color: str, icon=None,
    ) -> ft.Container:
        return ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(icon, size=14, color=color) if icon else ft.Container(),
                            ft.Text(
                                label.upper(), size=10, color=theme.TEXT_MUTED,
                                weight=ft.FontWeight.W_500,
                            ),
                        ],
                        spacing=6,
                    ),
                    ft.Container(height=8),
                    ft.Text(
                        value, size=26,
                        weight=ft.FontWeight.W_300, color=color,
                        font_family=theme.FONT_FAMILY_DISPLAY,
                    ),
                ],
                spacing=0, tight=True,
            ),
            padding=16,
            bgcolor=theme.SURFACE,
            border=ft.border.all(1, theme.DIVIDER),
            border_radius=2,
            expand=True,
        )

    total_spent_str = (
        f"₺{stats['total_spent']:,.0f}"
        .replace(",", "X").replace(".", ",").replace("X", ".")
    )

    stats_row_1 = ft.Row(
        [
            stat_card(
                "Toplam Harcama", total_spent_str,
                theme.ACCENT, ft.icons.PAYMENTS_OUTLINED,
            ),
            stat_card(
                "Toplam Randevu", str(stats["total_appts"]),
                theme.TEXT, ft.icons.EVENT_NOTE_OUTLINED,
            ),
        ],
        spacing=12,
    )
    stats_row_2 = ft.Row(
        [
            stat_card(
                "Tamamlanan", str(stats["completed"]),
                theme.SUCCESS, ft.icons.CHECK_CIRCLE_OUTLINE,
            ),
            stat_card(
                "İptal", str(stats["cancelled"]),
                theme.ERROR, ft.icons.CANCEL_OUTLINED,
            ),
            stat_card(
                "Gelmedi", str(stats["no_show"]),
                theme.WARN, ft.icons.REMOVE_CIRCLE_OUTLINE,
            ),
        ],
        spacing=12,
    )

    # ---------- SAĞ ALT: Geçmiş randevular tablosu ----------
    def tbl_header(label: str, width: Optional[int] = None,
                   expand: bool = False) -> ft.Container:
        return ft.Container(
            content=ft.Text(
                label.upper(), size=10, color=theme.TEXT_MUTED,
                weight=ft.FontWeight.W_500,
            ),
            width=width, expand=expand,
        )

    appt_table_header = ft.Container(
        content=ft.Row(
            [
                tbl_header("Tarih", 120),
                tbl_header("Hizmet", expand=True),
                tbl_header("Personel", 140),
                tbl_header("Durum", 100),
                tbl_header("Tutar", 90),
            ],
            spacing=12,
        ),
        padding=ft.padding.symmetric(horizontal=16, vertical=10),
        bgcolor=theme.SURFACE_ALT,
        border=ft.border.only(bottom=ft.BorderSide(1, theme.DIVIDER)),
    )

    appt_rows: list[ft.Control] = []
    if not appointments:
        appt_rows.append(ft.Container(
            content=ft.Column(
                [
                    ft.Icon(
                        ft.icons.EVENT_BUSY_OUTLINED, size=32,
                        color=theme.TEXT_FAINT,
                    ),
                    ft.Container(height=8),
                    ft.Text(
                        "Henüz randevu yok.", size=13,
                        color=theme.TEXT_MUTED,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER, tight=True,
            ),
            padding=40, alignment=ft.alignment.center,
        ))
    else:
        for a in appointments:
            when = a.appointment_at.strftime("%d.%m.%Y %H:%M") if a.appointment_at else "—"
            status_chip = ft.Container(
                content=ft.Text(
                    a.status_label, size=10, color=theme.SURFACE,
                    weight=ft.FontWeight.W_500,
                ),
                padding=ft.padding.symmetric(horizontal=8, vertical=3),
                bgcolor=STATUS_COLORS.get(a.status, theme.TEXT_MUTED),
                border_radius=2,
            )
            price_str = (
                f"₺{a.price:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
                if getattr(a, "price", None) else "—"
            )
            # Personel renkli nokta
            staff_chip_children: list[ft.Control] = []
            if a.staff_color:
                staff_chip_children.append(ft.Container(
                    width=8, height=8, bgcolor=a.staff_color,
                    border_radius=4,
                ))
            staff_chip_children.append(ft.Text(
                a.staff_name or "—", size=12, color=theme.TEXT,
                max_lines=1, overflow=ft.TextOverflow.ELLIPSIS,
            ))

            appt_rows.append(ft.Container(
                content=ft.Row(
                    [
                        ft.Container(
                            content=ft.Text(when, size=12, color=theme.TEXT),
                            width=120,
                        ),
                        ft.Container(
                            content=ft.Text(
                                a.service_name or "—", size=13,
                                color=theme.TEXT,
                                weight=ft.FontWeight.W_500,
                                max_lines=1, overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            expand=True,
                        ),
                        ft.Container(
                            content=ft.Row(staff_chip_children, spacing=6),
                            width=140,
                        ),
                        ft.Container(content=status_chip, width=100),
                        ft.Container(
                            content=ft.Text(
                                price_str, size=13,
                                color=theme.TEXT if a.price else theme.TEXT_MUTED,
                                weight=ft.FontWeight.W_500 if a.price else ft.FontWeight.W_400,
                            ),
                            width=90,
                        ),
                    ],
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=ft.padding.symmetric(horizontal=16, vertical=10),
                border=ft.border.only(bottom=ft.BorderSide(1, theme.DIVIDER)),
            ))

    appts_section = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Text(
                            "Randevu Geçmişi", size=14,
                            weight=ft.FontWeight.W_500, color=theme.TEXT,
                        ),
                        ft.Container(expand=True),
                        ft.Text(
                            f"{len(appointments)} kayıt", size=11,
                            color=theme.TEXT_MUTED,
                        ),
                    ],
                    spacing=8,
                ),
                ft.Container(height=10),
                ft.Container(
                    content=ft.Column(
                        [appt_table_header] + appt_rows,
                        spacing=0, scroll=ft.ScrollMode.AUTO,
                    ),
                    bgcolor=theme.SURFACE,
                    border=ft.border.all(1, theme.DIVIDER),
                    border_radius=2,
                    height=280,
                ),
            ],
            spacing=0, tight=True,
        ),
    )

    right_panel = ft.Container(
        content=ft.Column(
            [
                stats_row_1,
                ft.Container(height=12),
                stats_row_2,
                ft.Container(height=20),
                appts_section,
            ],
            spacing=0, scroll=ft.ScrollMode.AUTO,
        ),
        expand=True,
        padding=ft.padding.only(left=24),
        border=ft.border.only(left=ft.BorderSide(1, theme.DIVIDER)),
    )

    # ---------- Modal bütünü ----------
    dlg: ft.AlertDialog = ft.AlertDialog(modal=True, bgcolor=theme.SURFACE)

    def close(e=None):
        page.dialog.open = False
        page.update()

    def edit(e=None):
        page.dialog.open = False
        page.update()
        if on_edit:
            on_edit(customer_id)

    dlg.title = ft.Row(
        [
            ft.Text(
                "Müşteri Profili",
                color=theme.TEXT, weight=ft.FontWeight.W_400,
                font_family=theme.FONT_FAMILY_DISPLAY, size=22,
            ),
            ft.Container(expand=True),
            ft.IconButton(
                ft.icons.CLOSE, icon_color=theme.TEXT_MUTED,
                on_click=close, tooltip="Kapat",
            ),
        ],
        spacing=8,
    )
    dlg.content = ft.Container(
        content=ft.Row(
            [left_panel, right_panel],
            spacing=0,
            vertical_alignment=ft.CrossAxisAlignment.START,
        ),
        width=960,
        height=620,
    )
    dlg.actions = [
        theme.ghost_button("Kapat", on_click=close),
        theme.primary_button(
            "Bilgileri Düzenle",
            icon=ft.icons.EDIT_OUTLINED, on_click=edit,
        ),
    ]
    dlg.actions_alignment = ft.MainAxisAlignment.END

    page.dialog = dlg
    page.dialog.open = True
    page.update()
