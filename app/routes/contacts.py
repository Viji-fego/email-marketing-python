from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.config import get_db
from app.deps import get_current_user
from app.models import Contact, User

router = APIRouter(prefix="/contacts", tags=["contacts"])


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
        existing = db.query(Contact).filter(Contact.email == incoming.email).first()
        if existing:
            existing.name = incoming.name or existing.name
            existing.university = incoming.university or existing.university
            imported.append(existing)
        else:
            contact = Contact(name=incoming.name, email=incoming.email, university=incoming.university)
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
