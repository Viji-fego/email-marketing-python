import logging
from typing import Optional, Tuple, List
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models import Campaign, ContactList, ContactListContact, Contact, CampaignContact, EmailEvent
from app.services.brevo_service import send_email
from app.enums import EmailEventType

logger = logging.getLogger(__name__)


class CampaignService:
    """Service layer for Campaign operations."""

    @staticmethod
    def create_campaign(db: Session, name: str, contact_list_id: Optional[str] = None) -> Campaign:
        """Create a new campaign."""
        campaign = Campaign(name=name, contact_list_id=contact_list_id, status="draft")
        db.add(campaign)
        db.commit()
        db.refresh(campaign)
        logger.info(f"Created campaign: {campaign.id}")
        return campaign

    @staticmethod
    def get_campaign(db: Session, campaign_id: str) -> Optional[Campaign]:
        """Get a campaign by ID."""
        return db.query(Campaign).filter(Campaign.id == campaign_id).first()

    @staticmethod
    def update_campaign_contact_list(db: Session, campaign: Campaign, contact_list_id: str) -> Campaign:
        """Update campaign's contact list selection."""
        campaign.contact_list_id = contact_list_id
        db.commit()
        db.refresh(campaign)
        logger.info(f"Updated campaign {campaign.id} with contact list {contact_list_id}")
        return campaign

    @staticmethod
    def run_campaign(db: Session, campaign: Campaign, subject: str, body_html: str,
                     body_text: Optional[str] = None, cta_text: Optional[str] = None,
                     cta_url: Optional[str] = None) -> dict:
        """
        Run a campaign: send emails to all contacts in the selected contact list.

        Returns statistics about the campaign run.
        """
        if not campaign.contact_list_id:
            raise ValueError("Campaign does not have a contact list selected.")

        contact_list = db.query(ContactList).filter(
            and_(
                ContactList.id == campaign.contact_list_id,
                ContactList.is_active == '1'
            )
        ).first()

        if not contact_list:
            raise ValueError("Selected contact list not found or is inactive.")

        # Get all active contacts in the list
        active_contacts = db.query(Contact).join(ContactListContact).filter(
            and_(
                ContactListContact.contact_list_id == campaign.contact_list_id,
                ContactListContact.is_active == '1',
                Contact.is_active == '1'
            )
        ).all()

        if not active_contacts:
            raise ValueError("No active contacts found in the selected contact list.")

        sent = []
        failed = []

        for contact in active_contacts:
            try:
                # Check if campaign contact already exists for this contact
                campaign_contact = db.query(CampaignContact).filter(
                    and_(
                        CampaignContact.campaign_id == campaign.id,
                        CampaignContact.contact_id == contact.id
                    )
                ).first()

                if not campaign_contact:
                    campaign_contact = CampaignContact(
                        campaign_id=campaign.id,
                        contact_id=contact.id
                    )
                    db.add(campaign_contact)
                    db.commit()
                    db.refresh(campaign_contact)

                # Send email via Brevo with campaign_contact_id for reliable webhook matching
                message_id = send_email(
                    to_email=contact.email,
                    subject=subject,
                    html_content=body_html,
                    text_content=body_text,
                    cta_text=cta_text,
                    cta_url=cta_url,
                    campaign_contact_id=campaign_contact.id,
                )

                # Update campaign contact tracking
                campaign_contact.provider_message_id = message_id
                campaign_contact.status = "sent"
                campaign_contact.sent_at = datetime.now(timezone.utc)

                # Create email event
                db.add(EmailEvent(
                    campaign_contact_id=campaign_contact.id,
                    provider_message_id=message_id,
                    event_type=EmailEventType.SENT.value,
                    provider="brevo",
                ))
                db.commit()

                sent.append(contact.email)
                logger.info(f"Sent email to {contact.email} for campaign {campaign.id}")

            except Exception as exc:
                campaign_contact.status = "failed"
                db.add(EmailEvent(
                    campaign_contact_id=campaign_contact.id,
                    event_type=EmailEventType.FAILED.value,
                    provider="brevo",
                    detail=str(exc),
                ))
                db.commit()
                failed.append({"email": contact.email, "error": str(exc)})
                logger.error(f"Failed to send email to {contact.email}: {exc}")

        # Update campaign status
        campaign.status = "sent" if len(failed) == 0 else "partial"
        db.commit()

        return {
            "campaignId": campaign.id,
            "contactListId": campaign.contact_list_id,
            "total": len(active_contacts),
            "sent": len(sent),
            "failed": len(failed),
            "sentEmails": sent,
            "failures": failed,
        }

    @staticmethod
    def get_campaign_status(db: Session, campaign_id: str, offset: int = 0, limit: int = 100) -> dict:
        """Get detailed status of a campaign."""
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            raise ValueError("Campaign not found.")

        # Get all campaign contacts with pagination
        total = db.query(CampaignContact).filter(
            CampaignContact.campaign_id == campaign_id
        ).count()

        campaign_contacts = db.query(CampaignContact, Contact).join(Contact).filter(
            CampaignContact.campaign_id == campaign_id
        ).offset(offset).limit(limit).all()

        contacts_status = []
        for cc, contact in campaign_contacts:
            contacts_status.append({
                "campaignContactId": cc.id,
                "contactId": contact.id,
                "email": contact.email,
                "name": contact.name,
                "status": cc.status,
                "sentAt": cc.sent_at.isoformat() if cc.sent_at else None,
                "deliveredAt": cc.delivered_at.isoformat() if cc.delivered_at else None,
                "openedAt": cc.opened_at.isoformat() if cc.opened_at else None,
                "clickedAt": cc.clicked_at.isoformat() if cc.clicked_at else None,
                "bouncedAt": cc.bounced_at.isoformat() if cc.bounced_at else None,
                "providerMessageId": cc.provider_message_id,
            })

        return {
            "campaignId": campaign_id,
            "name": campaign.name,
            "status": campaign.status,
            "contactListId": campaign.contact_list_id,
            "createdAt": campaign.created_at.isoformat(),
            "total": total,
            "limit": limit,
            "offset": offset,
            "contacts": contacts_status,
        }
