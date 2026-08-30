
"""
AGENTCOMMERCE OS
PHASE 07.2 — MONGODB DATABASE SEEDER

Seeds the complete AgentCommerce OS dataset into MongoDB.

CSV → MongoDB

1. data/indian/Ecommerce.csv
      → commerce_events

2. data/catalog/product_catalog.csv
      → products

3. data/features/customer_features.csv
      → customers

4. data/features/product_features.csv
      → product_features

5. data/features/session_features.csv
      → session_features

6. data/intelligence/baseline_decisions.csv
      → baseline_decisions

7. data/policies/merchant_decisions.csv
      → merchant_decisions

Design goals:
    - MongoDB only
    - No SQLite
    - Safe to re-run
    - Bulk upserts
    - Deterministic document identity
    - Preserve numeric data types
    - No duplicate documents
    - Clear verification output
"""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from pymongo import UpdateOne


# ============================================================
# PROJECT ROOT
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ============================================================
# MONGODB
# ============================================================

from script.database.mongodb import (
    get_database,
    check_connection,
)


# ============================================================
# DATA DIRECTORIES
# ============================================================

DATA_DIR = ROOT / "data"


# ============================================================
# DATASET CONFIGURATION
# ============================================================

DATASETS = {

    "commerce_events": (
        DATA_DIR
        / "indian"
        / "Ecommerce.csv"
    ),

    "products": (
        DATA_DIR
        / "catalog"
        / "product_catalog.csv"
    ),

    "customers": (
        DATA_DIR
        / "features"
        / "customer_features.csv"
    ),

    "product_features": (
        DATA_DIR
        / "features"
        / "product_features.csv"
    ),

    "session_features": (
        DATA_DIR
        / "features"
        / "session_features.csv"
    ),

    "baseline_decisions": (
        DATA_DIR
        / "intelligence"
        / "baseline_decisions.csv"
    ),

    "merchant_decisions": (
        DATA_DIR
        / "policies"
        / "merchant_decisions.csv"
    ),

}


# ============================================================
# SOURCE NAMES
# ============================================================

SOURCE_NAMES = {

    "commerce_events":
        "indian_ecommerce",

    "products":
        "product_catalog",

    "customers":
        "customer_features",

    "product_features":
        "product_features",

    "session_features":
        "session_features",

    "baseline_decisions":
        "baseline_decisions",

    "merchant_decisions":
        "merchant_decisions",

}


# ============================================================
# COLUMN NORMALIZATION
# ============================================================

def normalize_columns(
    df: pd.DataFrame
) -> pd.DataFrame:

    """
    Normalize CSV column names.

    Example:

        Customer ID
        customer-id
        Customer_ID

    become:

        customer_id
    """

    df = df.copy()

    normalized = []

    for column in df.columns:

        name = str(column).strip().lower()

        name = (
            name
            .replace(" ", "_")
            .replace("-", "_")
            .replace("/", "_")
            .replace(".", "_")
        )

        normalized.append(name)

    df.columns = normalized

    return df


# ============================================================
# SAFE VALUE CONVERSION
# ============================================================

def safe_value(
    value: Any
) -> Any:

    """
    Convert pandas / numpy values
    into MongoDB-safe Python values.
    """

    if pd.isna(value):

        return None

    if hasattr(value, "item"):

        try:
            return value.item()

        except Exception:
            pass

    return value


# ============================================================
# ROW → DOCUMENT
# ============================================================

def row_to_document(
    row: pd.Series,
    source: str,
) -> Dict[str, Any]:

    document: Dict[str, Any] = {}

    for column, value in row.items():

        document[column] = safe_value(value)

    document["source"] = source

    return document


# ============================================================
# FIND ID COLUMN
# ============================================================

def find_id_column(
    df: pd.DataFrame,
    collection_name: str,
) -> Optional[str]:

    """
    Determine the deterministic identity column.

    Priority:

        collection-specific ID
        generic IDs
    """

    priorities = {

        "customers": [
            "customer_id"
        ],

        "products": [
            "product_id"
        ],

        "product_features": [
            "product_id"
        ],

        "session_features": [
            "session_id"
        ],

        "commerce_events": [
            "session_id",
            "event_id",
            "transaction_id"
        ],

        "baseline_decisions": [
            "session_id",
            "customer_id",
            "product_id",
            "decision_id"
        ],

        "merchant_decisions": [
            "product_id",
            "decision_id",
            "customer_id"
        ],

    }

    candidates = priorities.get(
        collection_name,
        []
    )

    for column in candidates:

        if column in df.columns:

            return column

    # Generic fallback

    generic = [
        "id",
        "_id",
        "record_id"
    ]

    for column in generic:

        if column in df.columns:

            return column

    return None


