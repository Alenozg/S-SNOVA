"""
Personel yönetimi — sade ve çalışır versiyon.

Butona tıklayınca AlertDialog'u güvenli şekilde açar.
Renk seçimi için 12 swatch'lı palette — her swatch'e tıklayınca state güncellenir,
görsel işaret (kenar çizgisi) palette tümüyle yeniden build edilir.
"""
import flet as ft

from models import Staff, STAFF_COLOR_PALETTE
from services import staff_service
from ui import theme


class StaffView:
    def __init__(self, page: ft.Page):
        self.page = page
        self.list_container = ft.Column(spacing=0)

    # ==================================================================
    # Ana görünüm
    # ==================================================================
    def build(self) -> ft.Control:
        # "Yeni Personel" butonu - on_click doğrudan metoda bağlı
        new_button = theme.primary_button(
            "Yeni Personel",
            icon=ft.icons.ADD,
            on_click=self._on_new_clicked,
        )

        header = ft.Row(
            [
                ft.Column(
                    [theme.caption("EKİP"), theme.h1("Personel")],
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
                        "Her personelin kendine özel bir rengi olur; "
                        "randevu takviminde bu renkle görünür.",
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
    # Liste yenileme
    # ==================================================================
    def refresh(self) -> None:
        staff_list = staff_service.list_staff()
        controls: list[ft.Control] = [self._header_row()]

        if not staff_list:
            controls.append(ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(ft.icons.PERSON_OUTLINED, size=36,
                                color=theme.TEXT_FAINT),
                        ft.Container(height=8),
                        theme.body("Henüz personel eklenmedi.", muted=True),
                        ft.Container(height=4),
                        theme.caption(
                            "Sağ üstteki 'Yeni Personel' düğmesine tıklayın."
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0,
                ),
                padding=40, alignment=ft.alignment.center,
            ))
        else:
            for s in staff_list:
                controls.append(self._staff_row_mobile(s) if is_mobile else self._staff_row(s))

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
                    ft.Container(width=48),   # renk dairesi için yer
                    col("Ad Soyad", expand=True),
                    col("Rol", w=180),
                    col("İletişim", w=200),
                    col("Durum", w=80),
                    ft.Container(width=100),
                ],
                spacing=16,
            ),
            padding=ft.padding.symmetric(horizontal=24, vertical=14),
            border=ft.border.only(bottom=ft.BorderSide(1, theme.DIVIDER)),
            bgcolor=theme.SURFACE_ALT,
        )

    def _staff_row_mobile(self, s: Staff) -> ft.Container:
        """Mobil için kompakt personel kartı."""
        color_dot = ft.Container(
            content=ft.Text(s.initials, size=11, weight=ft.FontWeight.W_500,
                            color="#FFFFFF", text_align=ft.TextAlign.CENTER),
            width=32, height=32, bgcolor=s.color, border_radius=16,
            alignment=ft.alignment.center,
        )
        return ft.Container(
            content=ft.Row([
                color_dot,
                ft.Container(width=8),
                ft.Column([
                    ft.Text(s.full_name, size=13, weight=ft.FontWeight.W_500,
                            color=theme.TEXT, no_wrap=True),
                    ft.Text(s.role or "—", size=11, color=theme.TEXT_MUTED),
                ], spacing=2, expand=True),
                ft.Container(
                    content=ft.Text("Aktif" if s.active else "Pasif", size=10,
                                    color=theme.SURFACE, weight=ft.FontWeight.W_500),
                    padding=ft.padding.symmetric(horizontal=6, vertical=3),
                    bgcolor=theme.SUCCESS if s.active else theme.TEXT_MUTED,
                    border_radius=2,
                ),
                ft.IconButton(ft.icons.EDIT_OUTLINED, icon_size=16,
                              icon_color=theme.TEXT_MUTED,
                              on_click=lambda e, sid=s.id: self._open_dialog(edit_id=sid)),
            ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
            border=ft.border.only(bottom=ft.BorderSide(1, theme.DIVIDER)),
            ink=True,
            on_click=lambda e, sid=s.id: self._open_dialog(edit_id=sid),
        )

    def _staff_row(self, s: Staff) -> ft.Container:
        color_dot = ft.Container(
            content=ft.Text(
                s.initials, size=12, weight=ft.FontWeight.W_500,
                color="#FFFFFF", text_align=ft.TextAlign.CENTER,
            ),
            width=36, height=36,
            bgcolor=s.color, border_radius=18,
            alignment=ft.alignment.center,
        )

        status_chip = ft.Container(
            content=ft.Text(
                "Aktif" if s.active else "Pasif", size=11,
                color=theme.SURFACE, weight=ft.FontWeight.W_500,
            ),
            padding=ft.padding.symmetric(horizontal=8, vertical=4),
            bgcolor=theme.SUCCESS if s.active else theme.TEXT_MUTED,
            border_radius=2,
        )

        contact = " · ".join(filter(None, [s.phone, s.email])) or "—"

        return ft.Container(
            content=ft.Row(
                [
                    ft.Container(content=color_dot, width=48),
                    ft.Container(
                        content=ft.Text(s.full_name, size=14,
                                        weight=ft.FontWeight.W_500,
                                        color=theme.TEXT),
                        expand=True,
                    ),
                    ft.Container(
                        content=theme.body(s.role or "—", muted=True),
                        width=180,
                    ),
                    ft.Container(content=theme.caption(contact), width=200),
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
                                    on_click=lambda e, sid=s.id, nm=s.full_name:
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
    # EKLEME / DÜZENLEME DİYALOĞU
    # Tek bir giriş noktası: _open_dialog. Hem "Yeni Personel" hem de
    # satırdaki edit butonu buraya düşer.
    # ==================================================================
    def _on_new_clicked(self, e) -> None:
        """Yeni Personel butonunun tek açık handler'ı — debug kolaylığı için."""
        print("[StaffView] Yeni Personel tıklandı, dialog açılıyor...")
        self._open_dialog(edit_id=None)

    def _open_dialog(self, edit_id: int | None = None) -> None:
        existing = staff_service.get_staff(edit_id) if edit_id else None

        # -------- form alanları --------
        first = theme.text_field(
            "Ad", existing.first_name if existing else "",
        )
        last = theme.text_field(
            "Soyad", existing.last_name if existing else "",
        )
        role = theme.text_field(
            "Rol", existing.role if existing else "",
            hint="Örn. Estetisyen, Lazer Uzmanı, Güzellik Uzmanı",
        )
        phone = theme.text_field(
            "İletişim Numarası", existing.phone if existing else "",
            hint="Opsiyonel",
        )
        email = theme.text_field(
            "E-posta", existing.email if existing else "",
            hint="Opsiyonel",
        )
        notes = theme.text_field(
            "Notlar", existing.notes if existing else "",
            multiline=True,
        )
        active_cb = ft.Checkbox(
            label="Aktif",
            value=bool(existing.active) if existing else True,
            check_color=theme.SURFACE, fill_color=theme.ACCENT,
            label_style=ft.TextStyle(size=12, color=theme.TEXT_MUTED),
        )
        error_text = ft.Text("", color=theme.ERROR, size=12)

        # Renk state'i — sabit list yerine mutable dict kullan
        initial_color = (
            existing.color if existing else staff_service.suggest_color()
        )
        color_state = {"value": initial_color}

        # Palette'i tutan container — yeniden build için referans
        palette_container = ft.Container(
            content=self._build_color_palette(color_state, on_pick_rebuild=None),
        )

        def on_color_pick(color: str):
            color_state["value"] = color
            # Palette'i güncel seçim işaretiyle yeniden build et
            palette_container.content = self._build_color_palette(
                color_state, on_pick_rebuild=on_color_pick,
            )
            palette_container.update()

        # İlk build'de callback'i bağla
        palette_container.content = self._build_color_palette(
            color_state, on_pick_rebuild=on_color_pick,
        )

        # -------- dialog --------
        # dlg'yi önce None olarak tanımla, kapatma için kullanılacak
        dlg_ref: dict = {"dlg": None}

        def close_dialog(e=None):
            if dlg_ref["dlg"] is not None:
                self.page.dialog.open = False
                self.page.update()

        def save(e):
            try:
                fn = (first.value or "").strip()
                ln = (last.value or "").strip()
                if not fn or not ln:
                    raise ValueError("Ad ve soyad zorunlu.")

                payload = Staff(
                    id=existing.id if existing else None,
                    first_name=fn,
                    last_name=ln,
                    role=(role.value or "").strip(),
                    phone=(phone.value or "").strip(),
                    email=(email.value or "").strip(),
                    color=color_state["value"],
                    active=bool(active_cb.value),
                    notes=(notes.value or "").strip(),
                )
                if existing:
                    staff_service.update_staff(payload)
                    msg = "Personel güncellendi."
                else:
                    staff_service.create_staff(payload)
                    msg = "Personel eklendi."

                close_dialog()
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
            modal=True,
            bgcolor=theme.SURFACE,
            title=ft.Text(
                "Personel Bilgileri" if existing else "Yeni Personel",
                color=theme.TEXT, weight=ft.FontWeight.W_400,
                font_family=theme.FONT_FAMILY_DISPLAY, size=22,
            ),
            content=ft.Column(
                    [
                        ft.Row([first, last], spacing=12),
                        role,
                        ft.Row([phone, email], spacing=12),
                        ft.Container(height=4),
                        theme.caption("TAKVİM RENGİ"),
                        palette_container,
                        ft.Container(height=4),
                        active_cb,
                        notes,
                        error_text,
                    ],
                    tight=True, spacing=12,
                ),
            actions=[
                theme.ghost_button("Vazgeç", on_click=close_dialog),
                theme.primary_button("Kaydet", on_click=save),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        dlg_ref["dlg"] = dlg

        # Flet sürümlerine göre farklı yollar dene — birinin çalışması garanti
        try:
            self.page.dialog = dlg
            self.page.dialog.open = True
            self.page.update()
        except Exception as e1:
            try:
                # Geriye uyumlu fallback
                self.page.dialog = dlg
                dlg.open = True
                self.page.update()
            except Exception as e2:
                print(f"[StaffView] Dialog açma hatası: {e1} / {e2}")
                self.page.snack_bar = ft.SnackBar(
                    ft.Text(f"Dialog açılamadı: {e1}"),
                    bgcolor=theme.ERROR,
                )
                self.page.snack_bar.open = True
                self.page.update()

    # ==================================================================
    # Renk paleti
    # ==================================================================
    def _build_color_palette(
        self,
        color_state: dict,
        on_pick_rebuild,
    ) -> ft.Control:
        """12 renkli palette — seçili olan kenar çizgili."""
        current = color_state["value"]
        swatches: list[ft.Control] = []

        for color in STAFF_COLOR_PALETTE:
            is_selected = color.upper() == current.upper()

            inner = ft.Container(
                width=28, height=28,
                bgcolor=color,
                border_radius=14,
                border=ft.border.all(
                    2, theme.TEXT if is_selected else "transparent",
                ),
            )
            wrapper = ft.Container(
                content=inner,
                padding=3,
                border_radius=18,
                ink=True,
                tooltip=color,
                # Callback'i on_click'e bağla - her swatch ayrı renk değeri tutar
                on_click=(
                    (lambda e, c=color: on_pick_rebuild(c))
                    if on_pick_rebuild else None
                ),
            )
            swatches.append(wrapper)

        return ft.Row(swatches, spacing=8, wrap=True)

    # ==================================================================
    # Silme
    # ==================================================================
    def _confirm_delete(self, staff_id: int, name: str) -> None:
        count = staff_service.appointment_count(staff_id)
        warning = (
            f"{name} adına kayıtlı {count} randevu var. "
            f"Personel silinirse bu randevular 'personel atanmamış' "
            f"duruma geçer, silinmez."
            if count else
            f"{name} silinecek. Emin misiniz?"
        )

        dlg_ref: dict = {"dlg": None}

        def close(e=None):
            if dlg_ref["dlg"]:
                self.page.dialog.open = False
                self.page.update()

        def do_delete(e):
            staff_service.delete_staff(staff_id)
            close()
            self.refresh()
            self.page.snack_bar = ft.SnackBar(
                ft.Text(f"{name} silindi."), bgcolor=theme.TEXT,
            )
            self.page.snack_bar.open = True
            self.page.update()

        dlg = ft.AlertDialog(
            modal=True, bgcolor=theme.SURFACE,
            title=ft.Text(
                "Personeli sil?", color=theme.TEXT,
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
    return StaffView(page).build()
