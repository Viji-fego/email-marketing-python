import logging
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas.contact_list import (
    ContactListCreate,
    ContactListUpdate,
    ContactListResponse,
    ContactListDetailResponse,
    AddContactsRequest,
    ImportContactsResponse,
    PaginatedContactsResponse,
    ContactInfo,
)
from app.services.contact_list_service import ContactListService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/contact-lists", tags=["contact-lists"])


@router.post("", response_model=ContactListResponse)
def create_contact_list(
    body: ContactListCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new contact list."""
    contact_list = ContactListService.create_contact_list(
        db, current_user.id, body.name, body.description
    )
    return contact_list


@router.get("", response_model=dict)
def list_contact_lists(
    offset: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all contact lists for the current user."""
    total, lists = ContactListService.list_contact_lists(db, current_user.id, offset, limit)
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "lists": [
            ContactListResponse.from_orm(l).__dict__ for l in lists
        ]
    }


@router.get("/{list_id}", response_model=ContactListDetailResponse)
def get_contact_list(
    list_id: str,
    offset: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get contact list details with paginated contacts."""
    contact_list = ContactListService.get_contact_list(db, list_id, current_user.id)
    if not contact_list:
        raise HTTPException(status_code=404, detail="Contact list not found.")

    total, contacts = ContactListService.get_list_contacts(db, list_id, offset, limit)

    return {
        "id": contact_list.id,
        "name": contact_list.name,
        "description": contact_list.description,
        "contact_count": contact_list.contact_count,
        "created_at": contact_list.created_at,
        "updated_at": contact_list.updated_at,
        "is_active": contact_list.is_active,
        "contacts": [
            {
                "id": c.id,
                "email": c.email,
                "name": c.name,
                "university": c.university,
            }
            for c in contacts
        ],
    }


@router.put("/{list_id}", response_model=ContactListResponse)
def update_contact_list(
    list_id: str,
    body: ContactListUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update contact list details."""
    contact_list = ContactListService.get_contact_list(db, list_id, current_user.id)
    if not contact_list:
        raise HTTPException(status_code=404, detail="Contact list not found.")

    updated_list = ContactListService.update_contact_list(
        db, contact_list, body.name, body.description
    )
    return updated_list


@router.delete("/{list_id}")
def delete_contact_list(
    list_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Soft delete a contact list."""
    contact_list = ContactListService.get_contact_list(db, list_id, current_user.id)
    if not contact_list:
        raise HTTPException(status_code=404, detail="Contact list not found.")

    ContactListService.delete_contact_list(db, contact_list)
    return {"success": True, "message": "Contact list deleted."}


@router.post("/{list_id}/import", response_model=ImportContactsResponse)
async def import_contacts(
    list_id: str,
    file: UploadFile = File(..., description="Excel or CSV file with contacts"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Import contacts from Excel/CSV file into the contact list."""
    contact_list = ContactListService.get_contact_list(db, list_id, current_user.id)
    if not contact_list:
        raise HTTPException(status_code=404, detail="Contact list not found.")

    if not file.filename.lower().endswith((".xlsx", ".xls", ".csv")):
        raise HTTPException(
            status_code=400,
            detail="Please upload an .xlsx, .xls, or .csv file.",
        )

    file_bytes = await file.read()

    try:
        result = ContactListService.import_contacts_from_excel(db, list_id, file_bytes)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error(f"Import failed: {exc}")
        raise HTTPException(status_code=500, detail="Failed to import contacts.")


@router.get("/{list_id}/contacts", response_model=PaginatedContactsResponse)
def get_list_contacts(
    list_id: str,
    offset: int = 0,
    limit: int = 100,
    search: str = None,
    sort_by: str = "email",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get paginated contacts in a list with search and sorting."""
    contact_list = ContactListService.get_contact_list(db, list_id, current_user.id)
    if not contact_list:
        raise HTTPException(status_code=404, detail="Contact list not found.")

    if sort_by not in ["email", "name"]:
        sort_by = "email"

    total, contacts = ContactListService.get_list_contacts(
        db, list_id, offset, limit, search, sort_by
    )

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "contacts": [
            {
                "id": c.id,
                "email": c.email,
                "name": c.name,
                "university": c.university,
            }
            for c in contacts
        ],
    }


@router.post("/{list_id}/contacts")
def add_contacts_to_list(
    list_id: str,
    body: AddContactsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add existing contacts to a contact list."""
    contact_list = ContactListService.get_contact_list(db, list_id, current_user.id)
    if not contact_list:
        raise HTTPException(status_code=404, detail="Contact list not found.")

    added = ContactListService.add_contacts_to_list(db, list_id, body.contact_ids)
    return {
        "success": True,
        "added": added,
        "message": f"Added {added} contacts to the list.",
    }


@router.delete("/{list_id}/contacts/{contact_id}")
def remove_contact_from_list(
    list_id: str,
    contact_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a contact from a contact list."""
    contact_list = ContactListService.get_contact_list(db, list_id, current_user.id)
    if not contact_list:
        raise HTTPException(status_code=404, detail="Contact list not found.")

    success = ContactListService.remove_contact_from_list(db, list_id, contact_id)
    if not success:
        raise HTTPException(status_code=404, detail="Contact not found in this list.")

    return {
        "success": True,
        "message": "Contact removed from the list.",
    }
