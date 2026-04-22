"""
Müşteri veri modeli.
İş kurallarını (telefon formatlama, yaş hesabı) burada tutar.
"""
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional
import re


@dataclass
class Customer:
    id: Optional[int] = None
    first_name: str = ""
    last_name: str = ""
    phone: str = ""                       # 905XXXXXXXXX; eksik/hatalıysa boş ""
    email: str = ""
    gender: str = ""                      # 'kadin' / 'erkek' / '' (belirtilmemiş)
    birth_date: Optional[date] = None
    iys_consent: bool = False
    iys_consent_date: Optional[datetime] = None
    notes: str = ""
    is_valid: bool = True                 # False = eksik/hatalı kayıt
    validation_errors: str = ""           # ör. "Telefon eksik; Tarih hatalı"
    created_at: Optional[datetime] = None

    # ----------------------------- yardımcılar

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def display_phone(self) -> str:
        """+90 (5XX) XXX XX XX biçiminde görünüm için."""
        p = self.phone or ""
        if not p:
            return "—"
        if len(p) == 12 and p.startswith("90"):
            return f"+90 ({p[2:5]}) {p[5:8]} {p[8:10]} {p[10:12]}"
        return p

    @property
    def age(self) -> Optional[int]:
        if not self.birth_date:
            return None
        today = date.today()
        return today.year - self.birth_date.year - (
            (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
        )

    @property
    def gender_label(self) -> str:
        return {"kadin": "Kadın", "erkek": "Erkek"}.get(self.gender, "—")

    # ----------------------------- fabrika / doğrulama

    @staticmethod
    def normalize_phone(raw: str) -> str:
        """
        Türk cep numaralarını 905XXXXXXXXX formatına getirir.
        Geçersizse ValueError atar.
        """
        digits = re.sub(r"\D", "", raw or "")
        if digits.startswith("0"):
            digits = digits[1:]
        if digits.startswith("90"):
            digits = digits[2:]
        if len(digits) != 10 or not digits.startswith("5"):
            raise ValueError("Gecerli bir Turkiye cep numarasi girin (5XX XXX XX XX).")
        return "90" + digits

    @classmethod
    def from_row(cls, row: dict) -> "Customer":
        """DB satırını modele çevirir."""
        if row is None:
            return None  # type: ignore

        bd = row.get("birth_date")
        if isinstance(bd, str) and bd:
            try:
                bd = date.fromisoformat(bd)
            except ValueError:
                bd = None

        icd = row.get("iys_consent_date")
        if isinstance(icd, str) and icd:
            try:
                icd = datetime.fromisoformat(icd)
            except ValueError:
                icd = None

        ca = row.get("created_at")
        if isinstance(ca, str) and ca:
            try:
                ca = datetime.fromisoformat(ca)
            except ValueError:
                ca = None

        return cls(
            id=row.get("id"),
            first_name=row.get("first_name", "") or "",
            last_name=row.get("last_name", "") or "",
            phone=row.get("phone") or "",
            email=row.get("email") or "",
            gender=row.get("gender") or "",
            birth_date=bd,
            iys_consent=bool(row.get("iys_consent", 0)),
            iys_consent_date=icd,
            notes=row.get("notes", "") or "",
            is_valid=bool(row.get("is_valid", 1)) if row.get("is_valid") is not None else True,
            validation_errors=row.get("validation_errors") or "",
            created_at=ca,
        )
