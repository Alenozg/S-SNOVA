"""
Veritabanı yönetimi — SQLite (lokal) veya PostgreSQL (Railway/üretim).

Railway'de DATABASE_URL env var varsa → PostgreSQL kullanır.
Yoksa → SQLite kullanır.
"""
import os
import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

# PostgreSQL URL var mı?
_PG_URL = os.getenv("DATABASE_URL", "").strip()
_USE_PG  = bool(_PG_URL and not _PG_URL.startswith("sqlite"))

if _USE_PG:
    log.info("Veritabani modu: PostgreSQL")
else:
    log.info("Veritabani modu: SQLite")


# ──────────────────────────────────────────────────────────────────
#  PostgreSQL adaptoru
# ──────────────────────────────────────────────────────────────────
if _USE_PG:
    import psycopg2
    import psycopg2.extras

    def _pg_connect():
        url = _PG_URL
        # Railway bazen "postgres://" verir, psycopg2 "postgresql://" ister
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://"):]
        conn = psycopg2.connect(url, cursor_factory=psycopg2.extras.RealDictCursor)
        conn.autocommit = False
        return conn

    def get_connection():
        return _pg_connect()

    @contextmanager
    def db_cursor(commit: bool = False):
        conn = _pg_connect()
        try:
            cur = conn.cursor()
            yield cur
            if commit:
                conn.commit()
            else:
                conn.rollback()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _adapt_sql(sql: str) -> str:
        """SQLite ? → PostgreSQL %s placeholder dönüşümü."""
        import re
        return re.sub(r'\?', '%s', sql)

    def fetch_all(query: str, params: tuple = ()) -> list[dict]:
        with db_cursor() as cur:
            cur.execute(_adapt_sql(query), params)
            rows = cur.fetchall()
            return [dict(r) for r in rows]

    def fetch_one(query: str, params: tuple = ()) -> Optional[dict]:
        with db_cursor() as cur:
            cur.execute(_adapt_sql(query), params)
            row = cur.fetchone()
            return dict(row) if row else None

    def execute(query: str, params: tuple = ()) -> int:
        """INSERT/UPDATE/DELETE. Son eklenen ID'yi veya etkilenen satır sayısını döner."""
        with db_cursor(commit=True) as cur:
            # PostgreSQL'de RETURNING ile lastrowid elde et
            sql = _adapt_sql(query)
            if sql.strip().upper().startswith("INSERT") and "RETURNING" not in sql.upper():
                sql = sql.rstrip().rstrip(";") + " RETURNING id"
                cur.execute(sql, params)
                row = cur.fetchone()
                return dict(row)["id"] if row else 0
            cur.execute(sql, params)
            return cur.rowcount

    def init_database() -> None:
        """PostgreSQL şemasını oluştur."""
        _pg_init()

    def _pg_init():
        conn = _pg_connect()
        try:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS customers (
                    id              SERIAL PRIMARY KEY,
                    first_name      TEXT NOT NULL,
                    last_name       TEXT NOT NULL,
                    phone           TEXT UNIQUE,
                    email           TEXT,
                    gender          TEXT,
                    birth_date      DATE,
                    iys_consent     INTEGER DEFAULT 0,
                    iys_consent_date TIMESTAMP,
                    notes           TEXT,
                    is_valid        INTEGER DEFAULT 1,
                    validation_errors TEXT,
                    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_customers_phone ON customers(phone);
                CREATE INDEX IF NOT EXISTS idx_customers_birth ON customers(birth_date);
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS staff (
                    id         SERIAL PRIMARY KEY,
                    first_name TEXT NOT NULL,
                    last_name  TEXT NOT NULL,
                    role       TEXT DEFAULT '',
                    phone      TEXT,
                    email      TEXT,
                    color      TEXT NOT NULL DEFAULT '#A89078',
                    active     INTEGER DEFAULT 1,
                    notes      TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS services (
                    id           SERIAL PRIMARY KEY,
                    name         TEXT NOT NULL UNIQUE,
                    duration_min INTEGER DEFAULT 30,
                    price        REAL DEFAULT 0,
                    active       INTEGER DEFAULT 1
                );
                INSERT INTO services (name, duration_min, price)
                VALUES
                    ('Lazer Epilasyon', 60, 500),
                    ('Cilt Bakimi', 75, 750),
                    ('Manikur', 45, 250),
                    ('Pedikur', 60, 300),
                    ('Kas Sekillendirme', 30, 150)
                ON CONFLICT (name) DO NOTHING;
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS appointments (
                    id             SERIAL PRIMARY KEY,
                    customer_id    INTEGER NOT NULL,
                    service_id     INTEGER,
                    staff_id       INTEGER,
                    appointment_at TIMESTAMP NOT NULL,
                    status         TEXT DEFAULT 'scheduled',
                    reminder_sent  INTEGER DEFAULT 0,
                    price          REAL,
                    completed_at   TIMESTAMP,
                    notes          TEXT,
                    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_appointments_at ON appointments(appointment_at);
                CREATE INDEX IF NOT EXISTS idx_appointments_status ON appointments(status);
                CREATE INDEX IF NOT EXISTS idx_appointments_staff ON appointments(staff_id);
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS sms_campaigns (
                    id           SERIAL PRIMARY KEY,
                    name         TEXT NOT NULL,
                    message      TEXT NOT NULL,
                    status       TEXT DEFAULT 'draft',
                    target_count INTEGER DEFAULT 0,
                    sent_count   INTEGER DEFAULT 0,
                    failed_count INTEGER DEFAULT 0,
                    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    sent_at      TIMESTAMP
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS sms_logs (
                    id                SERIAL PRIMARY KEY,
                    customer_id       INTEGER,
                    campaign_id       INTEGER,
                    appointment_id    INTEGER,
                    phone             TEXT NOT NULL,
                    message           TEXT NOT NULL,
                    sms_type          TEXT NOT NULL,
                    status            TEXT DEFAULT 'pending',
                    provider_response TEXT,
                    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_logs_type ON sms_logs(sms_type);
                CREATE INDEX IF NOT EXISTS idx_logs_date ON sms_logs(created_at);
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id            SERIAL PRIMARY KEY,
                    email         TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    full_name     TEXT NOT NULL,
                    role          TEXT DEFAULT 'user',
                    is_active     INTEGER DEFAULT 1,
                    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login    TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

                CREATE TABLE IF NOT EXISTS app_settings (
                    key        TEXT PRIMARY KEY,
                    value      TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                INSERT INTO app_settings (key, value)
                VALUES (
                    'reminder_template',
                    'Merhaba {name}, yarin {date} saat {time} randevunuzu hatirlatmak isteriz. Gorusmek uzere. {salon}'
                )
                ON CONFLICT (key) DO NOTHING;
            """)
            conn.commit()
            log.info("PostgreSQL şeması hazır.")
        except Exception as e:
            conn.rollback()
            log.error("PostgreSQL şema hatası: %s", e)
            raise
        finally:
            conn.close()

# ──────────────────────────────────────────────────────────────────
#  SQLite adaptoru (lokal)
# ──────────────────────────────────────────────────────────────────
else:
    import sqlite3
    import config

    def _dict_factory(cursor, row):
        return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

    def get_connection():
        conn = sqlite3.connect(
            str(config.DATABASE_PATH),
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
            check_same_thread=False,
        )
        conn.row_factory = _dict_factory
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = DELETE;")
        conn.execute("PRAGMA synchronous = FULL;")
        return conn

    @contextmanager
    def db_cursor(commit: bool = False):
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

    def fetch_all(query: str, params: tuple = ()) -> list[dict]:
        with db_cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall()

    def fetch_one(query: str, params: tuple = ()) -> Optional[dict]:
        with db_cursor() as cur:
            cur.execute(query, params)
            return cur.fetchone()

    def execute(query: str, params: tuple = ()) -> int:
        with db_cursor(commit=True) as cur:
            cur.execute(query, params)
            return cur.lastrowid or cur.rowcount

    def init_database() -> None:
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

    def _run_migrations(conn) -> None:
        cur = conn.cursor()
        # appointments.staff_id
        cur.execute("PRAGMA table_info(appointments)")
        cols = {r["name"] for r in cur.fetchall()}
        if "staff_id" not in cols:
            cur.execute("ALTER TABLE appointments ADD COLUMN staff_id INTEGER")
            conn.commit()
        cur.execute("CREATE INDEX IF NOT EXISTS idx_appointments_staff ON appointments(staff_id)")
        conn.commit()
        # customers.is_valid
        cur.execute("PRAGMA table_info(customers)")
        cnames = {r["name"] for r in cur.fetchall()}
        if "is_valid" not in cnames:
            cur.execute("ALTER TABLE customers ADD COLUMN is_valid INTEGER DEFAULT 1")
            conn.commit()
        if "validation_errors" not in cnames:
            cur.execute("ALTER TABLE customers ADD COLUMN validation_errors TEXT")
            conn.commit()
        if "email" not in cnames:
            cur.execute("ALTER TABLE customers ADD COLUMN email TEXT")
            conn.commit()
        if "gender" not in cnames:
            cur.execute("ALTER TABLE customers ADD COLUMN gender TEXT")
            conn.commit()
        # appointments.price + completed_at
        cur.execute("PRAGMA table_info(appointments)")
        anames = {r["name"] for r in cur.fetchall()}
        if "price" not in anames:
            cur.execute("ALTER TABLE appointments ADD COLUMN price REAL")
            conn.commit()
        if "completed_at" not in anames:
            cur.execute("ALTER TABLE appointments ADD COLUMN completed_at DATETIME")
            conn.commit()
        # users tablosu
        cur.execute("""CREATE TABLE IF NOT EXISTS users (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            email           TEXT NOT NULL UNIQUE,
            password_hash   TEXT NOT NULL,
            full_name       TEXT NOT NULL,
            role            TEXT DEFAULT 'user',
            is_active       INTEGER DEFAULT 1,
            created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_login      DATETIME
        )""")
        conn.commit()
        cur.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
        conn.commit()
        # app_settings key-value tablosu (mesaj şablonları vb.)
        cur.execute("""CREATE TABLE IF NOT EXISTS app_settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.commit()
        # Varsayılan hatırlatma şablonunu ekle (yoksa)
        cur.execute("""INSERT OR IGNORE INTO app_settings (key, value) VALUES (
            'reminder_template',
            'Merhaba {name}, yarin {time} saat {time} randevunuzu hatirlatmak isteriz. Gorusmek uzere. {salon}'
        )""")
        conn.commit()


# ── app_settings yardımcıları ────────────────────────────────────────────────
def get_setting(key: str, default: str = "") -> str:
    """Ayar değerini döner; yoksa default."""
    # execute() wrapper'ını atla: doğrudan cursor kullan
    try:
        with db_cursor() as cur:
            if _USE_PG:
                cur.execute("SELECT value FROM app_settings WHERE key=%s", (key,))
            else:
                cur.execute("SELECT value FROM app_settings WHERE key=?", (key,))
            row = cur.fetchone()
            if row:
                return dict(row).get("value", default)
    except Exception as e:
        log.warning("get_setting hata (%s): %s", key, e)
    return default


def set_setting(key: str, value: str) -> None:
    """Ayarı ekler veya günceller (SQLite ve PostgreSQL uyumlu)."""
    # execute() wrapper RETURNING id ekler; app_settings'te id yok → direkt cursor
    try:
        with db_cursor(commit=True) as cur:
            if _USE_PG:
                cur.execute(
                    """INSERT INTO app_settings (key, value, updated_at)
                       VALUES (%s, %s, CURRENT_TIMESTAMP)
                       ON CONFLICT (key) DO UPDATE
                       SET value = EXCLUDED.value,
                           updated_at = CURRENT_TIMESTAMP""",
                    (key, value),
                )
            else:
                cur.execute(
                    """INSERT OR REPLACE INTO app_settings (key, value, updated_at)
                       VALUES (?, ?, CURRENT_TIMESTAMP)""",
                    (key, value),
                )
    except Exception as e:
        log.error("set_setting hata (%s): %s", key, e)
        raise
