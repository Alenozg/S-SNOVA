-- ============================================
-- Salon CRM Veritabanı Şeması (SQLite)
-- PostgreSQL'e taşımada sadece AUTOINCREMENT ve
-- DATETIME tiplerini ayarlamanız yeterlidir.
-- ============================================

PRAGMA foreign_keys = ON;

-- Müşteriler
-- Müşteriler
-- NOT: Eksik/hatalı CSV satırlarını da tolere edebilmek için:
--   - phone: NULL olabilir (UNIQUE ama NULL değerler ihlal saymaz)
--   - is_valid: 0 = eksik/hatalı, arayüzde kırmızı vurgulanır
--   - validation_errors: hangi alanların sorunlu olduğunu serbest metin olarak saklar
CREATE TABLE IF NOT EXISTS customers (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name      TEXT NOT NULL,
    last_name       TEXT NOT NULL,
    phone           TEXT UNIQUE,                 -- 905XXXXXXXXX; NULL olabilir
    email           TEXT,
    gender          TEXT,                        -- 'kadin' / 'erkek' / 'belirtilmemis'
    birth_date      DATE,
    iys_consent     INTEGER DEFAULT 0,
    iys_consent_date DATETIME,
    notes           TEXT,
    is_valid        INTEGER DEFAULT 1,           -- 0 = eksik/hatalı kayıt
    validation_errors TEXT,                      -- ör. "Telefon eksik; Tarih bozuk"
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_customers_phone ON customers(phone);
CREATE INDEX IF NOT EXISTS idx_customers_birth ON customers(birth_date);

-- Personel
CREATE TABLE IF NOT EXISTS staff (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name      TEXT NOT NULL,
    last_name       TEXT NOT NULL,
    role            TEXT DEFAULT '',            -- ör. Estetisyen, Güzellik Uzmanı
    phone           TEXT,
    email           TEXT,
    color           TEXT NOT NULL,              -- #RRGGBB - takvimde görünecek renk
    active          INTEGER DEFAULT 1,
    notes           TEXT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_staff_active ON staff(active);

-- Hizmetler (salonda sunulan işlemler)
CREATE TABLE IF NOT EXISTS services (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL UNIQUE,
    duration_min    INTEGER DEFAULT 30,
    price           REAL DEFAULT 0,
    active          INTEGER DEFAULT 1
);

-- Randevular
CREATE TABLE IF NOT EXISTS appointments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id     INTEGER NOT NULL,
    service_id      INTEGER,
    staff_id        INTEGER,                    -- randevuyu alacak personel
    appointment_at  DATETIME NOT NULL,          -- ISO 8601: 2026-05-01 14:30:00
    status          TEXT DEFAULT 'scheduled',   -- scheduled / completed / cancelled / no_show
    reminder_sent   INTEGER DEFAULT 0,          -- 0 = gönderilmedi, 1 = gönderildi
    price           REAL,                       -- randevu tutarı (TL) — harcama hesabı için
    completed_at    DATETIME,                   -- tamamlanma zamanı
    notes           TEXT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    FOREIGN KEY (service_id)  REFERENCES services(id)  ON DELETE SET NULL,
    FOREIGN KEY (staff_id)    REFERENCES staff(id)     ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_appointments_at     ON appointments(appointment_at);
CREATE INDEX IF NOT EXISTS idx_appointments_status ON appointments(status);
-- idx_appointments_staff migration'da oluşturuluyor (eski DB'lerde staff_id kolonu yok)

-- Kampanyalar (toplu SMS)
CREATE TABLE IF NOT EXISTS sms_campaigns (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    message         TEXT NOT NULL,
    status          TEXT DEFAULT 'draft',       -- draft / sent
    target_count    INTEGER DEFAULT 0,
    sent_count      INTEGER DEFAULT 0,
    failed_count    INTEGER DEFAULT 0,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    sent_at         DATETIME
);

-- SMS Günlüğü (gönderilen her mesaj)
CREATE TABLE IF NOT EXISTS sms_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id     INTEGER,
    campaign_id     INTEGER,
    appointment_id  INTEGER,
    phone           TEXT NOT NULL,
    message         TEXT NOT NULL,
    sms_type        TEXT NOT NULL,              -- campaign / reminder / birthday
    status          TEXT DEFAULT 'pending',     -- pending / sent / failed
    provider_response TEXT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id)    REFERENCES customers(id)     ON DELETE SET NULL,
    FOREIGN KEY (campaign_id)    REFERENCES sms_campaigns(id) ON DELETE SET NULL,
    FOREIGN KEY (appointment_id) REFERENCES appointments(id)  ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_logs_type ON sms_logs(sms_type);
CREATE INDEX IF NOT EXISTS idx_logs_date ON sms_logs(created_at);

-- Başlangıç verisi: temel hizmetler
INSERT OR IGNORE INTO services (name, duration_min, price) VALUES
    ('Lazer Epilasyon',  60, 500),
    ('Cilt Bakimi',      75, 750),
    ('Manikur',          45, 250),
    ('Pedikur',          60, 300),
    ('Kas Sekillendirme',30, 150);
