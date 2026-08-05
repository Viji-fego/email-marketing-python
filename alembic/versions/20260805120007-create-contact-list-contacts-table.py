"""Create contact_list_contacts table

Revision ID: 20260805120007
Revises: 20260805120006
Create Date: 2026-08-05 12:00:07.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision: str = '20260805120007'
down_revision: Union[str, Sequence[str], None] = '20260805120006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create contact_list_contacts table."""
    op.create_table('contact_list_contacts',
    sa.Column('id', mysql.VARCHAR(length=36), nullable=False),
    sa.Column('contact_list_id', mysql.VARCHAR(length=36), nullable=False),
    sa.Column('contact_id', mysql.VARCHAR(length=36), nullable=False),
    sa.Column('created_at', mysql.DATETIME(), nullable=True),
    sa.Column('updated_at', mysql.DATETIME(), nullable=True),
    sa.Column('is_active', mysql.ENUM('0', '1'), server_default='1', nullable=False),
    sa.ForeignKeyConstraint(['contact_id'], ['contacts.id'], ),
    sa.ForeignKeyConstraint(['contact_list_id'], ['contact_lists.id'], ),
    sa.PrimaryKeyConstraint('id'),
    mysql_collate='utf8mb4_0900_ai_ci',
    mysql_default_charset='utf8mb4',
    mysql_engine='MyISAM'
    )
    op.create_index(op.f('ix_contact_list_contacts_contact_id'), 'contact_list_contacts', ['contact_id'])
    op.create_index(op.f('ix_contact_list_contacts_contact_list_id'), 'contact_list_contacts', ['contact_list_id'])
    op.create_unique_constraint('uq_contact_list_contacts_list_contact', 'contact_list_contacts', ['contact_list_id', 'contact_id'])


def downgrade() -> None:
    """Drop contact_list_contacts table."""
    op.drop_constraint('uq_contact_list_contacts_list_contact', 'contact_list_contacts', type_='unique')
    op.drop_index(op.f('ix_contact_list_contacts_contact_list_id'), table_name='contact_list_contacts')
    op.drop_index(op.f('ix_contact_list_contacts_contact_id'), table_name='contact_list_contacts')
    op.drop_table('contact_list_contacts')
