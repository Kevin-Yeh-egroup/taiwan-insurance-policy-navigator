from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_tii_exact_family_source_matrix import (
    choose_extractor,
    normalize_text,
    text_metrics,
)


assert normalize_text("保 險 金  額") == "保險金額"

anchors = ["身故保險金", "保單帳戶價值", "滿期保險金"]
good = text_metrics(
    ("身故保險金與保單帳戶價值。" * 80),
    anchors=anchors,
    page_count=3,
)
assert good["usable"] is True
assert good["anchor_count"] == 2
assert good["cjk_count"] >= 100

low_anchor = text_metrics(
    ("一般條款文字內容。" * 80),
    anchors=anchors,
    page_count=3,
)
assert low_anchor["usable"] is False

assert (
    choose_extractor(
        {
            "pypdf": {
                "usable": True,
                "anchor_count": 3,
                "cjk_count": 500,
            },
            "pymupdf": {
                "usable": True,
                "anchor_count": 2,
                "cjk_count": 900,
            },
        }
    )
    == "pypdf"
)
assert (
    choose_extractor(
        {
            "pypdf": {
                "usable": True,
                "anchor_count": 3,
                "cjk_count": 900,
            },
            "pymupdf": {
                "usable": True,
                "anchor_count": 3,
                "cjk_count": 800,
            },
        },
        forced_extractor="pymupdf",
    )
    == "pymupdf"
)
assert (
    choose_extractor(
        {
            "pypdf": {
                "usable": False,
                "anchor_count": 0,
                "cjk_count": 0,
            },
            "pymupdf": {
                "usable": False,
                "anchor_count": 1,
                "cjk_count": 50,
            },
        }
    )
    is None
)
assert (
    choose_extractor(
        {
            "pypdf": {
                "usable": False,
                "anchor_count": 0,
                "cjk_count": 0,
            },
            "pymupdf": {
                "usable": False,
                "anchor_count": 0,
                "cjk_count": 0,
            },
            "windows_ocr": {
                "usable": True,
                "anchor_count": 3,
                "cjk_count": 800,
            },
        }
    )
    == "windows_ocr"
)

print("TII exact-family source-matrix tests passed.")
