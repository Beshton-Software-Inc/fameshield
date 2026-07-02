"""Product catalog, athlete subscription lifecycle, and Stripe webhook."""
from datetime import datetime
from typing import Optional
from uuid import UUID

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.athlete_auth import get_current_athlete
from app.config import settings
from app.database import get_db
from app.models.athlete import Athlete
from app.models.subscription import (
    AthleteSubscription,
    BillingInterval,
    PaymentMethod,
    Product,
    SubscriptionStatus,
)
from app.services.stripe_service import StripeService, is_live as stripe_live

router = APIRouter(tags=["subscriptions"])


class ProductResponse(BaseModel):
    id: UUID
    slug: str
    name: str
    description: Optional[str] = None
    price_monthly_cents: int
    price_yearly_cents: int
    currency: str
    features: list
    is_active: bool

    class Config:
        from_attributes = True


class SubscribeRequest(BaseModel):
    product_id: UUID
    billing_interval: BillingInterval
    payment_method_id: Optional[UUID] = None  # existing PaymentMethod row


class ChangeSubscriptionRequest(BaseModel):
    product_id: UUID
    billing_interval: BillingInterval


class SubscriptionResponse(BaseModel):
    id: UUID
    product_id: UUID
    product_slug: str
    product_name: str
    billing_interval: BillingInterval
    status: SubscriptionStatus
    amount_cents: int
    currency: str
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool
    canceled_at: Optional[datetime] = None
    stripe_publishable_key: Optional[str] = None


class PaymentMethodResponse(BaseModel):
    id: UUID
    brand: Optional[str] = None
    last4: Optional[str] = None
    exp_month: Optional[int] = None
    exp_year: Optional[int] = None
    is_default: bool

    class Config:
        from_attributes = True


class SetupIntentResponse(BaseModel):
    client_secret: str
    publishable_key: Optional[str] = None
    stub_mode: bool


class PaymentMethodAttach(BaseModel):
    stripe_payment_method_id: str
    brand: Optional[str] = None
    last4: Optional[str] = None
    exp_month: Optional[int] = None
    exp_year: Optional[int] = None
    make_default: bool = True


@router.get("/products", response_model=list[ProductResponse])
async def list_products(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Product).where(Product.is_active.is_(True)).order_by(Product.sort_order)
    )
    return list(result.scalars().all())


async def _ensure_customer(athlete: Athlete, db: AsyncSession) -> str:
    if athlete.stripe_customer_id:
        return athlete.stripe_customer_id
    customer_id = StripeService.create_customer(athlete.email, athlete.full_name)
    athlete.stripe_customer_id = customer_id
    await db.commit()
    return customer_id


def _price_for(product: Product, interval: BillingInterval) -> tuple[int, Optional[str]]:
    if interval == BillingInterval.MONTH:
        return product.price_monthly_cents, product.stripe_price_monthly_id
    return product.price_yearly_cents, product.stripe_price_yearly_id


def _to_response(sub: AthleteSubscription, product: Product) -> SubscriptionResponse:
    return SubscriptionResponse(
        id=sub.id,
        product_id=product.id,
        product_slug=product.slug,
        product_name=product.name,
        billing_interval=sub.billing_interval,
        status=sub.status,
        amount_cents=sub.amount_cents,
        currency=sub.currency,
        current_period_start=sub.current_period_start,
        current_period_end=sub.current_period_end,
        cancel_at_period_end=sub.cancel_at_period_end,
        canceled_at=sub.canceled_at,
        stripe_publishable_key=settings.stripe_publishable_key,
    )


async def _active_subscription(
    athlete_id: UUID, db: AsyncSession
) -> Optional[AthleteSubscription]:
    result = await db.execute(
        select(AthleteSubscription)
        .where(
            AthleteSubscription.athlete_id == athlete_id,
            AthleteSubscription.status.in_(
                [
                    SubscriptionStatus.TRIALING,
                    SubscriptionStatus.ACTIVE,
                    SubscriptionStatus.PAST_DUE,
                    SubscriptionStatus.INCOMPLETE,
                    SubscriptionStatus.UNPAID,
                ]
            ),
        )
        .order_by(AthleteSubscription.created_at.desc())
    )
    return result.scalars().first()


