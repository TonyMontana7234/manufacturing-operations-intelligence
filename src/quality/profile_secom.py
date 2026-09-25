import pandas as pd
from pathlib import Path

RAW_DIR = Path("data/raw")
QUALITY_DIR = Path("data/quality")


def profile_dataset():
    QUALITY_DIR.mkdir(parents=True, exist_ok=True)

    features = pd.read_csv(
        RAW_DIR / "secom_features_raw.csv"
    )

    labels = pd.read_csv(
        RAW_DIR / "secom_labels_raw.csv"
    )

    print("\nDATASET SHAPE")
    print(features.shape)

    print("\nDUPLICATES")
    print(features.duplicated().sum())

    print("\nMISSING VALUES")
    missing = (
        features.isna()
        .sum()
        .sort_values(ascending=False)
    )

    print(missing.head(20))

    print("\nLABEL DISTRIBUTION")
    print(labels.iloc[:, 0].value_counts())

    print("\nDATA TYPES")
    print(features.dtypes.value_counts())

    missing.to_csv(
        QUALITY_DIR / "missing_values.csv"
    )


if __name__ == "__main__":
    profile_dataset()
