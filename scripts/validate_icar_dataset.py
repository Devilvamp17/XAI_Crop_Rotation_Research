from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data" / "icar_agro_zones_india.csv"
EXP = ROOT / "data" / "icar_agro_zones_india_exploded.csv"

BASE_COLS = [
    "zone_id","zone_name","zone_type","states","districts","lat_min","lat_max","lon_min","lon_max",
    "season","dominant_crops","suitable_crops_high","suitable_crops_med","suitable_crops_low","typical_soils",
    "rainfall_band","temp_band","key_risks","notes",
]
EXP_COLS = [
    "zone_id","zone_name","zone_type","state","district","season","crop","suitability","crop_family",
    "key_risks","soil_notes","climate_notes","evidence_text","source_name","source_ref","data_quality",
]


def fail(msg: str) -> None:
    print(f"[FAIL] {msg}")
    sys.exit(1)


def main() -> None:
    if not BASE.exists() or not EXP.exists():
        fail("Dataset CSVs missing. Run scripts/build_icar_dataset.py first.")

    b = pd.read_csv(BASE)
    e = pd.read_csv(EXP)

    for c in BASE_COLS:
        if c not in b.columns:
            fail(f"Base CSV missing column: {c}")
    for c in EXP_COLS:
        if c not in e.columns:
            fail(f"Exploded CSV missing column: {c}")

    if len(e) < 5000:
        fail(f"Exploded CSV must have >=5000 rows, found {len(e)}")

    if (e["source_name"].fillna("").str.strip() == "").any():
        fail("Exploded CSV has empty source_name values")
    if (e["source_ref"].fillna("").str.strip() == "").any():
        fail("Exploded CSV has empty source_ref values")

    if (~e["source_ref"].fillna("").str.match(r"^https?://", case=False)).any():
        fail("Exploded CSV source_ref must be URL-like (http/https)")

    if e["source_name"].fillna("").str.contains("compiled notes", case=False).any():
        fail("Exploded CSV contains non-source-traceable source_name entries")

    print(f"[OK] base_rows={len(b)} exploded_rows={len(e)}")


if __name__ == "__main__":
    main()
