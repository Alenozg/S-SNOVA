"""
Randevu veri modeli.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Appointment:
    id: Optional[int] = None
    customer_id: int = 0
    service_id: Optional[int] = None
    staff_id: Optional[int] = None
    appointment_at: Optional[datetime] = None
    status: str = "scheduled"        # scheduled / completed / cancelled / no_show
    reminder_sent: bool = False
    price: Optional[float] = None    # randevu tutarı (TL)
    completed_at: Optional[datetime] = None
    notes: str = ""

    # JOIN ile gelen alanlar (opsiyonel)
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    service_name: Optional[str] = None
    staff_name: Optional[str] = None
    staff_color: Optional[str] = None

    STATUS_LABELS = {
        "scheduled":   "Yeni Randevu",
        "confirmed":   "Onaylandı",
        "completed":   "Tamamlandı",
        "cancelled":   "İptal Edildi",
        "no_show":     "Gelmedi",
        "rescheduled": "Ertelendi",
    }

    @property
    def status_label(self) -> str:
        return self.STATUS_LABELS.get(self.status, self.status)

    @classmethod
    def from_row(cls, row: dict) -> "Appointment":
        if row is None:
            return None  # type: ignore

        at = row.get("appointment_at")
        if isinstance(at, str):
            try:
                at = datetime.fromisoformat(at)
            except ValueError:
                at = None

        ca = row.get("completed_at")
        if isinstance(ca, str) and ca:
            try:
                ca = datetime.fromisoformat(ca)
            except ValueError:
                ca = None

        price_val = row.get("price")
        try:
            price_val = float(price_val) if price_val is not None else None
        except (TypeError, ValueError):
            price_val = None

        return cls(
            id=row.get("id"),
            customer_id=row.get("customer_id", 0),
            service_id=row.get("service_id"),
            staff_id=row.get("staff_id"),
            appointment_at=at,
            status=row.get("status", "scheduled"),
            reminder_sent=bool(row.get("reminder_sent", 0)),
            price=price_val,
            completed_at=ca,
            notes=row.get("notes", "") or "",
            customer_name=row.get("customer_name"),
            customer_phone=row.get("customer_phone"),
            service_name=row.get("service_name"),
            staff_name=row.get("staff_name"),
            staff_color=row.get("staff_color"),
        )
