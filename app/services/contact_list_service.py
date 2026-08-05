import logging
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session

from app.models import ContactList, Contact, ContactListContact
from app.repositories.contact_list_repository import ContactListRepository
from app.services.excel_service import extract_contacts_from_excel
from app.schemas.contact_list import ImportContactsResponse

logger = logging.getLogger(__name__)


class ContactListService:
    """Service layer for Contact List operations."""

    @staticmethod
    def create_contact_list(db: Session, user_id: str, name: str, description: Optional[str] = None) -> ContactList:
        """Create a new contact list."""
        return ContactListRepository.create(db, user_id, name, description)

    @staticmethod
    def get_contact_list(db: Session, list_id: str, user_id: str) -> Optional[ContactList]:
        """Get a contact list by ID."""
        return ContactListRepository.get_by_id(db, list_id, user_id)

    @staticmethod
    def list_contact_lists(db: Session, user_id: str, offset: int = 0, limit: int = 100) -> Tuple[int, List[ContactList]]:
        """Get all contact lists for a user."""
        return ContactListRepository.list_by_user(db, user_id, offset, limit)

    @staticmethod
    def update_contact_list(db: Session, contact_list: ContactList, name: Optional[str] = None,
                           description: Optional[str] = None) -> ContactList:
        """Update a contact list."""
        return ContactListRepository.update(db, contact_list, name, description)

    @staticmethod
    def delete_contact_list(db: Session, contact_list: ContactList) -> ContactList:
        """Soft delete a contact list."""
        return ContactListRepository.soft_delete(db, contact_list)

    @staticmethod
    def import_contacts_from_excel(db: Session, list_id: str, file_bytes: bytes) -> ImportContactsResponse:
        """Import contacts from Excel file into a contact list."""
        try:
            rows = extract_contacts_from_excel(file_bytes)
        except Exception as exc:
            logger.error(f"Failed to read Excel file: {exc}")
            raise ValueError(f"Could not read the Excel file: {exc}")

        if not rows:
            raise ValueError("No valid email addresses found in the uploaded file.")

        created_contacts = 0
        existing_contacts = 0
        linked_contacts = 0
        skipped_duplicates = 0
        invalid_contacts = 0

        for row in rows:
            try:
                # Get or create contact
                contact = ContactListRepository.get_or_create_contact(
                    db,
                    email=row["email"],
                    name=row.get("name"),
                    university=row.get("university")
                )

                if contact.created_at == contact.updated_at:
                    created_contacts += 1
                else:
                    existing_contacts += 1

                # Add to list (skip if already exists)
                result = ContactListRepository.add_contact(db, list_id, contact.id)
                if result:
                    linked_contacts += 1
                else:
                    skipped_duplicates += 1

            except Exception as exc:
                logger.error(f"Failed to process contact {row.get('email')}: {exc}")
                invalid_contacts += 1

        # Update contact count
        ContactListRepository.update_contact_count(db, list_id)

        return ImportContactsResponse(
            total_rows=len(rows),
            created_contacts=created_contacts,
            existing_contacts=existing_contacts,
            linked_contacts=linked_contacts,
            skipped_duplicates=skipped_duplicates,
            invalid_contacts=invalid_contacts
        )

    @staticmethod
    def add_contacts_to_list(db: Session, list_id: str, contact_ids: List[str]) -> int:
        """Add existing contacts to a list."""
        added = ContactListRepository.add_contacts_bulk(db, list_id, contact_ids)
        ContactListRepository.update_contact_count(db, list_id)
        return added

    @staticmethod
    def remove_contact_from_list(db: Session, list_id: str, contact_id: str) -> bool:
        """Remove a contact from a list."""
        success = ContactListRepository.remove_contact(db, list_id, contact_id)
        if success:
            ContactListRepository.update_contact_count(db, list_id)
        return success

    @staticmethod
    def get_list_contacts(db: Session, list_id: str, offset: int = 0, limit: int = 100,
                         search: Optional[str] = None, sort_by: str = "email") -> Tuple[int, List[Contact]]:
        """Get paginated contacts in a list."""
        return ContactListRepository.get_contacts(db, list_id, offset, limit, search, sort_by)
