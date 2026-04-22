"""
Müşteri servisi: CRUD ve sorgular.
UI doğrudan DB'ye değil, bu katmana konuşur.
"""
from datetime import date, datetime
from typing import Optional

from database import fetch_all, fetch_one, execute
from models import Customer


def _tr_casefold(s: str) -> str:
    """
    Türkçe'ye duyarlı ve aksan-toleranslı normalizasyon.

    Amaç: Türkçe klavyesi olmayan veya yorgun tuşlayan kullanıcılar için
    "yilmaz" yazsa da "YILMAZ", "çakır" yazsa da "cakir", "şeyda" yazsa da
    "seyda" bulsun. Yani hem küçük/büyük farkı ortadan kalksın hem de
    Türkçe aksanlı harfler ASCII karşılıklarıyla eşleştirilsin.

    Örnekler:
      "PELİN"  -> "pelin"
      "Pelın"  -> "pelin"
      "YILMAZ" -> "yilmaz"
      "Çakır"  -> "cakir"
      "Şeyda"  -> "seyda"
    """
    if not s:
        return ""

    # Önce Türkçe i/İ/I/ı ikilemini çöz (casefold bunu Unicode-doğru yapar değil)
    # "İ" -> "i" (normal küçük i), "I" -> "ı"
    s = s.replace("İ", "i").replace("I", "ı")
    s = s.lower()  # lower() bu aşamada kalan harfleri indirger

    # Türkçe aksanlıları ASCII karşılıklarına indirge
    translation = str.maketrans({
        "ı": "i",   # noktasız ı -> i
        "ş": "s",
        "ç": "c",
        "ğ": "g",
        "ö": "o",
        "ü": "u",
    })
    return s.translate(translation)


def list_customers(
    search: str = "",
    only_iys: bool = False,
    only_invalid: bool = False,
) -> list[Customer]:
    # Önce tüm eşleşme kaybını önlemek için SQL'de geniş bir ön-filtre uygula
    # (sadece iys/invalid/telefon içerenler), sonra Python tarafında
    # Türkçe duyarsız arama yap.
    query = "SELECT * FROM customers WHERE 1=1"
    params: list = []

    if only_iys:
        query += " AND iys_consent = 1"

    if only_invalid:
        query += " AND (is_valid = 0 OR is_valid IS NULL)"

    # Hatalı kayıtlar önce çıksın, kullanıcı hemen görsün
    from database.db_manager import _USE_PG as _pg
    if _pg:
        query += " ORDER BY is_valid ASC, LOWER(first_name), LOWER(last_name)"
    else:
        query += " ORDER BY is_valid ASC, first_name COLLATE NOCASE, last_name COLLATE NOCASE"
    rows = fetch_all(query, tuple(params))
    customers = [Customer.from_row(r) for r in rows]

    # Arama varsa Python tarafında Türkçe duyarsız filtrele
    # - Ad, soyad, "ad soyad", telefon, e-posta alanlarında ara
    # - "pelin" yazınca "PELİN", "Pelin", "pelın" hepsini bulur
    if search and search.strip():
        needle = _tr_casefold(search.strip())
        def matches(c: Customer) -> bool:
            haystack = " ".join([
                _tr_casefold(c.first_name),
                _tr_casefold(c.last_name),
                _tr_casefold(c.full_name),
                (c.phone or "").lower(),
                _tr_casefold(c.email or ""),
            ])
            return needle in haystack
        customers = [c for c in customers if matches(c)]

    return customers


def count_invalid() -> int:
    """Eksik/hatalı kayıt sayısı."""
    row = fetch_one(
        "SELECT COUNT(*) AS c FROM customers WHERE is_valid = 0 OR is_valid IS NULL"
    )
    return (row or {}).get("c") or 0


def get_customer(customer_id: int) -> Optional[Customer]:
    row = fetch_one("SELECT * FROM customers WHERE id = ?", (customer_id,))
    return Customer.from_row(row) if row else None


def get_by_phone(phone: str) -> Optional[Customer]:
    row = fetch_one("SELECT * FROM customers WHERE phone = ?", (phone,))
    return Customer.from_row(row) if row else None


