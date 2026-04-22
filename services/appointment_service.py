"""
Randevu servisi. JOIN'lu listeleme, tarih aralığı sorguları ve
hatırlatma için bekleyen randevuları döner.
"""
from datetime import datetime, timedelta
from typing import Optional

from database import fetch_all, fetch_one, execute
from models import Appointment


JOIN_QUERY = """
    SELECT a.*,
           c.first_name || ' ' || c.last_name AS customer_name,
           c.phone                             AS customer_phone,
           s.name                              AS service_name,
           st.first_name || ' ' || st.last_name AS staff_name,
           st.color                             AS staff_color
    FROM appointments a
    JOIN customers c ON c.id = a.customer_id
    LEFT JOIN services s  ON s.id  = a.service_id
    LEFT JOIN staff    st ON st.id = a.staff_id
"""


def list_services() -> list[dict]:
    return fetch_all("SELECT * FROM services WHERE active = 1 ORDER BY name")


def list_appointments(
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    status: Optional[str] = None,
    staff_id: Optional[int] = None,
) -> list[Appointment]:
    q = JOIN_QUERY + " WHERE 1=1"
    params: list = []
    if start:
        q += " AND a.appointment_at >= ?"
        params.append(start.isoformat())
    if end:
        q += " AND a.appointment_at <= ?"
        params.append(end.isoformat())
    if status:
        q += " AND a.status = ?"
        params.append(status)
    if staff_id is not None:
        q += " AND a.staff_id = ?"
        params.append(staff_id)

    q += " ORDER BY a.appointment_at ASC"
    rows = fetch_all(q, tuple(params))
    return [Appointment.from_row(r) for r in rows]


def get_appointment(appointment_id: int) -> Optional[Appointment]:
    row = fetch_one(JOIN_QUERY + " WHERE a.id = ?", (appointment_id,))
    return Appointment.from_row(row) if row else None


def create_appointment(appt: Appointment) -> int:
    return execute(
        """INSERT INTO appointments
           (customer_id, service_id, staff_id, appointment_at, status, price, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            appt.customer_id,
            appt.service_id,
            appt.staff_id,
            appt.appointment_at.isoformat() if appt.appointment_at else None,
            appt.status or "scheduled",
            appt.price,
            appt.notes or "",
        ),
    )


def update_appointment(appt: Appointment) -> None:
    execute(
        """UPDATE appointments
           SET customer_id = ?, service_id = ?, staff_id = ?,
               appointment_at = ?, status = ?, price = ?, notes = ?
           WHERE id = ?""",
        (
            appt.customer_id,
            appt.service_id,
            appt.staff_id,
            appt.appointment_at.isoformat() if appt.appointment_at else None,
            appt.status,
            appt.price,
            appt.notes or "",
            appt.id,
        ),
    )


def set_status(appointment_id: int, status: str) -> None:
    execute("UPDATE appointments SET status = ? WHERE id = ?", (status, appointment_id))


def delete_appointment(appointment_id: int) -> None:
    execute("DELETE FROM appointments WHERE id = ?", (appointment_id,))


def mark_reminder_sent(appointment_id: int) -> None:
    execute("UPDATE appointments SET reminder_sent = 1 WHERE id = ?", (appointment_id,))


def pending_reminders(hours_before: int = 24) -> list[Appointment]:
    """
    Randevu saatinden "hours_before" saat önceye gelmiş, henüz hatırlatma
    gönderilmemiş ve İYS onaylı müşterilere ait randevuları döner.

    Mantik: (now <= appointment_at <= now + hours_before) penceresinde
    reminder_sent = 0 olan planlı randevular.
    """
    now = datetime.now()
    until = now + timedelta(hours=hours_before)
    q = JOIN_QUERY + """
        WHERE a.reminder_sent = 0
          AND a.status = 'scheduled'
          AND c.iys_consent = 1
          AND a.appointment_at >= ?
          AND a.appointment_at <= ?
        ORDER BY a.appointment_at
    """
    rows = fetch_all(q, (now.isoformat(), until.isoformat()))
    return [Appointment.from_row(r) for r in rows]


def today_appointments() -> list[Appointment]:
    today = datetime.now().date()
    start = datetime.combine(today, datetime.min.time())
    end = datetime.combine(today, datetime.max.time())
    return list_appointments(start=start, end=end)


def customer_appointments(customer_id: int) -> list[Appointment]:
    """Müşterinin tüm randevuları - profil ekranındaki geçmiş tablosu için.
    En yeni randevu başta."""
    q = JOIN_QUERY + """
        WHERE a.customer_id = ?
        ORDER BY a.appointment_at DESC
    """
    rows = fetch_all(q, (customer_id,))
    return [Appointment.from_row(r) for r in rows]
