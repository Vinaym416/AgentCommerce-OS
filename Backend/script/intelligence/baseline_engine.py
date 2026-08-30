import pandas as pd
import numpy as np
from pathlib import Path


# =============================================================================
# AGENTCOMMERCE OS — PHASE 01 STEP 05
# BASELINE INTELLIGENCE ENGINE
# =============================================================================

BASE_DIR = Path(__file__).resolve().parents[2]

FEATURE_DIR = BASE_DIR / "data" / "features"
OUTPUT_DIR = BASE_DIR / "data" / "intelligence"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


CUSTOMER_FILE = FEATURE_DIR / "customer_features.csv"
PRODUCT_FILE = FEATURE_DIR / "product_features.csv"
SESSION_FILE = FEATURE_DIR / "session_features.csv"


print("=" * 80)
print("AGENTCOMMERCE OS — BASELINE INTELLIGENCE ENGINE")
print("=" * 80)


# =============================================================================
# LOAD FEATURE DATA
# =============================================================================

customers = pd.read_csv(CUSTOMER_FILE)
products = pd.read_csv(PRODUCT_FILE)
sessions = pd.read_csv(SESSION_FILE)

print("\nLoaded:")
print(f"Customers : {len(customers):,}")
print(f"Products  : {len(products):,}")
print(f"Sessions  : {len(sessions):,}")


# =============================================================================
# NORMALIZATION HELPER
# =============================================================================

def minmax(series):
    minimum = series.min()
    maximum = series.max()

    if maximum == minimum:
        return pd.Series(0.5, index=series.index)

    return (series - minimum) / (maximum - minimum)


# =============================================================================
# CUSTOMER INTELLIGENCE
# =============================================================================

print("\nBuilding customer intelligence...")


customers["customer_affinity_score"] = (
    0.30 * minmax(customers["customer_purchase_rate"]) +
    0.25 * minmax(customers["customer_revenue"]) +
    0.15 * minmax(customers["customer_cart_rate"]) +
    0.15 * minmax(customers["customer_avg_engagement"]) +
    0.15 * minmax(customers["customer_avg_cart_intent"])
)


# Higher abandonment = lower immediate buying confidence
customers["customer_buying_confidence"] = (
    0.60 * customers["customer_purchase_rate"] +
    0.40 * (1 - customers["customer_abandonment_rate"])
)


# Customer price behavior
customers["customer_price_score"] = minmax(
    customers["customer_avg_price"]
)


# Customer discount dependence
customers["discount_dependence_score"] = minmax(
    customers["customer_avg_discount"]
)


# =============================================================================
# PRODUCT INTELLIGENCE
# =============================================================================

print("Building product intelligence...")


products["product_quality_score"] = (
    0.35 * minmax(products["product_conversion_rate"]) +
    0.25 * minmax(products["product_avg_rating"]) +
    0.20 * minmax(products["product_revenue"]) +
    0.20 * minmax(products["product_avg_helpful_votes"])
)


products["product_demand_score"] = (
    0.50 * minmax(products["product_sessions"]) +
    0.30 * minmax(products["product_purchases"]) +
    0.20 * minmax(products["product_revenue"])
)


products["product_conversion_score"] = minmax(
    products["product_conversion_rate"]
)


products["product_value_score"] = (
    0.50 * products["product_quality_score"] +
    0.30 * products["product_conversion_score"] +
    0.20 * products["product_demand_score"]
)


# =============================================================================
# SESSION INTELLIGENCE
# =============================================================================

print("Building session intelligence...")


sessions["session_intent_score"] = (
    0.45 * sessions["purchase_intent_score"] +
    0.30 * sessions["engagement_score"] +
    0.25 * sessions["added_to_cart"]
)


sessions["session_price_score"] = minmax(
    sessions["unit_price"]
)


sessions["session_discount_score"] = (
    sessions["discount_percent"] / 30.0
)


# =============================================================================
# MERGE CUSTOMER + PRODUCT INTELLIGENCE
# =============================================================================

print("Combining customer, product and session signals...")


customer_signal_columns = [
    "customer_id",
    "customer_affinity_score",
    "customer_buying_confidence",
    "customer_price_score",
    "discount_dependence_score",
    "customer_purchase_rate",
    "customer_revenue",
    "customer_avg_discount"
]


product_signal_columns = [
    "product_id",
    "product_category",
    "product_quality_score",
    "product_demand_score",
    "product_conversion_score",
    "product_value_score",
    "product_purchase_rate",
    "product_revenue",
    "product_avg_discount",
    "product_avg_rating"
]


session_signal_columns = [
    "session_id",
    "customer_id",
    "product_id",
    "product_category",
    "unit_price",
    "discount_percent",
    "added_to_cart",
    "engagement_score",
    "cart_intent",
    "purchase_intent_score",
    "session_intent_score",
    "session_price_score",
    "session_discount_score"
]


customer_signals = customers[customer_signal_columns]

