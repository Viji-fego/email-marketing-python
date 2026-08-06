"""Analytics service for campaign performance metrics.

Calculates metrics on-demand from EmailEvent and CampaignContact records.
No separate analytics table needed - this design allows flexibility and
ensures real-time accuracy.
"""

import logging
from typing import Dict, Any, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import CampaignContact, EmailEvent, Campaign
from app.models.base import iso_utc
from app.enums import EmailEventType

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Calculate campaign analytics from tracking data."""

    @staticmethod
    def get_campaign_analytics(db: Session, campaign_id: str) -> Dict[str, Any]:
        """
        Get campaign performance analytics.

        Calculates all metrics from campaign_contacts and email_events tables.

        Args:
            db: Database session
            campaign_id: Campaign ID

        Returns:
            Dictionary containing all campaign metrics
        """
        try:
            # Get campaign
            campaign = db.query(Campaign).filter_by(id=campaign_id).first()
            if not campaign:
                logger.warning("Campaign not found: %s", campaign_id)
                return {"error": "Campaign not found"}

            # Get all campaign_contacts
            campaign_contacts = db.query(CampaignContact).filter_by(
                campaign_id=campaign_id
            ).all()

            if not campaign_contacts:
                return {
                    "campaign_id": campaign_id,
                    "campaign_name": campaign.name,
                    "metrics": {
                        "total_sent": 0,
                        "total_failed": 0,
                        "total_delivered": 0,
                        "total_opened": 0,
                        "total_open_events": 0,
                        "total_open_events_raw": 0,
                        "prefetch_detected": 0,
                        "bot_scan_detected": 0,
                        "total_clicked": 0,
                        "total_bounced": 0,
                        "total_blocked": 0,
                        "total_deferred": 0,
                        "total_complained": 0,
                        "total_unsubscribed": 0,
                        "total_replied": 0,
                        "delivery_rate": 0.0,
                        "open_rate": 0.0,
                        "click_rate": 0.0,
                        "ctr": 0.0,
                        "bounce_rate": 0.0,
                        "complaint_rate": 0.0,
                        "unsubscribe_rate": 0.0,
                        "reply_rate": 0.0,
                    },
                }

            total = len(campaign_contacts)

            # Count by snapshot fields (latest state)
            delivered = sum(1 for cc in campaign_contacts if cc.delivered_at)
            failed = sum(1 for cc in campaign_contacts if cc.status == "failed")

            # Count UNIQUE contacts who opened (those with opened_at set)
            opened_genuine = sum(1 for cc in campaign_contacts if cc.opened_at)

            # Count UNIQUE contacts who clicked (those with clicked_at set)
            clicked = sum(1 for cc in campaign_contacts if cc.clicked_at)

            # Count total open/click EVENTS from email_events (for reference)
            open_events_genuine = db.query(func.count(EmailEvent.id)).join(
                CampaignContact,
                EmailEvent.campaign_contact_id == CampaignContact.id,
            ).filter(
                EmailEvent.event_type == EmailEventType.OPENED.value,
                EmailEvent.open_confidence == "genuine",
                CampaignContact.campaign_id == campaign_id,
            ).scalar() or 0

            open_events_raw = db.query(func.count(EmailEvent.id)).join(
                CampaignContact,
                EmailEvent.campaign_contact_id == CampaignContact.id,
            ).filter(
                EmailEvent.event_type == EmailEventType.OPENED.value,
                CampaignContact.campaign_id == campaign_id,
            ).scalar() or 0

            prefetch_detected = db.query(func.count(EmailEvent.id)).join(
                CampaignContact,
                EmailEvent.campaign_contact_id == CampaignContact.id,
            ).filter(
                EmailEvent.open_confidence == "likely_prefetch",
                CampaignContact.campaign_id == campaign_id,
            ).scalar() or 0

            bot_scan_detected = db.query(func.count(EmailEvent.id)).join(
                CampaignContact,
                EmailEvent.campaign_contact_id == CampaignContact.id,
            ).filter(
                EmailEvent.open_confidence == "likely_bot_scan",
                CampaignContact.campaign_id == campaign_id,
            ).scalar() or 0

            bounced = sum(
                1
                for cc in campaign_contacts
                if cc.status in ("bounced", "deferred", "blocked")
            )
            complained = sum(1 for cc in campaign_contacts if cc.status == "spam")
            unsubscribed = sum(
                1 for cc in campaign_contacts if cc.status == "unsubscribed"
            )

            # Count replied from email_events
            replied = db.query(func.count(EmailEvent.id)).join(
                CampaignContact,
                EmailEvent.campaign_contact_id == CampaignContact.id,
            ).filter(
                EmailEvent.event_type == EmailEventType.REPLIED.value,
                CampaignContact.campaign_id == campaign_id,
            ).scalar() or 0

            # Calculate rates (using unique counts)
            delivery_rate = (delivered / total * 100) if total > 0 else 0.0
            open_rate = (opened_genuine / delivered * 100) if delivered > 0 else 0.0
            click_rate = (clicked / opened_genuine * 100) if opened_genuine > 0 else 0.0
            ctr = (clicked / delivered * 100) if delivered > 0 else 0.0
            bounce_rate = (bounced / total * 100) if total > 0 else 0.0
            complaint_rate = (complained / total * 100) if total > 0 else 0.0
            unsubscribe_rate = (unsubscribed / total * 100) if total > 0 else 0.0
            reply_rate = (replied / opened_genuine * 100) if opened_genuine > 0 else 0.0

            return {
                "campaign_id": campaign_id,
                "campaign_name": campaign.name,
                "metrics": {
                    "total_sent": total,
                    "total_failed": failed,
                    "total_delivered": delivered,
                    "total_opened": opened_genuine,
                    "total_open_events": open_events_genuine,
                    "total_open_events_raw": open_events_raw,
                    "prefetch_detected": prefetch_detected,
                    "bot_scan_detected": bot_scan_detected,
                    "total_clicked": clicked,
                    "total_bounced": bounced,
                    "total_blocked": sum(
                        1 for cc in campaign_contacts if cc.status == "blocked"
                    ),
                    "total_deferred": sum(
                        1 for cc in campaign_contacts if cc.status == "deferred"
                    ),
                    "total_complained": complained,
                    "total_unsubscribed": unsubscribed,
                    "total_replied": replied,
                    "delivery_rate": round(delivery_rate, 2),
                    "open_rate": round(open_rate, 2),
                    "click_rate": round(click_rate, 2),
                    "ctr": round(ctr, 2),
                    "bounce_rate": round(bounce_rate, 2),
                    "complaint_rate": round(complaint_rate, 2),
                    "unsubscribe_rate": round(unsubscribe_rate, 2),
                    "reply_rate": round(reply_rate, 2),
                },
            }

        except Exception as e:
            logger.error("Error calculating campaign analytics: %s", e)
            return {"error": "Failed to calculate analytics"}

    @staticmethod
    def get_contact_email_history(
        db: Session, contact_id: str, campaign_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get email history for a contact across campaigns.

        Args:
            db: Database session
            contact_id: Contact ID
            campaign_id: Optional campaign ID to filter

        Returns:
            Dictionary with contact's email history
        """
        try:
            query = db.query(CampaignContact).filter_by(contact_id=contact_id)

            if campaign_id:
                query = query.filter_by(campaign_id=campaign_id)

            campaign_contacts = query.all()

            history = []
            for cc in campaign_contacts:
                campaign = db.query(Campaign).filter_by(id=cc.campaign_id).first()

                # Get all events for this email
                events = db.query(EmailEvent).filter_by(
                    campaign_contact_id=cc.id
                ).order_by(EmailEvent.created_at).all()

                history.append({
                    "campaign_id": cc.campaign_id,
                    "campaign_name": campaign.name if campaign else "Unknown",
                    "email_id": cc.id,
                    "status": cc.status,
                    "sent_at": iso_utc(cc.sent_at),
                    "delivered_at": iso_utc(cc.delivered_at),
                    "opened_at": iso_utc(cc.opened_at),
                    "clicked_at": iso_utc(cc.clicked_at),
                    "bounced_at": iso_utc(cc.bounced_at),
                    "unsubscribed_at": iso_utc(cc.unsubscribed_at),
                    "last_event": cc.last_event,
                    "last_event_at": iso_utc(cc.last_event_at),
                    "events": [
                        {
                            "event_type": e.event_type,
                            "timestamp": iso_utc(e.created_at),
                            "provider": e.provider,
                        }
                        for e in events
                    ],
                })

            return {
                "contact_id": contact_id,
                "total_campaigns": len(history),
                "history": history,
            }

        except Exception as e:
            logger.error("Error getting contact history: %s", e)
            return {"error": "Failed to get contact history"}

    @staticmethod
    def get_event_breakdown(
        db: Session, campaign_id: str
    ) -> Dict[str, Any]:
        """
        Get event type breakdown for a campaign.

        Args:
            db: Database session
            campaign_id: Campaign ID

        Returns:
            Event counts by type
        """
        try:
            campaign_contacts = db.query(CampaignContact).filter_by(
                campaign_id=campaign_id
            ).with_entities(CampaignContact.id).all()

            campaign_contact_ids = [cc[0] for cc in campaign_contacts]

            if not campaign_contact_ids:
                return {
                    "campaign_id": campaign_id,
                    "events": {},
                }

            # Count by event type
            event_counts = db.query(
                EmailEvent.event_type,
                func.count(EmailEvent.id).label("count"),
            ).filter(
                EmailEvent.campaign_contact_id.in_(campaign_contact_ids)
            ).group_by(
                EmailEvent.event_type
            ).all()

            events = {
                event_type: count
                for event_type, count in event_counts
            }

            return {
                "campaign_id": campaign_id,
                "events": events,
            }

        except Exception as e:
            logger.error("Error getting event breakdown: %s", e)
            return {"error": "Failed to get event breakdown"}
