import requests
from pathlib import Path


def main() -> None:
    url = "http://127.0.0.1:5001/api/comparative-report"

    payload = {
        "establishmentId": "667d2c1128c2cd002803f81a",
        "establishmentName": "Rochdale Sixth Form College",
        "reportType": "cycle_vs_cycle",
        "config": {
            "academicYear": "2025/2026",
            "cycle1": 1,
            "cycle2": 2,
            "yearGroup": "13",
            "includeGenderComparisons": True,
            "genders": ["Female", "Male"],
            "organizationalContext": (
                "Year 13 deep comparison across Cycle 1 and Cycle 2. "
                "Focus on VESPA and question-level patterns; gender insights are indicative "
                "based on available gender data."
            ),
        },
        "filters": {},
    }

    out_path = Path(
        r"C:\Users\tonyd\OneDrive - 4Sight Education Ltd\VESPA WEBISTE FILES\vespa-academy-new\public\reports"
        r"\ROCHDALE_Y13_Cycle1_vs_Cycle2_2025-26.html"
    )

    r = requests.post(url, json=payload, timeout=300)
    r.raise_for_status()
    data = r.json()

    html = data.get("html")
    if not html:
        raise RuntimeError("No 'html' returned in response")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    print("Saved:", out_path)


if __name__ == "__main__":
    main()