# ============================================================
# PREPARE DOCUMENTS
# ============================================================

def prepare_documents(
    df: pd.DataFrame,
    collection_name: str,
    source: str,
) -> List[Dict[str, Any]]:

    documents = []

    id_column = find_id_column(
        df,
        collection_name
    )

    if id_column is None:

        raise ValueError(

            f"Could not determine a unique ID "
            f"column for collection "
            f"'{collection_name}'.\n"
            f"Available columns: "
            f"{list(df.columns)}"
        )

    print(
        f"    Identity column: {id_column}"
    )

    for _, row in df.iterrows():

        document = row_to_document(
            row,
            source
        )

        identity = safe_value(
            row[id_column]
        )

        if identity is None:
            continue

        # Keep IDs as normal fields.
        #
        # We intentionally do not overwrite
        # MongoDB's internal _id with the
        # dataset's integer ID.

        document["_seed_id"] = str(identity)

        documents.append(
            document
        )

    return documents


# ============================================================
# BULK UPSERT
# ============================================================

def bulk_upsert(
    collection,
    documents: List[Dict[str, Any]],
) -> Dict[str, int]:

    """
    Safely insert/update documents.

    _seed_id is deterministic, therefore
    running this script multiple times will
    not create duplicates.
    """

    if not documents:

        return {
            "inserted": 0,
            "modified": 0,
            "matched": 0,
        }

    operations = []

    for document in documents:

        seed_id = document["_seed_id"]

        operations.append(

            UpdateOne(

                {
                    "_seed_id": seed_id
                },

                {
                    "$set": document
                },

                upsert=True
            )
        )

    result = collection.bulk_write(
        operations,
        ordered=False
    )

    return {

        "inserted": int(
            result.upserted_count
        ),

        "modified": int(
            result.modified_count
        ),

        "matched": int(
            result.matched_count
        ),

    }


# ============================================================
# SEED COLLECTION
# ============================================================

def seed_collection(
    db,
    collection_name: str,
    csv_path: Path,
) -> Dict[str, int]:

    print("\n" + "-" * 70)

    print(
        f"COLLECTION: {collection_name}"
    )

    print(
        f"CSV: {csv_path}"
    )

    print("-" * 70)

    if not csv_path.exists():

        raise FileNotFoundError(
            f"CSV file not found:\n{csv_path}"
        )

    # --------------------------------------------------------
    # LOAD
    # --------------------------------------------------------

    df = pd.read_csv(
        csv_path
    )

    print(
        f"    Rows loaded: {len(df):,}"
    )

    print(
        f"    Columns: {len(df.columns)}"
    )

    # --------------------------------------------------------
    # NORMALIZE
    # --------------------------------------------------------

    df = normalize_columns(
        df
    )

    # --------------------------------------------------------
    # PREPARE
    # --------------------------------------------------------

    documents = prepare_documents(

        df=df,

        collection_name=collection_name,

        source=SOURCE_NAMES[
            collection_name
        ],

    )

    print(
        f"    Documents prepared: "
        f"{len(documents):,}"
    )

    # --------------------------------------------------------
    # UPSERT
    # --------------------------------------------------------

    collection = db[
        collection_name
    ]

    result = bulk_upsert(
        collection,
        documents
    )

    print(
        f"    Inserted: "
        f"{result['inserted']:,}"
    )

    print(
        f"    Matched: "
        f"{result['matched']:,}"
    )

    print(
        f"    Modified: "
        f"{result['modified']:,}"
    )

    print(
        f"    Total MongoDB documents: "
        f"{collection.count_documents({}):,}"
    )

    return result


# ============================================================
# CREATE SEED INDEX
# ============================================================