def create_customer(customer: Customer) -> int:
    """Sıkı mod: telefon zorunlu, doğrulanabilir olmalı."""
    customer.phone = Customer.normalize_phone(customer.phone)
    if get_by_phone(customer.phone):
        raise ValueError("Bu telefon numarasi zaten kayitli.")
    return _insert_customer(customer)


def create_customer_tolerant(
    first_name: str,
    last_name: str,
    phone_raw: str = "",
    birth_date: Optional[date] = None,
    iys_consent: bool = False,
    notes: str = "",
) -> tuple[int, list[str]]:
    """
    Esnek mod: eksik/hatalı alanlar varsa kaydı yine oluşturur ama
    is_valid=0 ve validation_errors ile işaretler.
    CSV içe aktarma için kullanılır.

    Döner: (yeni_id, hata_listesi)
    """
    errors: list[str] = []

    # Ad / soyad zorunlu (bunlar olmadan kayıt anlamsız)
    first_name = (first_name or "").strip()
    last_name = (last_name or "").strip()
    if not first_name:
        errors.append("Ad eksik")
    if not last_name:
        errors.append("Soyad eksik")

    # Telefon tolere et: boşsa kaydet, geçersizse hata listele ama yine kaydet
    phone_normalized: Optional[str] = None
    phone_raw = (phone_raw or "").strip()
    if not phone_raw:
        errors.append("Telefon eksik")
    else:
        try:
            phone_normalized = Customer.normalize_phone(phone_raw)
        except ValueError:
            errors.append(f"Telefon hatalı ({phone_raw})")

    # Telefon çakışması varsa yine kaydet ama yinelenen olarak işaretle
    if phone_normalized and get_by_phone(phone_normalized):
        errors.append("Telefon zaten kayıtlı")
        # UNIQUE kısıtlamasını tetiklememek için yineleneni None yapıyoruz;
        # kullanıcı düzenlerken çakışan kaydı değiştirebilir.
        phone_normalized = None

    # Ad/soyad da boşsa placeholder koy (DB NOT NULL'ları tatmin etsin)
    if not first_name:
        first_name = "(Ad eksik)"
    if not last_name:
        last_name = "(Soyad eksik)"

    customer = Customer(
        first_name=first_name,
        last_name=last_name,
        phone=phone_normalized or "",
        birth_date=birth_date,
        iys_consent=iys_consent,
        notes=notes,
        is_valid=(len(errors) == 0),
        validation_errors="; ".join(errors),
    )
    new_id = _insert_customer(customer)
    return new_id, errors


