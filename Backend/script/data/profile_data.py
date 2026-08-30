from pathlib import Path
import pandas as pd


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

INDIAN_DATA = BASE_DIR / "data" / "indian" / "Ecommerce.csv"
CUSTOMER_DATA = BASE_DIR / "data" / "customer_behavior" / "ecommerce_data.csv"


# ============================================================
# HELPERS
# ============================================================

def percentage(value, total):
    if total == 0:
        return 0
    return (value / total) * 100


def section(title):
    print("\n")
    print("=" * 75)
    print(title)
    print("=" * 75)


# ============================================================
# DATASET 1
# INDIAN E-COMMERCE BEHAVIOR
# ============================================================

def profile_indian_data():

    df = pd.read_csv(INDIAN_DATA)

    section("DATASET 1 — INDIAN E-COMMERCE BEHAVIOR")

    # --------------------------------------------------------
    # BASIC
    # --------------------------------------------------------

    print(f"Rows                  : {len(df):,}")
    print(f"Unique customers      : {df['customer_id'].nunique():,}")
    print(f"Unique sessions       : {df['session_id'].nunique():,}")
    print(f"Unique products       : {df['product_id'].nunique():,}")
    print(f"Unique categories     : {df['product_category'].nunique():,}")

    # --------------------------------------------------------
    # PURCHASE FUNNEL
    # --------------------------------------------------------

    section("PURCHASE FUNNEL")

    total = len(df)

    purchased = df["purchased"].sum()
    added_cart = df["added_to_cart"].sum()
    abandoned = df["cart_abandoned"].sum()

    print(f"Sessions              : {total:,}")
    print(
        f"Added to cart         : {added_cart:,} "
        f"({percentage(added_cart, total):.2f}%)"
    )
    print(
        f"Purchased             : {purchased:,} "
        f"({percentage(purchased, total):.2f}%)"
    )
    print(
        f"Cart abandoned        : {abandoned:,} "
        f"({percentage(abandoned, total):.2f}%)"
    )

    # --------------------------------------------------------
    # REVENUE
    # --------------------------------------------------------

    section("REVENUE")

    print(f"Total revenue         : ₹{df['revenue'].sum():,.2f}")
    print(f"Average revenue       : ₹{df['revenue'].mean():,.2f}")
    print(f"Median revenue        : ₹{df['revenue'].median():,.2f}")
    print(f"Maximum revenue       : ₹{df['revenue'].max():,.2f}")

    # --------------------------------------------------------
    # PRICE
    # --------------------------------------------------------

    section("PRICE")

    print(f"Average unit price    : ₹{df['unit_price'].mean():,.2f}")
    print(f"Median unit price     : ₹{df['unit_price'].median():,.2f}")
    print(f"Minimum unit price    : ₹{df['unit_price'].min():,.2f}")
    print(f"Maximum unit price    : ₹{df['unit_price'].max():,.2f}")

    # --------------------------------------------------------
    # DISCOUNT
    # --------------------------------------------------------

    section("DISCOUNT")

    print(
        f"Average discount     : "
        f"{df['discount_percent'].mean():.2f}%"
    )

    print(
        f"Median discount      : "
        f"{df['discount_percent'].median():.2f}%"
    )

    print(
        f"Maximum discount     : "
        f"{df['discount_percent'].max():.2f}%"
    )

    # --------------------------------------------------------
    # PURCHASE RATE BY DISCOUNT
    # --------------------------------------------------------

    section("PURCHASE RATE BY DISCOUNT")

    discount_analysis = (
        df.groupby("discount_percent")
        .agg(
            sessions=("session_id", "count"),
            purchases=("purchased", "sum")
        )
    )

    discount_analysis["purchase_rate"] = (
        discount_analysis["purchases"]
        / discount_analysis["sessions"]
        * 100
    )

    print(discount_analysis.to_string())

    # --------------------------------------------------------
    # CATEGORY
    # --------------------------------------------------------

    section("CATEGORY DISTRIBUTION")

    category = (
        df.groupby("product_category")
        .agg(
            sessions=("session_id", "count"),
            purchases=("purchased", "sum"),
            revenue=("revenue", "sum")
        )
        .sort_values("revenue", ascending=False)
    )

    category["purchase_rate"] = (
        category["purchases"]
        / category["sessions"]
        * 100
    )

    print(category.to_string())

    # --------------------------------------------------------
    # PAYMENT METHOD
    # --------------------------------------------------------

    section("PAYMENT METHOD")

    print(df["payment_method"].value_counts().sort_index())

    # --------------------------------------------------------
    # DEVICE
    # --------------------------------------------------------

    section("DEVICE")

    print(df["device_type"].value_counts().sort_index())

    # --------------------------------------------------------
    # MARKETING CHANNEL
    # --------------------------------------------------------

    section("MARKETING CHANNEL")

    print(df["marketing_channel"].value_counts().sort_index())


