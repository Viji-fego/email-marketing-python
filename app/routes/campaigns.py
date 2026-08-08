import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings, get_db
from app.deps import get_current_user
from app.models import Campaign, CampaignContact, Contact, ContactList, EmailEvent, User
from app.models.base import iso_utc
from app.services.brevo_service import send_email
from app.services.excel_service import extract_contacts_from_excel
from app.services.analytics_service import AnalyticsService
from app.services.campaign_service import CampaignService
from app.enums import EmailEventType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


class CreateCampaignRequest(BaseModel):
    name: str
    contact_list_id: Optional[str] = None


class SelectContactListRequest(BaseModel):
    contact_list_id: str


class RunCampaignRequest(BaseModel):
    subject: str
    bodyHtml: str
    bodyText: Optional[str] = None
    ctaText: Optional[str] = None
    ctaUrl: Optional[str] = None


@router.post("")
def create_campaign(
    body: CreateCampaignRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new campaign with optional contact list selection."""
    campaign = CampaignService.create_campaign(db, current_user.id, body.name, body.contact_list_id)
    return {
        "id": campaign.id,
        "name": campaign.name,
        "status": campaign.status,
        "contactListId": campaign.contact_list_id,
        "createdAt": campaign.created_at.isoformat(),
    }


@router.get("")
def list_campaigns(
    page: int = 1,
    page_size: int = 10,
    search: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List campaigns with recipient/open/click/unsubscribe counts for the card list UI."""
    return CampaignService.list_campaigns(db, current_user.id, page, page_size, search)


@router.get("/{campaign_id}")
def get_campaign(
    campaign_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Campaign detail: summary + the full list of enrolled contacts with their delivery status."""
    try:
        return CampaignService.get_campaign_with_contacts(db, campaign_id, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


class EnrollRequest(BaseModel):
    contactIds: List[str]


@router.post("/{campaign_id}/enroll")
def enroll_contacts(
    campaign_id: str,
    body: EnrollRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return CampaignService.enroll_contacts(db, campaign_id, current_user.id, body.contactIds)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.put("/{campaign_id}/select-contact-list")
def select_contact_list(
    campaign_id: str,
    body: SelectContactListRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Select a contact list for the campaign."""
    try:
        campaign = CampaignService.select_contact_list(db, campaign_id, current_user.id, body.contact_list_id)
        return {
            "id": campaign.id,
            "name": campaign.name,
            "status": campaign.status,
            "contactListId": campaign.contact_list_id,
            "message": "Contact list selected for campaign.",
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/{campaign_id}/run")
def run_campaign(
    campaign_id: str,
    body: RunCampaignRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Run a campaign: send emails to all contacts in the selected contact list."""
    _require_brevo_configured()

    try:
        return CampaignService.run_campaign(
            db, campaign_id, current_user.id,
            subject=body.subject,
            body_html=body.bodyHtml,
            body_text=body.bodyText,
            cta_text=body.ctaText,
            cta_url=body.ctaUrl,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error(f"Campaign run failed: {exc}")
        raise HTTPException(status_code=500, detail="Failed to run campaign.")


def _require_brevo_configured():
    if not settings.BREVO_API_KEY or not settings.BREVO_SENDER_EMAIL:
        logger.error("STEP 1: Brevo Configuration Check - Missing BREVO_API_KEY or BREVO_SENDER_EMAIL")
        raise HTTPException(
            status_code=500,
            detail="Brevo is not configured. Set BREVO_API_KEY and BREVO_SENDER_EMAIL in .env.",
        )
    logger.info("STEP 1: Brevo Configuration Check - Brevo is properly configured")


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

    campaign = Campaign(name=campaign_name, user_id=current_user.id)
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    sent, failed = [], []

    for row in rows:
        contact = db.query(Contact).filter(
            Contact.email == row["email"],
            Contact.user_id == current_user.id
        ).first()
        if contact:
            contact.name = row["name"] or contact.name
            contact.university = row["university"] or contact.university
        else:
            contact = Contact(
                name=row["name"],
                email=row["email"],
                university=row["university"],
                user_id=current_user.id
            )
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
            campaign_contact.sent_at = datetime.now(timezone.utc)

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
    try:
        campaign = CampaignService.get_campaign(db, campaign_id, current_user.id)
        if not campaign:
            raise ValueError("Campaign not found.")
        return AnalyticsService.get_campaign_analytics(db, campaign_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


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
    try:
        campaign = CampaignService.get_campaign(db, campaign_id, current_user.id)
        if not campaign:
            raise ValueError("Campaign not found.")
        return AnalyticsService.get_event_breakdown(db, campaign_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete("/{campaign_id}")
def delete_campaign(
    campaign_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Soft delete a campaign."""
    try:
        CampaignService.soft_delete_campaign(db, campaign_id, current_user.id)
        return {"success": True, "message": "Campaign deleted."}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
