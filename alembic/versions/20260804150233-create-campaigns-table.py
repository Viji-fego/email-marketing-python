"""Create campaigns table

Revision ID: 20260804150233
Revises: 20260804150232
Create Date: 2026-08-04 15:02:33.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '20260804150233'
down_revision: Union[str, Sequence[str], None] = '20260804150232'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create campaigns table."""
    op.create_table('campaigns',
    sa.Column('id', mysql.VARCHAR(length=36), nullable=False),
    sa.Column('name', mysql.VARCHAR(length=255), nullable=False),
    sa.Column('status', mysql.VARCHAR(length=50), nullable=True),
    sa.Column('created_at', mysql.DATETIME(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    mysql_collate='utf8mb4_0900_ai_ci',
    mysql_default_charset='utf8mb4',
    mysql_engine='MyISAM'
    )


def downgrade() -> None:
    """Drop campaigns table."""
    op.drop_table('campaigns')
