"""
Uzun süredir gelmeyen müşteriler + No-Show takibi.
İki sekme: Kayıp Müşteriler | No-Show / İptal
"""
from datetime import datetime
import flet as ft

from services import analytics_service, sms_service
from database.db_manager import get_setting
import config
from ui import theme


def _dlg_close(page):
    try:
        page.dialog.open = False
        page.update()
    except Exception:
        pass


def _fmt_date(val) -> str:
    if not val:
        return "Hiç gelmedi"
    try:
        if isinstance(val, str):
            val = datetime.fromisoformat(val.split(".")[0])
        return val.strftime("%d.%m.%Y")
    except Exception:
        return str(val)[:10]


class InactiveView:
    def __init__(self, page: ft.Page):
        self.page = page
        self._selected: set[int] = set()
        self._inactive_days = 60
        self._tab_index = 0

        self._content = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)

    def build(self) -> ft.Control:
        self._render()
        return ft.Column(
            [
                ft.Container(
                    content=ft.Column([
                        theme.caption("MÜŞTERİ ANALİZİ"),
                        theme.h1("Kayıp & No-Show Takibi"),
                    ], spacing=4),
                    padding=ft.padding.only(bottom=20),
                ),
                self._content,
            ],
            expand=True,
        )

    def _render(self):
        tabs = ft.Tabs(
            selected_index=self._tab_index,
            animation_duration=200,
            on_change=self._on_tab,
            tabs=[
                ft.Tab(text="Uzun Süredir Gelmeyen"),
                ft.Tab(text="No-Show / İptal Geçmişi"),
            ],
        )
        if self._tab_index == 0:
            body = self._inactive_tab()
        else:
            body = self._noshow_tab()

        self._content.controls = [tabs, ft.Container(height=16), body]
        if self._content.page:
            self._content.update()

    def _on_tab(self, e):
        self._tab_index = e.control.selected_index
        self._selected.clear()
        self._render()

    # ── Tab 1: Uzun Süredir Gelmeyen ──────────────────────────────
    def _inactive_tab(self) -> ft.Control:
        rows = analytics_service.inactive_customers(self._inactive_days)

        # Filtre satırı
        days_dd = ft.Dropdown(
            value=str(self._inactive_days),
            width=160,
            options=[
                ft.dropdown.Option("30",  "30+ gün"),
                ft.dropdown.Option("60",  "60+ gün"),
                ft.dropdown.Option("90",  "90+ gün"),
                ft.dropdown.Option("180", "6+ ay"),
            ],
            border_color=theme.DIVIDER,
            focused_border_color=theme.ACCENT,
            bgcolor=theme.SURFACE,
            text_style=ft.TextStyle(color=theme.TEXT, size=13),
            content_padding=ft.padding.symmetric(horizontal=12, vertical=10),
            on_change=lambda e: self._change_days(int(e.control.value)),
        )

        filter_row = ft.Row([
            ft.Icon(ft.icons.FILTER_LIST_OUTLINED, size=16, color=theme.TEXT_MUTED),
            theme.body("Filtre:", muted=True),
            days_dd,
            ft.Container(expand=True),
            theme.caption(f"{len(rows)} müşteri bulundu"),
        ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER)

        # Bulk aksiyon çubuğu
        sel_count = len(self._selected)
        bulk_bar = ft.Container(
            visible=sel_count > 0,
            content=ft.Row([
                ft.Icon(ft.icons.CHECK_CIRCLE, size=16, color=theme.ACCENT),
                ft.Text(f"{sel_count} müşteri seçildi", size=13,
                        weight=ft.FontWeight.W_500, color=theme.TEXT),
                ft.Container(expand=True),
                theme.ghost_button("Seçimi Temizle",
                                   on_click=lambda e: self._clear_sel()),
                theme.primary_button("SMS Gönder", icon=ft.icons.SEND_OUTLINED,
                                     on_click=lambda e: self._bulk_sms(rows)),
            ], spacing=10),
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
            bgcolor=theme.SURFACE_ALT,
            border=ft.border.only(left=ft.BorderSide(3, theme.ACCENT)),
            border_radius=2,
            margin=ft.margin.only(bottom=12),
        )

        if not rows:
            table = ft.Container(
                content=ft.Column([
                    ft.Icon(ft.icons.FAVORITE_OUTLINED, size=40, color=theme.SUCCESS),
                    ft.Container(height=8),
                    theme.body("Tüm müşterileriniz düzenli geliyor! 🎉", muted=True),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                alignment=ft.alignment.center, padding=60,
            )
        else:
            header = ft.Container(
                content=ft.Row([
                    ft.Container(width=44),
                    ft.Container(theme.caption("MÜŞTERİ"), expand=True),
                    ft.Container(theme.caption("TELEFON"), width=150),
                    ft.Container(theme.caption("SON ZİYARET"), width=120),
                    ft.Container(theme.caption("TOP. ZİYARET"), width=110),
                    ft.Container(width=60),
                ], spacing=12),
                padding=ft.padding.symmetric(horizontal=20, vertical=12),
                bgcolor=theme.SURFACE_ALT,
                border=ft.border.only(bottom=ft.BorderSide(1, theme.DIVIDER)),
            )
            data_rows = [header]
            for r in rows:
                cid = r["id"]
                is_sel = cid in self._selected
                data_rows.append(ft.Container(
                    content=ft.Row([
                        ft.Container(
                            ft.Checkbox(
                                value=is_sel,
                                check_color=theme.SURFACE, fill_color=theme.ACCENT,
                                on_change=lambda e, c=cid: self._toggle(c, bool(e.control.value)),
                            ), width=44, alignment=ft.alignment.center_left,
                        ),
                        ft.Container(
                            ft.Text(f"{r['first_name']} {r['last_name']}",
                                    size=13, weight=ft.FontWeight.W_500, color=theme.TEXT),
                            expand=True,
                        ),
                        ft.Container(
                            ft.Text(r.get("phone") or "—", size=12, color=theme.TEXT_MUTED),
                            width=150,
                        ),
                        ft.Container(
                            ft.Column([
                                ft.Text(_fmt_date(r.get("last_visit")), size=12,
                                        color=theme.ERROR if not r.get("last_visit") else theme.TEXT_MUTED),
                            ], spacing=0),
                            width=120,
                        ),
                        ft.Container(
                            ft.Text(str(int(r.get("total_visits") or 0)) + " kez",
                                    size=12, color=theme.TEXT_MUTED),
                            width=110,
                        ),
                        ft.Container(
                            ft.IconButton(
                                ft.icons.SMS_OUTLINED, icon_size=16,
                                icon_color=theme.ACCENT,
                                tooltip="SMS Gönder",
                                on_click=lambda e, c=r: self._single_sms(c),
                            ), width=60,
                        ),
                    ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=ft.padding.symmetric(horizontal=20, vertical=12),
                    bgcolor="#F0EBE3" if is_sel else None,
                    border=ft.border.only(bottom=ft.BorderSide(1, theme.DIVIDER)),
                ))
            table = theme.card(ft.Column(data_rows, spacing=0), padding=0)

        return ft.Column([filter_row, ft.Container(height=12),
                          bulk_bar, table], spacing=0)

    # ── Tab 2: No-Show / İptal ────────────────────────────────────
    def _noshow_tab(self) -> ft.Control:
        rows = analytics_service.noshow_customers(min_count=1)

        if not rows:
            return ft.Container(
                content=ft.Column([
                    ft.Icon(ft.icons.VERIFIED_OUTLINED, size=40, color=theme.SUCCESS),
                    ft.Container(height=8),
                    theme.body("Kayıt yok — harika! 🎉", muted=True),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                alignment=ft.alignment.center, padding=60,
            )

        header = ft.Container(
            content=ft.Row([
                ft.Container(theme.caption("MÜŞTERİ"), expand=True),
                ft.Container(theme.caption("TELEFON"), width=160),
                ft.Container(theme.caption("GELMEDİ/İPTAL"), width=130),
                ft.Container(theme.caption("SON TARİH"), width=120),
                ft.Container(theme.caption("RİSK"), width=80),
            ], spacing=12),
            padding=ft.padding.symmetric(horizontal=20, vertical=12),
            bgcolor=theme.SURFACE_ALT,
            border=ft.border.only(bottom=ft.BorderSide(1, theme.DIVIDER)),
        )

        data_rows = [header]
        for r in rows:
            cnt = int(r.get("noshow_count") or 0)
            if cnt >= 4:
                risk_label, risk_color = "Yüksek", theme.ERROR
            elif cnt >= 2:
                risk_label, risk_color = "Orta", theme.WARN
            else:
                risk_label, risk_color = "Düşük", theme.SUCCESS

            data_rows.append(ft.Container(
                content=ft.Row([
                    ft.Container(
                        ft.Text(f"{r['first_name']} {r['last_name']}",
                                size=13, weight=ft.FontWeight.W_500, color=theme.TEXT),
                        expand=True,
                    ),
                    ft.Container(
                        ft.Text(r.get("phone") or "—", size=12, color=theme.TEXT_MUTED),
                        width=160,
                    ),
                    ft.Container(
                        ft.Text(f"{cnt} kez", size=13, color=risk_color,
                                weight=ft.FontWeight.W_600),
                        width=130,
                    ),
                    ft.Container(
                        ft.Text(_fmt_date(r.get("last_noshow")), size=12,
                                color=theme.TEXT_MUTED),
                        width=120,
                    ),
                    ft.Container(
                        ft.Container(
                            content=ft.Text(risk_label, size=10, color=theme.SURFACE,
                                            weight=ft.FontWeight.W_500),
                            padding=ft.padding.symmetric(horizontal=8, vertical=4),
                            bgcolor=risk_color, border_radius=2,
                        ), width=80,
                    ),
                ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                padding=ft.padding.symmetric(horizontal=20, vertical=13),
                border=ft.border.only(bottom=ft.BorderSide(1, theme.DIVIDER)),
            ))

        return theme.card(ft.Column(data_rows, spacing=0), padding=0)

    # ── Aksiyonlar ────────────────────────────────────────────────
    def _change_days(self, days: int):
        self._inactive_days = days
        self._selected.clear()
        self._render()

    def _toggle(self, cid: int, checked: bool):
        if checked:
            self._selected.add(cid)
        else:
            self._selected.discard(cid)
        self._render()

    def _clear_sel(self):
        self._selected.clear()
        self._render()

    def _single_sms(self, row: dict):
        self._open_sms_dialog(
            [(row["id"], row["first_name"], row.get("phone", ""))],
            title=f"{row['first_name']} {row['last_name']} – SMS Gönder",
        )

    def _bulk_sms(self, all_rows: list[dict]):
        targets = [
            (r["id"], r["first_name"], r.get("phone", ""))
            for r in all_rows if r["id"] in self._selected
        ]
        self._open_sms_dialog(targets, title=f"{len(targets)} müşteriye SMS Gönder")

    def _open_sms_dialog(self, targets: list[tuple], title: str):
        default_msg = (
            "Merhaba {name}, sizi çok ozledik! "
            "Randevu almak icin bize ulasabilirsiniz. {salon}"
        )
        msg_field = theme.text_field("Mesaj", multiline=True, hint="{name} = müşteri adı")
        msg_field.value = default_msg
        char_counter = theme.caption(f"{len(default_msg)} karakter • 1 SMS • ~0.40 TL")
        err = ft.Text("", color=theme.ERROR, size=12)

        def on_change(e):
            ln = len(msg_field.value or "")
            segs = max(1, -(-ln // 150))
            char_counter.value = f"{ln} karakter • {segs} SMS • ~{segs*0.40:.2f} TL"
            char_counter.update()

        msg_field.on_change = on_change

        def send(e):
            msg = (msg_field.value or "").strip()
            if not msg:
                err.value = "Mesaj boş olamaz."; err.update(); return
            ok = fail = 0
            for cid, fname, phone in targets:
                if not phone:
                    fail += 1; continue
                r = sms_service.send_sms(
                    phone=phone,
                    message=msg.replace("{name}", fname).replace("{salon}", config.SALON_NAME),
                    customer_id=cid, sms_type="campaign",
                )
                if r.success: ok += 1
                else: fail += 1
            _dlg_close(self.page)
            self.page.snack_bar = ft.SnackBar(
                ft.Text(f"SMS tamamlandı: {ok} başarılı, {fail} başarısız."),
                bgcolor=theme.SUCCESS if ok else theme.ERROR,
            )
            self.page.snack_bar.open = True
            self.page.update()
            self._clear_sel()

        dlg = ft.AlertDialog(
            modal=True, bgcolor=theme.SURFACE,
            title=ft.Text(title, color=theme.TEXT, weight=ft.FontWeight.W_400,
                          font_family=theme.FONT_FAMILY_DISPLAY, size=20),
            content=ft.Container(
                content=ft.Column([msg_field, char_counter, err],
                                  tight=True, spacing=8),
                width=480,
            ),
            actions=[
                theme.ghost_button("Vazgeç", on_click=lambda e: _dlg_close(self.page)),
                theme.primary_button("Gönder", icon=ft.icons.SEND, on_click=send),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.dialog = dlg
        self.page.dialog.open = True
        self.page.update()


def build(page: ft.Page) -> ft.Control:
    return InactiveView(page).build()