def create_seed_index(
    db,
    collection_name: str,
):

    """
    Create an index on _seed_id.

    This guarantees efficient upserts.
    """

    collection = db[
        collection_name
    ]

    collection.create_index(
        "_seed_id",
        unique=True,
        name="seed_id_unique"
    )


# ============================================================
# VERIFY CUSTOMER
# ============================================================

def verify_customer(
    db,
    customer_id: int,
):

    customer = db.customers.find_one(

        {
            "customer_id":
                customer_id
        },

        {
            "_id": 0
        }
    )

    print(
        f"\nCustomer {customer_id}:"
    )

    if customer:

        print(customer)

    else:

        print(
            "NOT FOUND"
        )


# ============================================================
# VERIFY PRODUCT
# ============================================================

def verify_product(
    db,
    product_id: int,
):

    product = db.products.find_one(

        {
            "product_id":
                product_id
        },

        {
            "_id": 0
        }
    )

    print(
        f"\nProduct {product_id}:"
    )

    if product:

        print(product)

    else:

        print(
            "NOT FOUND"
        )


# ============================================================
# COLLECTION SUMMARY
# ============================================================

def print_collection_summary(
    db,
):

    print("\n")

    print("=" * 70)

    print(
        "MONGODB COLLECTION SUMMARY"
    )

    print("=" * 70)

    for collection_name in DATASETS:

        count = db[
            collection_name
        ].count_documents({})

        print(
            f"{collection_name:<25} : "
            f"{count:,}"
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)

    print(
        "AGENTCOMMERCE OS"
    )

    print(
        "PHASE 07.2 — MONGODB DATABASE SEEDER"
    )

    print("=" * 70)

    # ========================================================
    # CONNECTION
    # ========================================================

    print(
        "\nChecking MongoDB connection..."
    )

    if not check_connection():

        print(
            "\nMongoDB connection failed."
        )

        raise SystemExit(1)

    print(
        "MongoDB connection successful."
    )

    db = get_database()

    print(
        f"Database: {db.name}"
    )

    # ========================================================
    # VERIFY FILES
    # ========================================================

    print("\n")

    print("=" * 70)

    print(
        "VERIFYING DATASETS"
    )

    print("=" * 70)

    missing_files = []

    for collection_name, path in DATASETS.items():

        if path.exists():

            print(
                f"[OK] "
                f"{collection_name:<25} "
                f"{path}"
            )

        else:

            print(
                f"[MISSING] "
                f"{collection_name:<25} "
                f"{path}"
            )

            missing_files.append(
                path
            )

    if missing_files:

        print("\n")

        print(
            "Database seeding aborted."
        )

        print(
            "Missing CSV files:"
        )

        for path in missing_files:

            print(
                f"  - {path}"
            )

        raise SystemExit(1)

    # ========================================================
    # SEED
    # ========================================================

    results = {}

    for collection_name, csv_path in DATASETS.items():

        try:

            result = seed_collection(

                db=db,

                collection_name=(
                    collection_name
                ),

                csv_path=csv_path,

            )

            results[
                collection_name
            ] = result

            create_seed_index(
                db,
                collection_name
            )

        except Exception as exc:

            print("\n")

            print(
                f"ERROR while seeding "
                f"{collection_name}: "
                f"{type(exc).__name__}: "
                f"{exc}"
            )

            raise

    # ========================================================
    # COLLECTION SUMMARY
    # ========================================================

    print_collection_summary(
        db
    )

    # ========================================================
    # VERIFICATION
    # ========================================================

    print("\n")

    print("=" * 70)

    print(
        "IMPORTANT RECORD VERIFICATION"
    )

    print("=" * 70)

    verify_customer(
        db,
        5176
    )

    verify_product(
        db,
        453
    )

    # ========================================================
    # FINAL RESULT
    # ========================================================

    print("\n")

    print("=" * 70)

    print(
        "DATABASE SEEDING COMPLETED SUCCESSFULLY"
    )

    print("=" * 70)

    print(
        "\nMongoDB database is now populated with:"
    )

    for collection_name in DATASETS:

        count = db[
            collection_name
        ].count_documents({})

        print(
            f"  ✓ {collection_name}: "
            f"{count:,} documents"
        )

    print(
        "\nThe seeder is safe to run again."
    )

    print(
        "Existing records will be updated "
        "instead of duplicated."
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()

