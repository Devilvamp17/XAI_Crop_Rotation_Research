from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
SOURCES_DIR = DATA_DIR / "sources"
BASE_OUT = DATA_DIR / "icar_agro_zones_india.csv"
EXPLODED_OUT = DATA_DIR / "icar_agro_zones_india_exploded.csv"

DISTRICT_JSON = SOURCES_DIR / "India-State-District.json"
CLAIMS_CSV = SOURCES_DIR / "icar_crop_memory_notes.csv"


def _load_district_master() -> pd.DataFrame:
    rows = json.loads(DISTRICT_JSON.read_text(encoding="utf-8"))
    out = []
    for r in rows:
        out.append(
            {
                "state": str(r.get("StateName", "")).strip(),
                "district": str(r.get("DistrictName(InEnglish)", "")).strip(),
                "district_lgd_code": str(r.get("DistrictLGDCode", "")).strip(),
                "source_name": "India State-District list with LGD codes",
                "source_ref": "https://www.data.gov.in/catalog/local-government-directory-lgd",
            }
        )
    df = pd.DataFrame(out)
    return df[df["state"].astype(bool) & df["district"].astype(bool)].copy()


def _load_claims() -> pd.DataFrame:
    df = pd.read_csv(CLAIMS_CSV)
    required = {
        "season",
        "crop",
        "suitability",
        "crop_family",
        "key_risks",
        "evidence_text",
        "source_name",
        "source_ref",
        "data_quality",
    }
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in {CLAIMS_CSV}: {missing}")
    for c in required:
        df[c] = df[c].fillna("").astype(str).str.strip()
    # Keep deterministic and conservative values only.
    df = df[df["season"].isin(["kharif", "rabi", "zaid"])].copy()
    df = df[df["suitability"].isin(["HIGH", "MED", "LOW"])].copy()
    return df


def _state_bbox_stub() -> dict[str, tuple[float | None, float | None, float | None, float | None]]:
    # Optional coarse boxes only when known in local sources.
    return {
        "Delhi": (28.40, 28.90, 76.83, 77.35),
        "Punjab": (29.4, 32.5, 73.9, 76.9),
        "West Bengal": (21.5, 27.2, 85.8, 89.9),
        "Haryana": (27.6, 30.9, 74.4, 77.6),
        "Maharashtra": (15.6, 22.1, 72.6, 80.9),
        "Karnataka": (11.5, 18.6, 74.0, 78.6),
        "Tamil Nadu": (8.0, 13.6, 76.2, 80.4),
        "Telangana": (15.8, 19.9, 77.1, 81.0),
    }


def build() -> tuple[pd.DataFrame, pd.DataFrame]:
    districts = _load_district_master()
    claims = _load_claims()
    bboxes = _state_bbox_stub()

    exploded_rows: list[dict[str, object]] = []

    for _, dr in districts.iterrows():
        state = str(dr["state"]).strip()
        district = str(dr["district"]).strip()
        district_lgd = str(dr["district_lgd_code"]).strip()

        for _, cr in claims.iterrows():
            season = str(cr["season"]).strip().lower()
            crop = str(cr["crop"]).strip().lower()
            suitability = str(cr["suitability"]).strip().upper()
            zone_id = f"AGROCLIM_{state.upper().replace(' ', '_')}_{season.upper()}"

            exploded_rows.append(
                {
                    "zone_id": zone_id,
                    "zone_name": f"{state} {season} memory zone",
                    "zone_type": "AGROCLIM_CURATED",
                    "state": state,
                    "district": district,
                    "season": season,
                    "crop": crop,
                    "suitability": suitability,
                    "crop_family": str(cr["crop_family"]).strip().lower() or "cash",
                    "key_risks": str(cr["key_risks"]).strip().lower(),
                    "soil_notes": "district-level soil detail unavailable in source snapshot",
                    "climate_notes": "seasonal crop guidance extracted from cited official sources",
                    "evidence_text": (
                        f"{str(cr['evidence_text']).strip()} "
                        f"Localization key: state={state}, district={district}, lgd={district_lgd}."
                    )[:200],
                    "source_name": str(cr["source_name"]).strip(),
                    "source_ref": str(cr["source_ref"]).strip(),
                    "data_quality": str(cr["data_quality"]).strip() or "incomplete",
                }
            )

    exp_df = pd.DataFrame(exploded_rows)
    exp_df = exp_df.sort_values(["state", "district", "season", "crop"]).reset_index(drop=True)

    # Build summary table from exploded rows (state-season granularity).
    base_rows: list[dict[str, object]] = []
    for (state, season), g in exp_df.groupby(["state", "season"], dropna=False):
        zone_id = f"AGROCLIM_{state.upper().replace(' ', '_')}_{str(season).upper()}"
        bbox = bboxes.get(state, (None, None, None, None))

        def _crops(s: str) -> str:
            return "|".join(sorted(g[g["suitability"] == s]["crop"].dropna().astype(str).str.lower().unique().tolist()))

        districts_list = "|".join(sorted(g["district"].dropna().astype(str).unique().tolist()))
        dominant = g[g["suitability"] == "HIGH"]["crop"].dropna().astype(str).str.lower().value_counts().head(6).index.tolist()

        base_rows.append(
            {
                "zone_id": zone_id,
                "zone_name": f"{state} {season} memory zone",
                "zone_type": "AGROCLIM_CURATED",
                "states": state,
                "districts": districts_list,
                "lat_min": bbox[0],
                "lat_max": bbox[1],
                "lon_min": bbox[2],
                "lon_max": bbox[3],
                "season": season,
                "dominant_crops": "|".join(dominant),
                "suitable_crops_high": _crops("HIGH"),
                "suitable_crops_med": _crops("MED"),
                "suitable_crops_low": _crops("LOW"),
                "typical_soils": "See row-level evidence_text and source_ref in exploded CSV",
                "rainfall_band": "medium",
                "temp_band": "moderate",
                "key_risks": "|".join(sorted(set("|".join(g["key_risks"].fillna("").astype(str)).split("|")) - {""})),
                "notes": "Compiled zone-memory dataset from official India agriculture portals; district assignment is localization metadata, not district-level agronomy proof.",
                "source_name": "Compiled from cited official source rows",
                "source_ref": "See exploded CSV source_ref",
                "data_quality": "incomplete",
            }
        )

    base_df = pd.DataFrame(base_rows).sort_values(["states", "season"]).reset_index(drop=True)

    BASE_OUT.parent.mkdir(parents=True, exist_ok=True)
    base_df.to_csv(BASE_OUT, index=False)
    exp_df.to_csv(EXPLODED_OUT, index=False)

    print(f"Wrote {BASE_OUT} rows={len(base_df)}")
    print(f"Wrote {EXPLODED_OUT} rows={len(exp_df)}")
    return base_df, exp_df


if __name__ == "__main__":
    build()
