"""
Kampanya servisi: İYS onaylı kitleye toplu SMS gönderimi.
"""
from database import execute, fetch_all
from services import sms_service, customer_service


def list_campaigns() -> list[dict]:
    return fetch_all("SELECT * FROM sms_campaigns ORDER BY created_at DESC")


def create_and_send_campaign(name: str, message: str) -> dict:
    """
    Kampanyayı kayıt eder, İYS onaylı tüm müşterilere gönderir.
    Mesaj içinde {name} kullanılabilir.
    """
    customers = customer_service.list_customers(only_iys=True)
    if not customers:
        raise ValueError("IYS onayli musteri bulunmuyor.")

    campaign_id = execute(
        """INSERT INTO sms_campaigns (name, message, target_count, status)
           VALUES (?, ?, ?, 'draft')""",
        (name.strip(), message, len(customers)),
    )

    recipients = [
        {"customer_id": c.id, "phone": c.phone, "name": c.first_name}
        for c in customers
    ]
    summary = sms_service.send_bulk(
        recipients=recipients,
        message_template=message,
        campaign_id=campaign_id,
        sms_type="campaign",
    )
    summary["campaign_id"] = campaign_id
    summary["name"] = name
    return summary