def _insert_customer(customer: Customer) -> int:
    """Düşük seviye insert — doğrulama yapmaz."""
    iys_date = datetime.now().isoformat() if customer.iys_consent else None
    return execute(
        """INSERT INTO customers
           (first_name, last_name, phone, email, gender, birth_date,
            iys_consent, iys_consent_date, notes, is_valid, validation_errors)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            customer.first_name.strip(),
            customer.last_name.strip(),
            customer.phone or None,          # boş string yerine NULL (UNIQUE'i ihlal etmemesi için)
            (customer.email or "").strip() or None,
            (customer.gender or "").strip() or None,
            customer.birth_date.isoformat() if customer.birth_date else None,
            1 if customer.iys_consent else 0,
            iys_date,
            customer.notes or "",
            1 if customer.is_valid else 0,
            customer.validation_errors or None,
        ),
    )


def update_customer(customer: Customer) -> None:
    if not customer.id:
        raise ValueError("Güncelleme için id gerekli.")

    # Telefon doğrulaması - düzenleme formunda hata olarak gösterilir
    phone_to_save: Optional[str] = None
    phone_raw = (customer.phone or "").strip()
    validation_errors: list[str] = []

    if phone_raw:
        try:
            phone_to_save = Customer.normalize_phone(phone_raw)
        except ValueError:
            raise   # UI tarafında kullanıcıya gösterilir
    else:
        validation_errors.append("Telefon eksik")

    # Çakışma kontrolü
    if phone_to_save:
        other = get_by_phone(phone_to_save)
        if other and other.id != customer.id:
            raise ValueError("Bu telefon numarası başka bir müşteride kayıtlı.")

    # İYS onayı yeni verildiyse tarih set et
    existing = get_customer(customer.id)
    iys_date = existing.iys_consent_date if existing else None
    if customer.iys_consent and not (existing and existing.iys_consent):
        iys_date = datetime.now()

    # is_valid durumunu otomatik hesapla:
    # - telefon var ve doğrulandıysa VE ad/soyad placeholder değilse -> geçerli
    is_now_valid = (
        phone_to_save is not None
        and customer.first_name.strip() not in ("", "(Ad eksik)")
        and customer.last_name.strip() not in ("", "(Soyad eksik)")
    )

    execute(
        """UPDATE customers
           SET first_name = ?, last_name = ?, phone = ?, email = ?, gender = ?,
               birth_date = ?, iys_consent = ?, iys_consent_date = ?,
               notes = ?, is_valid = ?, validation_errors = ?,
               updated_at = CURRENT_TIMESTAMP
           WHERE id = ?""",
        (
            customer.first_name.strip(),
            customer.last_name.strip(),
            phone_to_save,
            (customer.email or "").strip() or None,
            (customer.gender or "").strip() or None,
            customer.birth_date.isoformat() if customer.birth_date else None,
            1 if customer.iys_consent else 0,
            iys_date.isoformat() if iys_date else None,
            customer.notes or "",
            1 if is_now_valid else 0,
            "; ".join(validation_errors) if validation_errors else None,
            customer.id,
        ),
    )


def delete_customer(customer_id: int) -> None:
    execute("DELETE FROM customers WHERE id = ?", (customer_id,))


def get_birthday_customers(today: Optional[date] = None) -> list[Customer]:
    """Bugün doğum günü olan, İYS onayı olan müşteriler."""
    from database.db_manager import _USE_PG
    today = today or date.today()
    month_day = f"{today.month:02d}-{today.day:02d}"
    if _USE_PG:
        rows = fetch_all(
            """SELECT * FROM customers
               WHERE iys_consent = 1
                 AND birth_date IS NOT NULL
                 AND TO_CHAR(birth_date, 'MM-DD') = %s""",
            (month_day,),
        )
    else:
        rows = fetch_all(
            """SELECT * FROM customers
               WHERE iys_consent = 1
                 AND birth_date IS NOT NULL
                 AND strftime('%m-%d', birth_date) = ?""",
            (month_day,),
        )
    return [Customer.from_row(r) for r in rows]


def stats() -> dict:
    row = fetch_one(
        """SELECT
             COUNT(*) AS total,
             SUM(iys_consent)              AS iys_count,
             SUM(CASE WHEN birth_date IS NOT NULL THEN 1 ELSE 0 END) AS with_birthday
           FROM customers"""
    ) or {}
    return {
        "total": row.get("total") or 0,
        "iys": row.get("iys_count") or 0,
        "with_birthday": row.get("with_birthday") or 0,
    }


def customer_stats(customer_id: int) -> dict:
    """
    Bir müşteri için profil ekranında gösterilecek istatistikler.

    Döner:
      {
        "total_spent": float,     # tamamlanmış randevuların price toplamı (TL)
        "total_appts": int,
        "completed":  int,
        "scheduled":  int,
        "cancelled":  int,
        "no_show":    int,
      }
    """
    row = fetch_one(
        """SELECT
             COUNT(*)                                            AS total_appts,
             SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END)  AS completed,
             SUM(CASE WHEN status = 'scheduled' THEN 1 ELSE 0 END)  AS scheduled,
             SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END)  AS cancelled,
             SUM(CASE WHEN status = 'no_show'   THEN 1 ELSE 0 END)  AS no_show,
             COALESCE(SUM(CASE WHEN status = 'completed' THEN price END), 0) AS total_spent
           FROM appointments
           WHERE customer_id = ?""",
        (customer_id,),
    ) or {}
    return {
        "total_appts": row.get("total_appts") or 0,
        "completed":   row.get("completed") or 0,
        "scheduled":   row.get("scheduled") or 0,
        "cancelled":   row.get("cancelled") or 0,
        "no_show":     row.get("no_show") or 0,
        "total_spent": float(row.get("total_spent") or 0),
    }
