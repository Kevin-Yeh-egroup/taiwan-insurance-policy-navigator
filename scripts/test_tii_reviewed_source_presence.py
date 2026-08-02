from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from validate_data import validate_reviewed_benefits


ROOT = Path(__file__).resolve().parents[1]
reviewed_path = next(
    path
    for path in sorted(
        (ROOT / "data" / "tii" / "reviewed-benefits").glob("*.json")
    )
    if json.loads(path.read_text(encoding="utf-8")).get("records")
)
batch_id = reviewed_path.stem
reviewed_payload = json.loads(reviewed_path.read_text(encoding="utf-8"))
reviewed_record = reviewed_payload["records"][0]
product_id = reviewed_record["product_id"]

content_path = (
    ROOT / "data" / "tii" / "document-content" / f"{batch_id}.json"
)
content_payload = json.loads(content_path.read_text(encoding="utf-8"))
content_record = next(
    record
    for record in content_payload["records"]
    if record["product_id"] == product_id
)
source_path = (
    ROOT
    / "work"
    / "tii-documents"
    / batch_id
    / product_id
    / reviewed_record["source_file"]
)
assert source_path.is_file()

with tempfile.TemporaryDirectory() as temporary_directory:
    temporary_root = Path(temporary_directory)
    reviewed_output = (
        temporary_root
        / "data"
        / "tii"
        / "reviewed-benefits"
        / f"{batch_id}.json"
    )
    content_output = (
        temporary_root
        / "data"
        / "tii"
        / "document-content"
        / f"{batch_id}.json"
    )
    reviewed_output.parent.mkdir(parents=True)
    content_output.parent.mkdir(parents=True)
    reviewed_output.write_text(
        json.dumps(
            {
                "batch_id": batch_id,
                "record_count": 1,
                "records": [reviewed_record],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    content_output.write_text(
        json.dumps(
            {
                "batch_id": batch_id,
                "record_count": 1,
                "records": [content_record],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    original_cwd = Path.cwd()
    try:
        os.chdir(temporary_root)
        try:
            validate_reviewed_benefits()
        except SystemExit as error:
            assert "reviewed benefit source PDF is missing" in str(error)
        else:
            raise AssertionError("missing reviewed source PDF was accepted")

        source_output = (
            temporary_root
            / "work"
            / "tii-documents"
            / batch_id
            / product_id
            / reviewed_record["source_file"]
        )
        source_output.parent.mkdir(parents=True)
        source_output.write_bytes(source_path.read_bytes())
        assert validate_reviewed_benefits() == 1
    finally:
        os.chdir(original_cwd)

print(
    {
        "status": "ok",
        "batch_id": batch_id,
        "product_id": product_id,
        "missing_source_rejected": True,
    }
)
