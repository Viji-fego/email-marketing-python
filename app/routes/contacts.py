from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.config import get_db
from app.deps import get_current_user
from app.models import Contact, CampaignContact, Campaign, User
from app.models.base import iso_utc
from app.services.excel_service import extract_contacts_from_excel
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.get("")
def list_contacts(
    page: int = 1,
    page_size: int = 10,
    search: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Contact).filter(Contact.user_id == current_user.id)
    if search:
        query = query.filter(
            (Contact.email.ilike(f"%{search}%")) | (Contact.name.ilike(f"%{search}%"))
        )

    total = query.count()
    contacts = (
        query.order_by(Contact.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = []
    for contact in contacts:
        campaigns = (
            db.query(Campaign.id, Campaign.name)
            .join(CampaignContact, CampaignContact.campaign_id == Campaign.id)
            .filter(CampaignContact.contact_id == contact.id)
            .all()
        )
        items.append({
            "id": contact.id,
            "name": contact.name,
            "email": contact.email,
            "university": contact.university,
            "campaigns": [{"id": cid, "name": cname} for cid, cname in campaigns],
            "createdAt": iso_utc(contact.created_at),
        })

    pages = (total + page_size - 1) // page_size if page_size else 0
    return {"items": items, "total": total, "page": page, "page_size": page_size, "pages": pages}


@router.get("/{contact_id}")
def get_contact(
    contact_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contact = db.query(Contact).filter(
        Contact.id == contact_id,
        Contact.user_id == current_user.id
    ).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found.")

    history = AnalyticsService.get_contact_email_history(db, contact_id)["history"]

    return {
        "id": contact.id,
        "name": contact.name,
        "email": contact.email,
        "university": contact.university,
        "createdAt": iso_utc(contact.created_at),
        "campaigns": [
            {
                "campaignId": h["campaign_id"],
                "campaignName": h["campaign_name"],
                "status": h["status"],
                "sentAt": h["sent_at"],
                "deliveredAt": h["delivered_at"],
                "openedAt": h["opened_at"],
                "clickedAt": h["clicked_at"],
                "bouncedAt": h["bounced_at"],
                "unsubscribedAt": h["unsubscribed_at"],
            }
            for h in history
        ],
    }


@router.post("/import-excel")
async def import_contacts_excel(
    file: UploadFile = File(..., description="Excel file (.xlsx) with an 'email' column"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create or update contacts from an uploaded Excel file, matched by email.
    Not tied to any campaign — just populates the general contacts list."""
    if not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Please upload an .xlsx or .xls file.")

    file_bytes = await file.read()

    try:
        rows = extract_contacts_from_excel(file_bytes)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not read the Excel file: {exc}")

    if not rows:
        raise HTTPException(status_code=400, detail="No valid email addresses found in the uploaded file.")

    imported: List[Contact] = []
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
        imported.append(contact)

    db.commit()
    for contact in imported:
        db.refresh(contact)

    return {
        "imported": len(imported),
        "contacts": [
            {"id": c.id, "name": c.name, "email": c.email, "university": c.university} for c in imported
        ],
    }


class ContactIn(BaseModel):
    name: Optional[str] = None
    email: EmailStr
    university: Optional[str] = None


class ImportContactsRequest(BaseModel):
    contacts: List[ContactIn]


@router.post("/import")
def import_contacts(
    body: ImportContactsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create or update contacts by email. Existing contacts (matched by
    email) get their name/university refreshed rather than duplicated."""
    imported: List[Contact] = []

    for incoming in body.contacts:
        existing = db.query(Contact).filter(
            Contact.email == incoming.email,
            Contact.user_id == current_user.id
        ).first()
        if existing:
            existing.name = incoming.name or existing.name
            existing.university = incoming.university or existing.university
            imported.append(existing)
        else:
            contact = Contact(
                name=incoming.name,
                email=incoming.email,
                university=incoming.university,
                user_id=current_user.id
            )
            db.add(contact)
            imported.append(contact)

    db.commit()
    for contact in imported:
        db.refresh(contact)

    return {
        "imported": len(imported),
        "contacts": [
            {"id": c.id, "name": c.name, "email": c.email, "university": c.university} for c in imported
        ],
    }
