"""
Hizmet veri modeli.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class Service:
    id: Optional[int] = None
    name: str = ""
    duration_min: int = 30         # randevu takvimini ayarlamak için dakika cinsinden
    price: float = 0.0
    active: bool = True

    @property
    def display_price(self) -> str:
        if not self.price:
            return "—"
        # ₺1.500 gibi TR formatı
        formatted = f"{self.price:,.0f}".replace(",", ".")
        return f"₺{formatted}"

    @property
    def display_duration(self) -> str:
        if self.duration_min < 60:
            return f"{self.duration_min} dk"
        hours = self.duration_min // 60
        mins = self.duration_min % 60
        if mins == 0:
            return f"{hours} saat"
        return f"{hours} sa {mins} dk"

    @classmethod
    def from_row(cls, row: dict) -> "Service":
        if row is None:
            return None  # type: ignore
        return cls(
            id=row.get("id"),
            name=row.get("name", "") or "",
            duration_min=int(row.get("duration_min") or 30),
            price=float(row.get("price") or 0.0),
            active=bool(row.get("active", 1)),
        )
