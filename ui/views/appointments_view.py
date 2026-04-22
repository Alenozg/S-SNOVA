"""
Randevu yönetimi.

İki görünüm:
  - Liste: günlere göre gruplanmış, personel rengiyle sol bar
  - Takvim: gün içi, personel sütunlarında, rengiyle kart
"""
from datetime import datetime, timedelta, date, time
import flet as ft

def _dlg_close(page):
    """Flet 0.24.1 uyumlu dialog kapatma yardımcısı."""
    try:
        page.dialog.open = False
        page.update()
    except Exception:
        pass


from models import Appointment
from services import appointment_service, customer_service, staff_service
from ui import theme
from ui.components import SearchableCustomerPicker


STATUS_COLORS = {
    "scheduled": theme.ACCENT,
    "completed": theme.SUCCESS,
    "cancelled": theme.ERROR,
    "no_show":   theme.WARN,
}

# Takvim görünümü ayarları
DAY_START_HOUR = 9
DAY_END_HOUR = 20
PIXELS_PER_HOUR = 70  # yüksekliği belirler; 70 -> saatte 70 piksel
STAFF_COL_MIN_WIDTH = 180

# Randevu süresi belirtilmemişse varsayılan (hizmete göre otomatik de kullanılır)
DEFAULT_DURATION_MIN = 45