# ============================================================
# DATASET 2
# CUSTOMER PROFILE
# ============================================================

def profile_customer_data():

    df = pd.read_csv(CUSTOMER_DATA)

    section("DATASET 2 — CUSTOMER PROFILE")

    # --------------------------------------------------------
    # BASIC
    # --------------------------------------------------------

    print(f"Customers             : {len(df):,}")
    print(f"Unique customers      : {df['customer_id'].nunique():,}")

    # --------------------------------------------------------
    # CUSTOMER VALUE
    # --------------------------------------------------------

    section("CUSTOMER VALUE")

    print(
        f"Average total spend   : "
        f"${df['total_spend_usd'].mean():,.2f}"
    )

    print(
        f"Median total spend    : "
        f"${df['total_spend_usd'].median():,.2f}"
    )

    print(
        f"Average order value   : "
        f"${df['avg_order_value'].mean():,.2f}"
    )

    print(
        f"Median order value    : "
        f"${df['avg_order_value'].median():,.2f}"
    )

    # --------------------------------------------------------
    # REPEAT CUSTOMERS
    # --------------------------------------------------------

    section("REPEAT CUSTOMERS")

    repeat = df["is_repeat_customer"].sum()

    print(
        f"Repeat customers      : {repeat:,} "
        f"({percentage(repeat, len(df)):.2f}%)"
    )

    # --------------------------------------------------------
    # CART ABANDONMENT
    # --------------------------------------------------------

    section("CART ABANDONMENT")

    abandoned = df["has_abandoned_cart"].sum()

    print(
        f"Customers with abandoned cart : "
        f"{abandoned:,} "
        f"({percentage(abandoned, len(df)):.2f}%)"
    )

    # --------------------------------------------------------
    # CLV
    # --------------------------------------------------------

    section("CLV DISTRIBUTION")

    print(
        df["clv_tier"]
        .value_counts()
        .to_string()
    )

    # --------------------------------------------------------
    # PAYMENT
    # --------------------------------------------------------

    section("PREFERRED PAYMENT")

    print(
        df["preferred_payment"]
        .value_counts(dropna=False)
        .to_string()
    )

    # --------------------------------------------------------
    # CATEGORY
    # --------------------------------------------------------

    section("TOP CATEGORY")

    print(
        df["top_category_bought"]
        .value_counts(dropna=False)
        .to_string()
    )

    # --------------------------------------------------------
    # DEVICE
    # --------------------------------------------------------

    section("PREFERRED DEVICE")

    print(
        df["preferred_device_ord"]
        .value_counts(dropna=False)
        .to_string()
    )

    # --------------------------------------------------------
    # SOURCE
    # --------------------------------------------------------

    section("PREFERRED SOURCE")

    print(
        df["preferred_source"]
        .value_counts(dropna=False)
        .to_string()
    )

    # --------------------------------------------------------
    # DISCOUNT
    # --------------------------------------------------------

    section("CUSTOMER DISCOUNT BEHAVIOR")

    print(
        f"Average historical discount : "
        f"{df['avg_discount_pct'].mean():.2f}%"
    )

    print(
        f"Median historical discount  : "
        f"{df['avg_discount_pct'].median():.2f}%"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("\n")
    print("#" * 75)
    print("# AGENTCOMMERCE OS — PHASE 01 DATA PROFILE")
    print("#" * 75)

    profile_indian_data()
    profile_customer_data()

    print("\n")
    print("#" * 75)
    print("# PROFILE COMPLETE")
    print("#" * 75)


if __name__ == "__main__":
    main()