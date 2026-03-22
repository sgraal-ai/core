"""
One-time Stripe setup: creates the meter, product, and graduated price
with a 10,000-call free tier for omega_mem_preflight billing.

Usage:
    STRIPE_SECRET_KEY=sk_test_... python scripts/setup_stripe.py
"""

import os
import stripe

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
if not stripe.api_key:
    raise SystemExit("STRIPE_SECRET_KEY environment variable is required")

# 1. Create the meter
meter = stripe.billing.Meter.create(
    display_name="Omega Mem Preflight",
    event_name="omega_mem_preflight",
    default_aggregation={"formula": "sum"},
    customer_mapping={
        "type": "by_id",
        "event_payload_key": "stripe_customer_id",
    },
    value_settings={"event_payload_key": "value"},
)
print(f"Meter created: {meter.id}")

# 2. Create the product
product = stripe.Product.create(
    name="Sgraal Preflight API",
    description="Memory governance preflight checks for AI agents",
)
print(f"Product created: {product.id}")

# 3. Create graduated price: first 10,000 free, then $0.001 per call
price = stripe.Price.create(
    product=product.id,
    currency="usd",
    billing_scheme="tiered",
    tiers_mode="graduated",
    tiers=[
        {"up_to": 10000, "unit_amount": 0, "flat_amount": 0},
        {"up_to": "inf", "unit_amount_decimal": "0.1"},  # $0.001 per call
    ],
    recurring={
        "interval": "month",
        "usage_type": "metered",
        "meter": meter.id,
    },
)
print(f"Price created: {price.id}")

print(
    f"\nSetup complete. Attach price {price.id} to customer subscriptions.\n"
    f"First 10,000 preflight calls per month are free."
)
