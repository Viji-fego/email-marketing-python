"""Create contact_lists table

Revision ID: 20260805120006
Revises: 20260805120005
Create Date: 2026-08-05 12:00:06.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision: str = '20260805120006'
down_revision: Union[str, Sequence[str], None] = '20260805120005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create contact_lists table."""
    op.create_table('contact_lists',
    sa.Column('id', mysql.VARCHAR(length=36), nullable=False),
    sa.Column('user_id', mysql.VARCHAR(length=36), nullable=False),
    sa.Column('name', mysql.VARCHAR(length=255), nullable=False),
    sa.Column('description', mysql.TEXT(), nullable=True),
    sa.Column('contact_count', sa.Integer(), server_default='0', nullable=False),
    sa.Column('created_at', mysql.DATETIME(), nullable=True),
    sa.Column('updated_at', mysql.DATETIME(), nullable=True),
    sa.Column('is_active', mysql.ENUM('0', '1'), server_default='1', nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    mysql_collate='utf8mb4_0900_ai_ci',
    mysql_default_charset='utf8mb4',
    mysql_engine='MyISAM'
    )
    op.create_index(op.f('ix_contact_lists_user_id'), 'contact_lists', ['user_id'])
    op.create_index(op.f('ix_contact_lists_is_active'), 'contact_lists', ['is_active'])


def downgrade() -> None:
    """Drop contact_lists table."""
    op.drop_index(op.f('ix_contact_lists_is_active'), table_name='contact_lists')
    op.drop_index(op.f('ix_contact_lists_user_id'), table_name='contact_lists')
    op.drop_table('contact_lists')
