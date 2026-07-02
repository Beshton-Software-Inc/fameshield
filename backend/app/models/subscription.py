"""Subscription, product, and payment method models."""
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import uuid4
import enum

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.athlete import Athlete


class BillingInterval(str, enum.Enum):
    MONTH = "month"
    YEAR = "year"


class SubscriptionStatus(str, enum.Enum):
    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    INCOMPLETE = "incomplete"
    UNPAID = "unpaid"


class Product(Base):
    """A subscription plan (Basic / Pro / Elite / etc.)."""

    __tablename__ = "products"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    price_monthly_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    price_yearly_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD")

    # Stripe references — populated once synced. Nullable so we can seed local-only in dev.
    stripe_product_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    stripe_price_monthly_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    stripe_price_yearly_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    features: Mapped[list] = mapped_column(JSON, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )


class AthleteSubscription(Base):
    """An athlete's active or historical subscription to a Product."""

    __tablename__ = "athlete_subscriptions"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    athlete_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("athletes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id"), nullable=False
    )

    billing_interval: Mapped[BillingInterval] = mapped_column(
        Enum(BillingInterval, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus, values_callable=lambda x: [e.value for e in x]),
        default=SubscriptionStatus.INCOMPLETE,
        index=True,
    )

    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    current_period_start: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    current_period_end: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False)
    canceled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    athlete: Mapped["Athlete"] = relationship("Athlete", back_populates="subscriptions")
    product: Mapped["Product"] = relationship("Product")


class PaymentMethod(Base):
    """A tokenized payment method (Stripe payment_method) attached to an athlete."""

    __tablename__ = "payment_methods"
    __table_args__ = (
        UniqueConstraint("stripe_payment_method_id", name="uq_payment_methods_stripe_pm"),
    )

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    athlete_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("athletes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    stripe_payment_method_id: Mapped[str] = mapped_column(String(255), nullable=False)
    brand: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)  # visa, mastercard, ...
    last4: Mapped[Optional[str]] = mapped_column(String(4), nullable=True)
    exp_month: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    exp_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    athlete: Mapped["Athlete"] = relationship("Athlete", back_populates="payment_methods")
