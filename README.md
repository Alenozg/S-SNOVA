# Sisnova Beauty — Güzellik Salonu Yönetim Sistemi

Flet + Python + SQLite üzerine kurulu, "quiet luxury" estetiğinde, SMS otomasyonlu bir CRM.

## Özellikler

### Müşteri Yönetimi
- Ad, soyad, telefon (+90 formatında), e-posta, cinsiyet, doğum tarihi, adres, notlar
- İYS onayı takibi
- Türkçe karakter duyarlı arama: "pelin" → PELİN, "seyda" → Şeyda
- CSV toleranslı import (50+ header alias, eksik telefonlu satırlar "geçersiz" işaretiyle kaydedilir)
- Toplu seçim + toplu SMS
- Müşteri profil modalı: avatar, toplam harcama, randevu istatistikleri, geçmiş

### Personel
- 12 renkli palette — her personel kendi rengiyle takvimde görünür
- Ad, soyad, rol, iletişim, aktiflik
- Silindiğinde randevular korunur (staff_id NULL olur)

### Hizmetler
- Hizmet adı, işlem süresi (dk), fiyat (₺)
- Randevuda hizmet seçince süre/fiyat otomatik dolar
- Duplicate kontrolü, aktif/pasif toggle

### Randevular — 3 Görünüm
1. **Haftalık Grid** (varsayılan): Saat × gün matrisi (09:00–20:00, 30dk)
   - Boş hücreye tıkla → yeni randevu (tarih/saat otomatik)
   - Dolu bloğa tıkla → detay modalı
   - Bloklar personel renginde, soft pastel
2. **Gün**: Personel sütunları
3. **Liste**: Kronolojik, filtrelenebilir

### Randevu Detay Modalı
- Müşteri + telefon, hizmet, personel, tutar
- Durum Dropdown: Yeni Randevu / Onaylandı / Tamamlandı / İptal Edildi / Gelmedi / Ertelendi
- Sil / Yeniden Planla / Kaydet

### SMS Otomasyonu
- Toplu kampanya (İYS onaylılara, `{name}` kişiselleştirme)
- 24 saat öncesi randevu hatırlatma (15dk tarama)
- Doğum günü kutlamaları (her sabah 10:00)
- Provider: Netgsm / Generic REST / Mock
- Türkçe karakterler otomatik Latin'e çevrilir

## Mimari

```
salon_crm/
├── main.py               # Giriş (masaüstü + web/Railway)
├── config.py             # APP_NAME="Sisnova Beauty"
├── Procfile              # Railway: web: python main.py
├── requirements.txt
├── database/
│   ├── schema.sql        # Idempotent migration'lı
│   └── db_manager.py
├── models/               # customer, staff, service, appointment
├── services/             # İş katmanı (UI'dan bağımsız)
└── ui/
    ├── theme.py
    ├── app.py            # Router
    ├── components/       # sidebar, searchable_customer_picker
    └── views/            # 9 sayfa
```

## Kurulum

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

İlk açılışta `salon.db` otomatik oluşur.

## Deployment

### Railway
`PORT` env otomatik algılanır, web modu devreye girer.

```bash
git push origin main
```

Veritabanı kalıcılığı için Railway Volumes veya PostgreSQL eklentisi gerekli.

### Masaüstü
```bash
python main.py
```

### Yerel web testi
```bash
FLET_MODE=web python main.py
```

## SMS Sağlayıcı

```env
# Mock (geliştirme)
SMS_PROVIDER=mock

# Netgsm
SMS_PROVIDER=netgsm
NETGSM_USERCODE=...
NETGSM_PASSWORD=...
NETGSM_HEADER=SISNOVA

# Generic REST
SMS_PROVIDER=generic_rest
GENERIC_SMS_URL=https://...
GENERIC_SMS_API_KEY=...
```

## Tasarım

**Renkler:**
- BG `#F5F2ED` / SURFACE `#FFFFFF`
- ACCENT `#A89078` (taş bronzu)
- SUCCESS `#7A8471` / ERROR `#9B6B5F`

**Tipografi:** Cormorant Garamond (display) + Inter (body)

## Lisans

Özel — Sisnova Beauty.
