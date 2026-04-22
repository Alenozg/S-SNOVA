"""
Toplu içe/dışa aktarma (CSV).

Özellikler:
  - UTF-8, UTF-8-BOM, Windows-1254 (eski Türkçe Excel) otomatik algılar
  - Ayraç olarak hem virgül (,) hem noktalı virgül (;) destekler
  - Türkçe veya İngilizce başlık alias'ları (ad/first_name, soyad/last_name, ...)
  - Tarih formatları: 1990-05-17, 17.05.1990, 17/05/1990
  - İYS onayı: Evet/Hayır, Yes/No, 1/0, true/false
  - Yinelenen telefon: atla (skip) veya güncelle (update) modu
  - Her hatalı satır için satır numarası + sebep raporlar
  - macOS TCC izin koruması için geçici dizine kopyalama fallback'ı
"""
import csv
import io
import shutil
import tempfile
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from models import Customer
from services import customer_service


# Tanınan başlık adları → iç alan adları
HEADER_ALIASES = {
    "ad": "first_name",
    "adi": "first_name",
    "adı": "first_name",
    "isim": "first_name",
    "first_name": "first_name",
    "first name": "first_name",
    "firstname": "first_name",
    "name": "first_name",

    "soyad": "last_name",
    "soyadi": "last_name",
    "soyadı": "last_name",
    "last_name": "last_name",
    "last name": "last_name",
    "lastname": "last_name",
    "surname": "last_name",

    "telefon": "phone",
    "telefon no": "phone",
    "telefon numarasi": "phone",
    "telefon numarası": "phone",
    "tel": "phone",
    "tel no": "phone",
    "cep": "phone",
    "cep tel": "phone",
    "cep telefonu": "phone",
    "gsm": "phone",
    "gsm no": "phone",
    "phone": "phone",
    "phone_number": "phone",
    "phone number": "phone",
    "phonenumber": "phone",
    "mobile": "phone",
    "mobile_phone": "phone",
    "mobile phone": "phone",
    "mobil": "phone",
    "number": "phone",
    "no": "phone",

    "dogum_tarihi": "birth_date",
    "doğum_tarihi": "birth_date",
    "doğum tarihi": "birth_date",
    "dogum tarihi": "birth_date",
    "dogum": "birth_date",
    "doğum": "birth_date",
    "dogumgunu": "birth_date",
    "doğum günü": "birth_date",
    "dogum gunu": "birth_date",
    "birth_date": "birth_date",
    "birth date": "birth_date",
    "birthday": "birth_date",
    "birthdate": "birth_date",
    "dob": "birth_date",

    "iys_onay": "iys_consent",
    "iys onay": "iys_consent",
    "iys onayi": "iys_consent",
    "iys onayı": "iys_consent",
    "iys": "iys_consent",
    "iys_consent": "iys_consent",
    "consent": "iys_consent",
    "izin": "iys_consent",
    "sms izni": "iys_consent",
    "sms_izni": "iys_consent",

    "notlar": "notes",
    "not": "notes",
    "aciklama": "notes",
    "açıklama": "notes",
    "notes": "notes",
    "note": "notes",
    "comment": "notes",
    "comments": "notes",
    "yorum": "notes",
}


# Bu sütunlar tanıdık ama DB'de ayrı alanımız yok.
# Veri kaybolmasın diye "notes" alanına birleştireceğiz.
EXTRA_COLUMNS_TO_NOTES = {
    "email": "E-posta",
    "eposta": "E-posta",
    "e-posta": "E-posta",
    "mail": "E-posta",
    "e-mail": "E-posta",

    "address": "Adres",
    "adres": "Adres",

    "city": "Şehir",
    "sehir": "Şehir",
    "şehir": "Şehir",
    "il": "Şehir",

    "postal_code": "Posta kodu",
    "postal code": "Posta kodu",
    "postcode": "Posta kodu",
    "posta_kodu": "Posta kodu",
    "posta kodu": "Posta kodu",
    "zipcode": "Posta kodu",
    "zip": "Posta kodu",

    "ilce": "İlçe",
    "ilçe": "İlçe",
    "district": "İlçe",

    "meslek": "Meslek",
    "occupation": "Meslek",
    "job": "Meslek",
    "profession": "Meslek",

    "cinsiyet": "Cinsiyet",
    "gender": "Cinsiyet",
    "sex": "Cinsiyet",
}


@dataclass
class ImportResult:
    added: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[tuple[int, str]] = field(default_factory=list)  # (satir_no, mesaj)

    @property
    def total(self) -> int:
        return self.added + self.updated + self.skipped + len(self.errors)

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0


