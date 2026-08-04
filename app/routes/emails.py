import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.config import settings, get_db
from app.deps import get_current_user
from app.models import CampaignContact, EmailEvent, User
from app.services.brevo_service import send_email
from app.enums import EmailEventType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/emails", tags=["emails"])


class SendEmailRequest(BaseModel):
    to: EmailStr
    subject: str
    htmlContent: str
    textContent: Optional[str] = None
    campaignContactId: Optional[str] = None
    ctaText: Optional[str] = None
    ctaUrl: Optional[str] = None


@router.post("/send")
def send_email_route(
    body: SendEmailRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not settings.BREVO_API_KEY or not settings.BREVO_SENDER_EMAIL:
        raise HTTPException(
            status_code=500,
            detail="Brevo is not configured. Set BREVO_API_KEY and BREVO_SENDER_EMAIL in .env.",
        )

    campaign_contact = None
    if body.campaignContactId:
        campaign_contact = db.get(CampaignContact, body.campaignContactId)
        if not campaign_contact:
            raise HTTPException(status_code=404, detail="campaignContactId not found.")

    try:
        # Send email and capture message ID for tracking
        message_id = send_email(
            to_email=body.to,
            subject=body.subject,
            html_content=body.htmlContent,
            text_content=body.textContent,
            cta_text=body.ctaText,
            cta_url=body.ctaUrl,
        )

        if campaign_contact:
            # Store message ID for webhook tracking
            campaign_contact.provider_message_id = message_id
            campaign_contact.status = "sent"
            campaign_contact.sent_at = datetime.now(timezone.utc)
            db.add(EmailEvent(
                campaign_contact_id=campaign_contact.id,
                provider_message_id=message_id,
                event_type=EmailEventType.SENT.value,
                provider="brevo",
            ))
            db.commit()

    except Exception as exc:
        if campaign_contact:
            campaign_contact.status = "failed"
            db.add(EmailEvent(
                campaign_contact_id=campaign_contact.id,
                event_type=EmailEventType.FAILED.value,
                provider="brevo",
                detail=str(exc),
            ))
            db.commit()
        logger.error(f"Failed to send email to {body.to}: {exc}")
        raise HTTPException(status_code=502, detail=f"Brevo rejected the email: {exc}")

    return {"success": True, "to": body.to, "messageId": message_id if campaign_contact else None}
