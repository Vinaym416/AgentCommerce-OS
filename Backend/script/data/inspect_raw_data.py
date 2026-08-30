from pathlib import Path
import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_DIR / "data"


def inspect_csv(path: Path):
    print("\n" + "=" * 70)
    print(f"FILE: {path}")
    print("=" * 70)

    try:
        df = pd.read_csv(path)

        print(f"Rows    : {len(df):,}")
        print(f"Columns : {len(df.columns)}")

        print("\nColumns:")
        for column in df.columns:
            print(f"  - {column}")

        print("\nData types:")
        print(df.dtypes)

        print("\nMissing values:")
        missing = df.isnull().sum()
        print(missing[missing > 0])

        print("\nDuplicates:")
        print(df.duplicated().sum())

        print("\nFirst 3 rows:")
        print(df.head(3).to_string())

    except Exception as e:
        print(f"ERROR: {e}")


def main():
    files = list(RAW_DIR.rglob("*.csv"))

    if not files:
        print(f"No CSV files found under {RAW_DIR}")
        return

    print(f"Found {len(files)} CSV files.")

    for file in files:
        inspect_csv(file)


if __name__ == "__main__":
    main()