# -----------------------------------------------------------
# Yardımcılar
# -----------------------------------------------------------
def _decode(raw: bytes) -> str:
    """Birden çok kodlama deneyerek metne çevir."""
    for enc in ("utf-8-sig", "utf-8", "cp1254", "iso-8859-9", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    raise ValueError("Dosya kodlaması çözümlenemedi.")


def _detect_delimiter(sample: str) -> str:
    try:
        dialect = csv.Sniffer().sniff(sample[:2048], delimiters=",;\t|")
        return dialect.delimiter
    except csv.Error:
        # Fallback: noktalı virgül mü virgül mü, hangisi daha çok geçiyorsa
        return ";" if sample.count(";") > sample.count(",") else ","


def _normalize_header(h: str) -> Optional[str]:
    key = (h or "").strip().lower().replace("\ufeff", "")
    return HEADER_ALIASES.get(key)


def _parse_date(value: str) -> Optional[date]:
    if not value or not value.strip():
        return None
    s = value.strip()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise ValueError(
        f"Tarih formati anlasilamadi: '{s}' "
        f"(beklenen: 1990-05-17 veya 17.05.1990)"
    )


def _parse_iys(value: str) -> bool:
    if not value:
        return False
    v = value.strip().lower()
    return v in ("evet", "e", "yes", "y", "1", "true", "var", "dogru", "doğru", "x", "✓")


def _read_bytes_safely(path: Path) -> bytes:
    """
    Dosyayı doğrudan okumayı dener; izin hatası (macOS TCC koruması)
    alırsa dosyayı geçici bir dizine kopyalayıp oradan okur. Kopyalama
    da başarısız olursa kullanıcıya net bir mesajla hatayı yükseltir.

    macOS Catalina ve sonrasında Terminal'den çalıştırılan Python, kullanıcı
    ilgili izinleri vermediği sürece Downloads / Desktop / Documents gibi
    korunan klasörlerden doğrudan okuyamaz — [Errno 1] Operation not
    permitted hatası verir. shutil.copy2 ise çoğu durumda bu izin
    kapısından geçebildiği için güvenilir bir fallback'tir.
    """
    try:
        return path.read_bytes()
    except PermissionError:
        pass   # fallback'e düş

    # Geçici dizine kopyalayıp oradan oku
    try:
        with tempfile.TemporaryDirectory(prefix="salon_crm_import_") as tmpdir:
            tmp_file = Path(tmpdir) / path.name
            shutil.copy2(path, tmp_file)
            return tmp_file.read_bytes()
    except PermissionError as e:
        raise PermissionError(
            "macOS bu dosyaya erisim izni vermiyor "
            f"({path.parent}). Cozumler:\n\n"
            "1) Dosyayi Ev klasorunde (~/) yeni bir klasore tasiyin, "
            "orn. ~/salon_import/musteriler.csv\n"
            "2) Sistem Ayarlari -> Gizlilik ve Guvenlik -> "
            "Dosyalar ve Klasorler -> Terminal (veya Python) icin "
            "Downloads/Masaustu erisimini acin ve uygulamayi yeniden baslatin.\n"
            "3) Tam Disk Erisimi: Sistem Ayarlari -> Gizlilik ve Guvenlik -> "
            "Tam Disk Erisimi -> + -> Terminal."
        ) from e


def _read_csv(path: Path) -> tuple[list[str], list[dict]]:
    raw = _read_bytes_safely(path)
    text = _decode(raw)
    delim = _detect_delimiter(text)
    reader = csv.DictReader(io.StringIO(text), delimiter=delim)
    headers = reader.fieldnames or []
    rows = [row for row in reader]
    return headers, rows


# -----------------------------------------------------------
# Public API
# -----------------------------------------------------------
def import_customers_from_csv(
    path: str | Path,
    *,
    duplicate_mode: str = "skip",   # "skip" | "update"
) -> ImportResult:
    """
    CSV'den toplu müşteri içe aktarır.

    duplicate_mode:
      - "skip":   aynı telefonlu kayıt varsa atlar
      - "update": aynı telefonlu kaydı günceller
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(str(path))

    headers, rows = _read_csv(path)

    if not rows:
        raise ValueError("CSV dosyasi bos.")

    # Başlık haritalama:
    #  - known_mapping: bilinen sütunlar (ad, soyad, ...) -> iç alan adları
    #  - extra_mapping: DB'de alanı olmayan ama tanıdık sütunlar (email, adres,...)
    #                   -> notes alanına etiketli olarak eklenecek
    known_mapping: dict[str, str] = {}
    extra_mapping: dict[str, str] = {}   # original_header -> etiket (ör. "E-posta")

    for h in headers:
        norm = _normalize_header(h)
        if norm:
            known_mapping[h] = norm
            continue

        # Ekstra sütun mu? (email, adres, şehir, vb.)
        key = (h or "").strip().lower().replace("\ufeff", "")
        if key in EXTRA_COLUMNS_TO_NOTES:
            extra_mapping[h] = EXTRA_COLUMNS_TO_NOTES[key]
        # Tanınmayan sütunlar sessizce yok sayılır (hata atmaz)

    # Zorunlu alanlar
    found = set(known_mapping.values())
    required = {"first_name", "last_name", "phone"}
    missing = required - found
    if missing:
        missing_tr = {
            "first_name": "ad",
            "last_name": "soyad",
            "phone": "telefon",
        }
        missing_labels = [missing_tr[m] for m in missing]
        raise ValueError(
            f"Eksik zorunlu sütun(lar): {', '.join(missing_labels)}. "
            f"Bulunan sütunlar: {', '.join(headers)}"
        )

    result = ImportResult()

    for i, row in enumerate(rows, start=2):  # satir 1 = başlık
        try:
            data: dict[str, str] = {}
            for original, field_name in known_mapping.items():
                data[field_name] = (row.get(original) or "").strip()

            # Ekstra sütunları notes içine derle: "E-posta: x | Adres: y | Şehir: z"
            extras_parts: list[str] = []
            for original, label in extra_mapping.items():
                val = (row.get(original) or "").strip()
                if val:
                    extras_parts.append(f"{label}: {val}")

            base_notes = data.get("notes", "").strip()
            combined_notes = base_notes
            if extras_parts:
                extras_str = " | ".join(extras_parts)
                combined_notes = (
                    f"{base_notes} | {extras_str}" if base_notes else extras_str
                )

            # Doğum tarihi: başarısızsa sessizce None (notes'a not olarak ekleyebiliriz)
            birth_date = None
            raw_birth = data.get("birth_date", "")
            if raw_birth:
                try:
                    birth_date = _parse_date(raw_birth)
                except ValueError:
                    combined_notes = (
                        f"{combined_notes} | Doğum tarihi bozuk: {raw_birth}"
                        if combined_notes
                        else f"Doğum tarihi bozuk: {raw_birth}"
                    )

            iys = _parse_iys(data.get("iys_consent", ""))

            # Telefonu normalize et (hatalıysa boş bırak, tolerant create edilir)
            phone_raw = data.get("phone", "")
            phone_normalized = ""
            if phone_raw:
                try:
                    phone_normalized = Customer.normalize_phone(phone_raw)
                except ValueError:
                    # Normalize edilemedi - tolerant akışa gir (aşağıda)
                    phone_normalized = ""

            # Yinelenme kontrolü yalnızca telefon normalize edilebildiğinde anlamlı
            existing = (
                customer_service.get_by_phone(phone_normalized)
                if phone_normalized else None
            )

            # ---- Yinelenen: mevcut kuralları koru (skip / update) ----
            if existing:
                if duplicate_mode == "update":
                    customer = Customer(
                        id=existing.id,
                        first_name=data.get("first_name") or existing.first_name,
                        last_name=data.get("last_name") or existing.last_name,
                        phone=phone_normalized,
                        birth_date=birth_date or existing.birth_date,
                        iys_consent=iys,
                        notes=combined_notes or existing.notes,
                    )
                    customer_service.update_customer(customer)
                    result.updated += 1
                else:
                    result.skipped += 1
                continue

            # ---- Yeni kayıt: tolerant mod — eksik veriyi kabul et, is_valid=0 yap ----
            _, row_errors = customer_service.create_customer_tolerant(
                first_name=data.get("first_name", ""),
                last_name=data.get("last_name", ""),
                phone_raw=phone_raw,           # normalize edilmemiş ham değer
                birth_date=birth_date,
                iys_consent=iys,
                notes=combined_notes,
            )
            if row_errors:
                # Hata olarak da listele - özet ekranında gösterilsin
                result.errors.append((i, "; ".join(row_errors) + " (kaydedildi)"))
                result.added += 1   # DB'ye girdi, kullanıcı listede görecek
            else:
                result.added += 1

        except Exception as e:
            # Gerçek beklenmedik hata (ör. DB bağlantısı kopması) - loglanır, kayıt atlanır
            result.errors.append((i, f"İşlenemedi: {e}"))

    return result


def export_customers_to_csv(
    path: str | Path,
    *,
    only_iys: bool = False,
) -> int:
    """Tüm müşterileri CSV'ye yazar; yazılan kayıt sayısını döner."""
    path = Path(path)
    customers = customer_service.list_customers(only_iys=only_iys)

    # utf-8-sig → Excel'in BOM görüp Türkçe karakterleri doğru açmasını sağlar
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f, delimiter=",")
        writer.writerow(
            ["ad", "soyad", "telefon", "dogum_tarihi", "iys_onay", "notlar"]
        )
        for c in customers:
            writer.writerow([
                c.first_name,
                c.last_name,
                c.phone,  # 905XXXXXXXXX normalize hali
                c.birth_date.isoformat() if c.birth_date else "",
                "Evet" if c.iys_consent else "Hayır",
                c.notes or "",
            ])
    return len(customers)




