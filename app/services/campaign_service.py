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
    def create_campaign(db: Session, user_id: str, name: str, contact_list_id: Optional[str] = None) -> Campaign:
        """Create a new campaign."""
        campaign = Campaign(user_id=user_id, name=name, contact_list_id=contact_list_id, status="draft")
        db.add(campaign)
        db.commit()
        db.refresh(campaign)
        logger.info(f"Created campaign: {campaign.id}")
        return campaign

    @staticmethod
    def list_campaigns(db: Session, user_id: str, page: int = 1, page_size: int = 10, search: str = ""):
        """List active campaigns for a user."""
        query = db.query(Campaign).filter(Campaign.user_id == user_id, Campaign.is_active == '1')
        if search:
            query = query.filter(Campaign.name.ilike(f"%{search}%"))

        total = query.count()
        campaigns = (
            query.order_by(Campaign.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        items = []
        for campaign in campaigns:
            contacts = db.query(CampaignContact).filter_by(campaign_id=campaign.id).all()
            items.append({
                "id": campaign.id,
                "name": campaign.name,
                "status": campaign.status,
                "contactListId": campaign.contact_list_id,
                "contactListName": campaign.contact_list.name if campaign.contact_list else None,
                "contactCount": len(contacts),
                "sentCount": sum(1 for c in contacts if c.status == "sent"),
                "failedCount": sum(1 for c in contacts if c.status == "failed"),
                "unique_opened": sum(1 for c in contacts if c.opened_at),
                "unique_clicked": sum(1 for c in contacts if c.clicked_at),
                "unsubscribedCount": sum(1 for c in contacts if c.status == "unsubscribed"),
                "createdAt": campaign.created_at.isoformat(),
            })

        pages = (total + page_size - 1) // page_size if page_size else 0
        return {"items": items, "total": total, "page": page, "page_size": page_size, "pages": pages}

    @staticmethod
    def get_campaign_with_contacts(db: Session, campaign_id: str, user_id: str):
        """Get active campaign with all enrolled contacts."""
        campaign = db.query(Campaign).filter(
            Campaign.id == campaign_id,
            Campaign.user_id == user_id,
            Campaign.is_active == '1'
        ).first()
        if not campaign:
            raise ValueError("Campaign not found.")

        campaign_contacts = db.query(CampaignContact).filter_by(campaign_id=campaign_id).all()
        contacts = []
        for cc in campaign_contacts:
            contact = db.get(Contact, cc.contact_id)
            if not contact:
                continue
            contacts.append({
                "id": contact.id,
                "name": contact.name,
                "email": contact.email,
                "university": contact.university,
                "status": cc.status,
                "sentAt": cc.sent_at.isoformat() if cc.sent_at else None,
                "openedAt": cc.opened_at.isoformat() if cc.opened_at else None,
                "clickedAt": cc.clicked_at.isoformat() if cc.clicked_at else None,
            })

        return {
            "id": campaign.id,
            "name": campaign.name,
            "status": campaign.status,
            "contactListId": campaign.contact_list_id,
            "contactListName": campaign.contact_list.name if campaign.contact_list else None,
            "contactCount": len(contacts),
            "sentCount": sum(1 for c in contacts if c["status"] == "sent"),
            "createdAt": campaign.created_at.isoformat(),
            "contacts": contacts,
        }

    @staticmethod
    def enroll_contacts(db: Session, campaign_id: str, user_id: str, contact_ids: List[str]):
        """Enroll contacts in a campaign."""
        campaign = db.query(Campaign).filter(
            Campaign.id == campaign_id,
            Campaign.user_id == user_id
        ).first()
        if not campaign:
            raise ValueError("Campaign not found.")

        results = []
        for contact_id in contact_ids:
            contact = db.query(Contact).filter(
                Contact.id == contact_id,
                Contact.user_id == user_id
            ).first()
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

    @staticmethod
    def select_contact_list(db: Session, campaign_id: str, user_id: str, contact_list_id: str):
        """Select a contact list for the campaign."""
        campaign = db.query(Campaign).filter(
            Campaign.id == campaign_id,
            Campaign.user_id == user_id
        ).first()
        if not campaign:
            raise ValueError("Campaign not found.")

        contact_list = db.query(ContactList).filter(
            ContactList.id == contact_list_id,
            ContactList.user_id == user_id
        ).first()
        if not contact_list:
            raise ValueError("Contact list not found.")

        campaign.contact_list_id = contact_list_id
        db.commit()
        db.refresh(campaign)
        logger.info(f"Updated campaign {campaign.id} with contact list {contact_list_id}")
        return campaign

    @staticmethod
    def get_campaign(db: Session, campaign_id: str, user_id: Optional[str] = None) -> Optional[Campaign]:
        """Get a campaign by ID. If user_id is provided, checks ownership."""
        query = db.query(Campaign).filter(Campaign.id == campaign_id)
        if user_id:
            query = query.filter(Campaign.user_id == user_id)
        return query.first()

    @staticmethod
    def update_campaign_contact_list(db: Session, campaign: Campaign, contact_list_id: str) -> Campaign:
        """Update campaign's contact list selection (internal use only)."""
        campaign.contact_list_id = contact_list_id
        db.commit()
        db.refresh(campaign)
        logger.info(f"Updated campaign {campaign.id} with contact list {contact_list_id}")
        return campaign

    @staticmethod
    def soft_delete_campaign(db: Session, campaign_id: str, user_id: str) -> Campaign:
        """Soft delete a campaign (set is_active to '0')."""
        campaign = db.query(Campaign).filter(
            Campaign.id == campaign_id,
            Campaign.user_id == user_id
        ).first()
        if not campaign:
            raise ValueError("Campaign not found.")

        campaign.is_active = '0'
        db.commit()
        db.refresh(campaign)
        logger.info(f"Soft deleted campaign: {campaign.id}")
        return campaign

    @staticmethod
    def run_campaign(db: Session, campaign_id: str, user_id: str, subject: str, body_html: str,
                     body_text: Optional[str] = None, cta_text: Optional[str] = None,
                     cta_url: Optional[str] = None) -> dict:
        """
        Run a campaign: send emails to all contacts in the selected contact list.

        Returns statistics about the campaign run.
        """
        campaign = db.query(Campaign).filter(
            Campaign.id == campaign_id,
            Campaign.user_id == user_id
        ).first()
        if not campaign:
            raise ValueError("Campaign not found.")

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
