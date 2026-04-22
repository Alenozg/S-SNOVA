"""
Hizmet (service) servisi: CRUD.
"""
from typing import Optional

from database import fetch_all, fetch_one, execute
from models import Service


def list_services(only_active: bool = False) -> list[Service]:
    q = "SELECT * FROM services"
    if only_active:
        q += " WHERE active = 1"
    q += " ORDER BY name COLLATE NOCASE"
    rows = fetch_all(q)
    return [Service.from_row(r) for r in rows]


def get_service(service_id: int) -> Optional[Service]:
    row = fetch_one("SELECT * FROM services WHERE id = ?", (service_id,))
    return Service.from_row(row) if row else None


def create_service(service: Service) -> int:
    name = (service.name or "").strip()
    if not name:
        raise ValueError("Hizmet adı zorunlu.")
    if service.duration_min <= 0:
        raise ValueError("İşlem süresi pozitif bir sayı olmalı.")
    if service.price < 0:
        raise ValueError("Fiyat negatif olamaz.")

    # Aynı isimli hizmet var mı?
    existing = fetch_one(
        "SELECT id FROM services WHERE LOWER(name) = LOWER(?)", (name,),
    )
    if existing:
        raise ValueError(f"'{name}' adında bir hizmet zaten kayıtlı.")

    return execute(
        """INSERT INTO services (name, duration_min, price, active)
           VALUES (?, ?, ?, ?)""",
        (
            name,
            int(service.duration_min),
            float(service.price),
            1 if service.active else 0,
        ),
    )


def update_service(service: Service) -> None:
    if not service.id:
        raise ValueError("Güncelleme için id gerekli.")
    name = (service.name or "").strip()
    if not name:
        raise ValueError("Hizmet adı zorunlu.")
    if service.duration_min <= 0:
        raise ValueError("İşlem süresi pozitif bir sayı olmalı.")
    if service.price < 0:
        raise ValueError("Fiyat negatif olamaz.")

    # Başka bir hizmette aynı isim var mı?
    dup = fetch_one(
        "SELECT id FROM services WHERE LOWER(name) = LOWER(?) AND id != ?",
        (name, service.id),
    )
    if dup:
        raise ValueError(f"'{name}' adında başka bir hizmet zaten var.")

    execute(
        """UPDATE services
           SET name = ?, duration_min = ?, price = ?, active = ?
           WHERE id = ?""",
        (
            name,
            int(service.duration_min),
            float(service.price),
            1 if service.active else 0,
            service.id,
        ),
    )


def delete_service(service_id: int) -> None:
    """
    Hizmeti siler. İlgili randevuların service_id'si NULL'a düşer.
    FK ON DELETE SET NULL olmasa bile manuel olarak NULL yapıyoruz.
    """
    execute(
        "UPDATE appointments SET service_id = NULL WHERE service_id = ?",
        (service_id,),
    )
    execute("DELETE FROM services WHERE id = ?", (service_id,))


def appointment_count(service_id: int) -> int:
    row = fetch_one(
        "SELECT COUNT(*) AS c FROM appointments WHERE service_id = ?",
        (service_id,),
    )
    return (row or {}).get("c", 0) or 0