product_signals = products[product_signal_columns]

session_signals = sessions[session_signal_columns]


decision_table = (
    session_signals
    .merge(
        customer_signals,
        on="customer_id",
        how="left"
    )
    .merge(
        product_signals,
        on=["product_id", "product_category"],
        how="left"
    )
)


# =============================================================================
# AGENT PURCHASE OPPORTUNITY
# =============================================================================

decision_table["purchase_opportunity_score"] = (
    0.35 * decision_table["session_intent_score"] +
    0.25 * decision_table["customer_buying_confidence"] +
    0.20 * decision_table["product_conversion_score"] +
    0.10 * decision_table["product_quality_score"] +
    0.10 * decision_table["product_demand_score"]
)


# =============================================================================
# DISCOUNT OPPORTUNITY
# =============================================================================

# IMPORTANT:
#
# This is NOT saying:
# "Give the customer a discount."
#
# It estimates whether a discount might be useful.
#
# The future Merchant Policy Agent will decide whether the discount
# is actually permitted.

discount_need = (
    0.45 * decision_table["discount_dependence_score"] +
    0.30 * decision_table["session_discount_score"] +
    0.25 * decision_table["session_price_score"]
)

decision_table["discount_opportunity_score"] = discount_need


# =============================================================================
# MERCHANT GROWTH OPPORTUNITY
# =============================================================================

decision_table["merchant_growth_score"] = (
    0.40 * decision_table["purchase_opportunity_score"] +
    0.25 * decision_table["product_value_score"] +
    0.20 * decision_table["product_demand_score"] +
    0.15 * decision_table["customer_affinity_score"]
)


# =============================================================================
# AGENT DECISION CLASSIFICATION
# =============================================================================

def classify_opportunity(score):

    if score >= 0.75:
        return "HIGH"

    if score >= 0.50:
        return "MEDIUM"

    return "LOW"


decision_table["opportunity_level"] = (
    decision_table["merchant_growth_score"]
    .apply(classify_opportunity)
)


# =============================================================================
# EXPLAINABILITY
# =============================================================================

def generate_reason(row):

    reasons = []

    if row["session_intent_score"] >= 0.65:
        reasons.append("strong_session_intent")

    if row["customer_buying_confidence"] >= 0.65:
        reasons.append("strong_customer_buying_history")

    if row["product_conversion_score"] >= 0.65:
        reasons.append("high_product_conversion")

    if row["product_quality_score"] >= 0.65:
        reasons.append("strong_product_quality")

    if row["product_demand_score"] >= 0.65:
        reasons.append("high_product_demand")

    if row["discount_opportunity_score"] >= 0.65:
        reasons.append("possible_discount_opportunity")

    if not reasons:
        reasons.append("insufficient_strong_signals")

    return "|".join(reasons)


decision_table["decision_reasons"] = (
    decision_table.apply(generate_reason, axis=1)
)


# =============================================================================
# AGENT ACTION SUGGESTION
# =============================================================================

def suggest_action(row):

    score = row["merchant_growth_score"]

    if score >= 0.75:

        if row["discount_opportunity_score"] >= 0.65:
            return "CONSIDER_TARGETED_OFFER"

        return "PRIORITIZE_PRODUCT"

    if score >= 0.50:

        return "CONTINUE_ENGAGEMENT"

    return "NO_ACTION"


decision_table["agent_action"] = (
    decision_table.apply(suggest_action, axis=1)
)


# =============================================================================
# SAVE
# =============================================================================

OUTPUT_FILE = OUTPUT_DIR / "baseline_decisions.csv"

decision_table.to_csv(
    OUTPUT_FILE,
    index=False
)


# =============================================================================
# REPORT
# =============================================================================

print("\n" + "=" * 80)
print("BASELINE INTELLIGENCE RESULTS")
print("=" * 80)

print("\nOpportunity distribution:")

print(
    decision_table["opportunity_level"]
    .value_counts()
    .to_string()
)


print("\nAgent action distribution:")

print(
    decision_table["agent_action"]
    .value_counts()
    .to_string()
)


print("\nAverage scores:")

print(
    decision_table[
        [
            "purchase_opportunity_score",
            "discount_opportunity_score",
            "merchant_growth_score"
        ]
    ]
    .mean()
    .round(4)
    .to_string()
)


print("\nTop opportunities:")

top = (
    decision_table
    .sort_values(
        "merchant_growth_score",
        ascending=False
    )
    [
        [
            "session_id",
            "customer_id",
            "product_id",
            "purchase_opportunity_score",
            "discount_opportunity_score",
            "merchant_growth_score",
            "opportunity_level",
            "agent_action",
            "decision_reasons"
        ]
    ]
    .head(10)
)


print(top.to_string(index=False))


print("\n" + "=" * 80)
print("OUTPUT")
print("=" * 80)

print(f"\n{OUTPUT_FILE}")

print("\nPHASE 01 STEP 05 COMPLETE")
print("=" * 80)