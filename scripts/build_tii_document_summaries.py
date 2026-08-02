from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from extract_tii_document_content import compact_document_summary


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    temporary_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        for attempt in range(5):
            try:
                temporary_path.write_text(serialized, encoding="utf-8")
                os.replace(temporary_path, path)
                return
            except OSError:
                if attempt == 4:
                    raise
                time.sleep(0.1 * (2**attempt))
    finally:
        temporary_path.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build compact, browser-facing TII document summary shards.")
    parser.add_argument("--input-dir", type=Path, default=Path("data/tii/document-content"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/tii/document-summaries"))
    parser.add_argument("--reviewed-dir", type=Path, default=Path("data/tii/reviewed-benefits"))
    parser.add_argument("--batch-id", default=None)
    args = parser.parse_args()

    source_paths = sorted(args.input_dir.glob("*.json"))
    if args.batch_id:
        source_paths = [path for path in source_paths if path.stem == args.batch_id]
    if not source_paths:
        raise SystemExit("No TII document-content files matched the requested scope.")

    total_records = 0
    for source_path in source_paths:
        public_output = json.loads(source_path.read_text(encoding="utf-8"))
        reviewed_path = args.reviewed_dir / source_path.name
        reviewed_records = []
        if reviewed_path.is_file():
            reviewed_payload = json.loads(reviewed_path.read_text(encoding="utf-8"))
            if reviewed_payload.get("batch_id") != source_path.stem:
                raise SystemExit(f"reviewed benefit batch mismatch: {reviewed_path}")
            reviewed_records = reviewed_payload.get("records") or []
        compact = compact_document_summary(
            public_output,
            source_path.stem,
            reviewed_records=reviewed_records,
        )
        write_json(args.output_dir / source_path.name, compact)
        total_records += compact["record_count"]

    print(
        json.dumps(
            {
                "status": "ok",
                "batch_count": len(source_paths),
                "record_count": total_records,
                "output_dir": str(args.output_dir),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
