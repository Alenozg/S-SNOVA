"""
Müşteri yönetimi:
- Arama + tablo
- Toplu seçim + toplu SMS
- Yeni / düzenle diyaloğu
- Müşteri profili (büyük modal, istatistikler + geçmiş randevular)
- Silme onayı
- CSV toplu içe/dışa aktarma + şablon
"""
from datetime import date, datetime
from pathlib import Path

def _dlg_close(page):
    """Flet 0.24.1 uyumlu dialog kapatma yardımcısı."""
    try:
        page.dialog.open = False
        page.update()
    except Exception:
        pass


import flet as ft

from models import Customer
from services import customer_service, import_export_service
from ui import theme
from ui.views.customer_profile_view import open_customer_profile


class CustomersView:
    def __init__(self, page: ft.Page):
        self.page = page
        self.search_field = ft.TextField(
            hint_text="Ad, soyad, telefon veya e-posta ara...",
            border_color=theme.DIVIDER,
            focused_border_color=theme.ACCENT,
            bgcolor=theme.SURFACE,
            content_padding=ft.padding.symmetric(horizontal=14, vertical=14),
            border_radius=2,
            text_style=ft.TextStyle(size=13, color=theme.TEXT),
            prefix_icon=ft.icons.SEARCH,
            on_change=lambda e: self.refresh(),
            expand=True,
        )
        self.only_iys_cb = ft.Checkbox(
            label="Yalnızca İYS onaylı",
            value=False,
            check_color=theme.SURFACE,
            fill_color=theme.ACCENT,
            label_style=ft.TextStyle(size=12, color=theme.TEXT_MUTED),
            on_change=lambda e: self.refresh(),
        )
        self.only_invalid_cb = ft.Checkbox(
            label="Yalnızca eksik bilgililer",
            value=False,
            check_color=theme.SURFACE,
            fill_color=theme.INVALID_BAR,
            label_style=ft.TextStyle(size=12, color=theme.TEXT_MUTED),
            on_change=lambda e: self.refresh(),
        )
        self.list_container = ft.Column(spacing=0)

        # FilePicker'lar - Flet overlay'e eklenecek
        self.import_picker = ft.FilePicker(on_result=self._on_import_file_picked)
        self.export_picker = ft.FilePicker(on_result=self._on_export_path_picked)
        self.template_picker = ft.FilePicker(on_result=self._on_template_path_picked)
        self._pickers_mounted = False
        self._import_duplicate_mode = "skip"

        # ---- Toplu seçim state'i ----
        self._selected_ids: set[int] = set()
        # Görünümdeki müşterilerin id listesi (refresh başına güncellenir)
        self._visible_ids: list[int] = []
        # Header ve action bar widget'ları refresh'de güncellenebilsin
        self._select_all_checkbox: ft.Checkbox | None = None
        self._bulk_action_bar: ft.Container | None = None

    # ---------------------------------------------------------- build
    def build(self) -> ft.Control:
        # FilePicker'ları overlay'e ekle (sadece bir kez; view tekrar build edilirse tekrar eklenmesin)
        if not self._pickers_mounted:
            self.page.overlay.append(self.import_picker)
            self.page.overlay.append(self.export_picker)
            self.page.overlay.append(self.template_picker)
            self._pickers_mounted = True

        header = ft.Row(
            [
                ft.Column(
                    [theme.caption("CRM"), theme.h1("Müşteriler")],
                    spacing=4, expand=True,
                ),
                ft.Row(
                    [
                        theme.ghost_button(
                            "Şablon", icon=ft.icons.DESCRIPTION_OUTLINED,
                            on_click=lambda e: self._save_template(),
                        ),
                        theme.ghost_button(
                            "Dışa Aktar", icon=ft.icons.FILE_DOWNLOAD_OUTLINED,
                            on_click=lambda e: self._open_export(),
                        ),
                        theme.ghost_button(
                            "İçe Aktar", icon=ft.icons.FILE_UPLOAD_OUTLINED,
                            on_click=lambda e: self._open_import(),
                        ),
                        theme.primary_button(
                            "Yeni Müşteri", icon=ft.icons.ADD,
                            on_click=lambda e: self.open_form(),
                        ),
                    ],
                    spacing=8,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.END,
        )

        # Eksik/hatalı kayıt sayısını banner olarak göster (varsa)
        invalid_count = customer_service.count_invalid()
        invalid_banner = ft.Container(
            visible=invalid_count > 0,
            content=ft.Row(
                [
                    ft.Icon(ft.icons.WARNING_AMBER_OUTLINED,
                            size=16, color=theme.INVALID_TXT),
                    ft.Text(
                        f"{invalid_count} kayıtta eksik veya hatalı bilgi var. "
                        f"Liste üstünde renkli satırlardaki kalem ikonuna "
                        f"tıklayarak düzeltebilirsiniz.",
                        size=12, color=theme.INVALID_TXT, expand=True,
                        no_wrap=False,
                    ),
                ],
                spacing=10,
            ),
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
            bgcolor=theme.INVALID_BG,
            border=ft.border.only(left=ft.BorderSide(3, theme.INVALID_BAR)),
            border_radius=2,
            margin=ft.margin.only(top=16),
        )

        filter_row = ft.Container(
            content=ft.Row(
                [self.search_field, self.only_iys_cb, self.only_invalid_cb],
                spacing=16,
            ),
            padding=ft.padding.only(top=20, bottom=20),
        )

        # Toplu seçim aksiyon çubuğu (seçim yapıldıkça görünür)
        self._bulk_action_bar = self._build_bulk_action_bar()

        self.refresh()
        return ft.Column(
            [header, invalid_banner, filter_row,
             self._bulk_action_bar,
             theme.card(self.list_container, padding=0)],
            scroll=ft.ScrollMode.AUTO, expand=True,
        )

    def _build_bulk_action_bar(self) -> ft.Container:
        """Seçim varsa görünen, yoksa gizli aksiyon çubuğu."""
        count = len(self._selected_ids)
        return ft.Container(
            visible=count > 0,
            content=ft.Row(
                [
                    ft.Icon(ft.icons.CHECK_CIRCLE, size=16, color=theme.ACCENT),
                    ft.Text(
                        f"{count} müşteri seçildi", size=13,
                        weight=ft.FontWeight.W_500, color=theme.TEXT,
                    ),
                    ft.Container(expand=True),
                    theme.ghost_button(
                        "Seçimi Temizle",
                        on_click=lambda e: self._clear_selection(),
                    ),
                    theme.primary_button(
                        "Toplu SMS", icon=ft.icons.SEND_OUTLINED,
                        on_click=lambda e: self._bulk_sms(),
                    ),
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
            bgcolor=theme.SURFACE_ALT,
            border=ft.border.only(left=ft.BorderSide(3, theme.ACCENT)),
            border_radius=2,
            margin=ft.margin.only(bottom=16),
        )

    # ---------------------------------------------------------- bulk actions
    def _clear_selection(self) -> None:
        self._selected_ids.clear()
        self.refresh()

    def _bulk_sms(self) -> None:
        """Seçilen müşterilere toplu SMS - kampanya formunu önceden doldurur."""
        selected = [customer_service.get_customer(cid)
                    for cid in self._selected_ids]
        selected = [c for c in selected if c]

        # İYS onaysızları uyar
        iys_ok = [c for c in selected if c.iys_consent]
        iys_missing = len(selected) - len(iys_ok)

        info_text = f"{len(iys_ok)} müşteriye SMS gönderilecek."
        if iys_missing > 0:
            info_text += f" {iys_missing} müşteride İYS onayı olmadığı için atlanacak."

        message_field = theme.text_field(
            "Mesaj", multiline=True,
            hint="Merhaba {name}, ...  ({name} = müşteri adı)",
        )
        error_text = ft.Text("", color=theme.ERROR, size=12)

        def send(e):
            msg = (message_field.value or "").strip()
            if not msg:
                error_text.value = "Mesaj boş olamaz."
                error_text.update()
                return
            if not iys_ok:
                error_text.value = "İYS onaylı müşteri yok."
                error_text.update()
                return

            try:
                from services import sms_service
                recipients = [
                    {"customer_id": c.id, "phone": c.phone, "name": c.first_name}
                    for c in iys_ok
                ]
                result = sms_service.send_bulk(
                    recipients=recipients,
                    message_template=msg,
                    sms_type="campaign",
                )
                self.page.dialog.open = False
                self.page.update()
                self._clear_selection()
                self.page.snack_bar = ft.SnackBar(
                    ft.Text(
                        f"Toplu SMS tamamlandı: {result['sent']} başarılı, "
                        f"{result['failed']} başarısız."
                    ),
                    bgcolor=theme.SUCCESS,
                )
                self.page.snack_bar.open = True
                self.page.update()
            except Exception as ex:
                error_text.value = f"Hata: {ex}"
                error_text.update()

        dlg = ft.AlertDialog(
            modal=True, bgcolor=theme.SURFACE,
            title=ft.Text(
                "Seçilen Müşterilere SMS",
                color=theme.TEXT, weight=ft.FontWeight.W_400,
                font_family=theme.FONT_FAMILY_DISPLAY, size=22,
            ),
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Container(
                            content=ft.Row(
                                [
                                    ft.Icon(ft.icons.INFO_OUTLINE, size=14,
                                            color=theme.TEXT_MUTED),
                                    theme.body(info_text, muted=True),
                                ],
                                spacing=8,
                            ),
                            padding=12, bgcolor=theme.SURFACE_ALT,
                            border_radius=2,
                        ),
                        message_field,
                        error_text,
                    ],
                    tight=True, spacing=12,
                ),
                width=520,
            ),
            actions=[
                theme.ghost_button("Vazgeç",
                                   on_click=lambda e: _dlg_close(self.page)),
                theme.primary_button("Gönder",
                                     icon=ft.icons.SEND, on_click=send),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.dialog = dlg
        self.page.dialog.open = True
        self.page.update()

    def _toggle_select(self, customer_id: int, checked: bool) -> None:
        if checked:
            self._selected_ids.add(customer_id)
        else:
            self._selected_ids.discard(customer_id)
        self.refresh()

    def _toggle_select_all(self, checked: bool) -> None:
        if checked:
            self._selected_ids.update(self._visible_ids)
        else:
            # Sadece görünen müşterileri seçimden çıkar (filtre dışındakileri koru)
            self._selected_ids.difference_update(self._visible_ids)
        self.refresh()

    # ---------------------------------------------------------- refresh
    def refresh(self) -> None:
        customers = customer_service.list_customers(
            search=self.search_field.value or "",
            only_iys=bool(self.only_iys_cb.value),
            only_invalid=bool(self.only_invalid_cb.value),
        )
        # Görünür id'leri takip et (select-all ve toplu aksiyon için)
        self._visible_ids = [c.id for c in customers if c.id is not None]

        self.list_container.controls = [self._header_row()] + [
            self._customer_row(c) for c in customers
        ] if customers else [
            self._header_row(),
            ft.Container(
                content=theme.body("Kayıtlı müşteri bulunamadı.", muted=True),
                padding=40, alignment=ft.alignment.center,
            ),
        ]
        if self.list_container.page:
            self.list_container.update()

        # Bulk action bar görünürlüğünü ve sayıyı güncelle
        if self._bulk_action_bar is not None and self._bulk_action_bar.page:
            count = len(self._selected_ids)
            self._bulk_action_bar.visible = count > 0
            # Row içindeki ikinci child "N müşteri seçildi" text'i
            try:
                text_control = self._bulk_action_bar.content.controls[1]
                text_control.value = f"{count} müşteri seçildi"
            except Exception:
                pass
            self._bulk_action_bar.update()

    def _header_row(self) -> ft.Container:
        def col(label, w, expand=False):
            return ft.Container(
                content=ft.Text(label.upper(), size=10, color=theme.TEXT_MUTED,
                                weight=ft.FontWeight.W_500),
                width=None if expand else w, expand=expand,
            )

        # "Tümünü Seç" checkbox'ı - görünen müşterilerin hepsi seçiliyse işaretli
        all_visible_selected = (
            bool(self._visible_ids)
            and all(cid in self._selected_ids for cid in self._visible_ids)
        )
        self._select_all_checkbox = ft.Checkbox(
            value=all_visible_selected,
            check_color=theme.SURFACE,
            fill_color=theme.ACCENT,
            on_change=lambda e: self._toggle_select_all(bool(e.control.value)),
            tooltip="Tümünü seç / kaldır",
        )

        return ft.Container(
            content=ft.Row(
                [
                    # Checkbox sütunu
                    ft.Container(
                        content=self._select_all_checkbox,
                        width=44,
                        alignment=ft.alignment.center_left,
                    ),
                    col("Ad Soyad", 0, expand=True),
                    col("Telefon", 180),
                    col("Doğum Tarihi", 130),
                    col("İYS", 60),
                    ft.Container(width=100),
                ],
                spacing=16,
            ),
            padding=ft.padding.symmetric(horizontal=24, vertical=14),
            border=ft.border.only(bottom=ft.BorderSide(1, theme.DIVIDER)),
            bgcolor=theme.SURFACE_ALT,
        )

    def _customer_row(self, c: Customer) -> ft.Container:
        is_invalid = not c.is_valid

        iys_icon = ft.Icon(
            ft.icons.CHECK_CIRCLE_OUTLINE if c.iys_consent else ft.icons.REMOVE_CIRCLE_OUTLINE,
            size=16,
            color=theme.SUCCESS if c.iys_consent else theme.TEXT_FAINT,
        )
        bd = c.birth_date.strftime("%d.%m.%Y") if c.birth_date else "—"

        # Ad + uyarı ikonu (hatalıysa) + hata notu alt satırı
        name_row_children: list[ft.Control] = [
            ft.Text(c.full_name, size=14, weight=ft.FontWeight.W_500,
                    color=theme.TEXT),
        ]
        if is_invalid:
            name_row_children.append(
                ft.Icon(
                    ft.icons.WARNING_AMBER_OUTLINED,
                    size=14, color=theme.INVALID_TXT,
                    tooltip=c.validation_errors or "Eksik bilgi var",
                )
            )

        name_block_children: list[ft.Control] = [
            ft.Row(name_row_children, spacing=6,
                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ]
        # Alt satır: yaş veya hata notu
        if is_invalid and c.validation_errors:
            name_block_children.append(
                ft.Text(
                    c.validation_errors, size=11,
                    color=theme.INVALID_TXT,
                    italic=True,
                    max_lines=1, overflow=ft.TextOverflow.ELLIPSIS,
                )
            )
        elif c.age:
            name_block_children.append(theme.caption(f"{c.age} yaş"))

        # Telefonu hatalı satırda biraz daha vurgulu göster
        phone_display = c.display_phone
        phone_widget = ft.Text(
            phone_display,
            size=13,
            color=theme.INVALID_TXT if (is_invalid and phone_display == "—") else theme.TEXT_MUTED,
            weight=ft.FontWeight.W_500 if is_invalid else ft.FontWeight.W_400,
        )

        # Sol renkli aksan barı (hatalı kayıtlar için)
        left_bar = ft.Container(
            width=3,
            bgcolor=theme.INVALID_BAR if is_invalid else "transparent",
        )

        # Zemin rengi: seçili ise accent tint, hatalı ise gül kurusu, normal ise yok
        is_selected = c.id in self._selected_ids
        if is_selected:
            row_bg = "#F0EBE3"  # accent'in çok hafif tintli hali
        elif is_invalid:
            row_bg = theme.INVALID_BG
        else:
            row_bg = None

        # Satır checkbox'ı - seçili ise işaretli
        row_checkbox = ft.Checkbox(
            value=is_selected,
            check_color=theme.SURFACE,
            fill_color=theme.ACCENT,
            on_change=lambda e, cid=c.id: self._toggle_select(
                cid, bool(e.control.value)),
        )

        return ft.Container(
            content=ft.Row(
                [
                    # Checkbox sütunu (header ile aynı genişlik)
                    ft.Container(
                        content=row_checkbox,
                        width=44,
                        alignment=ft.alignment.center_left,
                    ),
                    left_bar,
                    ft.Container(
                        content=ft.Column(name_block_children, spacing=2),
                        expand=True,
                        padding=ft.padding.only(left=8),
                        # Ada tıklayınca profil ekranı açılsın
                        ink=True,
                        on_click=lambda e, cid=c.id: self.open_profile(cid),
                    ),
                    ft.Container(
                        content=phone_widget, width=180,
                        ink=True,
                        on_click=lambda e, cid=c.id: self.open_profile(cid),
                    ),
                    ft.Container(
                        content=ft.Text(bd, size=13, color=theme.TEXT_MUTED),
                        width=130,
                    ),
                    ft.Container(content=iys_icon, width=60),
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.IconButton(
                                    ft.icons.EDIT_OUTLINED, icon_size=16,
                                    icon_color=theme.INVALID_TXT if is_invalid else theme.TEXT_MUTED,
                                    on_click=lambda e, cid=c.id: self.open_form(cid),
                                    tooltip="Düzenle" + (" (eksik bilgi var)" if is_invalid else ""),
                                ),
                                ft.IconButton(
                                    ft.icons.DELETE_OUTLINE, icon_size=16,
                                    icon_color=theme.TEXT_MUTED,
                                    on_click=lambda e, cid=c.id, nm=c.full_name: self.confirm_delete(cid, nm),
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
            padding=ft.padding.only(top=12, bottom=12, right=24),
            bgcolor=row_bg,
            border=ft.border.only(bottom=ft.BorderSide(1, theme.DIVIDER)),
        )

    # ---------------------------------------------------------- profile
    def open_profile(self, customer_id: int) -> None:
        """Büyük müşteri profil modalı (istatistikler + geçmiş randevular)."""
        open_customer_profile(
            self.page,
            customer_id=customer_id,
            on_edit=lambda cid: self.open_form(cid),
        )

    # ---------------------------------------------------------- form
    def open_form(self, customer_id: int | None = None) -> None:
        existing = customer_service.get_customer(customer_id) if customer_id else None

        # Placeholder'ları formda boş göster (kullanıcı üstüne yazsın)
        initial_first = existing.first_name if existing else ""
        initial_last = existing.last_name if existing else ""
        if initial_first in ("(Ad eksik)",):
            initial_first = ""
        if initial_last in ("(Soyad eksik)",):
            initial_last = ""

        first = theme.text_field("Ad", initial_first)
        last = theme.text_field("Soyad", initial_last)
        phone = theme.text_field(
            "Telefon",
            existing.phone if existing else "",
            hint="5XX XXX XX XX",
        )
        email = theme.text_field(
            "E-posta",
            existing.email if existing else "",
            hint="ornek@mail.com (opsiyonel)",
        )
        gender_dd = ft.Dropdown(
            label="Cinsiyet",
            value=existing.gender if existing and existing.gender else "",
            options=[
                ft.dropdown.Option("", "— Belirtilmemiş —"),
                ft.dropdown.Option("kadin", "Kadın"),
                ft.dropdown.Option("erkek", "Erkek"),
            ],
            border_color=theme.DIVIDER, focused_border_color=theme.ACCENT,
            bgcolor=theme.SURFACE, border_radius=2,
            text_style=ft.TextStyle(size=13, color=theme.TEXT),
            label_style=ft.TextStyle(size=12, color=theme.TEXT_MUTED),
        )
        birth = theme.text_field(
            "Doğum Tarihi",
            existing.birth_date.isoformat() if existing and existing.birth_date else "",
            hint="YYYY-AA-GG (örn. 1990-05-17)",
        )
        notes = theme.text_field("Notlar", existing.notes if existing else "", multiline=True)
        iys = ft.Checkbox(
            label="İYS onayı verildi (ticari SMS gönderimi için gerekli)",
            value=bool(existing.iys_consent) if existing else False,
            check_color=theme.SURFACE, fill_color=theme.ACCENT,
            label_style=ft.TextStyle(size=12, color=theme.TEXT_MUTED),
        )
        error_text = ft.Text("", color=theme.ERROR, size=12)

        # Mevcut müşteri hatalıysa, en üste pastel kırmızı uyarı banner'ı
        invalid_banner = None
        if existing and not existing.is_valid:
            err_msg = existing.validation_errors or "Bu kayıtta eksik bilgi var."
            invalid_banner = ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(ft.icons.WARNING_AMBER_OUTLINED,
                                size=18, color=theme.INVALID_TXT),
                        ft.Column(
                            [
                                ft.Text(
                                    "Eksik veya hatalı bilgi tespit edildi",
                                    size=13, weight=ft.FontWeight.W_500,
                                    color=theme.INVALID_TXT,
                                ),
                                ft.Text(
                                    err_msg, size=12, color=theme.INVALID_TXT,
                                    no_wrap=False,
                                ),
                                ft.Text(
                                    "Alanları doldurup kaydettiğinizde uyarı kalkar.",
                                    size=11, color=theme.INVALID_TXT,
                                    italic=True,
                                ),
                            ],
                            spacing=2, tight=True, expand=True,
                        ),
                    ],
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
                padding=14,
                bgcolor=theme.INVALID_BG,
                border=ft.border.only(left=ft.BorderSide(3, theme.INVALID_BAR)),
                border_radius=2,
            )

        def save(e):
            try:
                bd = None
                if birth.value and birth.value.strip():
                    try:
                        bd = date.fromisoformat(birth.value.strip())
                    except ValueError:
                        # DD.MM.YYYY gibi formatlara da toleranslı olalım
                        for fmt in ("%d.%m.%Y", "%d/%m/%Y"):
                            try:
                                bd = datetime.strptime(birth.value.strip(), fmt).date()
                                break
                            except ValueError:
                                continue
                        if bd is None:
                            raise ValueError(
                                "Doğum tarihi formatı anlaşılamadı "
                                "(örn. 1990-05-17 veya 17.05.1990)."
                            )

                payload = Customer(
                    id=existing.id if existing else None,
                    first_name=(first.value or "").strip(),
                    last_name=(last.value or "").strip(),
                    phone=(phone.value or "").strip(),
                    email=(email.value or "").strip(),
                    gender=(gender_dd.value or "").strip(),
                    birth_date=bd,
                    iys_consent=bool(iys.value),
                    notes=notes.value or "",
                )
                if not payload.first_name or not payload.last_name:
                    raise ValueError("Ad ve soyad zorunlu.")

                if existing:
                    customer_service.update_customer(payload)
                    msg = "Müşteri güncellendi."
                else:
                    customer_service.create_customer(payload)
                    msg = "Müşteri eklendi."

                self.page.dialog.open = False
                self.page.update()
                self.refresh()
                self.page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor=theme.SUCCESS)
                self.page.snack_bar.open = True
                self.page.update()
            except ValueError as ex:
                error_text.value = str(ex)
                error_text.update()

        form_children: list[ft.Control] = []
        if invalid_banner is not None:
            form_children.append(invalid_banner)
        form_children.extend([
            ft.Row([first, last], spacing=12),
            ft.Row([phone, email], spacing=12),
            ft.Row([gender_dd, birth], spacing=12),
            iys, notes, error_text,
        ])

        dlg = ft.AlertDialog(
            modal=True, bgcolor=theme.SURFACE,
            title=ft.Text("Müşteri Bilgileri" if existing else "Yeni Müşteri",
                          color=theme.TEXT, weight=ft.FontWeight.W_400,
                          font_family=theme.FONT_FAMILY_DISPLAY, size=22),
            content=ft.Container(
                content=ft.Column(form_children, tight=True, spacing=12),
                width=520,
            ),
            actions=[
                theme.ghost_button("Vazgeç", on_click=lambda e: _dlg_close(self.page)),
                theme.primary_button("Kaydet", on_click=save),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.dialog = dlg
        self.page.dialog.open = True
        self.page.update()

    # ---------------------------------------------------------- delete
    def confirm_delete(self, customer_id: int, name: str) -> None:
        def do_delete(e):
            customer_service.delete_customer(customer_id)
            self.page.dialog.open = False
            self.page.update()
            self.refresh()
            self.page.snack_bar = ft.SnackBar(ft.Text(f"{name} silindi."),
                                       bgcolor=theme.TEXT)
            self.page.snack_bar.open = True
            self.page.update()

        dlg = ft.AlertDialog(
            modal=True, bgcolor=theme.SURFACE,
            title=ft.Text("Müşteriyi sil?", color=theme.TEXT,
                          weight=ft.FontWeight.W_400,
                          font_family=theme.FONT_FAMILY_DISPLAY, size=20),
            content=ft.Text(
                f"{name} ve geçmiş randevuları kalıcı olarak silinecek. Emin misiniz?",
                color=theme.TEXT_MUTED, size=13,
            ),
            actions=[
                theme.ghost_button("Vazgeç", on_click=lambda e: _dlg_close(self.page)),
                ft.ElevatedButton(
                    "Sil", on_click=do_delete,
                    style=ft.ButtonStyle(
                        bgcolor=theme.ERROR, color="#FFFFFF",
                        shape=ft.RoundedRectangleBorder(radius=2),
                        padding=ft.padding.symmetric(horizontal=24, vertical=18),
                    ),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.dialog = dlg
        self.page.dialog.open = True
        self.page.update()

    # ====================================================================
    #                      TOPLU İÇE / DIŞA AKTARMA
    # ====================================================================

    # --------------------------------------------- içe aktar: seçenek diyaloğu
    def _open_import(self) -> None:
        dup_dd = ft.Dropdown(
            label="Aynı telefonlu müşteri varsa",
            value="skip",
            options=[
                ft.dropdown.Option("skip", "Atla (yinelenenleri geç)"),
                ft.dropdown.Option("update", "Güncelle (üstüne yaz)"),
            ],
            border_color=theme.DIVIDER, focused_border_color=theme.ACCENT,
            bgcolor=theme.SURFACE, border_radius=2,
            text_style=ft.TextStyle(size=13, color=theme.TEXT),
            label_style=ft.TextStyle(size=12, color=theme.TEXT_MUTED),
        )
        info = ft.Container(
            content=ft.Column(
                [
                    theme.caption("CSV FORMATI"),
                    theme.body(
                        "Beklenen sütunlar: ad, soyad, telefon, dogum_tarihi, "
                        "iys_onay, notlar. Sadece ad, soyad, telefon zorunlu.",
                        muted=True,
                    ),
                    theme.body(
                        "Şablonu indirmek için üstteki 'Şablon' düğmesini kullanın.",
                        muted=True,
                    ),
                ],
                spacing=6,
            ),
            padding=16, bgcolor=theme.SURFACE_ALT, border_radius=2,
        )

        def pick_file(e):
            self._import_duplicate_mode = dup_dd.value or "skip"
            self.page.dialog.open = False
            self.page.update()
            self.import_picker.pick_files(
                dialog_title="İçe aktarılacak CSV dosyasını seçin",
                allowed_extensions=["csv", "CSV"],
                allow_multiple=False,
            )

        dlg = ft.AlertDialog(
            modal=True, bgcolor=theme.SURFACE,
            title=ft.Text("Toplu Müşteri İçe Aktarma",
                          color=theme.TEXT, weight=ft.FontWeight.W_400,
                          font_family=theme.FONT_FAMILY_DISPLAY, size=22),
            content=ft.Container(
                content=ft.Column([dup_dd, info], tight=True, spacing=16),
                width=520,
            ),
            actions=[
                theme.ghost_button("Vazgeç", on_click=lambda e: _dlg_close(self.page)),
                theme.primary_button(
                    "Dosya Seç", icon=ft.icons.FOLDER_OPEN_OUTLINED,
                    on_click=pick_file,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.dialog = dlg
        self.page.dialog.open = True
        self.page.update()

    def _on_import_file_picked(self, e: ft.FilePickerResultEvent) -> None:
        if not e.files:
            return
        f = e.files[0]
        try:
            # Flet 0.25.2: web modunda path server-side temp path olarak gelir
            if not f.path:
                self.page.snack_bar = ft.SnackBar(
                    ft.Text("Dosya yolu alınamadı. Lütfen tekrar deneyin."),
                    bgcolor=theme.ERROR,
                )
                self.page.snack_bar.open = True
                self.page.update()
                return
            path = Path(f.path)
            result = import_export_service.import_customers_from_csv(
                path, duplicate_mode=self._import_duplicate_mode,
            )
            self.refresh()
            self._show_import_result(result)
        except PermissionError as ex:
            # macOS TCC izin hatası - uzun mesaj, detaylı dialog gerekir
            self._show_permission_error(str(ex), str(path))
        except FileNotFoundError:
            self.page.snack_bar = ft.SnackBar(
                ft.Text(f"Dosya bulunamadı: {path}"), bgcolor=theme.ERROR,
            )
            self.page.snack_bar.open = True
            self.page.update()
        except ValueError as ex:
            # Format / içerik hataları (örn. eksik sütun, boş dosya)
            self._show_format_error(str(ex))
        except Exception as ex:
            # Yakalanmamış her şey - uygulama çökmesin
            self.page.snack_bar = ft.SnackBar(
                ft.Text(f"Beklenmeyen hata: {ex}"), bgcolor=theme.ERROR,
            )
            self.page.snack_bar.open = True
            self.page.update()

    def _show_permission_error(self, message: str, file_path: str) -> None:
        """macOS izin hatası için anlaşılır rehber dialog."""
        lines: list[ft.Control] = []

        # İlk satır: özet
        lines.append(ft.Row(
            [
                ft.Icon(ft.icons.LOCK_OUTLINE, size=20, color=theme.ERROR),
                ft.Text(
                    "macOS bu dosyaya erişim iznini engelliyor.",
                    size=14, weight=ft.FontWeight.W_500, color=theme.TEXT,
                    expand=True,
                ),
            ],
            spacing=10,
        ))

        lines.append(ft.Container(height=4))
        lines.append(ft.Container(
            content=ft.Column(
                [
                    theme.caption("DOSYA"),
                    ft.Text(file_path, size=12, color=theme.TEXT_MUTED,
                            selectable=True, no_wrap=False),
                ],
                spacing=4,
            ),
            padding=12, bgcolor=theme.SURFACE_ALT, border_radius=2,
        ))

        lines.append(ft.Container(height=8))
        lines.append(theme.caption("ÇÖZÜM YOLLARI"))

        solutions = [
            (
                "1",
                "En hızlı:",
                "CSV dosyanızı Downloads / Masaüstü yerine Ev klasörünüzde "
                "(~/) yeni bir klasöre taşıyın. Örneğin Finder'da ~/ altına "
                "'salon_import' adında bir klasör yapın, CSV'yi oraya koyup "
                "yeniden deneyin.",
            ),
            (
                "2",
                "Kalıcı çözüm:",
                "Sistem Ayarları → Gizlilik ve Güvenlik → Dosyalar ve "
                "Klasörler → Terminal (veya Python) için Downloads ve "
                "Masaüstü erişimini açın, sonra uygulamayı yeniden başlatın.",
            ),
            (
                "3",
                "Geliştiriciler için:",
                "Sistem Ayarları → Gizlilik ve Güvenlik → Tam Disk Erişimi "
                "→ Terminal ekleyin. Bir kez açılan izin tüm oturumlarda "
                "kalıcıdır.",
            ),
        ]

        for num, title, text in solutions:
            lines.append(ft.Container(
                content=ft.Row(
                    [
                        ft.Container(
                            content=ft.Text(
                                num, size=12, color=theme.SURFACE,
                                weight=ft.FontWeight.W_500,
                                text_align=ft.TextAlign.CENTER,
                            ),
                            width=24, height=24, border_radius=12,
                            bgcolor=theme.ACCENT,
                            alignment=ft.alignment.center,
                        ),
                        ft.Column(
                            [
                                ft.Text(title, size=12, color=theme.TEXT,
                                        weight=ft.FontWeight.W_500),
                                ft.Text(text, size=12, color=theme.TEXT_MUTED,
                                        no_wrap=False),
                            ],
                            spacing=3, expand=True, tight=True,
                        ),
                    ],
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
                padding=ft.padding.symmetric(vertical=6),
            ))

        lines.append(ft.Container(height=4))
        lines.append(ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.icons.INFO_OUTLINE, size=14,
                            color=theme.TEXT_MUTED),
                    ft.Text(
                        "Mevcut müşteri kayıtlarınız bu hatadan etkilenmez, "
                        "veritabanı güvendedir.",
                        size=11, color=theme.TEXT_MUTED, expand=True,
                        no_wrap=False,
                    ),
                ],
                spacing=8,
            ),
            padding=10, bgcolor=theme.SURFACE_ALT, border_radius=2,
        ))

        dlg = ft.AlertDialog(
            modal=True, bgcolor=theme.SURFACE,
            title=ft.Text(
                "İçe Aktarma — İzin Sorunu", color=theme.TEXT,
                weight=ft.FontWeight.W_400,
                font_family=theme.FONT_FAMILY_DISPLAY, size=22,
            ),
            content=ft.Container(
                content=ft.Column(lines, tight=True, spacing=8,
                                   scroll=ft.ScrollMode.AUTO),
                width=560,
            ),
            actions=[
                theme.primary_button("Anladım",
                                     on_click=lambda e: _dlg_close(self.page)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.dialog = dlg
        self.page.dialog.open = True
        self.page.update()

    def _show_format_error(self, message: str) -> None:
        """CSV format / içerik hatası için dialog."""
        dlg = ft.AlertDialog(
            modal=True, bgcolor=theme.SURFACE,
            title=ft.Text(
                "CSV Okunamadı", color=theme.TEXT,
                weight=ft.FontWeight.W_400,
                font_family=theme.FONT_FAMILY_DISPLAY, size=22,
            ),
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Icon(ft.icons.DESCRIPTION_OUTLINED,
                                        size=20, color=theme.WARN),
                                ft.Text(
                                    "Dosya okunabildi ama içeriği beklendiği "
                                    "gibi değil:",
                                    size=13, color=theme.TEXT, expand=True,
                                    no_wrap=False,
                                ),
                            ],
                            spacing=10,
                        ),
                        ft.Container(height=4),
                        ft.Container(
                            content=ft.Text(message, size=12, color=theme.TEXT,
                                             selectable=True, no_wrap=False),
                            padding=12, bgcolor=theme.SURFACE_ALT,
                            border_radius=2,
                        ),
                        ft.Container(height=8),
                        theme.caption("ÖNERİ"),
                        theme.body(
                            "Önce üstteki 'Şablon' düğmesinden örnek CSV'yi "
                            "indirin, kendi verinizi o sütunlara göre "
                            "düzenleyip yeniden deneyin.",
                            muted=True,
                        ),
                    ],
                    tight=True, spacing=6,
                ),
                width=520,
            ),
            actions=[
                theme.primary_button("Tamam",
                                     on_click=lambda e: _dlg_close(self.page)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.dialog = dlg
        self.page.dialog.open = True
        self.page.update()

    def _show_import_result(self, result: import_export_service.ImportResult) -> None:
        def stat(label: str, value: int, color: str) -> ft.Container:
            return ft.Container(
                content=ft.Column(
                    [
                        ft.Text(str(value), size=28, weight=ft.FontWeight.W_300,
                                color=color, font_family=theme.FONT_FAMILY_DISPLAY),
                        ft.Text(label.upper(), size=10, color=theme.TEXT_MUTED,
                                weight=ft.FontWeight.W_500),
                    ],
                    spacing=2,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=16, bgcolor=theme.SURFACE_ALT, border_radius=2, expand=True,
            )

        body_items: list[ft.Control] = [
            ft.Row(
                [
                    stat("Eklendi", result.added, theme.SUCCESS),
                    stat("Güncellendi", result.updated, theme.ACCENT),
                    stat("Atlandı", result.skipped, theme.TEXT_MUTED),
                    stat("Hata", len(result.errors), theme.ERROR),
                ],
                spacing=8,
            )
        ]

        if result.errors:
            errs: list[ft.Control] = []
            for line_no, msg in result.errors[:20]:
                errs.append(ft.Row(
                    [
                        ft.Container(
                            content=ft.Text(f"Satır {line_no}", size=11,
                                            color=theme.SURFACE,
                                            weight=ft.FontWeight.W_500),
                            padding=ft.padding.symmetric(horizontal=8, vertical=3),
                            bgcolor=theme.ERROR, border_radius=2,
                        ),
                        ft.Text(msg, size=12, color=theme.TEXT,
                                expand=True, no_wrap=False),
                    ],
                    spacing=10,
                ))
            if len(result.errors) > 20:
                errs.append(theme.caption(f"... ve {len(result.errors) - 20} hata daha"))

            body_items.append(ft.Container(height=8))
            body_items.append(theme.caption("HATALI SATIRLAR"))
            body_items.append(ft.Container(
                content=ft.Column(errs, spacing=8, scroll=ft.ScrollMode.AUTO),
                height=min(280, 38 * min(len(result.errors), 20) + 24),
                padding=14, bgcolor=theme.SURFACE_ALT, border_radius=2,
            ))

        dlg = ft.AlertDialog(
            modal=True, bgcolor=theme.SURFACE,
            title=ft.Text(
                "İçe Aktarma Tamamlandı" if not result.has_errors
                else "İçe Aktarma Tamamlandı (hatalarla)",
                color=theme.TEXT, weight=ft.FontWeight.W_400,
                font_family=theme.FONT_FAMILY_DISPLAY, size=22,
            ),
            content=ft.Container(
                content=ft.Column(body_items, tight=True, spacing=12),
                width=580,
            ),
            actions=[
                theme.primary_button("Tamam", on_click=lambda e: _dlg_close(self.page)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.dialog = dlg
        self.page.dialog.open = True
        self.page.update()

    # --------------------------------------------- dışa aktar
    def _open_export(self) -> None:
        self.export_picker.save_file(
            dialog_title="Müşterileri CSV olarak kaydet",
            file_name="musteriler.csv",
            allowed_extensions=["csv"],
        )

    def _on_export_path_picked(self, e: ft.FilePickerResultEvent) -> None:
        if not e.path:
            return
        path = Path(e.path)
        if path.suffix.lower() != ".csv":
            path = path.with_suffix(".csv")
        try:
            only_iys = bool(self.only_iys_cb.value)
            count = import_export_service.export_customers_to_csv(
                path, only_iys=only_iys,
            )
            suffix = " (sadece İYS onaylı)" if only_iys else ""
            self.page.snack_bar = ft.SnackBar(
                ft.Text(f"{count} müşteri CSV'ye yazıldı{suffix}."),
                bgcolor=theme.SUCCESS,
            )
            self.page.snack_bar.open = True
            self.page.update()
        except Exception as ex:
            self.page.snack_bar = ft.SnackBar(
                ft.Text(f"Dışa aktarma hatası: {ex}"), bgcolor=theme.ERROR,
            )
            self.page.snack_bar.open = True
            self.page.update()

    # --------------------------------------------- şablon
    def _save_template(self) -> None:
        self.template_picker.save_file(
            dialog_title="Şablonu kaydet",
            file_name="musteri_sablonu.csv",
            allowed_extensions=["csv"],
        )

    def _on_template_path_picked(self, e: ft.FilePickerResultEvent) -> None:
        if not e.path:
            return
        path = Path(e.path)
        if path.suffix.lower() != ".csv":
            path = path.with_suffix(".csv")
        try:
            import_export_service.generate_template_csv(path)
            self.page.snack_bar = ft.SnackBar(
                ft.Text(f"Şablon oluşturuldu: {path.name}"),
                bgcolor=theme.SUCCESS,
            )
            self.page.snack_bar.open = True
            self.page.update()
        except Exception as ex:
            self.page.snack_bar = ft.SnackBar(
                ft.Text(f"Şablon oluşturma hatası: {ex}"), bgcolor=theme.ERROR,
            )
            self.page.snack_bar.open = True
            self.page.update()


def build(page: ft.Page) -> ft.Control:
    return CustomersView(page).build()
