"""Password reset tokens for both athletes and staff users.

Revision ID: 005
Revises: 004
Create Date: 2026-07-02 06:00:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        # 'athlete' or 'staff' — which subject table the token points at.
        sa.Column("audience", sa.String(16), nullable=False),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=False),
        # SHA-256 hex of the raw token. Raw token is never stored.
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_password_reset_tokens_subject",
        "password_reset_tokens",
        ["audience", "subject_id"],
    )
    op.create_index(
        "ix_password_reset_tokens_expires",
        "password_reset_tokens",
        ["expires_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_password_reset_tokens_expires", table_name="password_reset_tokens")
    op.drop_index("ix_password_reset_tokens_subject", table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")
