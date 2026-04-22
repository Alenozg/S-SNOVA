"""
SearchableCustomerPicker — yazdıkça filtreleyen müşteri seçim widget'ı.

Kullanım:
    picker = SearchableCustomerPicker(
        on_select=lambda c: print("Seçilen:", c),
        initial_customer_id=42,  # opsiyonel, form düzenleme modunda
    )
    form.controls.append(picker)

Davranış:
- TextField'a yazdıkça alt açılır listede eşleşen müşteriler çıkar
- Listedeki bir müşteriye tıklanırsa: TextField dolar, liste kapanır,
  on_select callback çağrılır
- TextField temizlenirse seçim iptal olur
- Arama Türkçe duyarsız (pelin -> PELİN)
"""
from typing import Callable, Optional
import flet as ft

from models import Customer
from services import customer_service
from ui import theme


class SearchableCustomerPicker(ft.Container):
    """
    Bir Container'a oturtulmuş, kendi kendine yeten searchable picker.
    page.overlay'e bir şey eklemez, sadece kendi içinde açılır liste tutar.
    """

    def __init__(
        self,
        on_select: Callable[[Optional[Customer]], None],
        *,
        initial_customer_id: Optional[int] = None,
        label: str = "Müşteri",
        max_results: int = 8,
    ):
        super().__init__()
        self.on_select = on_select
        self.max_results = max_results

        self._selected: Optional[Customer] = None

        self.text_field = ft.TextField(
            label=label,
            hint_text="Ad, soyad, telefon ile arayın...",
            border_color=theme.DIVIDER,
            focused_border_color=theme.ACCENT,
            bgcolor=theme.SURFACE,
            content_padding=ft.padding.symmetric(horizontal=14, vertical=14),
            border_radius=2,
            text_style=ft.TextStyle(size=13, color=theme.TEXT),
            label_style=ft.TextStyle(size=12, color=theme.TEXT_MUTED),
            prefix_icon=ft.icons.PERSON_SEARCH_OUTLINED,
            on_change=self._on_text_change,
            on_focus=lambda e: self._show_results(),
        )

        self.results_list = ft.Column(
            spacing=0,
            tight=True,
        )

        self.results_container = ft.Container(
            visible=False,
            content=self.results_list,
            bgcolor=theme.SURFACE,
            border=ft.border.all(1, theme.DIVIDER),
            border_radius=2,
            padding=0,
            margin=ft.margin.only(top=2),
        )

        self.hint_text = ft.Text(
            "",
            size=11, color=theme.TEXT_MUTED, italic=True,
            visible=False,
        )

        self.content = ft.Column(
            [self.text_field, self.hint_text, self.results_container],
            spacing=4, tight=True,
        )

        # Başlangıç değeri varsa yükle
        if initial_customer_id is not None:
            c = customer_service.get_customer(initial_customer_id)
            if c:
                self._set_selected(c, update=False)

    # ---------------------------------------------------------- public API
    @property
    def selected(self) -> Optional[Customer]:
        return self._selected

    def clear(self) -> None:
        self._selected = None
        self.text_field.value = ""
        self.results_container.visible = False
        if self.page:
            self.text_field.update()
            self.results_container.update()

    # ---------------------------------------------------------- internal
    def _on_text_change(self, e) -> None:
        query = (self.text_field.value or "").strip()

        # Eğer seçim yapılmış ve kullanıcı yazıyı değiştirdiyse, seçimi sıfırla
        if self._selected is not None:
            expected = self._selected.full_name
            if query != expected:
                self._selected = None
                self.on_select(None)

        if not query:
            self.results_container.visible = False
            self.hint_text.visible = False
            if self.page:
                self.results_container.update()
                self.hint_text.update()
            return

        self._show_results()

    def _show_results(self) -> None:
        query = (self.text_field.value or "").strip()
        if not query:
            self.results_container.visible = False
            if self.page:
                self.results_container.update()
            return

        # Türkçe duyarsız arama — customer_service zaten hallediyor
        matches = customer_service.list_customers(search=query)

        # Görüntülenecek sayı
        display = matches[:self.max_results]
        overflow = len(matches) - len(display)

        if not display:
            # Hiç eşleşme yok
            self.results_container.visible = False
            self.hint_text.value = "Eşleşen müşteri yok"
            self.hint_text.visible = True
            if self.page:
                self.results_container.update()
                self.hint_text.update()
            return

        # Liste öğelerini oluştur
        items: list[ft.Control] = []
        for i, c in enumerate(display):
            items.append(self._build_result_item(c, is_last=(i == len(display) - 1 and overflow == 0)))

        if overflow > 0:
            items.append(ft.Container(
                content=ft.Text(
                    f"...ve {overflow} sonuç daha (daha fazla yazın)",
                    size=11, color=theme.TEXT_MUTED, italic=True,
                ),
                padding=ft.padding.symmetric(horizontal=14, vertical=10),
            ))

        self.results_list.controls = items
        self.results_container.visible = True
        self.hint_text.visible = False
        if self.page:
            self.results_list.update()
            self.results_container.update()
            self.hint_text.update()

    def _build_result_item(self, c: Customer, is_last: bool = False) -> ft.Container:
        # Müşteri satırı: ad soyad + telefon, tıklanabilir
        phone_display = c.display_phone if c.phone else "telefon yok"

        return ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text(
                                    c.full_name, size=13,
                                    weight=ft.FontWeight.W_500,
                                    color=theme.TEXT,
                                ),
                                ft.Text(
                                    phone_display, size=11,
                                    color=theme.TEXT_MUTED,
                                ),
                            ],
                            spacing=2, tight=True,
                        ),
                        expand=True,
                    ),
                    ft.Icon(
                        ft.icons.ARROW_FORWARD_IOS,
                        size=11, color=theme.TEXT_FAINT,
                    ),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
            border=(
                None if is_last
                else ft.border.only(bottom=ft.BorderSide(1, theme.DIVIDER))
            ),
            ink=True,
            on_click=lambda e, cust=c: self._set_selected(cust),
        )

    def _set_selected(self, customer: Customer, update: bool = True) -> None:
        self._selected = customer
        self.text_field.value = customer.full_name
        self.results_container.visible = False
        if update and self.page:
            self.text_field.update()
            self.results_container.update()
        self.on_select(customer)
