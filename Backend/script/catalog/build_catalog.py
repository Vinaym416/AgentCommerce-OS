import os
import pandas as pd


# ============================================================
# AGENTCOMMERCE OS — PRODUCTION CATALOG BUILDER
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )
)

INPUT_FILE = os.path.join(
    BASE_DIR,
    "data",
    "indian",
    "Ecommerce.csv"
)

OUTPUT_DIR = os.path.join(
    BASE_DIR,
    "data",
    "catalog"
)

OUTPUT_FILE = os.path.join(
    OUTPUT_DIR,
    "product_catalog.csv"
)


# ------------------------------------------------------------
# CONFIGURATION
# ------------------------------------------------------------

MIN_PRODUCT_SESSIONS = 5

# Prior used for Bayesian smoothing.
# This prevents 1/1 or 2/2 products from appearing
# artificially better than well-established products.
PRIOR_SESSIONS = 10
PRIOR_PURCHASES = 2


def main():

    print("=" * 80)
    print("AGENTCOMMERCE OS — PRODUCTION CATALOG BUILDER")
    print("=" * 80)

    df = pd.read_csv(INPUT_FILE)

    print(f"Loaded sessions : {len(df):,}")

    # ========================================================
    # PRODUCT-LEVEL AGGREGATION
    # ========================================================
    #
    # IMPORTANT:
    # One product_id = one catalog product.
    #
    # We therefore aggregate ONLY by product_id.
    #

    catalog = (
        df.groupby("product_id", as_index=False)
        .agg(
           product_category=(
    "product_category",
    lambda values: (
        values.mode().iloc[0]
        if not values.mode().empty
        else pd.NA
    ),
),

            base_price=("unit_price", "median"),
            avg_price=("unit_price", "mean"),
            min_price=("unit_price", "min"),
            max_price=("unit_price", "max"),

            avg_discount_percent=("discount_percent", "mean"),

            total_sessions=("session_id", "count"),
            total_purchases=("purchased", "sum"),

            total_revenue=("revenue", "sum"),

            avg_rating=("rating", "mean"),
            avg_review_helpful_votes=(
                "review_helpful_votes",
                "mean"
            ),

            avg_pages_viewed=("pages_viewed", "mean"),
            avg_time_on_site=("time_on_site_sec", "mean"),

            cart_rate=("added_to_cart", "mean")
        )
    )

    # --------------------------------------------------------
    # Fix mode aggregation returning a Series
    # --------------------------------------------------------

    catalog["product_category"] = catalog[
        "product_category"
    ].apply(
        lambda x: x.iloc[0]
        if hasattr(x, "iloc")
        else x
    )

    # ========================================================
    # MINIMUM SUPPORT
    # ========================================================

    catalog = catalog[
        catalog["total_sessions"] >= MIN_PRODUCT_SESSIONS
    ].copy()

    # ========================================================
    # RAW CONVERSION
    # ========================================================

    catalog["raw_conversion_rate"] = (
        catalog["total_purchases"]
        /
        catalog["total_sessions"]
    )

    # ========================================================
    # BAYESIAN / SMOOTHED CONVERSION
    # ========================================================
    #
    # Prevents:
    #
    # 1 purchase / 1 session = 100%
    #
    # from automatically beating:
    #
    # 500 purchases / 1000 sessions = 50%
    #

    catalog["conversion_rate"] = (
        catalog["total_purchases"]
        + PRIOR_PURCHASES
    ) / (
        catalog["total_sessions"]
        + PRIOR_SESSIONS
    )

    # ========================================================
    # DEMAND SCORE
    # ========================================================

    max_sessions = max(
        catalog["total_sessions"].max(),
        1
    )

    catalog["demand_score"] = (
        catalog["total_sessions"]
        /
        max_sessions
    )

    # ========================================================
    # QUALITY SCORE
    # ========================================================

    max_helpful_votes = max(
        catalog["avg_review_helpful_votes"].max(),
        1
    )

    catalog["quality_score"] = (
        (catalog["avg_rating"] / 5.0) * 0.70
        +
        (
            catalog["avg_review_helpful_votes"]
            /
            max_helpful_votes
        ) * 0.30
    )

    # ========================================================
    # PRODUCT SCORE
    # ========================================================

    catalog["product_score"] = (
        catalog["conversion_rate"] * 0.45
        +
        catalog["demand_score"] * 0.25
        +
        catalog["quality_score"] * 0.30
    )

    # ========================================================
    # PRODUCT METADATA
    # ========================================================

    catalog["current_price"] = catalog["base_price"]

    catalog["currency"] = "INR"

    catalog["availability"] = "available"

    catalog["product_name"] = (
        "Product "
        +
        catalog["product_id"].astype(str)
    )

    catalog["category_name"] = (
        "Category "
        +
        catalog["product_category"].astype(str)
    )

    # ========================================================
    # MERCHANT POLICY DEFAULTS
    # ========================================================

    catalog["max_discount_percent"] = 15

    catalog["minimum_margin_percent"] = 10

    catalog["max_negotiations"] = 3

    # ========================================================
    # RETRIEVAL FLAGS
    # ========================================================

    catalog["retrieval_enabled"] = True

    catalog["agent_visible"] = True

    # ========================================================
    # SORT
    # ========================================================

    catalog = catalog.sort_values(
        "product_score",
        ascending=False
    )

    # ========================================================
    # OUTPUT
    # ========================================================

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )

    catalog.to_csv(
        OUTPUT_FILE,
        index=False
    )

    # ========================================================
    # REPORT
    # ========================================================

    print()
    print("=" * 80)
    print("PRODUCTION CATALOG SUMMARY")
    print("=" * 80)

    print(
        f"Source sessions       : {len(df):,}"
    )

    print(
        f"Catalog products      : {len(catalog):,}"
    )

    print(
        f"Average product price : "
        f"₹{catalog['current_price'].mean():,.2f}"
    )

    print(
        f"Average raw conversion: "
        f"{catalog['raw_conversion_rate'].mean():.2%}"
    )

    print(
        f"Average smoothed conv.: "
        f"{catalog['conversion_rate'].mean():.2%}"
    )

    print(
        f"Average quality       : "
        f"{catalog['quality_score'].mean():.3f}"
    )

    print()
    print("Top products:")
    print("-" * 80)

    print(
        catalog[
            [
                "product_id",
                "category_name",
                "current_price",
                "total_sessions",
                "total_purchases",
                "raw_conversion_rate",
                "conversion_rate",
                "demand_score",
                "quality_score",
                "product_score"
            ]
        ]
        .head(10)
        .to_string(index=False)
    )

    print()
    print("=" * 80)
    print("OUTPUT")
    print("=" * 80)

    print(OUTPUT_FILE)

    print()
    print("PHASE 04 STEP 01 — PRODUCTION CATALOG COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()