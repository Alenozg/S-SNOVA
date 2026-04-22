"""
SQLite bağlantı yönetimi.
Tek bir bağlantı havuzu gibi davranır; row_factory ile dict benzeri satır döner.
PostgreSQL'e geçerken sadece bu dosyayı değiştirmek yeterli olur.
"""
import sqlite3
from contextlib import contextmanager
from pathlib import Path
import config


def _dict_factory(cursor, row):
    """Satırları dict olarak dönmek için factory."""
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


def get_connection() -> sqlite3.Connection:
    """Yeni bir bağlantı döner. Her iş parçacığı kendi bağlantısını almalı."""
    conn = sqlite3.connect(
        str(config.DATABASE_PATH),
        detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
        check_same_thread=False,
    )
    conn.row_factory = _dict_factory
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn


@contextmanager
def db_cursor(commit: bool = False):
    """
    Context manager: otomatik açıp kapatan cursor.

    Örnek:
        with db_cursor(commit=True) as cur:
            cur.execute("INSERT INTO customers ...")
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        yield cur
        if commit:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _run_migrations(conn: sqlite3.Connection) -> None:
    """
    Mevcut DB'leri yeni şemayla uyumlu hale getirir.
    Her migration idempotent olmalı.
    """
    cur = conn.cursor()

    # --- Migration #1: appointments.staff_id (v1.0 -> v1.1) ---
    cur.execute("PRAGMA table_info(appointments)")
    cols = {row["name"] for row in cur.fetchall()}
    if "staff_id" not in cols:
        cur.execute("ALTER TABLE appointments ADD COLUMN staff_id INTEGER")
        conn.commit()
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_appointments_staff "
        "ON appointments(staff_id)"
    )
    conn.commit()

    # --- Migration #2: customers tablosu esnetmesi (v1.1 -> v1.2) ---
    # Yeni alanlar: is_valid (geçerlilik bayrağı), validation_errors (hatalı alan notu)
    # Ayrıca phone kolonundaki NOT NULL kısıtlaması kaldırılmalı (SQLite'ta bunu
    # yapmanın tek yolu tabloyu yeniden oluşturmak).
    cur.execute("PRAGMA table_info(customers)")
    customer_cols = cur.fetchall()
    customer_col_names = {row["name"] for row in customer_cols}

    # Önce yeni kolonları ekle (varsa dokunma)
    if "is_valid" not in customer_col_names:
        cur.execute("ALTER TABLE customers ADD COLUMN is_valid INTEGER DEFAULT 1")
        conn.commit()
    if "validation_errors" not in customer_col_names:
        cur.execute("ALTER TABLE customers ADD COLUMN validation_errors TEXT")
        conn.commit()

    # Phone kısıtlamasını esnet: NOT NULL varsa tabloyu yeniden oluştur
    phone_row = next((r for r in customer_cols if r["name"] == "phone"), None)
    if phone_row and phone_row.get("notnull") == 1:
        # SQLite'ta kolon kısıtlaması kaldırmanın güvenli yolu:
        # 1) Yeni tablo oluştur
        # 2) Veriyi kopyala
        # 3) Eski tabloyu drop et
        # 4) Yeniden adlandır
        cur.execute("PRAGMA foreign_keys = OFF")
        try:
            cur.executescript("""
                CREATE TABLE customers_new (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    first_name      TEXT NOT NULL,
                    last_name       TEXT NOT NULL,
                    phone           TEXT UNIQUE,
                    birth_date      DATE,
                    iys_consent     INTEGER DEFAULT 0,
                    iys_consent_date DATETIME,
                    notes           TEXT,
                    is_valid        INTEGER DEFAULT 1,
                    validation_errors TEXT,
                    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
                );

                INSERT INTO customers_new
                    (id, first_name, last_name, phone, birth_date,
                     iys_consent, iys_consent_date, notes,
                     is_valid, validation_errors, created_at, updated_at)
                SELECT
                    id, first_name, last_name, phone, birth_date,
                    iys_consent, iys_consent_date, notes,
                    COALESCE(is_valid, 1), validation_errors, created_at, updated_at
                FROM customers;

                DROP TABLE customers;
                ALTER TABLE customers_new RENAME TO customers;

                CREATE INDEX IF NOT EXISTS idx_customers_phone ON customers(phone);
                CREATE INDEX IF NOT EXISTS idx_customers_birth ON customers(birth_date);
            """)
            conn.commit()
        finally:
            cur.execute("PRAGMA foreign_keys = ON")
        conn.commit()

    # is_valid üzerinde index (hatalı kayıtları hızlı filtrelemek için)
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_customers_valid ON customers(is_valid)"
    )
    conn.commit()

    # --- Migration #3: customers.email + customers.gender (v1.2 -> v1.3) ---
    # Profil ekranı için e-posta ve cinsiyet alanları
    cur.execute("PRAGMA table_info(customers)")
    customer_col_names = {row["name"] for row in cur.fetchall()}
    if "email" not in customer_col_names:
        cur.execute("ALTER TABLE customers ADD COLUMN email TEXT")
        conn.commit()
    if "gender" not in customer_col_names:
        cur.execute("ALTER TABLE customers ADD COLUMN gender TEXT")
        conn.commit()

    # --- Migration #4: appointments.price + appointments.completed_at (v1.2 -> v1.3) ---
    # Müşteri profil ekranında toplam harcama hesabı için
    cur.execute("PRAGMA table_info(appointments)")
    appt_col_names = {row["name"] for row in cur.fetchall()}
    if "price" not in appt_col_names:
        cur.execute("ALTER TABLE appointments ADD COLUMN price REAL")
        conn.commit()
    if "completed_at" not in appt_col_names:
        cur.execute("ALTER TABLE appointments ADD COLUMN completed_at DATETIME")
        conn.commit()


def init_database() -> None:
    """Şemayı yükler + migration'ları çalıştırır."""
    schema_path = Path(__file__).parent / "schema.sql"
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    conn = get_connection()
    try:
        conn.executescript(schema_sql)
        conn.commit()
        _run_migrations(conn)
    finally:
        conn.close()


def fetch_all(query: str, params: tuple = ()) -> list[dict]:
    with db_cursor() as cur:
        cur.execute(query, params)
        return cur.fetchall()


def fetch_one(query: str, params: tuple = ()) -> dict | None:
    with db_cursor() as cur:
        cur.execute(query, params)
        return cur.fetchone()


def execute(query: str, params: tuple = ()) -> int:
    """INSERT/UPDATE/DELETE için; etkilenen satır sayısını veya son id'yi döner."""
    with db_cursor(commit=True) as cur:
        cur.execute(query, params)
        return cur.lastrowid or cur.rowcount
