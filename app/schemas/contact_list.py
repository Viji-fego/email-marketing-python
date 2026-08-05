from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


class ContactListCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Contact list name")
    description: Optional[str] = Field(None, max_length=1000, description="List description")


class ContactListUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)


class ContactInfo(BaseModel):
    id: str
    email: str
    name: Optional[str]
    university: Optional[str]


class ContactListResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    contact_count: int
    created_at: datetime
    updated_at: Optional[datetime]
    is_active: bool

    class Config:
        from_attributes = True


class ContactListDetailResponse(ContactListResponse):
    contacts: List[ContactInfo] = []


class AddContactsRequest(BaseModel):
    contact_ids: List[str] = Field(..., min_items=1, description="List of contact IDs to add")


class ImportContactsResponse(BaseModel):
    total_rows: int
    created_contacts: int
    existing_contacts: int
    linked_contacts: int
    skipped_duplicates: int
    invalid_contacts: int


class PaginatedContactsResponse(BaseModel):
    total: int
    limit: int
    offset: int
    contacts: List[ContactInfo]
