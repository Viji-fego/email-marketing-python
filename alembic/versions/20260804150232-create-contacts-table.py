"""Create contacts table

Revision ID: 20260804150232
Revises: 20260804150231
Create Date: 2026-08-04 15:02:32.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '20260804150232'
down_revision: Union[str, Sequence[str], None] = '20260804150231'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create contacts table."""
    op.create_table('contacts',
    sa.Column('id', mysql.VARCHAR(length=36), nullable=False),
    sa.Column('name', mysql.VARCHAR(length=255), nullable=True),
    sa.Column('email', mysql.VARCHAR(length=191), nullable=False),
    sa.Column('university', mysql.VARCHAR(length=255), nullable=True),
    sa.Column('created_at', mysql.DATETIME(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    mysql_collate='utf8mb4_0900_ai_ci',
    mysql_default_charset='utf8mb4',
    mysql_engine='MyISAM'
    )
    op.create_index(op.f('ix_contacts_email'), 'contacts', ['email'], unique=True)


def downgrade() -> None:
    """Drop contacts table."""
    op.drop_index(op.f('ix_contacts_email'), table_name='contacts')
    op.drop_table('contacts')
