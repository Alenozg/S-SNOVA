"""
Personel veri modeli.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


# Önceden seçilmiş "quiet luxury" palet — birbirinden ayırt edilebilir ama mat
# Yeni personel eklerken listedeki bir sonraki kullanılmayan renk otomatik önerilir.
STAFF_COLOR_PALETTE = [
    "#A89078",  # taş bronzu
    "#7A8471",  # adaçayı
    "#9B6B5F",  # kiremit
    "#8E95A6",  # buzlu mavi
    "#B9A88E",  # krem bej
    "#6B7A8A",  # çelik mavi
    "#A07A7A",  # pudra
    "#7D7B6B",  # zeytin
    "#93867A",  # çakıl
    "#5F6B7A",  # gece mavisi
    "#C2A878",  # altın yulaf
    "#6E8278",  # okaliptüs
]


def suggest_next_color(used_colors: list[str]) -> str:
    """Paletten henüz kullanılmamış ilk rengi döner; hepsi kullanılmışsa
    başa döner."""
    used = {c.lower() for c in used_colors if c}
    for c in STAFF_COLOR_PALETTE:
        if c.lower() not in used:
            return c
    # Hepsi kullanıldıysa paletin ilkine döner
    return STAFF_COLOR_PALETTE[0]


@dataclass
class Staff:
    id: Optional[int] = None
    first_name: str = ""
    last_name: str = ""
    role: str = ""
    phone: str = ""
    email: str = ""
    color: str = "#A89078"
    active: bool = True
    notes: str = ""
    created_at: Optional[datetime] = None

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def initials(self) -> str:
        a = (self.first_name or " ")[0].upper()
        b = (self.last_name or " ")[0].upper()
        return (a + b).strip()

    @classmethod
    def from_row(cls, row: dict) -> "Staff":
        if row is None:
            return None  # type: ignore
        ca = row.get("created_at")
        if isinstance(ca, str) and ca:
            try:
                ca = datetime.fromisoformat(ca)
            except ValueError:
                ca = None
        return cls(
            id=row.get("id"),
            first_name=row.get("first_name", ""),
            last_name=row.get("last_name", ""),
            role=row.get("role", "") or "",
            phone=row.get("phone", "") or "",
            email=row.get("email", "") or "",
            color=row.get("color") or "#A89078",
            active=bool(row.get("active", 1)),
            notes=row.get("notes", "") or "",
            created_at=ca,
        )
