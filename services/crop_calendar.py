from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from zipfile import ZipFile

import pandas as pd

CALENDAR_PATH = Path(__file__).resolve().parent / "data" / "crop_calendar.csv"


@lru_cache(maxsize=1)
def _load_calendar() -> pd.DataFrame:
    if not CALENDAR_PATH.exists():
        raise FileNotFoundError(f"Crop calendar file missing: {CALENDAR_PATH}")
    return pd.read_csv(CALENDAR_PATH)


def get_crop_calendar(region: str, month: int) -> dict[str, float]:
    df = _load_calendar()
    region_norm = (region or "global").strip().lower()

    region_rows = df[(df["region"].str.lower() == region_norm) & (df["month"] == month)]
    if region_rows.empty:
        region_rows = df[(df["region"].str.lower() == "global") & (df["month"] == month)]

    return {str(row["crop"]).lower(): float(row["suitability"]) for _, row in region_rows.iterrows()}


def install_calendar_from_zip(zip_path: Path, csv_inside_zip: str, output_path: Path = CALENDAR_PATH) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(zip_path, "r") as zf:
        with zf.open(csv_inside_zip) as source:
            df = pd.read_csv(source)
    expected_cols = {"region", "month", "crop", "suitability"}
    missing = expected_cols.difference(df.columns)
    if missing:
        raise ValueError(f"Calendar CSV missing required columns: {sorted(missing)}")
    df.to_csv(output_path, index=False)
    _load_calendar.cache_clear()
    return output_path
