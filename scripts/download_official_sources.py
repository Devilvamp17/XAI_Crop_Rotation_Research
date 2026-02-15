from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "data" / "sources"
RAW_DIR = SRC_DIR / "raw"

SOURCES = [
    {
        "id": "icar_agro_ecological_catalog",
        "url": "https://www.data.gov.in/backend/dms/v2/catalog/agro-ecological-zoning?_format=json",
        "filename": "icar_agro_ecological_catalog.json",
        "type": "json",
        "notes": "OGD catalog metadata referencing ICAR-NBSS&LUP agro-ecological regions.",
    },
    {
        "id": "des_crop_production_catalog",
        "url": "https://www.data.gov.in/backend/dms/v2/catalog/district-wise-season-wise-crop-production-statistics-0?_format=json",
        "filename": "des_crop_production_catalog.json",
        "type": "json",
        "notes": "OGD catalog metadata for district/season/crop production statistics (DES, MoA&FW).",
    },
    {
        "id": "des_crop_production_resource",
        "url": "https://www.data.gov.in/resource/district-wise-season-wise-crop-production-statistics-1997",
        "filename": "des_crop_production_resource.html",
        "type": "text",
        "notes": "Resource detail page containing external datafile pointer.",
    },
    {
        "id": "icar_agro_ecological_page",
        "url": "https://www.data.gov.in/catalog/agro-ecological-zoning",
        "filename": "icar_agro_ecological_page.html",
        "type": "text",
        "notes": "Public catalog page for ICAR agro-ecological zoning.",
    },
]


def _download(url: str) -> requests.Response:
    return requests.get(url, timeout=60, headers={"User-Agent": "Mozilla/5.0"})


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    registry: list[dict[str, str]] = []

    for src in SOURCES:
        try:
            res = _download(src["url"])
            status = str(res.status_code)
            path = RAW_DIR / src["filename"]
            if src["type"] == "json":
                try:
                    payload = res.json()
                    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
                except Exception:
                    path.write_text(res.text, encoding="utf-8")
            else:
                path.write_text(res.text, encoding="utf-8")

            registry.append(
                {
                    "id": src["id"],
                    "url": src["url"],
                    "status": status,
                    "saved_as": str(path.relative_to(ROOT)),
                    "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
                    "notes": src["notes"],
                }
            )
            print(f"[OK] {src['id']} status={status}")
        except Exception as exc:
            registry.append(
                {
                    "id": src["id"],
                    "url": src["url"],
                    "status": "ERROR",
                    "saved_as": "",
                    "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
                    "notes": f"download failed: {exc}",
                }
            )
            print(f"[WARN] {src['id']} download failed: {exc}")

    (SRC_DIR / "official_source_registry.json").write_text(
        json.dumps(registry, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Wrote {SRC_DIR / 'official_source_registry.json'}")


if __name__ == "__main__":
    main()
