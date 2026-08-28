from pathlib import Path
import pandas as pd
import numpy as np


# ============================================================
# AGENTCOMMERCE OS
# PHASE 01 — STEP 03
# DATA QUALITY + SIGNAL + LEAKAGE ANALYSIS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

DATA_PATH = BASE_DIR / "data" / "indian" / "Ecommerce.csv"


def section(title):
    print("\n")
    print("=" * 80)
    print(title)
    print("=" * 80)


def analyze_dataset(df):

    # ========================================================
    # BASIC INFORMATION
    # ========================================================

    section("BASIC DATASET INFORMATION")

    print(f"Rows              : {len(df):,}")
    print(f"Columns           : {len(df.columns)}")
    print(f"Unique customers  : {df['customer_id'].nunique():,}")
    print(f"Unique sessions   : {df['session_id'].nunique():,}")
    print(f"Unique products   : {df['product_id'].nunique():,}")
    print(f"Unique categories : {df['product_category'].nunique():,}")

    # ========================================================
    # DUPLICATES
    # ========================================================

    section("DUPLICATE ANALYSIS")

    print("Full duplicate rows:", df.duplicated().sum())

    print(
        "Duplicate session IDs:",
        df["session_id"].duplicated().sum()
    )

    # ========================================================
    # MISSING VALUES
    # ========================================================

    section("MISSING VALUE ANALYSIS")

    missing = df.isnull().sum()

    print(
        missing[missing > 0]
        if missing.sum() > 0
        else "No missing values found."
    )

    # ========================================================
    # UNIQUE VALUE ANALYSIS
    # ========================================================

    section("FEATURE CARDINALITY")

    for column in df.columns:

        unique_count = df[column].nunique()

        print(
            f"{column:<25} "
            f"unique={unique_count:<8} "
            f"dtype={str(df[column].dtype)}"
        )

    # ========================================================
    # TARGET DISTRIBUTION
    # ========================================================

    section("PURCHASE TARGET")

    print(
        df["purchased"]
        .value_counts()
        .sort_index()
    )

    print("\nPurchase rate:")

    print(
        df["purchased"].mean() * 100,
        "%"
    )

    # ========================================================
    # CART / PURCHASE LOGIC
    # ========================================================

    section("FUNNEL LOGIC CONSISTENCY")

    print(
        "Added to cart:",
        df["added_to_cart"].sum()
    )

    print(
        "Purchased:",
        df["purchased"].sum()
    )

    print(
        "Cart abandoned:",
        df["cart_abandoned"].sum()
    )

    print()

    print(
        "Purchased WITHOUT adding to cart:",
        (
            (df["purchased"] == 1)
            & (df["added_to_cart"] == 0)
        ).sum()
    )

    print(
        "Abandoned WITHOUT adding to cart:",
        (
            (df["cart_abandoned"] == 1)
            & (df["added_to_cart"] == 0)
        ).sum()
    )

    print(
        "Purchased AND abandoned:",
        (
            (df["purchased"] == 1)
            & (df["cart_abandoned"] == 1)
        ).sum()
    )

    # ========================================================
    # REVENUE CONSISTENCY
    # ========================================================

    section("REVENUE CONSISTENCY")

    calculated_revenue = (
        df["unit_price"] * df["quantity"]
        - df["discount_amount"]
    )

    revenue_difference = (
        calculated_revenue - df["revenue"]
    ).abs()

    print(
        "Rows with revenue mismatch:",
        (revenue_difference > 0.01).sum()
    )

    print(
        "Maximum revenue difference:",
        revenue_difference.max()
    )

    print(
        "Purchased with zero revenue:",
        (
            (df["purchased"] == 1)
            & (df["revenue"] == 0)
        ).sum()
    )

    print(
        "Not purchased with positive revenue:",
        (
            (df["purchased"] == 0)
            & (df["revenue"] > 0)
        ).sum()
    )

    # ========================================================
    # DISCOUNT CONSISTENCY
    # ========================================================

    section("DISCOUNT CONSISTENCY")

    calculated_discount = (
        df["unit_price"]
        * df["quantity"]
        * df["discount_percent"]
        / 100
    )

    discount_difference = (
        calculated_discount - df["discount_amount"]
    ).abs()

    print(
        "Rows with discount mismatch:",
        (discount_difference > 0.05).sum()
    )

    print(
        "Maximum discount difference:",
        discount_difference.max()
    )

    # ========================================================
    # PRICE / QUANTITY VALIDATION
    # ========================================================

    section("NUMERIC RANGE VALIDATION")

    numeric_columns = [
        "unit_price",
        "quantity",
        "discount_percent",
        "discount_amount",
        "revenue",
        "pages_viewed",
        "time_on_site_sec",
        "rating",
        "review_helpful_votes",
        "revenue_normalized"
    ]

    for column in numeric_columns:

        print(
            f"\n{column}"
        )

        print(
            f"  min    : {df[column].min()}"
        )

        print(
            f"  max    : {df[column].max()}"
        )

        print(
            f"  mean   : {df[column].mean():.4f}"
        )

        print(
            f"  median : {df[column].median():.4f}"
        )

    # ========================================================
    # DISCOUNT VS PURCHASE
    # ========================================================

    section("PURCHASE RATE BY DISCOUNT")

    discount_analysis = (
        df.groupby("discount_percent")
        .agg(
            sessions=("session_id", "count"),
            purchases=("purchased", "sum"),
            revenue=("revenue", "sum")
        )
    )

    discount_analysis["purchase_rate"] = (
        discount_analysis["purchases"]
        / discount_analysis["sessions"]
        * 100
    )

    print(
        discount_analysis.to_string()
    )

    # ========================================================
    # CATEGORY SIGNAL
    # ========================================================

    section("CATEGORY SIGNAL")

    category_analysis = (
        df.groupby("product_category")
        .agg(
            sessions=("session_id", "count"),
            purchases=("purchased", "sum"),
            revenue=("revenue", "sum"),
            avg_price=("unit_price", "mean"),
            avg_discount=("discount_percent", "mean")
        )
    )

    category_analysis["purchase_rate"] = (
        category_analysis["purchases"]
        / category_analysis["sessions"]
        * 100
    )

    print(
        category_analysis.to_string()
    )

    # ========================================================
    # PRODUCT SIGNAL
    # ========================================================

    section("PRODUCT SIGNAL")

    product_analysis = (
        df.groupby("product_id")
        .agg(
            sessions=("session_id", "count"),
            purchases=("purchased", "sum"),
            revenue=("revenue", "sum"),
            avg_price=("unit_price", "mean"),
            avg_discount=("discount_percent", "mean")
        )
    )

    product_analysis["purchase_rate"] = (
        product_analysis["purchases"]
        / product_analysis["sessions"]
        * 100
    )

    print("\nTop products by revenue:")

    print(
        product_analysis
        .sort_values("revenue", ascending=False)
        .head(10)
        .to_string()
    )

    print("\nTop products by purchase rate:")

    # Require at least 20 sessions to avoid tiny-sample products
    reliable_products = product_analysis[
        product_analysis["sessions"] >= 20
    ]

    print(
        reliable_products
        .sort_values("purchase_rate", ascending=False)
        .head(10)
        .to_string()
    )

    # ========================================================
    # CUSTOMER SIGNAL
    # ========================================================

    section("CUSTOMER SIGNAL")

    customer_analysis = (
        df.groupby("customer_id")
        .agg(
            sessions=("session_id", "count"),
            purchases=("purchased", "sum"),
            revenue=("revenue", "sum"),
            avg_price=("unit_price", "mean"),
            avg_discount=("discount_percent", "mean"),
            avg_time=("time_on_site_sec", "mean"),
            avg_pages=("pages_viewed", "mean")
        )
    )

    customer_analysis["purchase_rate"] = (
        customer_analysis["purchases"]
        / customer_analysis["sessions"]
        * 100
    )

    print("\nTop customers by revenue:")

    print(
        customer_analysis
        .sort_values("revenue", ascending=False)
        .head(10)
        .to_string()
    )

    # ========================================================
    # CORRELATION — PURCHASE
    # ========================================================

    section("CORRELATION WITH PURCHASE")

    purchase_features = [
        "unit_price",
        "quantity",
        "discount_percent",
        "discount_amount",
        "pages_viewed",
        "time_on_site_sec",
        "added_to_cart",
        "cart_abandoned",
        "rating",
        "review_helpful_votes",
        "revenue"
    ]

    purchase_corr = (
        df[purchase_features + ["purchased"]]
        .corr(numeric_only=True)["purchased"]
        .sort_values(ascending=False)
    )

    print(
        purchase_corr.to_string()
    )

    # ========================================================
    # CORRELATION — REVENUE
    # ========================================================

    section("CORRELATION WITH REVENUE")

    revenue_features = [
        "unit_price",
        "quantity",
        "discount_percent",
        "discount_amount",
        "pages_viewed",
        "time_on_site_sec",
        "added_to_cart",
        "purchased",
        "cart_abandoned",
        "rating",
        "review_helpful_votes"
    ]

    revenue_corr = (
        df[revenue_features + ["revenue"]]
        .corr(numeric_only=True)["revenue"]
        .sort_values(ascending=False)
    )

    print(
        revenue_corr.to_string()
    )

    # ========================================================
    # POTENTIAL DATA LEAKAGE
    # ========================================================

    section("POTENTIAL DATA LEAKAGE")

    print(
        """
For PURCHASE prediction:

SAFE BEFORE PURCHASE
--------------------
customer_id
device_type
user_type
marketing_channel
product_id
product_category
unit_price
quantity
discount_percent
pages_viewed
time_on_site_sec
rating
review_helpful_votes
location
visit date/time features

POTENTIAL LEAKAGE
-----------------
revenue
revenue_normalized
purchased
cart_abandoned
discount_amount

The leakage decision will be finalized after examining
the actual relationships above.
"""
    )

    # ========================================================
    # TARGET DEPENDENCY
    # ========================================================

    section("TARGET DEPENDENCY CHECK")

    leakage_columns = [
        "revenue",
        "revenue_normalized",
        "cart_abandoned",
        "discount_amount"
    ]

    for column in leakage_columns:

        if column in df.columns:

            print(
                f"\n{column}"
            )

            print(
                pd.crosstab(
                    df[column],
                    df["purchased"],
                    normalize="index"
                )
                .head(20)
                .to_string()
            )

    # ========================================================
    # DATASET GENERATION SIGNAL
    # ========================================================

    section("DATA GENERATION / SYNTHETIC SIGNAL CHECK")

    print(
        "Product category distribution:"
    )

    print(
        df["product_category"]
        .value_counts()
        .sort_index()
        .to_string()
    )

    print(
        "\nDiscount distribution:"
    )

    print(
        df["discount_percent"]
        .value_counts()
        .sort_index()
        .to_string()
    )

    print(
        "\nPayment method distribution:"
    )

    print(
        df["payment_method"]
        .value_counts()
        .sort_index()
        .to_string()
    )

    print(
        "\nDevice distribution:"
    )

    print(
        df["device_type"]
        .value_counts()
        .sort_index()
        .to_string()
    )

    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    section("PHASE 01 — STEP 03 SUMMARY")

    print(
        """
The purpose of this analysis is NOT to train a model yet.

We are determining:

1. Which columns represent pre-purchase information.
2. Which columns are post-purchase information.
3. Whether revenue calculations are internally consistent.
4. Whether cart/purchase logic is internally consistent.
5. Which variables contain useful behavioral signal.
6. Whether the dataset contains synthetic-generation artifacts.
7. Which features can safely enter the future AI models.
"""
    )


def main():

    print("\n")
    print("#" * 80)
    print("# AGENTCOMMERCE OS — PHASE 01 DATA ANALYSIS")
    print("#" * 80)

    if not DATA_PATH.exists():

        print(
            f"\nERROR: Dataset not found:\n{DATA_PATH}"
        )

        return

    df = pd.read_csv(DATA_PATH)

    analyze_dataset(df)

    print("\n")
    print("#" * 80)
    print("# ANALYSIS COMPLETE")
    print("#" * 80)


if __name__ == "__main__":
    main()