@router.get("/me/subscription", response_model=Optional[SubscriptionResponse])
async def get_my_subscription(
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    sub = await _active_subscription(athlete.id, db)
    if not sub:
        return None
    product = (await db.execute(select(Product).where(Product.id == sub.product_id))).scalar_one()
    return _to_response(sub, product)


@router.post(
    "/me/subscription",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def subscribe(
    payload: SubscribeRequest,
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    existing = await _active_subscription(athlete.id, db)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Athlete already has an active subscription. Use PATCH to change plans.",
        )

    product = (
        await db.execute(select(Product).where(Product.id == payload.product_id))
    ).scalar_one_or_none()
    if not product or not product.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )

    customer_id = await _ensure_customer(athlete, db)
    amount, stripe_price_id = _price_for(product, payload.billing_interval)
    stripe_sub = StripeService.create_subscription(customer_id, stripe_price_id)

    sub = AthleteSubscription(
        athlete_id=athlete.id,
        product_id=product.id,
        billing_interval=payload.billing_interval,
        status=SubscriptionStatus(stripe_sub["status"])
        if stripe_sub.get("status") in {s.value for s in SubscriptionStatus}
        else SubscriptionStatus.ACTIVE,
        stripe_subscription_id=stripe_sub["id"],
        current_period_start=_ts_to_dt(stripe_sub.get("current_period_start")),
        current_period_end=_ts_to_dt(stripe_sub.get("current_period_end")),
        cancel_at_period_end=stripe_sub.get("cancel_at_period_end", False),
        amount_cents=amount,
        currency=product.currency,
    )
    db.add(sub)
    await db.commit()
    await db.refresh(sub)
    return _to_response(sub, product)


@router.patch("/me/subscription", response_model=SubscriptionResponse)
async def change_subscription(
    payload: ChangeSubscriptionRequest,
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    sub = await _active_subscription(athlete.id, db)
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No active subscription to change"
        )
    product = (
        await db.execute(select(Product).where(Product.id == payload.product_id))
    ).scalar_one_or_none()
    if not product or not product.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )
    amount, stripe_price_id = _price_for(product, payload.billing_interval)
    stripe_sub = StripeService.update_subscription(sub.stripe_subscription_id, stripe_price_id)

    sub.product_id = product.id
    sub.billing_interval = payload.billing_interval
    sub.amount_cents = amount
    sub.currency = product.currency
    sub.status = (
        SubscriptionStatus(stripe_sub["status"])
        if stripe_sub.get("status") in {s.value for s in SubscriptionStatus}
        else sub.status
    )
    sub.current_period_start = _ts_to_dt(stripe_sub.get("current_period_start")) or sub.current_period_start
    sub.current_period_end = _ts_to_dt(stripe_sub.get("current_period_end")) or sub.current_period_end
    sub.cancel_at_period_end = stripe_sub.get("cancel_at_period_end", False)
    sub.canceled_at = None
    await db.commit()
    await db.refresh(sub)
    return _to_response(sub, product)


@router.delete("/me/subscription", response_model=SubscriptionResponse)
async def cancel_subscription(
    at_period_end: bool = True,
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    sub = await _active_subscription(athlete.id, db)
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No active subscription"
        )
    product = (await db.execute(select(Product).where(Product.id == sub.product_id))).scalar_one()
    stripe_sub = StripeService.cancel_subscription(sub.stripe_subscription_id, at_period_end)
    sub.cancel_at_period_end = stripe_sub.get("cancel_at_period_end", at_period_end)
    if not at_period_end:
        sub.status = SubscriptionStatus.CANCELED
        sub.canceled_at = datetime.utcnow()
    await db.commit()
    await db.refresh(sub)
    return _to_response(sub, product)


@router.get("/me/payment-methods", response_model=list[PaymentMethodResponse])
async def list_payment_methods(
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.execute(
            select(PaymentMethod)
            .where(PaymentMethod.athlete_id == athlete.id)
            .order_by(PaymentMethod.is_default.desc(), PaymentMethod.created_at.desc())
        )
    ).scalars().all()
    return list(rows)


@router.post("/me/payment-methods/setup-intent", response_model=SetupIntentResponse)
async def create_setup_intent(
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    customer_id = await _ensure_customer(athlete, db)
    intent = StripeService.create_setup_intent(customer_id)
    return SetupIntentResponse(
        client_secret=intent["client_secret"],
        publishable_key=settings.stripe_publishable_key,
        stub_mode=not stripe_live(),
    )


@router.post(
    "/me/payment-methods",
    response_model=PaymentMethodResponse,
    status_code=status.HTTP_201_CREATED,
)
async def attach_payment_method(
    payload: PaymentMethodAttach,
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    if payload.make_default:
        existing = (
            await db.execute(
                select(PaymentMethod).where(PaymentMethod.athlete_id == athlete.id)
            )
        ).scalars().all()
        for pm in existing:
            pm.is_default = False

    pm = PaymentMethod(
        athlete_id=athlete.id,
        stripe_payment_method_id=payload.stripe_payment_method_id,
        brand=payload.brand,
        last4=payload.last4,
        exp_month=payload.exp_month,
        exp_year=payload.exp_year,
        is_default=payload.make_default,
    )
    db.add(pm)
    await db.commit()
    await db.refresh(pm)
    return pm


@router.post("/webhooks/stripe", status_code=status.HTTP_200_OK)
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(default=None, alias="Stripe-Signature"),
    db: AsyncSession = Depends(get_db),
):
    body = await request.body()
    if not stripe_live() or not settings.stripe_webhook_secret:
        # Accept and ignore in stub mode
        return {"received": True, "stub_mode": True}

    try:
        event = stripe.Webhook.construct_event(
            body, stripe_signature, settings.stripe_webhook_secret
        )
    except (ValueError, stripe.error.SignatureVerificationError) as e:  # type: ignore[attr-defined]
        raise HTTPException(status_code=400, detail=f"Invalid webhook: {e}")

    event_type = event["type"]
    data_object = event["data"]["object"]

    if event_type in {
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    }:
        stripe_sub_id = data_object["id"]
        result = await db.execute(
            select(AthleteSubscription).where(
                AthleteSubscription.stripe_subscription_id == stripe_sub_id
            )
        )
        sub = result.scalar_one_or_none()
        if sub:
            new_status = data_object.get("status")
            if new_status in {s.value for s in SubscriptionStatus}:
                sub.status = SubscriptionStatus(new_status)
            sub.current_period_start = _ts_to_dt(data_object.get("current_period_start"))
            sub.current_period_end = _ts_to_dt(data_object.get("current_period_end"))
            sub.cancel_at_period_end = bool(data_object.get("cancel_at_period_end"))
            if event_type == "customer.subscription.deleted":
                sub.status = SubscriptionStatus.CANCELED
                sub.canceled_at = datetime.utcnow()
            await db.commit()

    return {"received": True, "type": event_type}


def _ts_to_dt(ts: Optional[int]) -> Optional[datetime]:
    if ts is None:
        return None
    return datetime.utcfromtimestamp(int(ts))
