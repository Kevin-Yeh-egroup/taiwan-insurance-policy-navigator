from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen


TAIPEI = timezone(timedelta(hours=8))
QUERY_URL = "https://insprod.tii.org.tw/Query.aspx"
OUTPUT_PATH = Path("data/tii-query-metadata.json")


class SelectParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.current_select: str | None = None
        self.current_option: dict | None = None
        self.selects: dict[str, list[dict]] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = dict(attrs)
        if tag == "select":
            self.current_select = attr.get("name") or attr.get("id")
            if self.current_select:
                self.selects.setdefault(self.current_select, [])
        elif tag == "option" and self.current_select:
            self.current_option = {"value": attr.get("value") or "", "label": ""}

    def handle_data(self, data: str) -> None:
        if self.current_option is not None:
            self.current_option["label"] += data

    def handle_endtag(self, tag: str) -> None:
        if tag == "option" and self.current_select and self.current_option is not None:
            self.current_option["label"] = " ".join(self.current_option["label"].split())
            self.selects[self.current_select].append(self.current_option)
            self.current_option = None
        elif tag == "select":
            self.current_select = None


def fetch_query_page() -> str:
    request = Request(
        QUERY_URL,
        headers={
            "User-Agent": "Mozilla/5.0 policy-navigator metadata fetch",
        },
    )
    with urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def main() -> None:
    html = fetch_query_page()
    parser = SelectParser()
    parser.feed(html)

    company_options = parser.selects.get("CompanyID", [])
    category_options = parser.selects.get("f_CategoryId1", [])
    company_type_options = parser.selects.get("categoryId", [])

    output = {
        "generated_at": datetime.now(TAIPEI).isoformat(timespec="seconds"),
        "source_url": QUERY_URL,
        "source_name": "財團法人保險事業發展中心保險商品查詢",
        "captcha_required": "bmpC" in html and "bmp.ashx" in html,
        "forms": [
            {
                "name": "form1",
                "method": "post",
                "action": "ResultQueryAll.aspx",
                "captcha_field": "bmpC",
                "fields": [
                    "categoryId",
                    "CompanyID",
                    "f_CategoryId1",
                    "qry_beginDate_SD1",
                    "qry_beginDate_SD2",
                    "qry_endDate_ED1",
                    "qry_endDate_ED2",
                    "endDate2",
                    "fQueryAll",
                ],
            },
            {
                "name": "form2",
                "method": "post",
                "action": "QueryFullText.aspx",
                "captcha_field": "bmpC3",
                "fields": ["fQueryAll"],
            },
        ],
        "company_types": company_type_options,
        "companies": company_options,
        "insurance_categories": category_options,
        "query_dimensions": [
            "公司類別",
            "公司名稱",
            "保險類別",
            "銷售日區間",
            "停售日區間",
            "未停售",
            "關鍵字",
            "全文檢索",
        ],
        "compliance_note": "Query.aspx uses an image captcha. This project records metadata and supports manual result import; it does not bypass captcha.",
    }
    OUTPUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "companies": len(company_options),
                "insurance_categories": len(category_options),
                "captcha_required": output["captcha_required"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
