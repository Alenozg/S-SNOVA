"""
Kampanya (toplu SMS) yönetimi.
"""
from datetime import datetime
import flet as ft

def _dlg_close(page):
    """Flet 0.24.1 uyumlu dialog kapatma yardımcısı."""
    try:
        page.dialog.open = False
        page.update()
    except Exception:
        pass


import config
from services import campaign_service, customer_service
from ui import theme


class CampaignsView:
    def __init__(self, page: ft.Page):
        self.page = page
        self.list_container = ft.Column(spacing=0)

    def build(self) -> ft.Control:
        iys_count = customer_service.stats()["iys"]

        header = ft.Row(
            [
                ft.Column(
                    [theme.caption("PAZARLAMA"), theme.h1("Kampanyalar")],
                    spacing=4, expand=True,
                ),
                ft.IconButton(
                    ft.icons.SEND_OUTLINED,
                    icon_color=theme.SURFACE, bgcolor=theme.ACCENT,
                    icon_size=18, tooltip="Yeni Kampanya",
                    on_click=lambda e: self.open_form(),
                ) if (self.page.width or 1200) < 768 else theme.primary_button(
                    "Yeni Kampanya", icon=ft.icons.SEND_OUTLINED,
                    on_click=lambda e: self.open_form(),
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.END,
        )

        hint = ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.icons.INFO_OUTLINE, size=14, color=theme.TEXT_MUTED),
                    theme.body(
                        f"Kampanyalar yalnızca İYS onaylı müşterilere gönderilir. "
                        f"Şu an {iys_count} onaylı müşteri bulunuyor.",
                        muted=True,
                    ),
                ],
                spacing=8,
            ),
            padding=ft.padding.symmetric(vertical=20),
        )

        provider_warning = ft.Container(visible=False)
        if (config.SMS_PROVIDER or "mock").lower() == "mock":
            provider_warning = ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(ft.icons.WARNING_AMBER_ROUNDED, size=16, color="#b45309"),
                        ft.Text(
                            "SMS sağlayıcısı yapılandırılmamış (mock mod aktif). "
                            "Mesajlar iletilmeyecek — Ayarlar > SMS bölümünden Netgsm bilgilerini girin.",
                            size=12, color="#92400e",
                        ),
                    ],
                    spacing=8,
                ),
                padding=ft.padding.symmetric(horizontal=16, vertical=12),
                bgcolor="#fef3c7",
                border=ft.border.all(1, "#fcd34d"),
                border_radius=6,
            )

        self.refresh()
        return ft.Column(
            [header, hint, provider_warning, theme.card(self.list_container, padding=0)],
            scroll=ft.ScrollMode.AUTO, expand=True,
        )

    def refresh(self) -> None:
        items = campaign_service.list_campaigns()
        is_mob = (self.page.width or 1200) < 768
        controls: list[ft.Control] = [] if is_mob else [self._header_row()]
        if not items:
            controls.append(ft.Container(
                content=theme.body("Henüz kampanya gönderilmemiş.", muted=True),
                padding=40, alignment=ft.alignment.center,
            ))
        else:
            is_mob = (self.page.width or 1200) < 768
            for c in items:
                controls.append(self._row_mobile(c) if is_mob else self._row(c))

        self.list_container.controls = controls
        if self.list_container.page:
            self.list_container.update()

    def _header_row(self) -> ft.Container:
        def col(label, w=0, expand=False):
            return ft.Container(
                content=ft.Text(label.upper(), size=10, color=theme.TEXT_MUTED,
                                weight=ft.FontWeight.W_500),
                width=None if expand else w, expand=expand,
            )
        return ft.Container(
            content=ft.Row(
                [
                    col("Kampanya", expand=True),
                    col("Durum", 100),
                    col("Hedef", 70),
                    col("Gönderildi", 100),
                    col("Başarısız", 90),
                    col("Tarih", 140),
                ],
                spacing=16,
            ),
            padding=ft.padding.symmetric(horizontal=24, vertical=14),
            border=ft.border.only(bottom=ft.BorderSide(1, theme.DIVIDER)),
            bgcolor=theme.SURFACE_ALT,
        )

    def _row_mobile(self, c: dict) -> ft.Container:
        status_color = theme.SUCCESS if c["status"] == "sent" else theme.TEXT_MUTED
        sent_at = c.get("sent_at") or c.get("created_at") or ""
        try:
            from datetime import datetime
            sent_at = datetime.fromisoformat(sent_at).strftime("%d.%m.%Y")
        except Exception:
            pass
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text(c["name"], size=13, weight=ft.FontWeight.W_500,
                            color=theme.TEXT, expand=True, no_wrap=True,
                            overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Container(
                        content=ft.Text("Gönderildi" if c["status"]=="sent" else "Taslak",
                                        size=10, color=theme.SURFACE, weight=ft.FontWeight.W_500),
                        padding=ft.padding.symmetric(horizontal=6, vertical=3),
                        bgcolor=status_color, border_radius=2,
                    ),
                ], spacing=8),
                ft.Row([
                    ft.Text(f"Hedef: {c['target_count']}", size=11, color=theme.TEXT_MUTED),
                    ft.Text(f"✓ {c['sent_count']}", size=11, color=theme.SUCCESS),
                    ft.Text(f"✗ {c['failed_count']}", size=11, color=theme.ERROR),
                    ft.Container(expand=True),
                    ft.Text(str(sent_at)[:10], size=10, color=theme.TEXT_FAINT),
                ], spacing=10),
            ], spacing=6),
            padding=ft.padding.symmetric(horizontal=14, vertical=12),
            border=ft.border.only(bottom=ft.BorderSide(1, theme.DIVIDER)),
        )

    def _row(self, c: dict) -> ft.Container:
        status_color = theme.SUCCESS if c["status"] == "sent" else theme.TEXT_MUTED
        status_chip = ft.Container(
            content=ft.Text("Gönderildi" if c["status"] == "sent" else "Taslak",
                            size=10, color=theme.SURFACE, weight=ft.FontWeight.W_500),
            padding=ft.padding.symmetric(horizontal=8, vertical=4),
            bgcolor=status_color, border_radius=2,
        )
        sent_at = c.get("sent_at") or c.get("created_at") or ""
        if sent_at:
            try:
                sent_at = datetime.fromisoformat(sent_at).strftime("%d.%m.%Y %H:%M")
            except Exception:
                pass

        return ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text(c["name"], size=14, weight=ft.FontWeight.W_500,
                                        color=theme.TEXT),
                                theme.caption((c["message"] or "")[:90]),
                            ],
                            spacing=2,
                        ),
                        expand=True,
                    ),
                    ft.Container(content=status_chip, width=100),
                    ft.Container(content=theme.body(str(c["target_count"]), muted=True), width=70),
                    ft.Container(content=theme.body(str(c["sent_count"]), muted=True), width=100),
                    ft.Container(content=theme.body(str(c["failed_count"]), muted=True), width=90),
                    ft.Container(content=theme.caption(str(sent_at)), width=140),
                ],
                spacing=16,
            ),
            padding=ft.padding.symmetric(horizontal=24, vertical=14),
            border=ft.border.only(bottom=ft.BorderSide(1, theme.DIVIDER)),
        )

    # ------------------------------------------------- form
    def open_form(self) -> None:
        name = theme.text_field("Kampanya Adı", hint="Örn. Bahar Promosyonu")
        message = theme.text_field(
            "Mesaj", multiline=True,
            hint="Merhaba {name}, size özel %20 indirim fırsatı! ...",
        )
        char_counter = theme.caption("0 karakter • 1 SMS")

        def on_message_change(e):
            length = len(message.value or "")
            # Türkçe karakterli mesaj: 1 SMS = 150 karakter
            segments = max(1, -(-length // 150))
            cost = segments * 0.40
            char_counter.value = f"{length} karakter • {segments} SMS • ~{cost:.2f} TL"
            char_counter.update()

        message.on_change = on_message_change

        preview = ft.Container(
            content=ft.Column(
                [
                    theme.caption("MESAJ İPUCU"),
                    theme.body(
                        "{name} değişkeni müşterinin adıyla doldurulur. "
                        "Türkçe karakterler otomatik Latin'e çevrilir.",
                        muted=True,
                    ),
                ],
                spacing=4,
            ),
            padding=16, bgcolor=theme.SURFACE_ALT, border_radius=2,
        )
        error_text = ft.Text("", color=theme.ERROR, size=12)

        def send(e):
            if not (name.value and name.value.strip()):
                error_text.value = "Kampanya adı zorunlu."; error_text.update(); return
            if not (message.value and message.value.strip()):
                error_text.value = "Mesaj zorunlu."; error_text.update(); return

            try:
                summary = campaign_service.create_and_send_campaign(
                    name.value.strip(), message.value.strip()
                )
                self.page.dialog.open = False
                self.page.update()
                self.refresh()
                self.page.snack_bar = ft.SnackBar(
                    ft.Text(
                        f"Kampanya gönderildi: {summary['sent']} başarılı, "
                        f"{summary['failed']} başarısız."
                    ),
                    bgcolor=theme.SUCCESS,
                )
                self.page.snack_bar.open = True
                self.page.update()
            except ValueError as ex:
                error_text.value = str(ex); error_text.update()

        dlg = ft.AlertDialog(
            modal=True, bgcolor=theme.SURFACE,
            title=ft.Text("Yeni Kampanya", color=theme.TEXT,
                          weight=ft.FontWeight.W_400,
                          font_family=theme.FONT_FAMILY_DISPLAY, size=22),
            content=ft.Container(
                content=ft.Column(
                    [name, message, char_counter, preview, error_text],
                    tight=True, spacing=12,
                ),
                width=560,
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
    return CampaignsView(page).build()
