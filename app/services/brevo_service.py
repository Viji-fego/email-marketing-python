from typing import Optional
import logging
import json

import requests

from app.config import settings

logger = logging.getLogger(__name__)

BREVO_SEND_URL = "https://api.brevo.com/v3/smtp/email"


def _append_cta(html_content: str, cta_text: Optional[str], cta_url: Optional[str]) -> str:
    if not cta_text or not cta_url:
        return html_content
    button_html = (
        '<p style="margin-top:24px;">'
        f'<a href="{cta_url}" style="background:#9c3a56;color:#ffffff;padding:10px 20px;'
        'text-decoration:none;border-radius:4px;display:inline-block;">'
        f"{cta_text}</a></p>"
    )
    return html_content + button_html


def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: Optional[str] = None,
    cta_text: Optional[str] = None,
    cta_url: Optional[str] = None,
    campaign_contact_id: Optional[str] = None,
) -> str:
    """Send a single email through Brevo's transactional email API.

    The "from" address is always settings.BREVO_SENDER_EMAIL — it must be
    a sender that is already verified in the Brevo account, or Brevo will
    reject the request.

    Args:
        to_email: Recipient email address
        subject: Email subject
        html_content: HTML content
        text_content: Plain text content (optional)
        cta_text: Call-to-action button text (optional)
        cta_url: Call-to-action button URL (optional)
        campaign_contact_id: Internal campaign_contact UUID for reliable webhook matching (optional)

    Returns:
        str: Brevo message ID for tracking (SMTP format, for reference only)

    Raises:
        requests.HTTPError if Brevo rejects the request.
    """
    payload = {
        "sender": {
            "email": settings.BREVO_SENDER_EMAIL,
            "name": settings.BREVO_SENDER_NAME,
        },
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": _append_cta(html_content, cta_text, cta_url),
    }
    if text_content:
        payload["textContent"] = text_content

    # Add campaign_contact_id as tag so Brevo echoes it back on all webhooks
    # This is the primary lookup key for webhook matching (more reliable than message-id)
    if campaign_contact_id:
        payload["tags"] = [campaign_contact_id]
        logger.info(f"📌 Added tag to email: {campaign_contact_id}")

    headers = {
        "accept": "application/json",
        "api-key": settings.BREVO_API_KEY,
        "content-type": "application/json",
    }

    # Add custom header for additional tracking (echoed back in some webhook events)
    if campaign_contact_id:
        headers["X-Mailin-custom"] = campaign_contact_id
        logger.info(f"📌 Added custom header to email: {campaign_contact_id}")

    response = requests.post(BREVO_SEND_URL, json=payload, headers=headers, timeout=15)
    response.raise_for_status()

    # Extract message ID for audit trail (not primary lookup key anymore)
    response_data = response.json()

    logger.info(f"📧 BREVO RESPONSE: {json.dumps(response_data, indent=2)}")

    # Brevo returns messageId (SMTP format, for reference only)
    # Primary lookup is now by campaign_contact_id tag
    message_id = response_data.get("messageId")

    if not message_id:
        logger.error(f"❌ Brevo response missing messageId. Full response: {response_data}")
        raise ValueError("Brevo response missing messageId")

    logger.info(f"✅ Brevo messageId extracted: {message_id}")
    logger.info(f"📌 Campaign contact ID: {campaign_contact_id} (primary lookup key)")
    return message_id
