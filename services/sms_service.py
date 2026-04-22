"""
SMS Servisi.

Provider (Strategy) pattern kullanir. Netgsm, jenerik REST sağlayıcı veya
sahte (mock) sağlayıcıya aynı arayüzden erişilir; config.SMS_PROVIDER ile
kontrol edilir. Yeni sağlayıcı eklemek = yeni sınıf yazmak + factory'ye eklemek.
"""
from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

import requests

import config
from database import execute

log = logging.getLogger(__name__)


# -----------------------------------------------------------
# Veri yapıları
# -----------------------------------------------------------
@dataclass
class SmsResult:
    success: bool
    provider_response: str = ""


# -----------------------------------------------------------
# Soyut arayüz
# -----------------------------------------------------------
class SmsProvider(ABC):
    @abstractmethod
    def send(self, phone: str, message: str) -> SmsResult: ...


# -----------------------------------------------------------
# Mock (geliştirme)
# -----------------------------------------------------------
class MockProvider(SmsProvider):
    """Gerçek SMS göndermez; konsola log yazar."""

    def send(self, phone: str, message: str) -> SmsResult:
        log.info("[MOCK SMS] -> %s : %s", phone, message)
        return SmsResult(success=True, provider_response="mock_ok")


# -----------------------------------------------------------
# Netgsm
# -----------------------------------------------------------
class NetgsmProvider(SmsProvider):
    """
    Netgsm get/xml API entegrasyonu.
    Dokümantasyon: https://www.netgsm.com.tr/dokuman/
    """

    ENDPOINT = "https://api.netgsm.com.tr/sms/send/get"

    def __init__(self) -> None:
        self.usercode = config.NETGSM_USERCODE
        self.password = config.NETGSM_PASSWORD
        self.header = config.NETGSM_HEADER

    def send(self, phone: str, message: str) -> SmsResult:
        if not (self.usercode and self.password and self.header):
            return SmsResult(False, "Netgsm bilgileri tanımlı değil.")

        params = {
            "usercode": self.usercode,
            "password": self.password,
            "gsmno": phone,
            "message": message,
            "msgheader": self.header,
        }
        try:
            r = requests.get(self.ENDPOINT, params=params, timeout=15)
            text = r.text.strip()
            # Netgsm başarıda "00 <bulk_id>" döner; diğer kodlar hata.
            success = text.split(" ", 1)[0] == "00"
            return SmsResult(success, text)
        except requests.RequestException as e:
            return SmsResult(False, f"network_error: {e}")


# -----------------------------------------------------------
# Generic REST (örn. İletimerkezi, Mutlucell veya self-hosted API)
# -----------------------------------------------------------
class GenericRestProvider(SmsProvider):
    """
    Basit JSON REST sağlayıcı; sağlayıcıya göre payload'u uyarlayın.
    """

    def send(self, phone: str, message: str) -> SmsResult:
        if not config.GENERIC_SMS_URL:
            return SmsResult(False, "GENERIC_SMS_URL tanımlı değil.")

        payload = {
            "sender": config.GENERIC_SMS_SENDER,
            "phone": phone,
            "message": message,
        }
        headers = {"Authorization": f"Bearer {config.GENERIC_SMS_API_KEY}"}
        try:
            r = requests.post(
                config.GENERIC_SMS_URL, json=payload, headers=headers, timeout=15
            )
            return SmsResult(r.ok, f"{r.status_code}:{r.text[:200]}")
        except requests.RequestException as e:
            return SmsResult(False, f"network_error: {e}")


# -----------------------------------------------------------
# Factory
# -----------------------------------------------------------
def _build_provider() -> SmsProvider:
    name = (config.SMS_PROVIDER or "mock").lower()
    if name == "netgsm":
        return NetgsmProvider()
    if name == "generic_rest":
        return GenericRestProvider()
    return MockProvider()


_provider: SmsProvider = _build_provider()


# -----------------------------------------------------------
# Public API (UI ve scheduler buraları çağırır)
# -----------------------------------------------------------
GSM_LATIN_MAP = str.maketrans({
    "ç": "c", "Ç": "C", "ğ": "g", "Ğ": "G",
    "ı": "i", "İ": "I", "ö": "o", "Ö": "O",
    "ş": "s", "Ş": "S", "ü": "u", "Ü": "U",
})


def sanitize_message(text: str) -> str:
    """
    Türkçe karakterleri Latin'e çevirir. Çoğu SMS sağlayıcısında
    Türkçe karakter 1 SMS karakteri = 70'e düşer, bu yüzden genellikle
    maliyet için sanitize edilir. Normal GSM set seçilirse 160 karakter hakkı olur.
    """
    return (text or "").translate(GSM_LATIN_MAP)


def send_sms(
    phone: str,
    message: str,
    *,
    customer_id: Optional[int] = None,
    campaign_id: Optional[int] = None,
    appointment_id: Optional[int] = None,
    sms_type: str = "campaign",
    sanitize: bool = True,
) -> SmsResult:
    """
    Tek bir SMS gönderir ve sms_logs tablosuna işler.
    """
    msg = sanitize_message(message) if sanitize else message
    phone_digits = re.sub(r"\D", "", phone or "")
    result = _provider.send(phone_digits, msg)

    execute(
        """INSERT INTO sms_logs
           (customer_id, campaign_id, appointment_id, phone, message,
            sms_type, status, provider_response)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            customer_id,
            campaign_id,
            appointment_id,
            phone_digits,
            msg,
            sms_type,
            "sent" if result.success else "failed",
            result.provider_response,
        ),
    )
    return result


def send_bulk(
    recipients: list[dict],   # [{"customer_id": 1, "phone": "90...", "name": "Ayşe"}, ...]
    message_template: str,
    *,
    campaign_id: Optional[int] = None,
    sms_type: str = "campaign",
) -> dict:
    """
    Toplu gönderim. message_template içinde {name} değişkeni kullanılabilir.
    Kampanya tablosundaki sayaçları günceller.
    """
    sent, failed = 0, 0
    for r in recipients:
        personalized = message_template.format(
            name=r.get("name", ""),
            salon=config.SALON_NAME,
        )
        result = send_sms(
            r["phone"],
            personalized,
            customer_id=r.get("customer_id"),
            campaign_id=campaign_id,
            sms_type=sms_type,
        )
        if result.success:
            sent += 1
        else:
            failed += 1

    if campaign_id is not None:
        execute(
            """UPDATE sms_campaigns
               SET sent_count = ?, failed_count = ?, status = 'sent',
                   sent_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (sent, failed, campaign_id),
        )

    return {"sent": sent, "failed": failed, "total": len(recipients)}
