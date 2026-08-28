import pandas as pd
import numpy as np
from pathlib import Path


# ============================================================
# AGENTCOMMERCE OS — PHASE 01 STEP 04
# BUILD AGENT INTELLIGENCE FEATURES
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

INPUT_FILE = BASE_DIR / "data" / "indian" / "Ecommerce.csv"

OUTPUT_DIR = BASE_DIR / "data" / "features"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


print("=" * 80)
print("AGENTCOMMERCE OS — PHASE 01 STEP 04")
print("BUILDING AGENT INTELLIGENCE FEATURES")
print("=" * 80)


# ============================================================
# LOAD DATA
# ============================================================

df = pd.read_csv(INPUT_FILE)

print(f"\nLoaded dataset: {len(df):,} rows")


# ============================================================
# BASIC CLEANUP
# ============================================================

df["visit_date"] = pd.to_datetime(
    df["visit_date"],
    format="%d-%m-%Y",
    errors="coerce"
)

# Safety check
if df["visit_date"].isna().any():
    print("WARNING: Some visit_date values could not be parsed.")


# ============================================================
# DERIVED SESSION FEATURES
# ============================================================

df["effective_price"] = (
    df["unit_price"] -
    df["discount_amount"] / df["quantity"].replace(0, 1)
)

df["cart_intent"] = (
    0.5 * df["added_to_cart"] +
    0.3 * (df["pages_viewed"] / df["pages_viewed"].max()) +
    0.2 * (df["time_on_site_sec"] / df["time_on_site_sec"].max())
)

df["engagement_score"] = (
    0.5 * (df["pages_viewed"] / df["pages_viewed"].max()) +
    0.5 * (df["time_on_site_sec"] / df["time_on_site_sec"].max())
)


# ============================================================
# 1. CUSTOMER FEATURES
# ============================================================

print("\nBuilding customer features...")


customer_features = (
    df.groupby("customer_id")
    .agg(
        customer_sessions=("session_id", "count"),

        customer_purchases=("purchased", "sum"),

        customer_revenue=("revenue", "sum"),

        customer_avg_order_value=(
            "revenue",
            lambda x: x[x > 0].mean() if (x > 0).any() else 0
        ),

        customer_avg_price=("unit_price", "mean"),

        customer_avg_discount=("discount_percent", "mean"),

        customer_avg_quantity=("quantity", "mean"),

        customer_avg_session_time=("time_on_site_sec", "mean"),

        customer_avg_pages=("pages_viewed", "mean"),

        customer_cart_rate=("added_to_cart", "mean"),

        customer_abandonment_rate=("cart_abandoned", "mean"),

        customer_purchase_rate=("purchased", "mean"),

        customer_avg_rating=("rating", "mean"),

        customer_avg_helpful_votes=("review_helpful_votes", "mean"),

        customer_avg_engagement=("engagement_score", "mean"),

        customer_avg_cart_intent=("cart_intent", "mean"),
    )
    .reset_index()
)


# Number of purchased sessions
customer_features["customer_purchase_rate"] = (
    customer_features["customer_purchases"] /
    customer_features["customer_sessions"]
)


# Customer value score
customer_features["customer_value_score"] = (
    customer_features["customer_revenue"]
    .rank(pct=True)
)


# ============================================================
# CUSTOMER CATEGORY PREFERENCE
# ============================================================

customer_category = (
    df[df["purchased"] == 1]
    .groupby(["customer_id", "product_category"])
    .size()
    .reset_index(name="category_purchases")
)

customer_top_category = (
    customer_category
    .sort_values(
        ["customer_id", "category_purchases"],
        ascending=[True, False]
    )
    .drop_duplicates("customer_id")
    [["customer_id", "product_category"]]
    .rename(columns={
        "product_category": "preferred_category"
    })
)


customer_features = customer_features.merge(
    customer_top_category,
    on="customer_id",
    how="left"
)


# ============================================================
# 2. PRODUCT FEATURES
# ============================================================

