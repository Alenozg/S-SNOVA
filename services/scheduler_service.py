"""
Arka plan zamanlayıcı (APScheduler BackgroundScheduler).

İki iş:
  1) remind_upcoming_appointments — her N dakikada bir çalışır,
     24 saat içindeki randevulara hatırlatma SMS'i atar.
  2) send_birthday_messages — her sabah belirlenen saatte çalışır,
     o gün doğum günü olan İYS onaylı müşterilere SMS atar.

Uygulama kapanırken shutdown() çağrılmalı.
"""
import logging
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

import config
from services import sms_service
from services import customer_service
from services import appointment_service

log = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


# -----------------------------------------------------------
# İşler (jobs)
# -----------------------------------------------------------
def remind_upcoming_appointments() -> None:
    """Hatırlatma gönderilmemiş, 24 saat içindeki randevular için SMS at."""
    try:
        pending = appointment_service.pending_reminders(
            hours_before=config.REMINDER_HOURS_BEFORE
        )
        if not pending:
            return

        log.info("Hatirlatma: %d randevu bulundu.", len(pending))
        # Önce DB'den şablon oku; yoksa config'e düş
        from database.db_manager import get_setting
        _db_tpl = get_setting("reminder_template", "")
        template = _db_tpl if _db_tpl.strip() else config.MESSAGE_TEMPLATES["appointment_reminder"]

        for appt in pending:
            when = appt.appointment_at
            msg = template.format(
                name=(appt.customer_name or "").split(" ")[0],
                date=when.strftime("%d.%m.%Y") if when else "",
                time=when.strftime("%H:%M") if when else "",
                service=appt.service_name or "",
                salon=config.SALON_NAME,
            )
            result = sms_service.send_sms(
                phone=appt.customer_phone or "",
                message=msg,
                customer_id=appt.customer_id,
                appointment_id=appt.id,
                sms_type="reminder",
            )
            if result.success:
                appointment_service.mark_reminder_sent(appt.id)
    except Exception as e:
        log.exception("Hatirlatma isi sirasinda hata: %s", e)


def send_birthday_messages() -> None:
    """Bugün doğum günü olan İYS onaylı müşterilere kutlama gönder."""
    try:
        customers = customer_service.get_birthday_customers()
        if not customers:
            return

        log.info("Dogum gunu: %d musteri bulundu.", len(customers))
        from database.db_manager import get_setting
        _db_bday = get_setting("birthday_template", "")
        template = _db_bday if _db_bday.strip() else config.MESSAGE_TEMPLATES["birthday"]

        for c in customers:
            msg = template.format(name=c.first_name, salon=config.SALON_NAME)
            sms_service.send_sms(
                phone=c.phone,
                message=msg,
                customer_id=c.id,
                sms_type="birthday",
            )
    except Exception as e:
        log.exception("Dogum gunu isi sirasinda hata: %s", e)


# -----------------------------------------------------------
# Scheduler yönetimi
# -----------------------------------------------------------
def start() -> BackgroundScheduler:
    """Zamanlayıcıyı başlatır (idempotent)."""
    global _scheduler
    if _scheduler and _scheduler.running:
        return _scheduler

    scheduler = BackgroundScheduler(timezone="Europe/Istanbul")

    scheduler.add_job(
        remind_upcoming_appointments,
        trigger=IntervalTrigger(
            minutes=config.SCHEDULER_CHECK_INTERVAL_MINUTES
        ),
        id="appointment_reminders",
        name="Randevu hatirlatma tarayicisi",
        replace_existing=True,
        next_run_time=datetime.now(),   # açılışta hemen bir kez tara
    )

    scheduler.add_job(
        send_birthday_messages,
        trigger=CronTrigger(hour=config.BIRTHDAY_SEND_HOUR, minute=0),
        id="birthday_greetings",
        name="Dogum gunu kutlamalari",
        replace_existing=True,
    )

    scheduler.start()
    _scheduler = scheduler
    log.info("Scheduler baslatildi.")
    return scheduler


def shutdown() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        log.info("Scheduler durduruldu.")
        _scheduler = None


def get_scheduler() -> BackgroundScheduler | None:
    return _scheduler
