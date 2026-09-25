from pathlib import Path
from ucimlrepo import fetch_ucirepo

RAW_DIR = Path("data/raw")


def download_secom():
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    print("Fetching SECOM dataset (id=179) from UCI Machine Learning Repository...")
    secom = fetch_ucirepo(id=179)

    if secom.data.features is not None and secom.data.targets is not None:
        X = secom.data.features
        y = secom.data.targets
    else:
        # UCI SECOM repository metadata provides full table in secom.data.original
        orig = secom.data.original
        y = orig[["class"]]
        X = orig.drop(columns=["class"])

    X.to_csv(RAW_DIR / "secom_features_raw.csv", index=False)
    y.to_csv(RAW_DIR / "secom_labels_raw.csv", index=False)

    print(f"Features saved: {X.shape}")
    print(f"Labels saved: {y.shape}")
    return X, y


if __name__ == "__main__":
    download_secom()