def import_customers_from_bytes(
    raw: bytes,
    filename: str = "import.csv",
    *,
    duplicate_mode: str = "skip",
) -> "ImportResult":
    """Web modunda FilePicker bytes'ından CSV içe aktar."""
    text = _decode(raw)
    delim = _detect_delimiter(text)
    import csv as _csv, io as _io
    reader = _csv.DictReader(_io.StringIO(text), delimiter=delim)
    headers = list(reader.fieldnames or [])
    rows = list(reader)

    if not rows:
        raise ValueError("CSV dosyası boş.")

    known_mapping: dict[str, str] = {}
    extra_mapping: dict[str, str] = {}
    for h in headers:
        norm = _normalize_header(h)
        if norm:
            known_mapping[h] = norm
            continue
        key = (h or "").strip().lower().replace("\ufeff", "")
        if key in EXTRA_COLUMNS_TO_NOTES:
            extra_mapping[h] = EXTRA_COLUMNS_TO_NOTES[key]

    found = set(known_mapping.values())
    required = {"first_name", "last_name", "phone"}
    missing = required - found
    if missing:
        missing_tr = {"first_name": "ad", "last_name": "soyad", "phone": "telefon"}
        raise ValueError(
            f"Eksik zorunlu sütun(lar): {', '.join(missing_tr[m] for m in missing)}. "
            f"Bulunan sütunlar: {', '.join(headers)}"
        )

    from models import Customer
    from services import customer_service as _cs
    result = ImportResult()

    for i, row in enumerate(rows, start=2):
        try:
            data: dict[str, str] = {}
            for original, field_name in known_mapping.items():
                data[field_name] = (row.get(original) or "").strip()

            extras_parts = []
            for original, label in extra_mapping.items():
                val = (row.get(original) or "").strip()
                if val:
                    extras_parts.append(f"{label}: {val}")

            base_notes = data.get("notes", "").strip()
            combined_notes = base_notes
            if extras_parts:
                extras_str = " | ".join(extras_parts)
                combined_notes = f"{base_notes} | {extras_str}" if base_notes else extras_str

            birth_date = None
            raw_birth = data.get("birth_date", "")
            if raw_birth:
                try:
                    birth_date = _parse_date(raw_birth)
                except ValueError:
                    combined_notes = (
                        f"{combined_notes} | Doğum tarihi bozuk: {raw_birth}"
                        if combined_notes else f"Doğum tarihi bozuk: {raw_birth}"
                    )

            iys = _parse_iys(data.get("iys_consent", ""))
            phone_raw = data.get("phone", "")
            phone_normalized = ""
            if phone_raw:
                try:
                    phone_normalized = Customer.normalize_phone(phone_raw)
                except ValueError:
                    phone_normalized = ""

            existing = _cs.get_by_phone(phone_normalized) if phone_normalized else None

            if existing:
                if duplicate_mode == "update":
                    customer = Customer(
                        id=existing.id,
                        first_name=data.get("first_name") or existing.first_name,
                        last_name=data.get("last_name") or existing.last_name,
                        phone=phone_normalized,
                        birth_date=birth_date or existing.birth_date,
                        iys_consent=iys,
                        notes=combined_notes or existing.notes,
                    )
                    _cs.update_customer(customer)
                    result.updated += 1
                else:
                    result.skipped += 1
                continue

            _, row_errors = _cs.create_customer_tolerant(
                first_name=data.get("first_name", ""),
                last_name=data.get("last_name", ""),
                phone_raw=phone_raw,
                birth_date=birth_date,
                iys_consent=iys,
                notes=combined_notes,
            )
            if row_errors:
                result.errors.append((i, "; ".join(row_errors) + " (kaydedildi)"))
            result.added += 1
        except Exception as e:
            result.errors.append((i, f"İşlenemedi: {e}"))

    return result


def generate_template_csv(path: str | Path) -> None:
    """Örnek satırlı şablon CSV oluştur."""
    path = Path(path)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f, delimiter=",")
        writer.writerow(
            ["ad", "soyad", "telefon", "dogum_tarihi", "iys_onay", "notlar"]
        )
        writer.writerow(
            ["Ayşe", "Yılmaz", "05321234567", "1990-05-17", "Evet", "VIP"]
        )
        writer.writerow(
            ["Zeynep", "Kaya", "+90 533 222 33 44", "15.06.1985", "Hayır", ""]
        )
        writer.writerow(
            ["Elif", "Demir", "05344445566", "", "Hayır", "İlk ziyaret"]
        )
