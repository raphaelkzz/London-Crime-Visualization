"""Download and verify the raw inputs listed in data/SOURCE_MANIFEST.csv."""

from __future__ import annotations

import csv
import hashlib
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "SOURCE_MANIFEST.csv"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def fetch(row: dict[str, str]) -> Path:
    path = (ROOT / row["relative_path"]).resolve()
    if not path.is_relative_to(ROOT / "data" / "raw"):
        raise ValueError(f"Invalid manifest path: {row['relative_path']}")
    expected = row["sha256"].upper()
    if path.exists():
        if sha256(path) != expected:
            raise ValueError(f"SHA-256 mismatch; check the local file: {path}")
        print(f"OK       {path.relative_to(ROOT)}")
        return path

    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, suffix=".part", delete=False) as temp:
        temp_path = Path(temp.name)
    try:
        request = urllib.request.Request(row["direct_download"], headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(request, timeout=120) as response, temp_path.open("wb") as output:
            shutil.copyfileobj(response, output)
        if sha256(temp_path) != expected:
            raise ValueError(f"Downloaded SHA-256 mismatch: {row['dataset_id']} ({row['source_page']})")
        temp_path.replace(path)
    finally:
        temp_path.unlink(missing_ok=True)
    print(f"DOWNLOAD {path.relative_to(ROOT)}")
    return path


def extract_member(archive: Path, member: str, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / member
    if target.exists():
        return
    with zipfile.ZipFile(archive) as zipped:
        with zipped.open(member) as source, target.open("wb") as output:
            shutil.copyfileobj(source, output)
    print(f"EXTRACT  {target.relative_to(ROOT)}")


def extract_boundaries(archive: Path) -> None:
    destination = ROOT / "data" / "raw" / "boundaries" / "LB_LSOA2021_shp"
    with zipfile.ZipFile(archive) as zipped:
        for member in zipped.infolist():
            name = Path(member.filename)
            if member.is_dir() or name.parts[0] != "LB_shp" or ".." in name.parts:
                continue
            target = (destination / name).resolve()
            if not target.is_relative_to(destination) or target.exists():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with zipped.open(member) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output)
            print(f"EXTRACT  {target.relative_to(ROOT)}")


def main() -> None:
    with MANIFEST.open(newline="", encoding="utf-8-sig") as source:
        rows = list(csv.DictReader(source))
    files = {row["dataset_id"]: fetch(row) for row in rows}
    extract_member(
        files["POPULATION_TS001"],
        "census2021-ts001-lsoa.csv",
        ROOT / "data" / "raw" / "population" / "census2021-ts001",
    )
    extract_member(
        files["FRONT_COUNTER_TRAVEL_2013"],
        "lsoatimings.csv",
        ROOT / "data" / "raw" / "security" / "lsoa_police_front_counter_travel_times_2013",
    )
    extract_boundaries(files["LSOA_BOUNDARY"])
    print("Raw data ready.")


if __name__ == "__main__":
    main()
