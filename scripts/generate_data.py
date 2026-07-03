import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone

API_KEY = os.environ["MFDS_API_KEY"]
KST = timezone(timedelta(hours=9))

SEAFOOD_TYPES = ["기타 수산물가공품", "어묵", "양념젓갈", "조미건어포", "건어포", "가공김(조미김 또는 구운김)"]
PROCESSED_TYPES = ["기타가공품"]
PRODUCE_TYPES = ["과.채가공품", "과.채주스", "과.채음료", "김치", "절임식품", "당절임", "서류가공품", "두류가공품", "신선편의식품"]
ALL_TYPES = set(SEAFOOD_TYPES + PROCESSED_TYPES + PRODUCE_TYPES)

def fetch_all(date_range):
    rows = []
    start = 1
    page = 1000
    while True:
        end = start + page - 1
        url = f"http://openapi.foodsafetykorea.go.kr/api/{API_KEY}/I1250/json/{start}/{end}/CHNG_DT={date_range}"
        with urllib.request.urlopen(url, timeout=60) as resp:
            data = json.load(resp)
        block = data.get("I1250", {})
        page_rows = block.get("row", [])
        if not page_rows:
            break
        rows.extend(page_rows)
        total = int(block.get("total_count", 0))
        if len(rows) >= total:
            break
        start += page
    return rows

def build_samples(rows, types):
    items = [r for r in rows if r.get("PRDLST_DCNM") in types]
    items.sort(key=lambda r: r.get("PRMS_DT", ""), reverse=True)
    out = []
    for r in items[:8]:
        out.append({
            "date": f"{r['PRMS_DT'][4:6]}-{r['PRMS_DT'][6:8]}" if len(r.get("PRMS_DT", "")) == 8 else r.get("PRMS_DT", ""),
            "company": r.get("BSSH_NM", ""),
            "name": r.get("PRDLST_NM", ""),
            "type": r.get("PRDLST_DCNM", ""),
        })
    return items, out

def main():
    now = datetime.now(KST)
    start_date = (now - timedelta(days=7)).strftime("%Y%m%d")
    end_date = now.strftime("%Y%m%d")
    date_range = f"{start_date}~{end_date}"

    rows = fetch_all(date_range)

    seafood_items, seafood_samples = build_samples(rows, SEAFOOD_TYPES)
    processed_items, processed_samples = build_samples(rows, PROCESSED_TYPES)
    produce_items, produce_samples = build_samples(rows, PRODUCE_TYPES)

    total = len(seafood_items) + len(processed_items) + len(produce_items)

    data = {
        "dateRange": f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:8]} ~ {end_date[:4]}-{end_date[4:6]}-{end_date[6:8]}",
        "generatedAt": now.isoformat(),
        "counts": {
            "seafood": len(seafood_items),
            "processed": len(processed_items),
            "produce": len(produce_items),
        },
        "total": total,
        "csvNote": "최근 7일 신규 품목제조보고 (수산물/가공식품/야채과일)",
        "samples": {
            "seafood": seafood_samples,
            "processed": processed_samples,
            "produce": produce_samples,
        },
    }

    out_path = os.path.join(os.path.dirname(__file__), "..", "data.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Wrote {out_path}: total={total}")

if __name__ == "__main__":
    main()
