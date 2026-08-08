import logging
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models import ContactList, ContactListContact, Contact

logger = logging.getLogger(__name__)


class ContactListRepository:
    """Repository for ContactList operations."""

    @staticmethod
    def create(db: Session, user_id: str, name: str, description: Optional[str] = None) -> ContactList:
        """Create a new contact list."""
        contact_list = ContactList(
            user_id=user_id,
            name=name,
            description=description,
            contact_count=0
        )
        db.add(contact_list)
        db.commit()
        db.refresh(contact_list)
        logger.info(f"Created contact list: {contact_list.id}")
        return contact_list

    @staticmethod
    def get_by_id(db: Session, list_id: str, user_id: str) -> Optional[ContactList]:
        """Get contact list by ID (user-scoped)."""
        return db.query(ContactList).filter(
            and_(
                ContactList.id == list_id,
                ContactList.user_id == user_id,
                ContactList.is_active == '1'
            )
        ).first()

    @staticmethod
    def list_by_user(db: Session, user_id: str, offset: int = 0, limit: int = 100) -> Tuple[int, List[ContactList]]:
        """Get all active contact lists for a user with pagination."""
        query = db.query(ContactList).filter(
            and_(
                ContactList.user_id == user_id,
                ContactList.is_active == '1'
            )
        )
        total = query.count()
        lists = query.order_by(ContactList.updated_at.desc()).offset(offset).limit(limit).all()
        return total, lists

    @staticmethod
    def update(db: Session, contact_list: ContactList, name: Optional[str] = None,
               description: Optional[str] = None) -> ContactList:
        """Update contact list details."""
        if name is not None:
            contact_list.name = name
        if description is not None:
            contact_list.description = description
        db.commit()
        db.refresh(contact_list)
        logger.info(f"Updated contact list: {contact_list.id}")
        return contact_list

    @staticmethod
    def soft_delete(db: Session, contact_list: ContactList) -> ContactList:
        """Soft delete a contact list."""
        contact_list.is_active = '0'
        db.commit()
        db.refresh(contact_list)
        logger.info(f"Soft deleted contact list: {contact_list.id}")
        return contact_list

    @staticmethod
    def add_contact(db: Session, list_id: str, contact_id: str) -> Optional[ContactListContact]:
        """Add a contact to the list (skip if already exists and active)."""
        existing = db.query(ContactListContact).filter(
            and_(
                ContactListContact.contact_list_id == list_id,
                ContactListContact.contact_id == contact_id,
                ContactListContact.is_active == '1'
            )
        ).first()

        if existing:
            return None

        # Check if there's a soft-deleted mapping that we can reactivate
        deleted_mapping = db.query(ContactListContact).filter(
            and_(
                ContactListContact.contact_list_id == list_id,
                ContactListContact.contact_id == contact_id,
                ContactListContact.is_active == '0'
            )
        ).first()

        if deleted_mapping:
            deleted_mapping.is_active = '1'
            db.commit()
            db.refresh(deleted_mapping)
            logger.info(f"Reactivated contact {contact_id} in list {list_id}")
            return deleted_mapping

        mapping = ContactListContact(contact_list_id=list_id, contact_id=contact_id)
        db.add(mapping)
        db.commit()
        db.refresh(mapping)
        logger.info(f"Added contact {contact_id} to list {list_id}")
        return mapping

    @staticmethod
    def add_contacts_bulk(db: Session, list_id: str, contact_ids: List[str]) -> int:
        """Add multiple contacts to a list (bulk insert with duplicate skipping)."""
        existing_ids = db.query(ContactListContact.contact_id).filter(
            and_(
                ContactListContact.contact_list_id == list_id,
                ContactListContact.is_active == '1'
            )
        ).all()
        existing_ids_set = {row[0] for row in existing_ids}

        # Check for soft-deleted mappings to reactivate
        deleted_ids = db.query(ContactListContact).filter(
            and_(
                ContactListContact.contact_list_id == list_id,
                ContactListContact.contact_id.in_(contact_ids),
                ContactListContact.is_active == '0'
            )
        ).all()

        reactivated = 0
        for deleted_mapping in deleted_ids:
            if deleted_mapping.contact_id not in existing_ids_set:
                deleted_mapping.is_active = '1'
                reactivated += 1

        new_contact_ids = [cid for cid in contact_ids if cid not in existing_ids_set and cid not in {d.contact_id for d in deleted_ids}]

        new_mappings = []
        if new_contact_ids:
            new_mappings = [
                {"contact_list_id": list_id, "contact_id": cid}
                for cid in new_contact_ids
            ]
            db.bulk_insert_mappings(ContactListContact, new_mappings)

        if reactivated > 0 or len(new_mappings) > 0:
            db.commit()
            logger.info(f"Added {len(new_mappings)} new contacts and reactivated {reactivated} contacts to list {list_id}")

        return len(new_mappings) + reactivated

    @staticmethod
    def remove_contact(db: Session, list_id: str, contact_id: str) -> bool:
        """Soft delete a contact from the list (set is_active='0')."""
        mapping = db.query(ContactListContact).filter(
            and_(
                ContactListContact.contact_list_id == list_id,
                ContactListContact.contact_id == contact_id,
                ContactListContact.is_active == '1'
            )
        ).first()

        if not mapping:
            return False

        mapping.is_active = '0'
        db.commit()
        db.refresh(mapping)
        logger.info(f"Soft deleted contact {contact_id} from list {list_id}")
        return True

    @staticmethod
    def get_contacts(db: Session, list_id: str, offset: int = 0, limit: int = 100,
                     search: Optional[str] = None, sort_by: str = "email") -> Tuple[int, List[Contact]]:
        """Get paginated active contacts in a list with optional search."""
        query = db.query(Contact).join(ContactListContact).filter(
            and_(
                ContactListContact.contact_list_id == list_id,
                ContactListContact.is_active == '1'
            )
        )

        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                (Contact.email.ilike(search_pattern)) |
                (Contact.name.ilike(search_pattern))
            )

        total = query.count()

        if sort_by == "name":
            query = query.order_by(Contact.name)
        else:
            query = query.order_by(Contact.email)

        contacts = query.offset(offset).limit(limit).all()
        return total, contacts

    @staticmethod
    def update_contact_count(db: Session, list_id: str) -> int:
        """Update the active contact count for a list."""
        count = db.query(ContactListContact).filter(
            and_(
                ContactListContact.contact_list_id == list_id,
                ContactListContact.is_active == '1'
            )
        ).count()

        contact_list = db.query(ContactList).filter(ContactList.id == list_id).first()
        if contact_list:
            contact_list.contact_count = count
            db.commit()
            db.refresh(contact_list)
            logger.info(f"Updated contact count for list {list_id}: {count}")

        return count

    @staticmethod
    def get_or_create_contact(db: Session, email: str, user_id: str, name: Optional[str] = None,
                             university: Optional[str] = None) -> Contact:
        """Get existing contact or create a new one."""
        contact = db.query(Contact).filter(Contact.email == email, Contact.user_id == user_id).first()

        if contact:
            if name and not contact.name:
                contact.name = name
            if university and not contact.university:
                contact.university = university
            db.commit()
            db.refresh(contact)
            return contact

        contact = Contact(email=email, user_id=user_id, name=name, university=university)
        db.add(contact)
        db.commit()
        db.refresh(contact)
        logger.info(f"Created contact: {contact.id}")
        return contact
