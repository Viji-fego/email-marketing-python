import logging
from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings, get_db
from app.deps import get_current_user
from app.models import Campaign, CampaignContact, Contact, EmailEvent, User
from app.services.brevo_service import send_email
from app.services.excel_service import extract_contacts_from_excel
from app.services.analytics_service import AnalyticsService
from app.enums import EmailEventType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


class CreateCampaignRequest(BaseModel):
    name: str


@router.post("")
def create_campaign(
    body: CreateCampaignRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    campaign = Campaign(name=body.name)
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return {"id": campaign.id, "name": campaign.name, "status": campaign.status}


class EnrollRequest(BaseModel):
    contactIds: List[str]


@router.post("/{campaign_id}/enroll")
def enroll_contacts(
    campaign_id: str,
    body: EnrollRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    campaign = db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found.")

    results = []
    for contact_id in body.contactIds:
        contact = db.get(Contact, contact_id)
        if not contact:
            continue
        existing = (
            db.query(CampaignContact)
            .filter_by(campaign_id=campaign_id, contact_id=contact_id)
            .first()
        )
        cc = existing or CampaignContact(campaign_id=campaign_id, contact_id=contact_id)
        if not existing:
            db.add(cc)
        results.append(cc)

    db.commit()
    for cc in results:
        db.refresh(cc)

    return {
        "enrolled": len(results),
        "campaignContacts": [{"id": cc.id, "contactId": cc.contact_id, "status": cc.status} for cc in results],
    }


def _require_brevo_configured():
    if not settings.BREVO_API_KEY or not settings.BREVO_SENDER_EMAIL:
        raise HTTPException(
            status_code=500,
            detail="Brevo is not configured. Set BREVO_API_KEY and BREVO_SENDER_EMAIL in .env.",
        )


@router.post("/send-from-excel")
async def send_from_excel(
    file: UploadFile = File(..., description="Excel file (.xlsx) with an 'email' column"),
    campaign_name: str = Form(..., description="Name for the campaign this creates"),
    subject: str = Form(..., description="Email subject line"),
    body_html: str = Form(..., description="Email body as HTML"),
    body_text: str = Form(None, description="Email body as plain text (optional)"),
    cta_text: str = Form(None, description="Call-to-action button text (optional)"),
    cta_url: str = Form(None, description="Call-to-action button link (optional)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload an Excel file of contacts and send an email to every one of
    them, in one step: creates a campaign, imports/updates the contacts,
    enrolls them in the campaign, and sends — same underlying send logic
    (and same tracking) as /api/emails/send, just looped over the file."""
    _require_brevo_configured()

    if not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Please upload an .xlsx or .xls file.")

    file_bytes = await file.read()

    try:
        rows = extract_contacts_from_excel(file_bytes)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not read the Excel file: {exc}")

    if not rows:
        raise HTTPException(status_code=400, detail="No valid email addresses found in the uploaded file.")

    campaign = Campaign(name=campaign_name)
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    sent, failed = [], []

    for row in rows:
        contact = db.query(Contact).filter(Contact.email == row["email"]).first()
        if contact:
            contact.name = row["name"] or contact.name
            contact.university = row["university"] or contact.university
        else:
            contact = Contact(name=row["name"], email=row["email"], university=row["university"])
            db.add(contact)
        db.commit()
        db.refresh(contact)

        campaign_contact = CampaignContact(campaign_id=campaign.id, contact_id=contact.id)
        db.add(campaign_contact)
        db.commit()
        db.refresh(campaign_contact)

        try:
            # Send email and capture message ID for tracking
            message_id = send_email(
                to_email=contact.email,
                subject=subject,
                html_content=body_html,
                text_content=body_text,
                cta_text=cta_text,
                cta_url=cta_url,
            )

            # Store message ID for webhook tracking
            campaign_contact.provider_message_id = message_id
            campaign_contact.status = "sent"
            campaign_contact.sent_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)

            # Log event
            db.add(EmailEvent(
                campaign_contact_id=campaign_contact.id,
                provider_message_id=message_id,
                event_type=EmailEventType.SENT.value,
                provider="brevo",
            ))
            sent.append(contact.email)
        except Exception as exc:
            campaign_contact.status = "failed"
            db.add(EmailEvent(
                campaign_contact_id=campaign_contact.id,
                event_type=EmailEventType.FAILED.value,
                provider="brevo",
                detail=str(exc),
            ))
            failed.append({"email": contact.email, "error": str(exc)})
            logger.error(f"Failed to send email to {contact.email}: {exc}")

        db.commit()

    return {
        "campaignId": campaign.id,
        "total": len(rows),
        "sent": len(sent),
        "failed": len(failed),
        "failures": failed,
    }


@router.get("/{campaign_id}/analytics")
def get_campaign_analytics(
    campaign_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get campaign performance analytics.

    Returns metrics including:
    - Total sent, delivered, opened, clicked
    - Bounce rates, complaint rates, unsubscribe rates
    - Engagement metrics (open rate, click rate, CTR)
    """
    return AnalyticsService.get_campaign_analytics(db, campaign_id)


@router.get("/{campaign_id}/events")
def get_campaign_events(
    campaign_id: str,
    event_type: str = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get event breakdown for a campaign.

    Shows count of each event type (sent, delivered, opened, clicked, etc.).
    """
    return AnalyticsService.get_event_breakdown(db, campaign_id)
