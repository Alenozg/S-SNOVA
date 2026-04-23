"""
Hizmetler (services) yönetim sayfası.
- Sade tablo görünümü
- Üstte "Yeni Hizmet" butonu
- Her satırda düzenle/sil ikonları
"""
import flet as ft

from models import Service
from services import service_service
from ui import theme


class ServicesView:
    def __init__(self, page: ft.Page):
        self.page = page
        self.list_container = ft.Column(spacing=0)

    # ==================================================================
    def build(self) -> ft.Control:
        new_button = theme.primary_button(
            "Yeni Hizmet",
            icon=ft.icons.ADD,
            on_click=lambda e: self._open_dialog(edit_id=None),
        )

        header = ft.Row(
            [
                ft.Column(
                    [theme.caption("İŞLEMLER"), theme.h1("Hizmetler")],
                    spacing=4, expand=True,
                ),
                new_button,
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.END,
        )

        info = ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.icons.INFO_OUTLINE, size=14, color=theme.TEXT_MUTED),
                    theme.body(
                        "Randevu oluştururken seçilen hizmete göre "
                        "işlem süresi ve fiyat otomatik doldurulur.",
                        muted=True,
                    ),
                ],
                spacing=8,
            ),
            padding=ft.padding.symmetric(vertical=20),
        )

        self.refresh()
        return ft.Column(
            [header, info, theme.card(self.list_container, padding=0)],
            scroll=ft.ScrollMode.AUTO, expand=True,
        )

    # ==================================================================
    def refresh(self) -> None:
        items = service_service.list_services()
        is_mob = (self.page.width or 1200) < 768
        controls: list[ft.Control] = [] if is_mob else [self._header_row()]

        if not items:
            controls.append(ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(
                            ft.icons.DESIGN_SERVICES_OUTLINED,
                            size=36, color=theme.TEXT_FAINT,
                        ),
                        ft.Container(height=8),
                        theme.body("Henüz hizmet eklenmedi.", muted=True),
                        ft.Container(height=4),
                        theme.caption(
                            "Sağ üstteki 'Yeni Hizmet' düğmesine tıklayın."
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0,
                ),
                padding=40, alignment=ft.alignment.center,
            ))
        else:
            for s in items:
                controls.append(self._service_row_mobile(s) if is_mob else self._service_row(s))

        self.list_container.controls = controls
        if self.list_container.page:
            self.list_container.update()

    def _header_row(self) -> ft.Container:
        def col(label: str, w: int = 0, expand: bool = False):
            return ft.Container(
                content=ft.Text(label.upper(), size=10, color=theme.TEXT_MUTED,
                                weight=ft.FontWeight.W_500),
                width=None if expand else w, expand=expand,
            )
        return ft.Container(
            content=ft.Row(
                [
                    col("Hizmet Adı", expand=True),
                    col("Süre", w=120),
                    col("Fiyat", w=120),
                    col("Durum", w=80),
                    ft.Container(width=100),
                ],
                spacing=16,
            ),
            padding=ft.padding.symmetric(horizontal=24, vertical=14),
            border=ft.border.only(bottom=ft.BorderSide(1, theme.DIVIDER)),
            bgcolor=theme.SURFACE_ALT,
        )

    def _service_row_mobile(self, s: Service) -> ft.Container:
        return ft.Container(
            content=ft.Row([
                ft.Column([
                    ft.Text(s.name, size=13, weight=ft.FontWeight.W_500,
                            color=theme.TEXT, no_wrap=True,
                            overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Row([
                        ft.Text(f"{int(s.duration_min)} dk", size=11, color=theme.TEXT_MUTED),
                        ft.Text("·", size=11, color=theme.TEXT_FAINT),
                        ft.Text(f"{s.price:.0f} ₺", size=11,
                                color=theme.ACCENT, weight=ft.FontWeight.W_500),
                    ], spacing=6),
                ], spacing=3, expand=True),
                ft.Container(
                    content=ft.Text("Aktif" if s.active else "Pasif",
                                    size=10, color=theme.SURFACE, weight=ft.FontWeight.W_500),
                    padding=ft.padding.symmetric(horizontal=6, vertical=3),
                    bgcolor=theme.SUCCESS if s.active else theme.TEXT_MUTED, border_radius=2,
                ),
                ft.IconButton(ft.icons.EDIT_OUTLINED, icon_size=16,
                              icon_color=theme.TEXT_MUTED,
                              on_click=lambda e, sv=s: self.open_form(sv)),
            ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.padding.symmetric(horizontal=14, vertical=11),
            border=ft.border.only(bottom=ft.BorderSide(1, theme.DIVIDER)),
        )

    def _service_row(self, s: Service) -> ft.Container:
        status_chip = ft.Container(
            content=ft.Text(
                "Aktif" if s.active else "Pasif", size=11,
                color=theme.SURFACE, weight=ft.FontWeight.W_500,
            ),
            padding=ft.padding.symmetric(horizontal=8, vertical=4),
            bgcolor=theme.SUCCESS if s.active else theme.TEXT_MUTED,
            border_radius=2,
        )

        return ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        content=ft.Text(
                            s.name, size=14,
                            weight=ft.FontWeight.W_500, color=theme.TEXT,
                        ),
                        expand=True,
                    ),
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Icon(
                                    ft.icons.SCHEDULE,
                                    size=13, color=theme.TEXT_MUTED,
                                ),
                                ft.Text(
                                    s.display_duration, size=13,
                                    color=theme.TEXT_MUTED,
                                ),
                            ],
                            spacing=5,
                        ),
                        width=120,
                    ),
                    ft.Container(
                        content=ft.Text(
                            s.display_price, size=14,
                            color=theme.TEXT, weight=ft.FontWeight.W_500,
                        ),
                        width=120,
                    ),
                    ft.Container(content=status_chip, width=80),
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.IconButton(
                                    ft.icons.EDIT_OUTLINED, icon_size=16,
                                    icon_color=theme.TEXT_MUTED,
                                    on_click=lambda e, sid=s.id:
                                        self._open_dialog(edit_id=sid),
                                    tooltip="Düzenle",
                                ),
                                ft.IconButton(
                                    ft.icons.DELETE_OUTLINE, icon_size=16,
                                    icon_color=theme.TEXT_MUTED,
                                    on_click=lambda e, sid=s.id, nm=s.name:
                                        self._confirm_delete(sid, nm),
                                    tooltip="Sil",
                                ),
                            ],
                            spacing=0,
                        ),
                        width=100,
                    ),
                ],
                spacing=16,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.symmetric(horizontal=24, vertical=14),
            border=ft.border.only(bottom=ft.BorderSide(1, theme.DIVIDER)),
            ink=True,
            on_click=lambda e, sid=s.id: self._open_dialog(edit_id=sid),
        )

    # ==================================================================
    # Ekleme / düzenleme diyaloğu
    # ==================================================================
    def _open_dialog(self, edit_id: int | None = None) -> None:
        existing = service_service.get_service(edit_id) if edit_id else None

        name_field = theme.text_field(
            "Hizmet Adı", existing.name if existing else "",
            hint="Örn. Lazer Epilasyon, İpek Kirpik, Cilt Bakımı",
        )
        duration_field = theme.text_field(
            "Süre (dk)",
            str(existing.duration_min) if existing else "30",
            hint="Sadece sayı — randevu takvimi bu süreyi kullanır",
        )
        price_field = theme.text_field(
            "Fiyat (₺)",
            str(int(existing.price)) if existing and existing.price is not None else "",
            hint="Ondalık için nokta kullanın (örn. 250 veya 249.90)",
        )
        active_cb = ft.Checkbox(
            label="Aktif (pasif hizmet yeni randevuda seçilemez)",
            value=bool(existing.active) if existing else True,
            check_color=theme.SURFACE, fill_color=theme.ACCENT,
            label_style=ft.TextStyle(size=12, color=theme.TEXT_MUTED),
        )
        error_text = ft.Text("", color=theme.ERROR, size=12)

        dlg_ref: dict = {"dlg": None}

        def close(e=None):
            if dlg_ref["dlg"]:
                self.page.dialog.open = False
                self.page.update()

        def save(e):
            try:
                # Süre parse
                try:
                    duration = int((duration_field.value or "").strip())
                except ValueError:
                    raise ValueError("İşlem süresi sayı olmalı (dakika).")

                # Fiyat parse (boş ise 0)
                price_raw = (price_field.value or "").strip().replace(",", ".")
                try:
                    price = float(price_raw) if price_raw else 0.0
                except ValueError:
                    raise ValueError("Fiyat sayı olmalı (örn. 250 veya 249.90).")

                payload = Service(
                    id=existing.id if existing else None,
                    name=(name_field.value or "").strip(),
                    duration_min=duration,
                    price=price,
                    active=bool(active_cb.value),
                )

                if existing:
                    service_service.update_service(payload)
                    msg = "Hizmet güncellendi."
                else:
                    service_service.create_service(payload)
                    msg = "Hizmet eklendi."

                close()
                self.refresh()
                self.page.snack_bar = ft.SnackBar(
                    ft.Text(msg), bgcolor=theme.SUCCESS,
                )
                self.page.snack_bar.open = True
                self.page.update()
            except ValueError as ex:
                error_text.value = str(ex)
                error_text.update()
            except Exception as ex:
                error_text.value = f"Beklenmedik hata: {ex}"
                error_text.update()

        dlg = ft.AlertDialog(
            modal=True, bgcolor=theme.SURFACE,
            title=ft.Text(
                "Hizmet Bilgileri" if existing else "Yeni Hizmet",
                color=theme.TEXT, weight=ft.FontWeight.W_400,
                font_family=theme.FONT_FAMILY_DISPLAY, size=22,
            ),
            content=ft.Column(
                    [
                        name_field,
                        duration_field,
                        price_field,
                        active_cb,
                        error_text,
                    ],
                    tight=True, spacing=12,
                ),
            actions=[
                theme.ghost_button("Vazgeç", on_click=close),
                theme.primary_button("Kaydet", on_click=save),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        dlg_ref["dlg"] = dlg

        try:
            self.page.dialog = dlg
            self.page.dialog.open = True
            self.page.update()
        except Exception as e1:
            try:
                self.page.dialog = dlg
                dlg.open = True
                self.page.update()
            except Exception as e2:
                self.page.snack_bar = ft.SnackBar(
                    ft.Text(f"Dialog açılamadı: {e1}"),
                    bgcolor=theme.ERROR,
                )
                self.page.snack_bar.open = True
                self.page.update()

    # ==================================================================
    # Silme onayı
    # ==================================================================
    def _confirm_delete(self, service_id: int, name: str) -> None:
        count = service_service.appointment_count(service_id)
        warning = (
            f"'{name}' hizmeti {count} randevuda kullanılmış. "
            f"Silindiğinde bu randevularda hizmet alanı boşalır, "
            f"randevular silinmez."
            if count else
            f"'{name}' silinecek. Emin misiniz?"
        )

        dlg_ref: dict = {"dlg": None}

        def close(e=None):
            if dlg_ref["dlg"]:
                self.page.dialog.open = False
                self.page.update()

        def do_delete(e):
            service_service.delete_service(service_id)
            close()
            self.refresh()
            self.page.snack_bar = ft.SnackBar(
                ft.Text(f"'{name}' silindi."), bgcolor=theme.TEXT,
            )
            self.page.snack_bar.open = True
            self.page.update()

        dlg = ft.AlertDialog(
            modal=True, bgcolor=theme.SURFACE,
            title=ft.Text(
                "Hizmeti sil?", color=theme.TEXT,
                weight=ft.FontWeight.W_400,
                font_family=theme.FONT_FAMILY_DISPLAY, size=20,
            ),
            content=ft.Text(warning, color=theme.TEXT_MUTED, size=13),
            actions=[
                theme.ghost_button("Vazgeç", on_click=close),
                ft.ElevatedButton(
                    "Sil", on_click=do_delete,
                    style=ft.ButtonStyle(
                        bgcolor=theme.ERROR, color="#FFFFFF",
                        shape=ft.RoundedRectangleBorder(radius=2),
                        padding=ft.padding.symmetric(
                            horizontal=24, vertical=18,
                        ),
                    ),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        dlg_ref["dlg"] = dlg
        self.page.dialog = dlg
        self.page.dialog.open = True
        self.page.update()


def build(page: ft.Page) -> ft.Control:
    return ServicesView(page).build()
