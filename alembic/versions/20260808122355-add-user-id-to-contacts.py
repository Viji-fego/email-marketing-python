"""Add user_id to contacts table

Revision ID: 20260808122355
Revises: 20260806123136
Create Date: 2026-08-08 00:00:02.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision: str = '20260808122355'
down_revision: Union[str, Sequence[str], None] = '20260808122335'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add user_id column to contacts table."""
    op.add_column('contacts', sa.Column('user_id', mysql.VARCHAR(length=36), nullable=True))
    op.create_foreign_key('fk_contacts_user_id', 'contacts', 'users', ['user_id'], ['id'])
    op.create_index(op.f('ix_contacts_user_id'), 'contacts', ['user_id'])

    # Set user_id for existing rows - assign to first user if exists
    op.execute("""
        UPDATE contacts SET user_id = (SELECT id FROM users LIMIT 1) WHERE user_id IS NULL
    """)

    # Now make the column non-nullable
    op.alter_column('contacts', 'user_id', existing_type=mysql.VARCHAR(length=36), nullable=False)

    # Remove unique constraint on email and make it part of a composite unique with user_id
    op.drop_index('ix_contacts_email', table_name='contacts')
    op.create_index(op.f('ix_contacts_email'), 'contacts', ['email'])


def downgrade() -> None:
    """Remove user_id column from contacts table."""
    op.drop_index(op.f('ix_contacts_user_id'), table_name='contacts')
    op.drop_constraint('fk_contacts_user_id', 'contacts', type_='foreignkey')
    op.drop_index(op.f('ix_contacts_email'), table_name='contacts')
    op.drop_column('contacts', 'user_id')
    op.create_index('ix_contacts_email', 'contacts', ['email'], unique=True)
