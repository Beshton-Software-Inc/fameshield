"""Thin Stripe wrapper with a no-key stub fallback for local dev.

If STRIPE_SECRET_KEY is set, calls hit Stripe. Otherwise, methods return
plausible fake IDs so the subscription state machine can be exercised end-to-end
without a real Stripe account. All persistent state lives in our DB either way.
"""
from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4

import stripe

from app.config import settings


def is_live() -> bool:
    return bool(settings.stripe_secret_key)


def _configure() -> None:
    if is_live():
        stripe.api_key = settings.stripe_secret_key


class StripeService:
    """Wraps the tiny subset of Stripe operations the app needs."""

    @staticmethod
    def create_customer(email: str, name: str) -> str:
        _configure()
        if not is_live():
            return f"cus_stub_{uuid4().hex[:12]}"
        customer = stripe.Customer.create(email=email, name=name)
        return customer.id

    @staticmethod
    def create_setup_intent(customer_id: str) -> dict:
        _configure()
        if not is_live():
            return {
                "client_secret": f"seti_stub_{uuid4().hex[:16]}_secret_stub",
                "customer": customer_id,
            }
        intent = stripe.SetupIntent.create(customer=customer_id, usage="off_session")
        return {"client_secret": intent.client_secret, "customer": customer_id}

    @staticmethod
    def create_subscription(
        customer_id: str, stripe_price_id: Optional[str]
    ) -> dict:
        _configure()
        now = datetime.utcnow()
        if not is_live() or not stripe_price_id:
            return {
                "id": f"sub_stub_{uuid4().hex[:12]}",
                "status": "active",
                "current_period_start": int(now.timestamp()),
                "current_period_end": int((now + timedelta(days=30)).timestamp()),
                "cancel_at_period_end": False,
            }
        sub = stripe.Subscription.create(
            customer=customer_id,
            items=[{"price": stripe_price_id}],
            payment_behavior="default_incomplete",
            expand=["latest_invoice.payment_intent"],
        )
        return _sub_to_dict(sub)

    @staticmethod
    def update_subscription(
        stripe_subscription_id: Optional[str], new_price_id: Optional[str]
    ) -> dict:
        _configure()
        if not is_live() or not stripe_subscription_id or stripe_subscription_id.startswith("sub_stub_"):
            now = datetime.utcnow()
            return {
                "id": stripe_subscription_id or f"sub_stub_{uuid4().hex[:12]}",
                "status": "active",
                "current_period_start": int(now.timestamp()),
                "current_period_end": int((now + timedelta(days=30)).timestamp()),
                "cancel_at_period_end": False,
            }
        sub = stripe.Subscription.retrieve(stripe_subscription_id)
        stripe.Subscription.modify(
            stripe_subscription_id,
            cancel_at_period_end=False,
            proration_behavior="create_prorations",
            items=[{"id": sub["items"]["data"][0].id, "price": new_price_id}],
        )
        sub = stripe.Subscription.retrieve(stripe_subscription_id)
        return _sub_to_dict(sub)

    @staticmethod
    def cancel_subscription(
        stripe_subscription_id: Optional[str], at_period_end: bool = True
    ) -> dict:
        _configure()
        if not is_live() or not stripe_subscription_id or stripe_subscription_id.startswith("sub_stub_"):
            return {
                "id": stripe_subscription_id or f"sub_stub_{uuid4().hex[:12]}",
                "status": "canceled" if not at_period_end else "active",
                "cancel_at_period_end": at_period_end,
            }
        if at_period_end:
            sub = stripe.Subscription.modify(
                stripe_subscription_id, cancel_at_period_end=True
            )
        else:
            sub = stripe.Subscription.delete(stripe_subscription_id)
        return _sub_to_dict(sub)


def _sub_to_dict(sub) -> dict:
    return {
        "id": sub.id,
        "status": sub.status,
        "current_period_start": sub.current_period_start,
        "current_period_end": sub.current_period_end,
        "cancel_at_period_end": bool(sub.cancel_at_period_end),
    }
