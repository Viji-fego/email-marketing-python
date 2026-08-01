from typing import Optional

import requests

from app.config import settings

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
) -> None:
    """Send a single email through Brevo's transactional email API.

    The "from" address is always settings.BREVO_SENDER_EMAIL — it must be
    a sender that is already verified in the Brevo account, or Brevo will
    reject the request.

    Raises requests.HTTPError if Brevo rejects the request.
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

    headers = {
        "accept": "application/json",
        "api-key": settings.BREVO_API_KEY,
        "content-type": "application/json",
    }
    response = requests.post(BREVO_SEND_URL, json=payload, headers=headers, timeout=15)
    response.raise_for_status()