print("Building product features...")


product_features = (
    df.groupby("product_id")
    .agg(
        product_sessions=("session_id", "count"),

        product_purchases=("purchased", "sum"),

        product_revenue=("revenue", "sum"),

        product_avg_price=("unit_price", "mean"),

        product_avg_discount=("discount_percent", "mean"),

        product_avg_quantity=("quantity", "mean"),

        product_avg_rating=("rating", "mean"),

        product_avg_helpful_votes=("review_helpful_votes", "mean"),

        product_cart_rate=("added_to_cart", "mean"),

        product_abandonment_rate=("cart_abandoned", "mean"),

        product_purchase_rate=("purchased", "mean"),

        product_avg_engagement=("engagement_score", "mean"),
    )
    .reset_index()
)


product_features["product_conversion_rate"] = (
    product_features["product_purchases"] /
    product_features["product_sessions"]
)


# ============================================================
# PRODUCT POPULARITY
# ============================================================

product_features["product_popularity_score"] = (
    product_features["product_sessions"]
    .rank(pct=True)
)


# ============================================================
# PRODUCT REVENUE SCORE
# ============================================================

product_features["product_revenue_score"] = (
    product_features["product_revenue"]
    .rank(pct=True)
)


# ============================================================
# PRODUCT CATEGORY
# ============================================================

product_category_map = (
    df[["product_id", "product_category"]]
    .drop_duplicates("product_id")
)

product_features = product_features.merge(
    product_category_map,
    on="product_id",
    how="left"
)


# ============================================================
# 3. SESSION FEATURES
# ============================================================

print("Building session features...")


session_columns = [
    "session_id",
    "customer_id",
    "product_id",
    "product_category",
    "unit_price",
    "quantity",
    "discount_percent",
    "pages_viewed",
    "time_on_site_sec",
    "added_to_cart",
    "purchased",
    "cart_abandoned",
    "rating",
    "location",
    "device_type",
    "user_type",
    "marketing_channel",
    "payment_method",
    "visit_date",
    "session_duration_bucket",
    "effective_price",
    "engagement_score",
    "cart_intent"
]


session_features = df[session_columns].copy()


# ============================================================
# SESSION INTENT FEATURES
# ============================================================

session_features["purchase_intent_score"] = (
    0.45 * session_features["cart_intent"] +
    0.30 * session_features["engagement_score"] +
    0.25 * session_features["added_to_cart"]
)


# ============================================================
# SESSION PRICE PRESSURE
# ============================================================

session_features["price_pressure_score"] = (
    session_features["unit_price"] /
    df["unit_price"].max()
)


# ============================================================
# SESSION DISCOUNT RESPONSE
# ============================================================

session_features["discount_score"] = (
    session_features["discount_percent"] / 30.0
)


# ============================================================
# SAVE
# ============================================================

customer_path = OUTPUT_DIR / "customer_features.csv"
product_path = OUTPUT_DIR / "product_features.csv"
session_path = OUTPUT_DIR / "session_features.csv"


customer_features.to_csv(customer_path, index=False)
product_features.to_csv(product_path, index=False)
session_features.to_csv(session_path, index=False)


# ============================================================
# SUMMARY
# ============================================================

print("\n" + "=" * 80)
print("FEATURE BUILD COMPLETE")
print("=" * 80)

print(f"\nCustomer features : {len(customer_features):,}")
print(f"Product features  : {len(product_features):,}")
print(f"Session features  : {len(session_features):,}")

print("\nGenerated files:")

print(f"  {customer_path}")
print(f"  {product_path}")
print(f"  {session_path}")


print("\nCustomer feature columns:")
print(customer_features.columns.tolist())

print("\nProduct feature columns:")
print(product_features.columns.tolist())

print("\nSession feature columns:")
print(session_features.columns.tolist())


print("\n" + "=" * 80)
print("PHASE 01 STEP 04 COMPLETE")
print("=" * 80)