class AppointmentsView:
    def __init__(self, page: ft.Page):
        self.page = page
        self.view_mode = "week"   # "week" | "calendar" | "list"
        self.selected_date = date.today()

        self.filter_status = ft.Dropdown(
            value="all",
            options=[
                ft.dropdown.Option("all", "Tümü"),
                ft.dropdown.Option("scheduled",   "Yeni Randevu"),
                ft.dropdown.Option("confirmed",   "Onaylandı"),
                ft.dropdown.Option("completed",   "Tamamlandı"),
                ft.dropdown.Option("cancelled",   "İptal Edildi"),
                ft.dropdown.Option("no_show",     "Gelmedi"),
                ft.dropdown.Option("rescheduled", "Ertelendi"),
            ],
            on_change=lambda e: self.refresh(),
            border_color=theme.DIVIDER, focused_border_color=theme.ACCENT,
            text_style=ft.TextStyle(size=13, color=theme.TEXT),
            content_padding=ft.padding.symmetric(horizontal=12, vertical=12),
            border_radius=2, bgcolor=theme.SURFACE, width=180,
        )

        # Görünüm toggle butonları (build'de oluşturulur)
        self.view_toggle = ft.Row(spacing=0)
        self.body_container = ft.Container(expand=True, bgcolor=theme.BG, clip_behavior=ft.ClipBehavior.ANTI_ALIAS)
        self.date_label = ft.Text(
            "", size=16, weight=ft.FontWeight.W_400, color=theme.TEXT,
            font_family=theme.FONT_FAMILY_DISPLAY,
        )

    # ---------------------------------------------------------- build
    def build(self) -> ft.Control:
        header = ft.Row(
            [
                ft.Column(
                    [theme.caption("AJANDA"), theme.h1("Randevular")],
                    spacing=4, expand=True,
                ),
                theme.primary_button(
                    "Yeni Randevu", icon=ft.icons.ADD,
                    on_click=lambda e: self.open_form(),
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.END,
        )

        self._rebuild_view_toggle()

        toolbar = ft.Container(
            content=ft.Row(
                [
                    self.view_toggle,
                    ft.Container(width=24),
                    self._date_navigator(),
                    ft.Container(expand=True),
                    theme.body("Durum:", muted=True),
                    self.filter_status,
                ],
                spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.only(top=20, bottom=20),
        )

        self.refresh()
        return ft.Column(
            [header, toolbar, self.body_container],
            expand=True, spacing=0,
        )

    # ---------------------------------------------------------- view toggle
    def _rebuild_view_toggle(self) -> None:
        def tab(key: str, label: str, icon) -> ft.Container:
            is_active = self.view_mode == key
            return ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(icon, size=14,
                                color=theme.TEXT if is_active else theme.TEXT_MUTED),
                        ft.Text(
                            label, size=12,
                            weight=ft.FontWeight.W_500 if is_active else ft.FontWeight.W_400,
                            color=theme.TEXT if is_active else theme.TEXT_MUTED,
                        ),
                    ],
                    spacing=6,
                ),
                padding=ft.padding.symmetric(horizontal=14, vertical=9),
                bgcolor=theme.SURFACE if is_active else None,
                border_radius=2,
                ink=True,
                on_click=lambda e, k=key: self._set_view(k),
            )

        self.view_toggle.controls = [
            tab("week",     "Hafta",  ft.icons.CALENDAR_VIEW_WEEK_OUTLINED),
            tab("calendar", "Gün",    ft.icons.CALENDAR_VIEW_DAY_OUTLINED),
            tab("list",     "Liste",  ft.icons.LIST_OUTLINED),
        ]
        for c in self.view_toggle.controls:
            c.border = ft.border.all(1, theme.DIVIDER)
            c.expand = False

    def _set_view(self, key: str) -> None:
        if self.view_mode == key:
            return
        self.view_mode = key
        self._rebuild_view_toggle()
        self.view_toggle.update()
        self.refresh()

    # ---------------------------------------------------------- date nav
    def _date_navigator(self) -> ft.Row:
        self._update_date_label()
        return ft.Row(
            [
                ft.IconButton(
                    ft.icons.CHEVRON_LEFT, icon_color=theme.TEXT_MUTED,
                    on_click=lambda e: self._shift_date(-1),
                ),
                ft.Container(
                    content=self.date_label,
                    padding=ft.padding.symmetric(horizontal=8),
                    width=220, alignment=ft.alignment.center,
                ),
                ft.IconButton(
                    ft.icons.CHEVRON_RIGHT, icon_color=theme.TEXT_MUTED,
                    on_click=lambda e: self._shift_date(1),
                ),
                theme.ghost_button(
                    "Bugün", on_click=lambda e: self._goto_today(),
                ),
            ],
            spacing=0, vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _update_date_label(self) -> None:
        tr_months = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
                     "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
        tr_days = ["Pazartesi", "Salı", "Çarşamba", "Perşembe",
                   "Cuma", "Cumartesi", "Pazar"]
        d = self.selected_date
        if self.view_mode == "week":
            # Haftanın ilk gününü (Pazartesi) bul
            week_start = d - timedelta(days=d.weekday())
            week_end = week_start + timedelta(days=6)
            if week_start.month == week_end.month:
                label = (
                    f"{week_start.day}–{week_end.day} "
                    f"{tr_months[week_start.month - 1]} {week_end.year}"
                )
            else:
                label = (
                    f"{week_start.day} {tr_months[week_start.month - 1]} – "
                    f"{week_end.day} {tr_months[week_end.month - 1]} "
                    f"{week_end.year}"
                )
        else:
            label = (
                f"{d.day} {tr_months[d.month - 1]} {d.year}"
                f"  ·  {tr_days[d.weekday()]}"
            )
        self.date_label.value = label

    def _shift_date(self, delta_days: int) -> None:
        # Hafta görünümündeyse 7 gün kaydır; diğerlerinde delta_days kadar
        # delta_days zaten ±1 geliyor (sol/sağ butonları)
        if self.view_mode == "week":
            step = 7 if delta_days > 0 else -7
        else:
            step = delta_days
        self.selected_date = self.selected_date + timedelta(days=step)
        self._update_date_label()
        self.date_label.update()
        self.refresh()

    def _goto_today(self) -> None:
        self.selected_date = date.today()
        self._update_date_label()
        self.date_label.update()
        self.refresh()

    # ---------------------------------------------------------- refresh
    def refresh(self) -> None:
        if self.view_mode == "week":
            self.body_container.content = self._build_week_grid()
        elif self.view_mode == "calendar":
            self.body_container.content = self._build_calendar()
        else:
            self.body_container.content = self._build_list()
        # Tarih etiketi view mode'a göre format değiştirdiği için güncelle
        self._update_date_label()
        if self.date_label.page:
            self.date_label.update()
        if self.body_container.page:
            self.body_container.update()

    # ========================================================================
    #                              TAKVİM GÖRÜNÜMÜ
    # ========================================================================
    def _build_calendar(self) -> ft.Control:
        """Seçili günün personel sütunlu takvim görünümü."""
        staff_list = staff_service.list_staff(only_active=False)
        # Aktif olmayanları göster ama sonda; o günde randevusu varsa zaten göstermeliyiz
        if not staff_list:
            return theme.card(
                ft.Column(
                    [
                        ft.Container(height=20),
                        ft.Icon(ft.icons.GROUP_OUTLINED, size=40,
                                color=theme.TEXT_FAINT),
                        ft.Container(height=10),
                        theme.body(
                            "Takvimi kullanmak için önce personel eklemelisiniz.",
                            muted=True,
                        ),
                        ft.Container(height=4),
                        theme.caption("Sol menüden 'Personel' bölümüne gidin."),
                        ft.Container(height=20),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=40,
            )

        # Seçili günün tüm randevularını çek
        start = datetime.combine(self.selected_date, time.min)
        end = datetime.combine(self.selected_date, time.max)
        status = (self.filter_status.value
                  if self.filter_status.value != "all" else None)
        appts = appointment_service.list_appointments(
            start=start, end=end, status=status,
        )

        # Personellere göre grupla (staff_id yoksa "Atanmamış" sütununa)
        by_staff: dict[int | None, list[Appointment]] = {}
        for a in appts:
            by_staff.setdefault(a.staff_id, []).append(a)

        # Sütunlar: önce aktif personel, sonra pasifler, en sonda "Atanmamış" (eğer var)
        columns = []
        for s in staff_list:
            columns.append(self._staff_column(s, by_staff.get(s.id, [])))

        if None in by_staff:
            columns.append(self._unassigned_column(by_staff[None]))

        # Sol tarafta saat eksen
        axis = self._time_axis()

        # Alt alta: personel başlıkları + saat sütunu
        total_height = (DAY_END_HOUR - DAY_START_HOUR) * PIXELS_PER_HOUR

        # Başlık satırı
        header_tiles = [ft.Container(width=52)]  # axis column için boşluk
        for s in staff_list:
            header_tiles.append(self._staff_header(s))
        if None in by_staff:
            header_tiles.append(self._unassigned_header())

        # Gövde
        body_row = ft.Row(
            [axis] + columns,
            spacing=0,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

        return ft.Container(
            content=ft.Column(
                [
                    ft.Container(
                        content=ft.Row(header_tiles, spacing=0),
                        bgcolor=theme.SURFACE,
                        border=ft.border.only(bottom=ft.BorderSide(1, theme.DIVIDER)),
                    ),
                    ft.Container(
                        content=ft.Row(
                            [ft.Container(
                                content=body_row,
                                height=total_height + 10,
                            )],
                            scroll=ft.ScrollMode.AUTO,
                        ),
                        expand=True,
                    ),
                ],
                spacing=0, expand=True,
            ),
            expand=True,
            bgcolor=theme.SURFACE,
            border=ft.border.all(1, theme.DIVIDER),
            border_radius=4,
        )

    def _time_axis(self) -> ft.Container:
        """Saat etiketlerini gösteren sol sütun."""
        labels = []
        for h in range(DAY_START_HOUR, DAY_END_HOUR):
            labels.append(ft.Container(
                content=ft.Text(
                    f"{h:02d}:00", size=10, color=theme.TEXT_MUTED,
                    weight=ft.FontWeight.W_500,
                ),
                height=PIXELS_PER_HOUR,
                padding=ft.padding.only(top=4, right=6),
                alignment=ft.alignment.top_right,
            ))
        return ft.Container(
            content=ft.Column(labels, spacing=0),
            width=52,
            border=ft.border.only(right=ft.BorderSide(1, theme.DIVIDER)),
        )

    def _staff_header(self, s) -> ft.Container:
        """Bir personelin başlık kutusu (renkli)."""
        return ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        width=10, height=10, bgcolor=s.color, border_radius=5,
                    ),
                    ft.Column(
                        [
                            ft.Text(s.full_name, size=13,
                                    weight=ft.FontWeight.W_500, color=theme.TEXT),
                            theme.caption(s.role or ""),
                        ],
                        spacing=0, tight=True,
                    ),
                ],
                spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            width=STAFF_COL_MIN_WIDTH,
            padding=ft.padding.symmetric(horizontal=12, vertical=12),
            border=ft.border.only(right=ft.BorderSide(1, theme.DIVIDER)),
        )

    def _unassigned_header(self) -> ft.Container:
        return ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.icons.HELP_OUTLINE, size=14, color=theme.TEXT_FAINT),
                    ft.Text(
                        "Personel Atanmamış", size=13,
                        weight=ft.FontWeight.W_500, color=theme.TEXT_MUTED,
                    ),
                ],
                spacing=8,
            ),
            width=STAFF_COL_MIN_WIDTH,
            padding=ft.padding.symmetric(horizontal=12, vertical=12),
            border=ft.border.only(right=ft.BorderSide(1, theme.DIVIDER)),
        )

    def _staff_column(self, s, appts: list[Appointment]) -> ft.Container:
        """Bir personelin sütunu - zemin ızgarası + üstüne konumlandırılmış randevu kartları."""
        return self._column_with_stack(s.color, appts)

    def _unassigned_column(self, appts: list[Appointment]) -> ft.Container:
        return self._column_with_stack(theme.TEXT_MUTED, appts)

    def _column_with_stack(
        self, fallback_color: str, appts: list[Appointment],
    ) -> ft.Container:
        # Arka plan: her saat için ince çizgi
        grid_rows = []
        for h in range(DAY_START_HOUR, DAY_END_HOUR):
            grid_rows.append(ft.Container(
                height=PIXELS_PER_HOUR,
                border=ft.border.only(top=ft.BorderSide(1, theme.DIVIDER)),
            ))

        grid = ft.Column(grid_rows, spacing=0)

        # Randevu kartlarını Stack içinde konumlandır (top = saat offseti)
        cards: list[ft.Control] = [grid]
        for a in appts:
            cards.append(self._calendar_card(a, fallback_color))

        return ft.Container(
            content=ft.Stack(cards),
            width=STAFF_COL_MIN_WIDTH,
            border=ft.border.only(right=ft.BorderSide(1, theme.DIVIDER)),
        )

    def _calendar_card(
        self, a: Appointment, fallback_color: str,
    ) -> ft.Container:
        """
        Saate göre konumlandırılmış, personel rengiyle boyanmış randevu kartı.
        Top piksel = (appointment_at - gun_baslangici) * PIXELS_PER_HOUR / 60
        """
        when = a.appointment_at
        if not when:
            return ft.Container(visible=False)

        # Dakika bazında offset (saat 09:00 -> 0 px, 09:30 -> 35 px ...)
        minutes_from_start = (
            (when.hour - DAY_START_HOUR) * 60 + when.minute
        )
        # Aralık dışındaysa atla
        if minutes_from_start < 0:
            return ft.Container(visible=False)

        top_px = minutes_from_start * PIXELS_PER_HOUR / 60

        # Süre: hizmet üzerinden tahmini (sunucuda yok, varsayılan)
        duration = DEFAULT_DURATION_MIN
        height_px = max(32, duration * PIXELS_PER_HOUR / 60 - 4)

        color = a.staff_color or fallback_color
        cancelled = a.status in ("cancelled", "no_show")
        bg_opacity = 0.12 if not cancelled else 0.06

        when_label = when.strftime("%H:%M")

        content = ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text(
                                when_label, size=10, color=color,
                                weight=ft.FontWeight.W_600,
                            ),
                            ft.Container(expand=True),
                            ft.Text(
                                a.status_label if cancelled else "",
                                size=9, color=theme.TEXT_MUTED,
                                weight=ft.FontWeight.W_400,
                            ),
                        ],
                        spacing=4,
                    ),
                    ft.Text(
                        a.customer_name or "", size=12,
                        weight=ft.FontWeight.W_500,
                        color=theme.TEXT if not cancelled else theme.TEXT_MUTED,
                        max_lines=1, overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                    ft.Text(
                        a.service_name or "—", size=10, color=theme.TEXT_MUTED,
                        max_lines=1, overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                ],
                spacing=2, tight=True,
            ),
            bgcolor=_with_alpha(color, bg_opacity),
            border=ft.border.only(left=ft.BorderSide(3, color)),
            border_radius=2,
            padding=ft.padding.symmetric(horizontal=8, vertical=6),
            width=STAFF_COL_MIN_WIDTH - 8,
            height=height_px,
            ink=True,
            on_click=lambda e, aid=a.id: self.open_detail(aid),
        )

        # Stack positioning: top değeri offset'e göre
        return ft.Container(
            content=content,
            top=top_px + 2,
            left=4,
        )

    # ========================================================================
    #                      HAFTALIK GRID GÖRÜNÜMÜ (YENİ)
    # Saat × gün tablosu. Boş hücreye tıklanınca yeni randevu formu (tarih+saat
    # dolu gelir); dolu bloğa tıklanınca randevu detay modalı açılır.
    # ========================================================================

    # Çalışma saatleri: 09:00 – 20:00, 30 dakikalık dilimler
    WEEK_HOUR_START = 9
    WEEK_HOUR_END = 20
    WEEK_SLOT_MIN = 30      # dakika
    WEEK_SLOT_PX = 44       # her 30dk'lık dilimin yüksekliği
    WEEK_TIME_COL_W = 64    # saat sütunu genişliği

    def _build_week_grid(self) -> ft.Control:
        # Haftanın Pazartesisi
        week_start = self.selected_date - timedelta(days=self.selected_date.weekday())
        week_days = [week_start + timedelta(days=i) for i in range(7)]

        # Statü filtresi
        status = (
            self.filter_status.value
            if self.filter_status.value != "all" else None
        )

        # Hafta boyunca tüm randevular tek sorguda gelsin
        start_dt = datetime.combine(week_start, time(0, 0))
        end_dt = datetime.combine(week_start + timedelta(days=7), time(0, 0))
        all_appts = appointment_service.list_appointments(
            start=start_dt, end=end_dt, status=status,
        )

        # Gün bazında indeksle
        by_day: dict[date, list[Appointment]] = {d: [] for d in week_days}
        for a in all_appts:
            if a.appointment_at:
                d = a.appointment_at.date()
                if d in by_day:
                    by_day[d].append(a)

        # Gün sütunlarını üret (her biri Stack içinde mutlak konumlu bloklar)
        columns: list[ft.Control] = [self._week_time_axis()]
        for d in week_days:
            columns.append(self._week_day_column(d, by_day[d]))

        grid = ft.Row(
            columns,
            spacing=0,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

        # Üstte gün başlıkları
        headers: list[ft.Control] = [
            ft.Container(width=self.WEEK_TIME_COL_W),   # saat sütunu başlığı boş
        ]
        for d in week_days:
            headers.append(self._week_day_header(d))

        header_row = ft.Container(
            content=ft.Row(headers, spacing=0),
            bgcolor=theme.SURFACE_ALT,
            border=ft.border.only(bottom=ft.BorderSide(1, theme.DIVIDER)),
        )

        return theme.card(
            ft.Column(
                [
                    header_row,
                    ft.Container(
                        content=grid,
                        # Dikey scroll uzun görünümler için
                    ),
                ],
                spacing=0, scroll=ft.ScrollMode.AUTO,
            ),
            padding=0,
        )

    def _week_day_header(self, d: date) -> ft.Container:
        tr_short_days = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]
        is_today = d == date.today()
        is_weekend = d.weekday() >= 5

        day_label = ft.Text(
            tr_short_days[d.weekday()].upper(),
            size=10,
            color=theme.ACCENT if is_today else theme.TEXT_MUTED,
            weight=ft.FontWeight.W_500,
        )
        num_label = ft.Text(
            str(d.day),
            size=18,
            color=theme.ACCENT if is_today else (
                theme.TEXT_MUTED if is_weekend else theme.TEXT
            ),
            weight=ft.FontWeight.W_500 if is_today else ft.FontWeight.W_400,
            font_family=theme.FONT_FAMILY_DISPLAY,
        )

        return ft.Container(
            content=ft.Column(
                [day_label, num_label],
                spacing=0,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            expand=True,
            padding=ft.padding.symmetric(vertical=10),
            alignment=ft.alignment.center,
            border=ft.border.only(left=ft.BorderSide(1, theme.DIVIDER)),
        )

    def _week_time_axis(self) -> ft.Container:
        rows: list[ft.Control] = []
        slots_per_hour = 60 // self.WEEK_SLOT_MIN
        total_slots = (self.WEEK_HOUR_END - self.WEEK_HOUR_START) * slots_per_hour

        for i in range(total_slots):
            hour = self.WEEK_HOUR_START + (i // slots_per_hour)
            minute = (i % slots_per_hour) * self.WEEK_SLOT_MIN
            # Sadece saat başlarını yaz, yarım saatleri boş bırak (minimal)
            label = f"{hour:02d}:00" if minute == 0 else ""
            rows.append(ft.Container(
                content=ft.Text(
                    label, size=10, color=theme.TEXT_MUTED,
                    weight=ft.FontWeight.W_500,
                ),
                height=self.WEEK_SLOT_PX,
                padding=ft.padding.only(right=10, top=4),
                alignment=ft.alignment.top_right,
            ))

        return ft.Container(
            content=ft.Column(rows, spacing=0),
            width=self.WEEK_TIME_COL_W,
            bgcolor=theme.SURFACE_ALT,
            border=ft.border.only(right=ft.BorderSide(1, theme.DIVIDER)),
        )

    def _week_day_column(self, day: date, appts: list[Appointment]) -> ft.Container:
        """Bir gün için dikey kolon: saat dilimleri (tıklanabilir boş hücreler)
        + üstte mutlak konumlandırılmış dolu randevu blokları."""
        slots_per_hour = 60 // self.WEEK_SLOT_MIN
        total_slots = (self.WEEK_HOUR_END - self.WEEK_HOUR_START) * slots_per_hour
        col_height = total_slots * self.WEEK_SLOT_PX

        # 1) Alt zemin: her 30dk'lık dilim için tıklanabilir boş hücre
        slot_cells: list[ft.Control] = []
        for i in range(total_slots):
            hour = self.WEEK_HOUR_START + (i // slots_per_hour)
            minute = (i % slots_per_hour) * self.WEEK_SLOT_MIN

            # Her saat başı alt kenarı biraz daha belirgin
            is_hour_start = (minute == 0)
            border = ft.border.only(
                bottom=ft.BorderSide(
                    1 if is_hour_start else 0,
                    theme.DIVIDER,
                ),
            )

            slot_cells.append(ft.Container(
                height=self.WEEK_SLOT_PX,
                border=border,
                ink=True,
                tooltip=f"{hour:02d}:{minute:02d} — Yeni randevu",
                on_click=(
                    lambda e, d=day, h=hour, m=minute:
                        self._on_empty_slot_clicked(d, h, m)
                ),
            ))

        base_column = ft.Column(slot_cells, spacing=0)

        # 2) Üst katman: randevu blokları (mutlak konumlu)
        blocks = [
            self._week_appointment_block(a)
            for a in appts
            if a.appointment_at is not None
        ]
        blocks = [b for b in blocks if b is not None]

        stack = ft.Stack(
            [base_column] + blocks,
            width=None,
            height=col_height,
        )

        return ft.Container(
            content=stack,
            expand=True,
            border=ft.border.only(left=ft.BorderSide(1, theme.DIVIDER)),
        )

    def _week_appointment_block(self, a: Appointment) -> ft.Control | None:
        """Tek randevu için soft renkli blok (tıklanabilir)."""
        if not a.appointment_at:
            return None

        t = a.appointment_at.time()
        # Günün başlangıcından (WEEK_HOUR_START) itibaren kaç dakika?
        start_minutes = (t.hour - self.WEEK_HOUR_START) * 60 + t.minute
        if start_minutes < 0:
            return None  # Çalışma saati öncesi
        # Üst limit
        end_minute = (self.WEEK_HOUR_END - self.WEEK_HOUR_START) * 60
        if start_minutes >= end_minute:
            return None

        top_px = (start_minutes / self.WEEK_SLOT_MIN) * self.WEEK_SLOT_PX

        # Süreyi hizmetten al (yoksa varsayılan 60dk)
        duration = 60
        # JOIN'de service.duration_min yok ama bunu ayrıca sorgulamak overkill;
        # randevu kartı özet için sabit 60dk bloku göstermek yeterli.
        # Blok yüksekliği: 60dk = 2 slot = 2 * WEEK_SLOT_PX
        block_height = max(
            self.WEEK_SLOT_PX,   # en az 1 slot
            (duration / self.WEEK_SLOT_MIN) * self.WEEK_SLOT_PX - 4,
        )

        # Renk: personel rengi (yoksa accent). Saydam zemin + solid sol bar.
        base_color = a.staff_color or theme.ACCENT
        # İptal/gelmedi durumları soluk göster
        faded = a.status in ("cancelled", "no_show")

        bg = _with_alpha(base_color, 0.08 if faded else 0.16)
        bar_color = (
            _with_alpha(base_color, 0.4) if faded else base_color
        )
        text_color = theme.TEXT_MUTED if faded else theme.TEXT

        # İçerik: saat • müşteri • hizmet
        time_str = f"{t.hour:02d}:{t.minute:02d}"
        customer_name = a.customer_name or "—"
        service_name = a.service_name or ""

        status_mark = ""
        if a.status == "confirmed":
            status_mark = "✓ "
        elif a.status == "cancelled":
            status_mark = "✕ "
        elif a.status == "no_show":
            status_mark = "⊘ "
        elif a.status == "completed":
            status_mark = "● "
        elif a.status == "rescheduled":
            status_mark = "↻ "

        content = ft.Column(
            [
                ft.Text(
                    f"{status_mark}{time_str}  {customer_name}",
                    size=11,
                    color=text_color,
                    weight=ft.FontWeight.W_500,
                    max_lines=1,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
                ft.Text(
                    service_name, size=10, color=theme.TEXT_MUTED,
                    max_lines=1, overflow=ft.TextOverflow.ELLIPSIS,
                ) if service_name else ft.Container(height=0),
            ],
            spacing=2, tight=True,
        )

        block = ft.Container(
            content=content,
            width=None,
            height=block_height,
            padding=ft.padding.symmetric(horizontal=8, vertical=6),
            bgcolor=bg,
            border=ft.border.only(left=ft.BorderSide(3, bar_color)),
            border_radius=2,
            ink=True,
            tooltip=(
                f"{time_str} · {customer_name}\n"
                f"{service_name} · {a.status_label}"
            ),
            on_click=lambda e, aid=a.id: self._on_appointment_clicked(aid),
        )

        # Stack içinde mutlak konumlu
        return ft.Container(
            content=block,
            top=top_px + 1,
            left=2,
            right=2,
        )

    # ---------------------------------------------------------- grid events
    def _on_empty_slot_clicked(self, d: date, hour: int, minute: int) -> None:
        """Boş hücre tıklaması: yeni randevu formu, tarih+saat önceden dolu."""
        preset_dt = datetime.combine(d, time(hour, minute))
        self.open_form(appointment_id=None, preset_datetime=preset_dt)

    def _on_appointment_clicked(self, appointment_id: int) -> None:
        """Dolu blok tıklaması: randevu detay modalı."""
        self.open_detail(appointment_id)

    # ========================================================================
    #                              LİSTE GÖRÜNÜMÜ
    # ========================================================================
    def _build_list(self) -> ft.Control:
        status = (self.filter_status.value
                  if self.filter_status.value != "all" else None)
        items = appointment_service.list_appointments(status=status)

        grouped: dict[str, list[Appointment]] = {}
        for a in items:
            key = a.appointment_at.strftime("%d %B %Y") if a.appointment_at else "—"
            grouped.setdefault(key, []).append(a)

        controls: list[ft.Control] = []
        if not items:
            controls.append(ft.Container(
                content=theme.body("Kayıtlı randevu bulunmuyor.", muted=True),
                padding=40, alignment=ft.alignment.center,
            ))
        for day, appts in grouped.items():
            controls.append(ft.Container(
                content=ft.Text(day.upper(), size=10, color=theme.TEXT_MUTED,
                                weight=ft.FontWeight.W_500),
                padding=ft.padding.only(left=24, top=18, bottom=8),
            ))
            for a in appts:
                controls.append(self._list_row(a))

        return ft.Column(
            [theme.card(ft.Column(controls, spacing=0), padding=0)],
            scroll=ft.ScrollMode.AUTO, expand=True,
        )

    def _list_row(self, a: Appointment) -> ft.Container:
        when = a.appointment_at.strftime("%H:%M") if a.appointment_at else "—"
        staff_color = a.staff_color or theme.TEXT_MUTED
        staff_label = a.staff_name or "Personel atanmamış"

        status_chip = ft.Container(
            content=ft.Text(a.status_label, size=10, color=theme.SURFACE,
                            weight=ft.FontWeight.W_500),
            padding=ft.padding.symmetric(horizontal=10, vertical=4),
            bgcolor=STATUS_COLORS.get(a.status, theme.TEXT_MUTED),
            border_radius=2,
        )

        reminder_chip = ft.Container(
            content=ft.Row(
                [ft.Icon(ft.icons.SCHEDULE_SEND, size=12, color=theme.SUCCESS),
                 ft.Text("Hatırlatma gönderildi", size=10, color=theme.TEXT_MUTED)],
                spacing=4,
            ),
            visible=a.reminder_sent,
        )

        return ft.Container(
            content=ft.Row(
                [
                    # Sol renk bar - personel rengi
                    ft.Container(width=3, bgcolor=staff_color, border_radius=2),
                    ft.Container(
                        content=ft.Text(when, size=18, weight=ft.FontWeight.W_400,
                                        color=theme.ACCENT,
                                        font_family=theme.FONT_FAMILY_DISPLAY),
                        width=70,
                        padding=ft.padding.only(left=10),
                    ),
                    ft.Column(
                        [
                            ft.Text(a.customer_name or "", size=14,
                                    weight=ft.FontWeight.W_500, color=theme.TEXT),
                            ft.Row(
                                [
                                    theme.caption(a.service_name or "—"),
                                    theme.caption("•"),
                                    ft.Container(
                                        content=ft.Row(
                                            [
                                                ft.Container(
                                                    width=8, height=8,
                                                    bgcolor=staff_color,
                                                    border_radius=4,
                                                ),
                                                ft.Text(
                                                    staff_label, size=11,
                                                    color=theme.TEXT_MUTED,
                                                ),
                                            ],
                                            spacing=6,
                                        ),
                                    ),
                                    theme.caption("•") if a.reminder_sent else ft.Container(),
                                    reminder_chip,
                                ],
                                spacing=6,
                            ),
                        ],
                        spacing=3, expand=True,
                    ),
                    status_chip,
                    ft.PopupMenuButton(
                        icon=ft.icons.MORE_VERT,
                        icon_color=theme.TEXT_MUTED,
                        items=[
                            ft.PopupMenuItem(text="Detay",
                                             on_click=lambda e, aid=a.id: self.open_detail(aid)),
                            ft.PopupMenuItem(text="Düzenle",
                                             on_click=lambda e, aid=a.id: self.open_form(aid)),
                            ft.PopupMenuItem(text="Tamamlandı",
                                             on_click=lambda e, aid=a.id: self._set_status(aid, "completed")),
                            ft.PopupMenuItem(text="İptal et",
                                             on_click=lambda e, aid=a.id: self._set_status(aid, "cancelled")),
                            ft.PopupMenuItem(text="Gelmedi",
                                             on_click=lambda e, aid=a.id: self._set_status(aid, "no_show")),
                            ft.PopupMenuItem(),
                            ft.PopupMenuItem(text="Sil",
                                             on_click=lambda e, aid=a.id: self._delete(aid)),
                        ],
                    ),
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.only(top=12, bottom=12, right=20),
            border=ft.border.only(bottom=ft.BorderSide(1, theme.DIVIDER)),
            ink=True,
            on_click=lambda e, aid=a.id: self.open_detail(aid),
        )

    def _set_status(self, aid: int, status: str) -> None:
        appointment_service.set_status(aid, status)
        self.refresh()

    def _delete(self, aid: int) -> None:
        appointment_service.delete_appointment(aid)
        self.refresh()
        self.page.snack_bar = ft.SnackBar(ft.Text("Randevu silindi."), bgcolor=theme.TEXT)
        self.page.snack_bar.open = True
        self.page.update()

    # ========================================================================
    #                      RANDEVU DETAY MODALI (YENİ)
    # Grid'de veya listede randevuya tıklanınca açılır. Kapsamlı bilgi
    # gösterir, statü değiştirilebilir, sil/yeniden planla/kaydet aksiyonları
    # ========================================================================
    def open_detail(self, appointment_id: int) -> None:
        a = appointment_service.get_appointment(appointment_id)
        if not a:
            self.page.snack_bar = ft.SnackBar(
                ft.Text("Randevu bulunamadı."), bgcolor=theme.ERROR,
            )
            self.page.snack_bar.open = True
            self.page.update()
            return

        # ----- Bilgi satırları (salt okunur) -----
        def info_row(label: str, value: str, icon=None) -> ft.Control:
            children: list[ft.Control] = []
            if icon:
                children.append(ft.Icon(icon, size=14, color=theme.TEXT_MUTED))
            children.append(ft.Column(
                [
                    ft.Text(label.upper(), size=10, color=theme.TEXT_MUTED,
                            weight=ft.FontWeight.W_500),
                    ft.Text(value or "—", size=14, color=theme.TEXT,
                            weight=ft.FontWeight.W_400),
                ],
                spacing=3, tight=True, expand=True,
            ))
            return ft.Container(
                content=ft.Row(
                    children, spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
                padding=ft.padding.symmetric(vertical=10),
                border=ft.border.only(bottom=ft.BorderSide(1, theme.DIVIDER)),
            )

        when_str = (
            a.appointment_at.strftime("%d.%m.%Y · %H:%M")
            if a.appointment_at else "—"
        )
        price_str = (
            f"₺{a.price:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
            if a.price else "—"
        )

        # Personel renkli nokta
        staff_display: ft.Control = ft.Text(
            a.staff_name or "—", size=14, color=theme.TEXT,
        )
        if a.staff_name and a.staff_color:
            staff_display = ft.Row(
                [
                    ft.Container(
                        width=8, height=8, bgcolor=a.staff_color,
                        border_radius=4,
                    ),
                    ft.Text(a.staff_name, size=14, color=theme.TEXT),
                ],
                spacing=8,
            )

        # ----- Durum değiştirici (Dropdown) -----
        # state — save'de okunacak
        status_state = {"value": a.status}

        def on_status_changed(e):
            status_state["value"] = e.control.value

        status_dd = ft.Dropdown(
            label="Durum",
            value=a.status,
            options=[
                ft.dropdown.Option("scheduled",   "Yeni Randevu"),
                ft.dropdown.Option("confirmed",   "Onaylandı"),
                ft.dropdown.Option("completed",   "Tamamlandı"),
                ft.dropdown.Option("cancelled",   "İptal Edildi"),
                ft.dropdown.Option("no_show",     "Gelmedi"),
                ft.dropdown.Option("rescheduled", "Ertelendi"),
            ],
            on_change=on_status_changed,
            border_color=theme.DIVIDER, focused_border_color=theme.ACCENT,
            bgcolor=theme.SURFACE, border_radius=2,
            text_style=ft.TextStyle(size=13, color=theme.TEXT),
            label_style=ft.TextStyle(size=12, color=theme.TEXT_MUTED),
        )

        notes_field = theme.text_field(
            "Notlar", a.notes or "", multiline=True,
        )
        error_text = ft.Text("", color=theme.ERROR, size=12)

        dlg_ref: dict = {"dlg": None}

        def close(e=None):
            if dlg_ref["dlg"]:
                self.page.dialog.open = False
                self.page.update()

        def save_changes(e):
            try:
                # Güncel halini çek ve sadece status/notes değiştir
                cur = appointment_service.get_appointment(appointment_id)
                if not cur:
                    raise ValueError("Randevu silinmiş olabilir.")
                cur.status = status_state["value"]
                cur.notes = notes_field.value or ""
                appointment_service.update_appointment(cur)
                close()
                self.refresh()
                self.page.snack_bar = ft.SnackBar(
                    ft.Text("Randevu güncellendi."), bgcolor=theme.SUCCESS,
                )
                self.page.snack_bar.open = True
                self.page.update()
            except Exception as ex:
                error_text.value = f"Hata: {ex}"
                error_text.update()

        def delete_clicked(e):
            close()
            self._confirm_delete_appointment(appointment_id)

        def reschedule_clicked(e):
            close()
            self.open_reschedule(appointment_id)

        # ----- Dialog bütünü -----
        # Telefonu +90 (5XX) XXX XX XX formatında göster
        phone_display = ""
        if a.customer_phone and len(a.customer_phone) == 12 and a.customer_phone.startswith("90"):
            p = a.customer_phone
            phone_display = f" · +90 ({p[2:5]}) {p[5:8]} {p[8:10]} {p[10:12]}"
        elif a.customer_phone:
            phone_display = f" · {a.customer_phone}"
        customer_contact = phone_display

        title_row = ft.Row(
            [
                ft.Column(
                    [
                        ft.Text(
                            "Randevu Detayı",
                            size=11, color=theme.TEXT_MUTED,
                            weight=ft.FontWeight.W_500,
                        ),
                        ft.Text(
                            (a.customer_name or "—") + customer_contact,
                            size=22, color=theme.TEXT,
                            weight=ft.FontWeight.W_400,
                            font_family=theme.FONT_FAMILY_DISPLAY,
                        ),
                    ],
                    spacing=2, expand=True,
                ),
                ft.IconButton(
                    ft.icons.CLOSE, icon_color=theme.TEXT_MUTED,
                    on_click=close, tooltip="Kapat",
                ),
            ],
            spacing=8,
        )

        dlg = ft.AlertDialog(
            modal=True, bgcolor=theme.SURFACE,
            title=title_row,
            content=ft.Column(
                    [
                        info_row(
                            "Tarih / Saat", when_str,
                            icon=ft.icons.EVENT_OUTLINED,
                        ),
                        info_row(
                            "Hizmet", a.service_name or "—",
                            icon=ft.icons.DESIGN_SERVICES_OUTLINED,
                        ),
                        ft.Container(
                            content=ft.Row(
                                [
                                    ft.Icon(
                                        ft.icons.BADGE_OUTLINED,
                                        size=14, color=theme.TEXT_MUTED,
                                    ),
                                    ft.Column(
                                        [
                                            ft.Text(
                                                "PERSONEL", size=10,
                                                color=theme.TEXT_MUTED,
                                                weight=ft.FontWeight.W_500,
                                            ),
                                            staff_display,
                                        ],
                                        spacing=3, tight=True, expand=True,
                                    ),
                                ],
                                spacing=10,
                                vertical_alignment=ft.CrossAxisAlignment.START,
                            ),
                            padding=ft.padding.symmetric(vertical=10),
                            border=ft.border.only(
                                bottom=ft.BorderSide(1, theme.DIVIDER),
                            ),
                        ),
                        info_row(
                            "Tutar", price_str,
                            icon=ft.icons.PAYMENTS_OUTLINED,
                        ),
                        ft.Container(height=8),
                        # Durum ve notlar düzenlenebilir
                        status_dd,
                        notes_field,
                        error_text,
                    ],
                    tight=True, spacing=8,
                ),
            actions=[
                ft.ElevatedButton(
                    "Sil", on_click=delete_clicked,
                    icon=ft.icons.DELETE_OUTLINE,
                    style=ft.ButtonStyle(
                        bgcolor=_with_alpha(theme.ERROR, 0.12),
                        color=theme.ERROR,
                        shape=ft.RoundedRectangleBorder(radius=2),
                        padding=ft.padding.symmetric(
                            horizontal=18, vertical=16,
                        ),
                    ),
                ),
                theme.ghost_button(
                    "Yeniden Planla", icon=ft.icons.SCHEDULE_OUTLINED,
                    on_click=reschedule_clicked,
                ),
                theme.primary_button(
                    "Kaydet", on_click=save_changes,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        dlg_ref["dlg"] = dlg

        try:
            self.page.dialog = dlg
            self.page.dialog.open = True
            self.page.update()
        except Exception:
            self.page.dialog = dlg
            dlg.open = True
            self.page.update()

    # ---------------------------------------------------------- reschedule
    def open_reschedule(self, appointment_id: int) -> None:
        """Küçük bir alt diyalog: sadece tarih/saat ve 'Ertele' butonu.
        Durum 'rescheduled' olur, appointment_at güncellenir."""
        a = appointment_service.get_appointment(appointment_id)
        if not a:
            return

        current_dt = a.appointment_at or datetime.now()
        date_field = theme.text_field(
            "Yeni Tarih", current_dt.strftime("%Y-%m-%d"),
            hint="YYYY-AA-GG",
        )
        time_field = theme.text_field(
            "Yeni Saat", current_dt.strftime("%H:%M"),
            hint="SS:DD",
        )
        error_text = ft.Text("", color=theme.ERROR, size=12)

        dlg_ref: dict = {"dlg": None}

        def close(e=None):
            if dlg_ref["dlg"]:
                self.page.dialog.open = False
                self.page.update()

        def do_reschedule(e):
            try:
                new_dt = datetime.strptime(
                    f"{date_field.value.strip()} {time_field.value.strip()}",
                    "%Y-%m-%d %H:%M",
                )
                cur = appointment_service.get_appointment(appointment_id)
                cur.appointment_at = new_dt
                cur.status = "rescheduled"
                appointment_service.update_appointment(cur)
                close()
                self.refresh()
                self.page.snack_bar = ft.SnackBar(
                    ft.Text(
                        f"Randevu {new_dt.strftime('%d.%m.%Y %H:%M')} "
                        f"olarak ertelendi."
                    ),
                    bgcolor=theme.SUCCESS,
                )
                self.page.snack_bar.open = True
                self.page.update()
            except ValueError as ex:
                error_text.value = f"Tarih/saat hatalı: {ex}"
                error_text.update()
            except Exception as ex:
                error_text.value = f"Hata: {ex}"
                error_text.update()

        dlg = ft.AlertDialog(
            modal=True, bgcolor=theme.SURFACE,
            title=ft.Text(
                "Yeniden Planla",
                color=theme.TEXT, weight=ft.FontWeight.W_400,
                font_family=theme.FONT_FAMILY_DISPLAY, size=20,
            ),
            content=ft.Column(
                    [
                        theme.caption(
                            f"Mevcut: {current_dt.strftime('%d.%m.%Y %H:%M')}"
                        ),
                        ft.Container(height=8),
                        ft.Row([date_field, time_field], spacing=12),
                        error_text,
                    ],
                    tight=True, spacing=8,
                ),
            actions=[
                theme.ghost_button("Vazgeç", on_click=close),
                theme.primary_button(
                    "Ertele", icon=ft.icons.SCHEDULE_OUTLINED,
                    on_click=do_reschedule,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        dlg_ref["dlg"] = dlg
        self.page.dialog = dlg
        self.page.dialog.open = True
        self.page.update()

    # ---------------------------------------------------------- delete confirm
    def _confirm_delete_appointment(self, appointment_id: int) -> None:
        a = appointment_service.get_appointment(appointment_id)
        if not a:
            return

        when = (
            a.appointment_at.strftime("%d.%m.%Y %H:%M")
            if a.appointment_at else ""
        )
        msg = (
            f"{a.customer_name or 'Müşteri'} adına {when} tarihli "
            f"randevu silinecek. Emin misiniz?"
        )

        dlg_ref: dict = {"dlg": None}

        def close(e=None):
            if dlg_ref["dlg"]:
                self.page.dialog.open = False
                self.page.update()

        def do_delete(e):
            self._delete(appointment_id)
            close()

        dlg = ft.AlertDialog(
            modal=True, bgcolor=theme.SURFACE,
            title=ft.Text(
                "Randevuyu sil?", color=theme.TEXT,
                weight=ft.FontWeight.W_400,
                font_family=theme.FONT_FAMILY_DISPLAY, size=20,
            ),
            content=ft.Text(msg, color=theme.TEXT_MUTED, size=13),
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

    # ========================================================================
    #                                  FORM
    # ========================================================================
    def open_form(
        self,
        appointment_id: int | None = None,
        preset_datetime: datetime | None = None,
    ) -> None:
        existing = (appointment_service.get_appointment(appointment_id)
                    if appointment_id else None)

        customers = customer_service.list_customers()
        services = appointment_service.list_services()
        staff_list = staff_service.list_staff(only_active=True)

        if not customers:
            self.page.snack_bar = ft.SnackBar(
                ft.Text("Önce müşteri eklemelisiniz."), bgcolor=theme.ERROR)
            self.page.snack_bar.open = True
            self.page.update()
            return

        # Müşteri için searchable picker (önceki Dropdown yerine)
        # Seçilen müşteri id'sini tutan mutable state (lambda içinde kullanmak için)
        selected_customer_state = {
            "id": existing.customer_id if existing else None
        }

        def on_customer_selected(customer):
            selected_customer_state["id"] = customer.id if customer else None

        customer_picker = SearchableCustomerPicker(
            on_select=on_customer_selected,
            initial_customer_id=existing.customer_id if existing else None,
            label="Müşteri",
            max_results=8,
        )

        # Hizmet dropdown - seçim değişince fiyat/süre otomatik dolsun
        service_dd = ft.Dropdown(
            label="Hizmet",
            value=str(existing.service_id) if existing and existing.service_id else
                  (str(services[0]["id"]) if services else None),
            options=[
                ft.dropdown.Option(
                    str(s["id"]),
                    f"{s['name']}  ·  {s.get('duration_min', 30)} dk  ·  ₺{int(s.get('price', 0) or 0)}",
                )
                for s in services
            ],
            border_color=theme.DIVIDER, focused_border_color=theme.ACCENT,
            bgcolor=theme.SURFACE, border_radius=2,
            text_style=ft.TextStyle(size=13, color=theme.TEXT),
            label_style=ft.TextStyle(size=12, color=theme.TEXT_MUTED),
        )

        # Service id -> dict eşlemesi (on_change handler için)
        services_by_id = {str(s["id"]): s for s in services}

        # Ek alanlar: süre ve fiyat — hizmet seçilince otomatik dolar ama düzenlenebilir
        initial_duration = ""
        initial_price = ""
        if existing:
            if existing.service_id and str(existing.service_id) in services_by_id:
                s_info = services_by_id[str(existing.service_id)]
                initial_duration = str(s_info.get("duration_min") or "")
            if existing.price:
                initial_price = str(int(existing.price))
        elif services:
            s_info = services[0]
            initial_duration = str(s_info.get("duration_min") or "")
            initial_price = str(int(s_info.get("price") or 0))

        duration_field = theme.text_field(
            "Süre (dk)", initial_duration,
            hint="Hizmet seçince otomatik gelir",
        )
        price_field = theme.text_field(
            "Fiyat (₺)", initial_price,
            hint="Hizmet seçince otomatik gelir",
        )

        def on_service_changed(e):
            svc = services_by_id.get(service_dd.value or "")
            if svc:
                duration_field.value = str(svc.get("duration_min") or "")
                price_field.value = str(int(svc.get("price") or 0))
                if duration_field.page:
                    duration_field.update()
                if price_field.page:
                    price_field.update()

        service_dd.on_change = on_service_changed

        # Personel dropdown - opsiyonel (boş değer destekli)
        staff_options = [ft.dropdown.Option("", "— Atanmamış —")]
        for s in staff_list:
            staff_options.append(ft.dropdown.Option(str(s.id), s.full_name))

        staff_value = ""
        if existing and existing.staff_id:
            staff_value = str(existing.staff_id)
        elif staff_list:
            staff_value = str(staff_list[0].id)

        staff_dd = ft.Dropdown(
            label="Personel",
            value=staff_value,
            options=staff_options,
            border_color=theme.DIVIDER, focused_border_color=theme.ACCENT,
            bgcolor=theme.SURFACE, border_radius=2,
            text_style=ft.TextStyle(size=13, color=theme.TEXT),
            label_style=ft.TextStyle(size=12, color=theme.TEXT_MUTED),
        )

        # Varsayılan tarih/saat önceliği:
        #   1) Düzenleme ise mevcut randevu tarihi
        #   2) Haftalık grid'den gelen preset_datetime (boş hücre tıklaması)
        #   3) Görünen tarihin 10:00'u
        if existing:
            default_dt = existing.appointment_at or datetime.combine(
                self.selected_date, time(10, 0))
        elif preset_datetime:
            default_dt = preset_datetime
        else:
            default_dt = datetime.combine(self.selected_date, time(10, 0))

        date_field = theme.text_field(
            "Tarih", default_dt.strftime("%Y-%m-%d"),
            hint="YYYY-AA-GG",
        )
        time_field = theme.text_field(
            "Saat", default_dt.strftime("%H:%M"),
            hint="SS:DD (örn. 14:30)",
        )
        notes = theme.text_field(
            "Notlar", existing.notes if existing else "", multiline=True,
        )
        error_text = ft.Text("", color=theme.ERROR, size=12)

        def save(e):
            try:
                dt = datetime.strptime(
                    f"{date_field.value.strip()} {time_field.value.strip()}",
                    "%Y-%m-%d %H:%M",
                )
                staff_id = int(staff_dd.value) if staff_dd.value else None

                # Müşteri seçimi zorunlu
                cust_id = selected_customer_state["id"]
                if cust_id is None:
                    raise ValueError("Müşteri seçilmedi.")

                # Fiyat parse (opsiyonel)
                price_raw = (price_field.value or "").strip().replace(",", ".")
                price_val = None
                if price_raw:
                    try:
                        price_val = float(price_raw)
                    except ValueError:
                        raise ValueError("Fiyat sayı olmalı (örn. 250 veya 249.90).")

                payload = Appointment(
                    id=existing.id if existing else None,
                    customer_id=cust_id,
                    service_id=int(service_dd.value) if service_dd.value else None,
                    staff_id=staff_id,
                    appointment_at=dt,
                    status=existing.status if existing else "scheduled",
                    price=price_val,
                    notes=notes.value or "",
                )
                if existing:
                    appointment_service.update_appointment(payload)
                    msg = "Randevu güncellendi."
                else:
                    appointment_service.create_appointment(payload)
                    msg = "Randevu oluşturuldu."

                self.page.dialog.open = False
                self.page.update()
                self.refresh()
                self.page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor=theme.SUCCESS)
                self.page.snack_bar.open = True
                self.page.update()
            except Exception as ex:
                error_text.value = f"Hata: {ex}"
                error_text.update()

        dlg = ft.AlertDialog(
            modal=True, bgcolor=theme.SURFACE,
            title=ft.Text("Randevu Bilgileri" if existing else "Yeni Randevu",
                          color=theme.TEXT, weight=ft.FontWeight.W_400,
                          font_family=theme.FONT_FAMILY_DISPLAY, size=22),
            content=ft.Container(
                content=ft.Column(
                    [
                        customer_picker,
                        ft.Row([service_dd, staff_dd], spacing=12),
                        ft.Row([duration_field, price_field], spacing=12),
                        ft.Row([date_field, time_field], spacing=12),
                        notes,
                        error_text,
                    ],
                    tight=True, spacing=12,
                ),
                width=560,
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


# -----------------------------------------------------------
# Yardımcı: hex rengi alpha ile karıştır (zemin transparentçe)
# -----------------------------------------------------------
def _with_alpha(hex_color: str, alpha: float) -> str:
    """Flet color string with opacity: 'rgba(r, g, b, a)' formatı yerine
    Flet'te '#AARRGGBB' formatı ya da doğrudan opacity kullanılabilir.
    Basitçe alpha kanalıyla hex üretiyoruz."""
    if not hex_color or not hex_color.startswith("#") or len(hex_color) != 7:
        return hex_color
    a = max(0, min(255, int(alpha * 255)))
    # Flet beklediği format: #AARRGGBB
    return f"#{a:02X}{hex_color[1:].upper()}"


def build(page: ft.Page) -> ft.Control:
    return AppointmentsView(page).build()
