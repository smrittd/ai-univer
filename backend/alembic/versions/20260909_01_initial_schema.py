"""initial AI University schema

Revision ID: 20260909_01
Revises:
Create Date: 2026-09-09
"""
from alembic import op

import app.models  # noqa: F401
from app.core.database import Base

revision = "20260909_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # This baseline deliberately uses the single SQLAlchemy metadata source so the ORM and
    # migration cannot drift before the first released schema. Later revisions are additive.
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
