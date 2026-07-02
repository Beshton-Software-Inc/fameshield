"""Backfill: attach self-serve athletes (organization_id IS NULL) to a shared
'FameShield Self-Serve' organization so they surface in the admin dashboard.

Revision ID: 004
Revises: 003
Create Date: 2026-07-02 05:00:00
"""
from typing import Sequence, Union
from uuid import UUID as _UUID, uuid4

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SELF_SERVE_ORG_NAME = "FameShield Self-Serve"


def upgrade() -> None:
    conn = op.get_bind()

    org_id_row = conn.execute(
        sa.text("SELECT id FROM organizations WHERE name = :name"),
        {"name": SELF_SERVE_ORG_NAME},
    ).first()

    if org_id_row is None:
        org_id = uuid4()
        conn.execute(
            sa.text(
                """
                INSERT INTO organizations (id, name, type, tier, settings, created_at, updated_at)
                VALUES (:id, :name, 'individual', 'starter', :settings, now(), now())
                """
            ),
            {
                "id": org_id,
                "name": SELF_SERVE_ORG_NAME,
                "settings": '{"monitoring_frequency": 15, "severity_thresholds": {}, "escalation_rules": {}, "allowed_platforms": ["twitter", "instagram", "tiktok", "youtube"]}',
            },
        )
    else:
        org_id = org_id_row[0]

    conn.execute(
        sa.text(
            "UPDATE athletes SET organization_id = :org_id WHERE organization_id IS NULL"
        ),
        {"org_id": org_id},
    )


def downgrade() -> None:
    # Reversing the backfill would require knowing which athletes were previously
    # NULL vs org-attached, which we don't track. Leave the association in place.
    pass
