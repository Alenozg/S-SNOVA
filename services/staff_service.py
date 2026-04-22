"""
Personel servisi: CRUD + renk önerisi.
"""
import re
from typing import Optional

from database import fetch_all, fetch_one, execute
from models import Staff, suggest_next_color


HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


def _validate_color(color: str) -> str:
    color = (color or "").strip()
    if not HEX_COLOR_RE.match(color):
        raise ValueError(f"Gecerli bir #RRGGBB renk kodu girin. Aldim: '{color}'")
    return color.upper()


def list_staff(only_active: bool = False) -> list[Staff]:
    q = "SELECT * FROM staff"
    if only_active:
        q += " WHERE active = 1"
    q += " ORDER BY first_name, last_name"
    rows = fetch_all(q)
    return [Staff.from_row(r) for r in rows]


def get_staff(staff_id: int) -> Optional[Staff]:
    row = fetch_one("SELECT * FROM staff WHERE id = ?", (staff_id,))
    return Staff.from_row(row) if row else None


def suggest_color() -> str:
    """Henüz kullanılmamış bir renk döner (yeni personel ekleme formu için)."""
    used = [r["color"] for r in fetch_all("SELECT color FROM staff")]
    return suggest_next_color(used)


def create_staff(staff: Staff) -> int:
    if not staff.first_name.strip() or not staff.last_name.strip():
        raise ValueError("Ad ve soyad zorunlu.")
    staff.color = _validate_color(staff.color)
    return execute(
        """INSERT INTO staff
           (first_name, last_name, role, phone, email, color, active, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            staff.first_name.strip(),
            staff.last_name.strip(),
            (staff.role or "").strip(),
            (staff.phone or "").strip(),
            (staff.email or "").strip(),
            staff.color,
            1 if staff.active else 0,
            staff.notes or "",
        ),
    )


def update_staff(staff: Staff) -> None:
    if not staff.id:
        raise ValueError("Güncelleme için id gerekli.")
    if not staff.first_name.strip() or not staff.last_name.strip():
        raise ValueError("Ad ve soyad zorunlu.")
    staff.color = _validate_color(staff.color)
    execute(
        """UPDATE staff
           SET first_name = ?, last_name = ?, role = ?, phone = ?,
               email = ?, color = ?, active = ?, notes = ?
           WHERE id = ?""",
        (
            staff.first_name.strip(),
            staff.last_name.strip(),
            (staff.role or "").strip(),
            (staff.phone or "").strip(),
            (staff.email or "").strip(),
            staff.color,
            1 if staff.active else 0,
            staff.notes or "",
            staff.id,
        ),
    )


def delete_staff(staff_id: int) -> None:
    """
    Personeli siler. İlgili randevuların staff_id'si açıkça NULL'a düşer;
    randevular silinmez.

    Not: Yeni kurulumlarda ON DELETE SET NULL FK kısıtlaması bu işi
    otomatik yapar ama migration ile staff_id eklenmiş eski DB'lerde
    FK kısıtlaması olmayabilir. Bu nedenle güvenlik için manuel de yapıyoruz.
    """
    execute(
        "UPDATE appointments SET staff_id = NULL WHERE staff_id = ?",
        (staff_id,),
    )
    execute("DELETE FROM staff WHERE id = ?", (staff_id,))


def set_active(staff_id: int, active: bool) -> None:
    execute("UPDATE staff SET active = ? WHERE id = ?",
            (1 if active else 0, staff_id))


def appointment_count(staff_id: int) -> int:
    row = fetch_one(
        "SELECT COUNT(*) AS c FROM appointments WHERE staff_id = ?",
        (staff_id,),
    )
    return (row or {}).get("c", 0) or 0
