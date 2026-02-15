from __future__ import annotations

from pathlib import Path
import shutil

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
EXP = ROOT / "data" / "icar_agro_zones_india_exploded.csv"
OUT = ROOT / "rag_corpus" / "icar_zones"


def _doc_name(i: int, row: pd.Series) -> str:
    state = str(row["state"]).lower().replace(" ", "_")
    district = str(row["district"]).lower().replace(" ", "_")
    season = str(row["season"]).lower()
    crop = str(row["crop"]).lower().replace(" ", "_")
    return f"{i:06d}_{state}_{district}_{season}_{crop}.md"


def build() -> int:
    if not EXP.exists():
        raise FileNotFoundError(f"Missing exploded CSV: {EXP}")

    df = pd.read_csv(EXP)
    # Remove stale corpus entries from old builds to keep retrieval deterministic.
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True, exist_ok=True)

    for i, row in df.iterrows():
        fn = OUT / _doc_name(i, row)
        text = (
            f"# ICAR Zone Memory Row {i}\n\n"
            f"ZONE_ID:{row['zone_id']}\n"
            f"ZONE_NAME:{row['zone_name']}\n"
            f"STATE:{row['state']}\n"
            f"DISTRICT:{row['district']}\n"
            f"SEASON:{row['season']}\n"
            f"CROP:{row['crop']}\n"
            f"SUITABILITY:{row['suitability']}\n"
            f"FAMILY:{row['crop_family']}\n"
            f"RISK:{row['key_risks']}\n"
            f"SOIL:{row['soil_notes']}\n"
            f"CLIMATE:{row['climate_notes']}\n"
            f"SOURCE_NAME:{row['source_name']}\n"
            f"SOURCE_REF:{row['source_ref']}\n"
            f"DATA_QUALITY:{row.get('data_quality', 'incomplete')}\n\n"
            f"EVIDENCE:{row['evidence_text']}\n\n"
            f"Summary: This is a structured memory row for deterministic reranking.\n"
        )
        fn.write_text(text, encoding="utf-8")

    print(f"Wrote {len(df)} docs to {OUT}")
    return len(df)


if __name__ == "__main__":
    build()
