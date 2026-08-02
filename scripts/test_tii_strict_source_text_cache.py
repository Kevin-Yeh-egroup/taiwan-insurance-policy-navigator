from __future__ import annotations

import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    FARGLORY_GINJILI_VARIABLE_UNIVERSAL_LIFE_VERSIONS,
    PRUDENTIAL_BAILE_VARIABLE_LIFE_VERSIONS,
    STRICT_SOURCE_TEXT_CACHE_VERSION,
    complete_strict_source_document,
    load_strict_source_text_cache,
    strict_source_cache_path,
    strict_source_dependency_version,
)


ROOT = Path(__file__).resolve().parents[1]
PRODUCT_ID = "216121M31A03103"
VERSION = FARGLORY_GINJILI_VARIABLE_UNIVERSAL_LIFE_VERSIONS[
    PRODUCT_ID
]
SOURCE_PATH = (
    ROOT
    / "work"
    / "tii-documents"
    / "tii-life-083"
    / PRODUCT_ID
    / VERSION["file_name"]
)
DOCUMENT = {
    "batch_id": "tii-life-083",
    "product_id": PRODUCT_ID,
    "document_type": "policy_terms",
    "file_name": VERSION["file_name"],
    "source_document_sha256": VERSION["source_document_sha256"],
}


with TemporaryDirectory() as temp_dir:
    cache_dir = Path(temp_dir)
    first = complete_strict_source_document(
        DOCUMENT,
        SOURCE_PATH,
        cache_dir=cache_dir,
    )
    assert first["page_count"] == VERSION["page_count"]
    assert first["source_text_extractor"] == "pypdf"
    dependency_version = strict_source_dependency_version("pypdf")
    cache_path = strict_source_cache_path(
        cache_dir=cache_dir,
        source_document_sha256=VERSION["source_document_sha256"],
        source_text_extractor="pypdf",
        dependency_version=dependency_version,
    )
    assert cache_path.is_file()
    cache_payload = json.loads(cache_path.read_text(encoding="utf-8"))
    assert cache_payload["cache_version"] == STRICT_SOURCE_TEXT_CACHE_VERSION
    first_mtime = cache_path.stat().st_mtime_ns

    second = complete_strict_source_document(
        DOCUMENT,
        SOURCE_PATH,
        cache_dir=cache_dir,
    )
    assert second == first
    assert cache_path.stat().st_mtime_ns == first_mtime

    cache_payload["text"] = "tampered text"
    cache_path.write_text(
        json.dumps(cache_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    assert (
        load_strict_source_text_cache(
            cache_dir=cache_dir,
            source_document_sha256=VERSION[
                "source_document_sha256"
            ],
            source_text_extractor="pypdf",
            dependency_version=dependency_version,
        )
        is None
    )
    recovered = complete_strict_source_document(
        DOCUMENT,
        SOURCE_PATH,
        cache_dir=cache_dir,
    )
    assert recovered == first
    repaired_payload = json.loads(
        cache_path.read_text(encoding="utf-8")
    )
    assert repaired_payload["text"] == first["text"]

    mismatched_document = {
        **DOCUMENT,
        "source_document_sha256": "0" * 64,
    }
    assert (
        complete_strict_source_document(
            mismatched_document,
            SOURCE_PATH,
            cache_dir=cache_dir,
        )
        == mismatched_document
    )

OCR_PRODUCT_ID = "203141M31A01001"
OCR_VERSION = PRUDENTIAL_BAILE_VARIABLE_LIFE_VERSIONS[
    OCR_PRODUCT_ID
]
OCR_SOURCE_PATH = (
    ROOT
    / "work"
    / "tii-documents"
    / "tii-life-017"
    / OCR_PRODUCT_ID
    / f"{OCR_PRODUCT_ID}-A.pdf"
)
OCR_DOCUMENT = {
    "batch_id": "tii-life-017",
    "product_id": OCR_PRODUCT_ID,
    "document_type": "policy_terms",
    "file_name": f"{OCR_PRODUCT_ID}-A.pdf",
    "source_document_sha256": OCR_VERSION[
        "source_document_sha256"
    ],
}

with TemporaryDirectory() as temp_dir:
    cache_dir = Path(temp_dir)
    ocr_document = complete_strict_source_document(
        OCR_DOCUMENT,
        OCR_SOURCE_PATH,
        cache_dir=cache_dir,
    )
    assert ocr_document["source_text_extractor"] == "windows_ocr"
    assert ocr_document["page_count"] == OCR_VERSION["page_count"]
    assert "保誠人壽百樂人生變額壽險" in ocr_document["text"]
    ocr_dependency = strict_source_dependency_version("windows_ocr")
    ocr_cache = strict_source_cache_path(
        cache_dir=cache_dir,
        source_document_sha256=OCR_VERSION[
            "source_document_sha256"
        ],
        source_text_extractor="windows_ocr",
        dependency_version=ocr_dependency,
    )
    assert ocr_cache.is_file()

print(
    {
        "status": "ok",
        "cache_version": STRICT_SOURCE_TEXT_CACHE_VERSION,
        "source_sha_verified_before_cache": True,
        "tampered_cache_rejected": True,
        "windows_ocr_cache_verified": True,
    }
)
