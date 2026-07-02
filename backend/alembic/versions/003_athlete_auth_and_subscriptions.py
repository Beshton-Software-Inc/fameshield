"""Athlete self-serve auth, address, subscriptions, payment methods, and product seed.

Revision ID: 003
Revises: 002
Create Date: 2026-07-01 12:00:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("athletes", sa.Column("hashed_password", sa.String(255), nullable=True))
    op.add_column("athletes", sa.Column("phone", sa.String(30), nullable=True))
    op.add_column("athletes", sa.Column("address_line1", sa.String(255), nullable=True))
    op.add_column("athletes", sa.Column("address_line2", sa.String(255), nullable=True))
    op.add_column("athletes", sa.Column("city", sa.String(100), nullable=True))
    op.add_column("athletes", sa.Column("state", sa.String(100), nullable=True))
    op.add_column("athletes", sa.Column("postal_code", sa.String(20), nullable=True))
    op.add_column("athletes", sa.Column("country", sa.String(2), nullable=True))
    op.add_column("athletes", sa.Column("stripe_customer_id", sa.String(255), nullable=True))
    op.add_column("athletes", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))

    op.create_index("ix_athletes_stripe_customer", "athletes", ["stripe_customer_id"])
    op.create_unique_constraint("uq_athletes_email", "athletes", ["email"])

    # organization_id becomes optional so self-serve athletes have no org
    op.alter_column("athletes", "organization_id", nullable=True)

    # products
    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(50), nullable=False, unique=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.String(1000), nullable=True),
        sa.Column("price_monthly_cents", sa.Integer, nullable=False),
        sa.Column("price_yearly_cents", sa.Integer, nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("stripe_product_id", sa.String(255), nullable=True),
        sa.Column("stripe_price_monthly_id", sa.String(255), nullable=True),
        sa.Column("stripe_price_yearly_id", sa.String(255), nullable=True),
        sa.Column("features", postgresql.JSON, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # athlete_subscriptions
    op.create_table(
        "athlete_subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "athlete_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("athletes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("products.id"),
            nullable=False,
        ),
        sa.Column(
            "billing_interval",
            sa.Enum("month", "year", name="billinginterval"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "trialing",
                "active",
                "past_due",
                "canceled",
                "incomplete",
                "unpaid",
                name="subscriptionstatus",
            ),
            nullable=False,
            server_default="incomplete",
        ),
        sa.Column("stripe_subscription_id", sa.String(255), nullable=True),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("amount_cents", sa.Integer, nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_athlete_subs_athlete", "athlete_subscriptions", ["athlete_id"])
    op.create_index("ix_athlete_subs_status", "athlete_subscriptions", ["status"])

    # payment_methods
    op.create_table(
        "payment_methods",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "athlete_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("athletes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("stripe_payment_method_id", sa.String(255), nullable=False),
        sa.Column("brand", sa.String(30), nullable=True),
        sa.Column("last4", sa.String(4), nullable=True),
        sa.Column("exp_month", sa.Integer, nullable=True),
        sa.Column("exp_year", sa.Integer, nullable=True),
        sa.Column("is_default", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("stripe_payment_method_id", name="uq_payment_methods_stripe_pm"),
    )
    op.create_index("ix_payment_methods_athlete", "payment_methods", ["athlete_id"])

    # Seed default products (Basic / Pro / Elite)
    products_table = sa.table(
        "products",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("slug", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.String),
        sa.column("price_monthly_cents", sa.Integer),
        sa.column("price_yearly_cents", sa.Integer),
        sa.column("currency", sa.String),
        sa.column("features", postgresql.JSON),
        sa.column("sort_order", sa.Integer),
    )
    op.bulk_insert(
        products_table,
        [
            {
                "id": "11111111-1111-1111-1111-111111111111",
                "slug": "basic",
                "name": "Basic",
                "description": "Essential monitoring for one social platform.",
                "price_monthly_cents": 1900,
                "price_yearly_cents": 19000,
                "currency": "USD",
                "features": [
                    "1 social platform monitored",
                    "Automated classification",
                    "Weekly summary email",
                ],
                "sort_order": 10,
            },
            {
                "id": "22222222-2222-2222-2222-222222222222",
                "slug": "pro",
                "name": "Pro",
                "description": "Advanced protection across all major platforms.",
                "price_monthly_cents": 4900,
                "price_yearly_cents": 49000,
                "currency": "USD",
                "features": [
                    "All social platforms",
                    "Priority classification queue",
                    "Evidence capture with chain of custody",
                    "Real-time alerts",
                ],
                "sort_order": 20,
            },
            {
                "id": "33333333-3333-3333-3333-333333333333",
                "slug": "elite",
                "name": "Elite",
                "description": "Full concierge protection with legal support.",
                "price_monthly_cents": 19900,
                "price_yearly_cents": 199000,
                "currency": "USD",
                "features": [
                    "Everything in Pro",
                    "Assigned protection specialist",
                    "Takedown workflow management",
                    "24/7 escalation support",
                    "Quarterly analytics review",
                ],
                "sort_order": 30,
            },
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_payment_methods_athlete", table_name="payment_methods")
    op.drop_table("payment_methods")

    op.drop_index("ix_athlete_subs_status", table_name="athlete_subscriptions")
    op.drop_index("ix_athlete_subs_athlete", table_name="athlete_subscriptions")
    op.drop_table("athlete_subscriptions")
    sa.Enum(name="subscriptionstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="billinginterval").drop(op.get_bind(), checkfirst=True)

    op.drop_table("products")

    op.drop_constraint("uq_athletes_email", "athletes", type_="unique")
    op.drop_index("ix_athletes_stripe_customer", table_name="athletes")
    op.alter_column("athletes", "organization_id", nullable=False)

    for col in [
        "last_login_at",
        "stripe_customer_id",
        "country",
        "postal_code",
        "state",
        "city",
        "address_line2",
        "address_line1",
        "phone",
        "hashed_password",
    ]:
        op.drop_column("athletes", col)
