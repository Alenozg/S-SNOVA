"""
Ayarlar: SMS sağlayıcı, arka plan görevlerinin durumu ve veri depolama bilgisi.
Gerçek ayarları .env üzerinden yönetiyoruz; burası bilgilendirme panelidir.
"""
from pathlib import Path
import flet as ft

import config
from database import fetch_one
from services import scheduler_service
from ui import theme


def _db_stats() -> dict:
    """Veritabanındaki toplam kayıt sayılarını döner."""
    def _count(table: str) -> int:
        row = fetch_one(f"SELECT COUNT(*) AS c FROM {table}")
        return (row or {}).get("c") or 0

    try:
        return {
            "customers": _count("customers"),
            "appointments": _count("appointments"),
            "staff": _count("staff"),
            "sms_logs": _count("sms_logs"),
        }
    except Exception:
        return {"customers": 0, "appointments": 0, "staff": 0, "sms_logs": 0}


def _db_size_kb() -> int:
    p = Path(config.DATABASE_PATH)
    try:
        return max(1, int(p.stat().st_size / 1024))
    except Exception:
        return 0


def build(page: ft.Page) -> ft.Control:
    scheduler = scheduler_service.get_scheduler()
    jobs_info = []
    if scheduler and scheduler.running:
        for job in scheduler.get_jobs():
            nxt = job.next_run_time.strftime("%d.%m.%Y %H:%M") if job.next_run_time else "—"
            jobs_info.append((job.name, nxt))

    def info_row(label: str, value: str, badge_color: str | None = None) -> ft.Container:
        value_widget = ft.Text(value, size=13, color=theme.TEXT,
                               weight=ft.FontWeight.W_500)
        if badge_color:
            value_widget = ft.Container(
                content=ft.Text(value, size=11, color=theme.SURFACE,
                                weight=ft.FontWeight.W_500),
                padding=ft.padding.symmetric(horizontal=10, vertical=4),
                bgcolor=badge_color, border_radius=2,
            )
        return ft.Container(
            content=ft.Row(
                [
                    ft.Container(content=theme.body(label, muted=True), width=200),
                    ft.Container(content=value_widget, expand=True),
                ],
                spacing=16,
            ),
            padding=ft.padding.symmetric(vertical=12),
            border=ft.border.only(bottom=ft.BorderSide(1, theme.DIVIDER)),
        )

    provider_color = {
        "mock": theme.WARN, "netgsm": theme.SUCCESS,
        "generic_rest": theme.SUCCESS,
    }.get(config.SMS_PROVIDER, theme.TEXT_MUTED)

    general_card = theme.card(
        ft.Column(
            [
                theme.h3("Salon"),
                ft.Container(height=8),
                info_row("Salon Adı", config.SALON_NAME),
                info_row("Uygulama Sürümü", config.APP_VERSION),
            ],
            spacing=0,
        )
    )

    # --- Veri Depolama Kartı (kalıcılık güvencesi) ---
    stats = _db_stats()
    db_path = Path(config.DATABASE_PATH)
    size_kb = _db_size_kb()

    storage_card = theme.card(
        ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(ft.icons.SHIELD_OUTLINED, size=18,
                                color=theme.SUCCESS),
                        theme.h3("Veri Depolama"),
                    ],
                    spacing=8,
                ),
                ft.Container(height=8),
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(ft.icons.CHECK_CIRCLE_OUTLINE, size=16,
                                    color=theme.SUCCESS),
                            ft.Text(
                                "Verileriniz kalıcı olarak SQLite veritabanında "
                                "saklanıyor. Uygulamayı kapatıp açsanız da, "
                                "bilgisayarınızı kapatsanız da kayıtlar korunur.",
                                size=12, color=theme.TEXT, expand=True,
                                no_wrap=False,
                            ),
                        ],
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                    ),
                    padding=12, bgcolor=theme.SURFACE_ALT, border_radius=2,
                ),
                ft.Container(height=8),
                info_row("Müşteri Sayısı", f"{stats['customers']} kayıt"),
                info_row("Randevu Sayısı", f"{stats['appointments']} kayıt"),
                info_row("Personel Sayısı", f"{stats['staff']} kayıt"),
                info_row("SMS Geçmişi", f"{stats['sms_logs']} kayıt"),
                info_row("Veritabanı Boyutu", f"{size_kb} KB"),
                ft.Container(height=8),
                theme.caption("VERİTABANI DOSYASI"),
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(ft.icons.FOLDER_OUTLINED, size=14,
                                    color=theme.TEXT_MUTED),
                            ft.Text(
                                str(db_path), size=11, color=theme.TEXT_MUTED,
                                selectable=True, no_wrap=False, expand=True,
                            ),
                        ],
                        spacing=8,
                    ),
                    padding=12, bgcolor=theme.SURFACE_ALT, border_radius=2,
                ),
                ft.Container(height=4),
                theme.caption(
                    "Yedekleme önerisi: Bu dosyanın bir kopyasını periyodik olarak "
                    "iCloud / Time Machine gibi güvenli bir yere alın."
                ),
            ],
            spacing=0,
        )
    )

    sms_card = theme.card(
        ft.Column(
            [
                theme.h3("SMS Sağlayıcı"),
                ft.Container(height=8),
                info_row("Aktif Sağlayıcı", config.SMS_PROVIDER.upper(),
                         badge_color=provider_color),
                info_row(
                    "Netgsm Başlığı",
                    config.NETGSM_HEADER or "— (tanımsız)",
                ),
                info_row(
                    "Netgsm Kullanıcı",
                    "**** (tanımlı)" if config.NETGSM_USERCODE else "— (tanımsız)",
                ),
                ft.Container(
                    content=theme.caption(
                        "Bu değerleri proje kök dizinindeki .env dosyasından "
                        "yönetebilirsiniz. Değişiklik sonrası uygulamayı yeniden başlatın."
                    ),
                    padding=ft.padding.only(top=16),
                ),
            ],
            spacing=0,
        )
    )

    automation_rows: list[ft.Control] = [
        theme.h3("Otomasyon"),
        ft.Container(height=8),
        info_row(
            "Zamanlayıcı Durumu",
            "Çalışıyor" if scheduler and scheduler.running else "Durduruldu",
            badge_color=theme.SUCCESS if scheduler and scheduler.running else theme.ERROR,
        ),
        info_row("Hatırlatma Penceresi", f"{config.REMINDER_HOURS_BEFORE} saat önce"),
        info_row("Tarama Sıklığı",
                 f"{config.SCHEDULER_CHECK_INTERVAL_MINUTES} dakikada bir"),
        info_row("Doğum Günü Gönderim Saati",
                 f"{config.BIRTHDAY_SEND_HOUR:02d}:00"),
    ]
    if jobs_info:
        automation_rows.append(ft.Container(height=16))
        automation_rows.append(theme.caption("PLANLANMIŞ GÖREVLER"))
        for name, nxt in jobs_info:
            automation_rows.append(info_row(name, f"Sonraki: {nxt}"))

    automation_card = theme.card(ft.Column(automation_rows, spacing=0))

    header_block = ft.Container(
        content=ft.Column(
            [theme.caption("SİSTEM"), theme.h1("Ayarlar")],
            spacing=4,
        ),
        padding=ft.padding.only(bottom=28),
    )

    return ft.Column(
        [
            header_block,
            general_card,
            ft.Container(height=16),
            storage_card,
            ft.Container(height=16),
            sms_card,
            ft.Container(height=16),
            automation_card,
        ],
        scroll=ft.ScrollMode.AUTO, expand=True,
    )
