#!/usr/bin/env python3
"""
E-ACT Journey Report Generator (Cycle 1 -> Cycle 2, Cycle 3-ready).

Creates:
- Trust executive journey report
- 6 school journey reports

Publishes to stable journey links in website public/reports.
"""

from __future__ import annotations

import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

import build_eact_reports as ber


ROOT = Path(r"C:\Users\tonyd\OneDrive - 4Sight Education Ltd\Apps\DASHBOARD\DASHBOARD")
CSV_PATH = ROOT / "E-ACT-Cycle2.csv"
C1_CSV_PATH = ROOT / "E-ACT-VESPAC1.csv"
REPORTS_DIR = Path(
    r"C:\Users\tonyd\OneDrive - 4Sight Education Ltd\VESPA WEBISTE FILES\vespa-academy-new\public\reports"
)
TUTOR_ACTIVITIES_PATH = ROOT / "tutor_activities.json"
INSIGHT_AGREE_THRESHOLD = 4

SCHOOLS = [
    "Montpelier High School",
    "Ousedale School",
    "Daventry 6th Form",
    "West Walsall Academy",
    "Crest Academy",
    "North Birmingham Academy",
]

TARGET_FILES = {
    "EXEC": "EACT_VESPA_JOURNEY_EXEC-SUMMARY_2025-26.html",
    "Montpelier High School": "MONTPELIER_VESPA_JOURNEY_2025-26.html",
    "Ousedale School": "OUSEDALE_VESPA_JOURNEY_2025-26.html",
    "Daventry 6th Form": "DAVENTRY_VESPA_JOURNEY_2025-26.html",
    "West Walsall Academy": "WWA_VESPA_JOURNEY_2025-26.html",
    "Crest Academy": "CREST_VESPA_JOURNEY_2025-26.html",
    "North Birmingham Academy": "NBA_VESPA_JOURNEY_2025-26.html",
}

DIM_COLS = {
    "Vision": ("V1_calc", "V2_calc"),
    "Effort": ("E1_calc", "E2_calc"),
    "Systems": ("S1_calc", "S2_calc"),
    "Practice": ("P1_calc", "P2_calc"),
    "Attitude": ("A1_calc", "A2_calc"),
    "Overall": ("O1_calc", "O2_calc"),
}

THEME_HEX = {
    "Vision": "#ff8f00",
    "Effort": "#86b4f0",
    "Systems": "#72cb44",
    "Practice": "#7f31a4",
    "Attitude": "#f032e6",
    "Overall": "#ffd700",
}

INSIGHT_TO_THEME = {
    "growth_mindset": "Attitude",
    "time_management": "Systems",
    "academic_momentum": "Effort",
    "support_help_seeking": "Attitude",
    "resilience_factor": "Attitude",
    "exam_confidence": "Attitude",
    "revision_readiness": "Practice",
    "stress_management": "Attitude",
    "study_strategies": "Practice",
    "organization_materials": "Systems",
    "active_learning": "Practice",
    "vision_purpose": "Vision",
}

NATIONAL_MEANS = {
    1: {"Vision": 6.1, "Effort": 5.49, "Systems": 5.27, "Practice": 5.75, "Attitude": 5.59, "Overall": 5.64},
    2: {"Vision": 6.34, "Effort": 5.65, "Systems": 5.52, "Practice": 5.98, "Attitude": 5.93, "Overall": 5.88},
}

NATIONAL_DIST_COUNTS = {
    1: {
        "Vision": {1: 96, 2: 269, 3: 638, 4: 482, 5: 610, 6: 1262, 7: 615, 8: 977, 9: 368, 10: 494},
        "Effort": {1: 320, 2: 218, 3: 899, 4: 681, 5: 774, 6: 864, 7: 732, 8: 516, 9: 639, 10: 168},
        "Systems": {1: 345, 2: 391, 3: 685, 4: 997, 5: 540, 6: 1116, 7: 529, 8: 757, 9: 239, 10: 212},
        "Practice": {1: 206, 2: 268, 3: 520, 4: 792, 5: 1060, 6: 583, 7: 947, 8: 686, 9: 449, 10: 300},
        "Attitude": {1: 219, 2: 393, 3: 681, 4: 581, 5: 698, 6: 1198, 7: 688, 8: 769, 9: 389, 10: 195},
        "Overall": {1: 43, 2: 151, 3: 493, 4: 864, 5: 1167, 6: 1262, 7: 936, 8: 593, 9: 228, 10: 74},
    },
    2: {
        "Vision": {1: 56, 2: 185, 3: 552, 4: 414, 5: 530, 6: 1261, 7: 735, 8: 1066, 9: 376, 10: 496},
        "Effort": {1: 216, 2: 183, 3: 837, 4: 623, 5: 813, 6: 855, 7: 819, 8: 541, 9: 618, 10: 166},
        "Systems": {1: 265, 2: 277, 3: 598, 4: 862, 5: 549, 6: 1256, 7: 612, 8: 800, 9: 240, 10: 212},
        "Practice": {1: 151, 2: 207, 3: 440, 4: 715, 5: 1060, 6: 506, 7: 1024, 8: 774, 9: 490, 10: 304},
        "Attitude": {1: 142, 2: 270, 3: 563, 4: 510, 5: 670, 6: 1195, 7: 800, 8: 838, 9: 440, 10: 243},
        "Overall": {1: 16, 2: 122, 3: 351, 4: 744, 5: 1048, 6: 1309, 7: 1133, 8: 621, 9: 226, 10: 101},
    },
}

VESPA_THRESHOLDS = {
    "VISION": [(0, 2.26), (2.26, 2.7), (2.7, 3.02), (3.02, 3.33), (3.33, 3.52), (3.52, 3.84), (3.84, 4.15), (4.15, 4.47), (4.47, 4.79), (4.79, 5.0)],
    "EFFORT": [(0, 2.42), (2.42, 2.73), (2.73, 3.04), (3.04, 3.36), (3.36, 3.67), (3.67, 3.86), (3.86, 4.17), (4.17, 4.48), (4.48, 4.8), (4.8, 5.0)],
    "SYSTEMS": [(0, 2.36), (2.36, 2.76), (2.76, 3.16), (3.16, 3.46), (3.46, 3.75), (3.75, 4.05), (4.05, 4.35), (4.35, 4.64), (4.64, 4.94), (4.94, 5.0)],
    "PRACTICE": [(0, 1.74), (1.74, 2.1), (2.1, 2.46), (2.46, 2.74), (2.74, 3.02), (3.02, 3.3), (3.3, 3.66), (3.66, 3.94), (3.94, 4.3), (4.3, 5.0)],
    "ATTITUDE": [(0, 2.31), (2.31, 2.72), (2.72, 3.01), (3.01, 3.3), (3.3, 3.53), (3.53, 3.83), (3.83, 4.06), (4.06, 4.35), (4.35, 4.7), (4.7, 5.0)],
}

JOURNEY_INSIGHTS = {
    "time_management": {
        "title": "Time Management",
        "icon": "⏰",
        "questions": [
            "I plan and organise my time to get my work done",
            "I complete all my homework on time",
            "I always meet deadlines ",
        ],
    },
    "growth_mindset": {
        "title": "Growth Mindset",
        "icon": "🌱",
        "questions": [
            "No matter who you are, you can change your intelligence a lot",
            "Your intelligence is something about you that you can change very much",
            "I like hearing feedback about how I can improve",
            "I enjoy learning new things ",
        ],
    },
    "academic_momentum": {
        "title": "Academic Momentum",
        "icon": "🚀",
        "questions": [
            "I strive to achieve the goals I set for myself",
            "I enjoy learning new things ",
            "I'm not happy unless my work is the best it can be",
            "I am a hard working student",
        ],
    },
    "support_help_seeking": {
        "title": "Support & Help-Seeking",
        "icon": "🤝",
        "questions": [
            "I have the support I need to achieve this year?",
            "I'm happy to ask questions in front of a group.",
            "I like hearing feedback about how I can improve",
        ],
    },
    "resilience_factor": {
        "title": "Resilience Factor",
        "icon": "💪",
        "questions": [
            "I don't let a poor test/assessment result get me down for too long",
            "I like hearing feedback about how I can improve",
            "I have a positive view of myself",
        ],
    },
    "exam_confidence": {
        "title": "Exam Confidence",
        "icon": "⭐",
        "questions": [
            " I am confident I will achieve my potential in my final exams?",
            "I am confident in my academic ability",
            "I can control my nerves in tests/practical assessments.",
        ],
    },
    "revision_readiness": {
        "title": "Revision Readiness",
        "icon": "📖",
        "questions": [
            " I feel equipped to face the study and revision challenges this year?",
            "I test myself on important topics until I remember them",
            "I spread out my revision,  rather than cramming at the last minute.",
            "I take good notes in class which are useful for revision",
        ],
    },
    "stress_management": {
        "title": "Stress Management",
        "icon": "😌",
        "questions": [
            "I feel I can cope with the pressure at school/college/University",
            "I can control my nerves in tests/practical assessments.",
            "I'm happy to ask questions in front of a group.",
        ],
    },
    "study_strategies": {
        "title": "Study Strategies",
        "icon": "📚",
        "questions": [
            "I test myself on important topics until I remember them",
            "I spread out my revision,  rather than cramming at the last minute.",
            "I summarise important information in diagrams, tables or lists",
            "I take good notes in class which are useful for revision",
        ],
    },
    "organization_materials": {
        "title": "Organization & Materials",
        "icon": "📦",
        "questions": [
            "My books/files are organised",
            "I take good notes in class which are useful for revision",
            "I use highlighting/colour coding for revision",
        ],
    },
    "active_learning": {
        "title": "Active Learning",
        "icon": "🎓",
        "questions": [
            "When preparing for a test/exam I teach someone else the material",
            "When revising I mix different kinds of topics/subjects in one study session",
            "I test myself on important topics until I remember them",
        ],
    },
    "vision_purpose": {
        "title": "Vision & Purpose",
        "icon": "🎯",
        "questions": [
            "I've worked out the next steps in my life",
            "I give a lot of attention to my career planning",
            "I understand why education is important for my future",
        ],
    },
}

def hex_to_rgba(hex_color: str, alpha: float) -> str:
    color = (hex_color or "").strip()
    if color.startswith("#") and len(color) == 7:
        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)
        return f"rgba({r},{g},{b},{alpha})"
    return f"rgba(102,126,234,{alpha})"


def norm_text(s: str) -> str:
    s = (s or "").strip().lower()
    s = s.replace("out loud", "outloud").replace("–", "-")
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[^\w\s']", "", s)
    return s


# Supports wording variants across report generations and data exports.
INSIGHT_QUESTION_ALIASES = {
    norm_text("I understand why education is important for my future"): [
        norm_text("I know what grades I want to achieve")
    ],
    norm_text("When preparing for a test/exam I teach someone else the material"): [
        norm_text("I study by explaining difficult topics outloud")
    ],
}


def clean_likert_df(df: pd.DataFrame) -> pd.DataFrame:
    vals = df.apply(pd.to_numeric, errors="coerce")
    # Valid questionnaire responses are 1..5; 0s are missing exports.
    vals = vals.where((vals >= 1) & (vals <= 5))
    return vals


def clean_likert_series(s: pd.Series) -> pd.Series:
    vals = pd.to_numeric(s, errors="coerce")
    vals = vals.where((vals >= 1) & (vals <= 5))
    return vals


def load_tutor_activities() -> List[Dict]:
    if not TUTOR_ACTIVITIES_PATH.exists():
        return []
    try:
        data = json.loads(TUTOR_ACTIVITIES_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []
    records = data.get("records", [])
    out = []
    for r in records:
        category = str(r.get("category", "")).strip()
        title = str(r.get("title", "")).strip()
        html = str(r.get("html_content", "")).strip()
        if not category or not title:
            continue
        m = re.search(r'src="([^"]+)"', html)
        link = m.group(1) if m else ""
        pdf_matches = re.findall(r'href="([^"]+\.pdf[^"]*)"', html, flags=re.IGNORECASE)
        pdf_link = pdf_matches[0] if pdf_matches else ""
        clean_title = re.sub(r"^[A-Z]+\s*-\s*", "", title).strip()
        out.append(
            {
                "category": category,
                "title": clean_title or title,
                "url": link,
                "pdf_url": pdf_link,
                "raw_title": title,
            }
        )
    return out


def pick_activity_suggestions(
    priority_categories: List[str], used_titles: set[str], n: int = 3
) -> List[Dict]:
    acts = load_tutor_activities()
    if not acts:
        return []
    chosen: List[Dict] = []
    for cat in priority_categories:
        for a in acts:
            if a["category"] != cat:
                continue
            if a["title"] in used_titles:
                continue
            chosen.append(a)
            used_titles.add(a["title"])
            break
        if len(chosen) >= n:
            break
    if len(chosen) < n:
        for a in acts:
            if a["title"] in used_titles:
                continue
            chosen.append(a)
            used_titles.add(a["title"])
            if len(chosen) >= n:
                break
    return chosen[:n]


def activity_justification(category: str, weakest: str, second_weakest: str, strongest: str) -> str:
    base = {
        "Vision": "builds clarity on goals and long-term direction",
        "Effort": "strengthens consistency and follow-through during busy weeks",
        "Systems": "improves planning, routines, and deadline control",
        "Practice": "improves revision quality and retrieval habits",
        "Attitude": "supports confidence, resilience, and responses to setbacks",
    }.get(category, "supports habit development in this area")
    if category == weakest:
        return f"Selected because this is the weakest movement area; this activity helps directly where pressure is highest ({base})."
    if category == second_weakest:
        return f"Selected because this is another slower-growth area; this activity should stabilise progress ({base})."
    if category == strongest:
        return f"Selected to protect current strengths and keep momentum in this area ({base})."
    return f"Selected to support this theme in a practical, classroom-friendly way ({base})."


def flagship_activity_catalog() -> Dict[str, List[Dict[str, str]]]:
    return {
        "Vision": [
            {
                "title": "20 Questions",
                "context": "Supports self-reflection and goal clarity by helping students identify strengths, interests and possible future pathways.",
            },
            {
                "title": "Fix your Dashboard",
                "context": "Builds values-led motivation by asking students to analyse qualities they admire and align these with their own goals.",
            },
            {
                "title": "Ikigai",
                "context": "Helps students connect what they enjoy, what they are good at and what is useful in the real world to sharpen purpose.",
            },
            {
                "title": "Diver & Thriver Goals",
                "context": "Moves students from outcome-only goals toward action-based goals that improve work rate and reduce procrastination.",
            },
        ],
        "Effort": [
            {
                "title": "Proactive vs Reactive",
                "context": "Develops self-starting study habits so students do more high-impact work before pressure builds.",
            },
            {
                "title": "Indistractible",
                "context": "Reduces attention loss by helping students identify triggers and build distraction-proof study routines.",
            },
            {
                "title": "Disruption Cost and Deep Work",
                "context": "Shows the cost of interruptions and trains students to plan focused deep-work sessions for demanding tasks.",
            },
        ],
        "Systems": [
            {
                "title": "Energy Line",
                "context": "Improves task prioritisation by sorting work by effort required and deadline, reducing overwhelm.",
            },
            {
                "title": "Pending, Doing, Done",
                "context": "Gives students a visual taskboard to manage workload and reduce stress through clear progress tracking.",
            },
            {
                "title": "Cornell Notes",
                "context": "Strengthens note quality and recall by adding a structured review stage after lessons.",
            },
        ],
        "Practice": [
            {
                "title": "High & Low Utility",
                "context": "Helps students replace weak revision habits with higher-impact methods linked to better exam outcomes.",
            },
            {
                "title": "The Command Verb Table",
                "context": "Builds exam confidence by training students to decode task words and respond with the right approach.",
            },
            {
                "title": "Overnight Boost",
                "context": "Uses sleep and retrieval timing to improve memory consolidation and next-day recall.",
            },
            {
                "title": "Closed Book Notetaking",
                "context": "Uses active recall to improve retention and understanding more effectively than passive rereading.",
            },
        ],
        "Attitude": [
            {
                "title": "Check Ahead, Check Back",
                "context": "Improves self-monitoring by building a habit of planning forwards and reviewing what worked.",
            },
            {
                "title": "NAF vs NAch",
                "context": "Builds mindset awareness by helping students shift from avoiding failure to pursuing challenge and growth.",
            },
            {
                "title": "Change Curve",
                "context": "Normalises emotional responses to change and helps students move toward acceptance and productive action.",
            },
        ],
    }


def norm_key(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (text or "").lower())


def resolve_activity_link(activity_title: str, activities: List[Dict]) -> str:
    if not activities:
        return ""
    target = norm_key(activity_title)
    if not target:
        return ""
    aliases = {
        "indistractible": ["becomingindestractable", "indistractible", "indestractable"],
        "disruptioncostanddeepwork": ["disruptioncostanddeepwork", "deepwork", "disruptioncost"],
        "diverthrivergoals": ["diversandthrivers", "thriver", "diver"],
        "fixyourdashboard": ["fixyourdashboard", "dashboard"],
    }
    targets = [target] + aliases.get(target, [])
    best = None
    best_score = -1
    for a in activities:
        t = norm_key(str(a.get("title", "")))
        raw = norm_key(str(a.get("raw_title", "")))
        hay = f"{t} {raw}"
        score = 0
        for tgt in targets:
            if tgt and tgt in hay:
                score += len(tgt) + 20
            if hay and hay in tgt:
                score += len(hay) + 10
            for token in re.findall(r"[a-z0-9]+", tgt):
                if len(token) >= 4 and token in hay:
                    score += len(token)
        if score > best_score:
            best_score = score
            best = a
    if best and best_score > 0:
        return str(best.get("pdf_url") or best.get("url") or "")
    return ""


def choose_flagship_activities(
    priority_categories: List[str],
    weakest: str,
    second_weakest: str,
    strongest: str,
    low_insights: List[Dict],
    statements: List[Dict],
    n: int = 3,
) -> List[Dict]:
    catalog = flagship_activity_catalog()
    acts = load_tutor_activities()
    signal_text = " ".join(
        [str(i.get("title", "")) for i in low_insights[:3]] + [str(s.get("statement", "")) for s in statements[:4]]
    ).lower()
    keyword_map = {
        "systems": ["time", "deadline", "organis", "organize", "homework", "file", "note"],
        "effort": ["hard working", "strive", "effort", "focus", "distraction"],
        "practice": ["revision", "test", "exam", "notes", "recall", "study"],
        "vision": ["career", "future", "purpose", "goal", "next steps"],
        "attitude": ["confidence", "nerves", "pressure", "resilience", "feedback"],
    }

    # Pressure signals come from weakest dimensions plus lowest insight and statement patterns.
    pressure_by_cat: Dict[str, int] = {k: 0 for k in catalog.keys()}
    for i, cat in enumerate(priority_categories):
        if cat in pressure_by_cat:
            pressure_by_cat[cat] += max(0, 3 - i)
    for i in low_insights[:4]:
        t = INSIGHT_TO_THEME.get(str(i.get("id", "")))
        if t in pressure_by_cat:
            pressure_by_cat[t] += 2
    for s in statements[:8]:
        c = str(s.get("category", "")).strip()
        if c in pressure_by_cat:
            pressure_by_cat[c] += 1

    candidates: List[Tuple[float, str, Dict[str, str]]] = []
    for cat, options in catalog.items():
        cat_key = cat.lower()
        base_pressure = pressure_by_cat.get(cat, 0)
        for opt in options:
            title_l = opt["title"].lower()
            ctx_l = opt["context"].lower()
            score = float(base_pressure * 3)
            if cat == weakest:
                score += 4.0
            elif cat == second_weakest:
                score += 2.0
            elif cat == strongest:
                score += 1.0
            for kw in keyword_map.get(cat_key, []):
                if kw in signal_text:
                    score += 1.5
                if kw in title_l or kw in ctx_l:
                    score += 0.8
            candidates.append((score, cat, opt))

    candidates.sort(key=lambda x: x[0], reverse=True)
    used_titles: set[str] = set()
    picks: List[Dict] = []
    for _, cat, opt in candidates:
        if opt["title"] in used_titles:
            continue
        used_titles.add(opt["title"])
        picks.append(
            {
                "category": cat,
                "title": opt["title"],
                "context": opt["context"],
                "why": activity_justification(cat, weakest, second_weakest, strongest),
                "url": resolve_activity_link(opt["title"], acts),
            }
        )
        if len(picks) >= n:
            break
    return picks


def to_pct(dist_counts: Dict[int, int]) -> Dict[int, float]:
    total = float(sum(dist_counts.values()))
    if total == 0:
        return {i: 0.0 for i in range(1, 11)}
    return {i: dist_counts.get(i, 0) * 100 / total for i in range(1, 11)}


def dedupe_students(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["Email"] = df["Email"].fillna("").astype(str).str.strip().str.lower()
    df = df[df["Email"] != ""]
    if "Completed Date" in df.columns:
        df["Completed Date"] = pd.to_datetime(df["Completed Date"], dayfirst=True, errors="coerce")
    # Keep latest record per student.
    df = df.sort_values("Completed Date").drop_duplicates("Email", keep="last")
    return df


def load_c1_aggregates() -> pd.DataFrame:
    if not C1_CSV_PATH.exists():
        return pd.DataFrame(columns=["Email", "V1_src", "E1_src", "S1_src", "P1_src", "A1_src", "O1_src"])
    c1 = pd.read_csv(C1_CSV_PATH, encoding="utf-8-sig")
    email_col = "Student Email" if "Student Email" in c1.columns else "Email"
    c1["Email"] = c1[email_col].fillna("").astype(str).str.strip().str.lower()
    c1 = c1[c1["Email"] != ""].copy()
    date_col = "Questionnaire Completed Date" if "Questionnaire Completed Date" in c1.columns else None
    if date_col:
        c1[date_col] = pd.to_datetime(c1[date_col], dayfirst=True, errors="coerce")
        c1 = c1.sort_values(date_col).drop_duplicates("Email", keep="last")
    else:
        c1 = c1.drop_duplicates("Email", keep="last")
    keep = ["Email", "V1", "E1", "S1", "P1", "A1", "O1"]
    present = [k for k in keep if k in c1.columns]
    c1 = c1[present].copy()
    rename = {k: f"{k}_src" for k in ["V1", "E1", "S1", "P1", "A1", "O1"] if k in c1.columns}
    c1 = c1.rename(columns=rename)
    for k in ["V1_src", "E1_src", "S1_src", "P1_src", "A1_src", "O1_src"]:
        if k in c1.columns:
            c1[k] = pd.to_numeric(c1[k], errors="coerce")
    return c1


def apply_c1_aggregates(df: pd.DataFrame, c1_agg: pd.DataFrame) -> pd.DataFrame:
    if c1_agg.empty:
        return df
    out = df.merge(c1_agg, on="Email", how="left")
    out["V1_calc"] = out["V1_src"].combine_first(out["V1_calc"])
    out["E1_calc"] = out["E1_src"].combine_first(out["E1_calc"])
    out["S1_calc"] = out["S1_src"].combine_first(out["S1_calc"])
    out["P1_calc"] = out["P1_src"].combine_first(out["P1_calc"])
    out["A1_calc"] = out["A1_src"].combine_first(out["A1_calc"])
    # Recompute O1 from the final C1 dimension scores to keep consistency.
    out["O1_calc"] = out[["V1_calc", "E1_calc", "S1_calc", "P1_calc", "A1_calc"]].mean(axis=1)
    drop_cols = [c for c in ["V1_src", "E1_src", "S1_src", "P1_src", "A1_src", "O1_src"] if c in out.columns]
    return out.drop(columns=drop_cols)


def avg_to_vespa_score(category: str, avg_val: float) -> float:
    if pd.isna(avg_val):
        return np.nan
    key = category.upper()
    if key not in VESPA_THRESHOLDS:
        return np.nan
    thresholds = VESPA_THRESHOLDS[key]
    for idx, (lo, hi) in enumerate(thresholds, start=1):
        if lo <= avg_val < hi or (idx == 10 and avg_val >= lo):
            return float(idx)
    return np.nan


def derive_cycle_scales_from_questions(df: pd.DataFrame, cycle: int) -> pd.DataFrame:
    out = df.copy()
    cat_suffix = {
        "Vision": "v",
        "Effort": "e",
        "Systems": "s",
        "Practice": "p",
        "Attitude": "a",
    }
    for cat, suff in cat_suffix.items():
        cols = [c for c in out.columns if re.match(rf"^c{cycle}_Q\d+{suff}$", str(c))]
        if not cols:
            out[f"{cat[0]}{cycle}_calc"] = np.nan
            continue
        means = clean_likert_df(out[cols]).mean(axis=1)
        out[f"{cat[0]}{cycle}_calc"] = means.apply(lambda x: avg_to_vespa_score(cat, x))
    out[f"O{cycle}_calc"] = out[[f"V{cycle}_calc", f"E{cycle}_calc", f"S{cycle}_calc", f"P{cycle}_calc", f"A{cycle}_calc"]].mean(axis=1)
    return out


def matched_cohort(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    return out[
        pd.to_numeric(out["O1_calc"], errors="coerce").notna()
        & pd.to_numeric(out["O2_calc"], errors="coerce").notna()
    ].copy()


def statement_map() -> Dict[int, str]:
    non_outcome = [s for s, cat in ber.STATEMENT_MAPPING.items() if cat != "Outcome"]
    return {i + 1: text for i, text in enumerate(non_outcome[:29])}


def question_col(df: pd.DataFrame, cycle: int, q_num: int) -> str | None:
    pat = re.compile(rf"^c{cycle}_Q{q_num}[a-zA-Z]*$")
    for c in df.columns:
        if pat.match(str(c)):
            return c
    return None


def calc_eri(df: pd.DataFrame, cycle: int) -> float:
    cols = [f"c{cycle}_sup", f"c{cycle}_prep", f"c{cycle}_conf"]
    present = [c for c in cols if c in df.columns]
    if len(present) < 3:
        return float("nan")
    vals = clean_likert_df(df[present]).values
    return float(np.nanmean(np.nanmean(vals, axis=1)))


def calc_dimension_stats(df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
    out = {}
    for dim, (c1, c2) in DIM_COLS.items():
        s1 = pd.to_numeric(df[c1], errors="coerce")
        s2 = pd.to_numeric(df[c2], errors="coerce")
        matched = df[[c1, c2]].apply(pd.to_numeric, errors="coerce").dropna()
        out[dim] = {
            "c1_mean": float(s1.mean()),
            "c2_mean": float(s2.mean()),
            "delta_matched": float((matched[c2] - matched[c1]).mean()) if len(matched) else float("nan"),
            "n_c1": int(s1.notna().sum()),
            "n_c2": int(s2.notna().sum()),
            "n_matched": int(len(matched)),
        }
    return out


def pct_change(c1: float, c2: float) -> float:
    if pd.isna(c1) or pd.isna(c2) or c1 == 0:
        return float("nan")
    return float(((c2 - c1) / c1) * 100.0)


def calc_statement_journey(df: pd.DataFrame) -> List[Dict]:
    mapping = statement_map()
    rows = []
    for q_num, text in mapping.items():
        c1 = question_col(df, 1, q_num)
        c2 = question_col(df, 2, q_num)
        if not c1 or not c2:
            continue
        pair = clean_likert_df(df[[c1, c2]]).dropna()
        if len(pair) == 0:
            continue
        m1 = float(pair[c1].mean())
        m2 = float(pair[c2].mean())
        rows.append(
            {
                "q": q_num,
                "statement": text,
                "c1_mean": m1,
                "c2_mean": m2,
                "delta": float(m2 - m1),
                "n": int(len(pair)),
                "category": ber.STATEMENT_MAPPING.get(text, "Unknown"),
            }
        )
    rows.sort(key=lambda x: x["delta"])
    return rows


def calc_insights_journey(df: pd.DataFrame) -> List[Dict]:
    mapping = statement_map()
    rev = {norm_text(v): k for k, v in mapping.items()}
    outcome_cols = {
        norm_text("I have the support I need to achieve this year?"): ("c1_sup", "c2_sup"),
        norm_text(" I feel equipped to face the study and revision challenges this year?"): ("c1_prep", "c2_prep"),
        norm_text(" I am confident I will achieve my potential in my final exams?"): ("c1_conf", "c2_conf"),
    }

    def agree_pct(cols: List[str]) -> Tuple[float, int]:
        total = 0
        agree = 0
        for col in cols:
            if col not in df.columns:
                continue
            s = clean_likert_series(df[col]).dropna()
            total += len(s)
            agree += int((s >= INSIGHT_AGREE_THRESHOLD).sum())
        return ((agree / total) * 100.0 if total else 0.0), total

    insights = []
    for insight_id, cfg in JOURNEY_INSIGHTS.items():
        c1_cols = []
        c2_cols = []
        for q_text in cfg["questions"]:
            nqt = norm_text(q_text)
            if nqt in outcome_cols:
                c1_cols.append(outcome_cols[nqt][0])
                c2_cols.append(outcome_cols[nqt][1])
                continue
            q_num = rev.get(nqt)
            if not q_num:
                for alt in INSIGHT_QUESTION_ALIASES.get(nqt, []):
                    q_num = rev.get(alt)
                    if q_num:
                        break
            if not q_num:
                continue
            c1 = question_col(df, 1, q_num)
            c2 = question_col(df, 2, q_num)
            if c1:
                c1_cols.append(c1)
            if c2:
                c2_cols.append(c2)

        c1_pct, c1_n = agree_pct(c1_cols)
        c2_pct, c2_n = agree_pct(c2_cols)
        insights.append(
            {
                "id": insight_id,
                "title": cfg["title"],
                "icon": cfg["icon"],
                "questions": cfg["questions"],
                "c1_pct": c1_pct,
                "c2_pct": c2_pct,
                "delta": c2_pct - c1_pct,
                "n_c1": c1_n,
                "n_c2": c2_n,
            }
        )
    insights.sort(key=lambda x: x["delta"])
    return insights


def distribution(series: pd.Series) -> Dict[int, float]:
    s = pd.to_numeric(series, errors="coerce").dropna()
    if len(s) == 0:
        return {i: 0.0 for i in range(1, 11)}
    out = {}
    for i in range(1, 11):
        out[i] = float((s.round() == i).sum() * 100.0 / len(s))
    return out


def chart_distribution(df: pd.DataFrame, dim: str) -> str:
    c1_col, c2_col = DIM_COLS[dim]
    c1 = distribution(df[c1_col])
    c2 = distribution(df[c2_col])
    nat1 = to_pct(NATIONAL_DIST_COUNTS[1][dim])
    nat2 = to_pct(NATIONAL_DIST_COUNTS[2][dim])
    x = list(range(1, 11))

    base_color = ber.COLORS.get(dim, "#667eea")
    c1_color = hex_to_rgba(base_color, 0.35)
    c2_color = hex_to_rgba(base_color, 0.9)

    fig = go.Figure()
    fig.add_trace(go.Bar(x=x, y=[c1[i] for i in x], name="School C1", marker_color=c1_color))
    fig.add_trace(go.Bar(x=x, y=[c2[i] for i in x], name="School C2", marker_color=c2_color))
    fig.add_trace(go.Scatter(x=x, y=[nat1[i] for i in x], name="National C1", mode="lines+markers", line=dict(color="#888", dash="dot")))
    fig.add_trace(go.Scatter(x=x, y=[nat2[i] for i in x], name="National C2", mode="lines+markers", line=dict(color="#d62728")))
    fig.update_layout(
        barmode="group",
        title=f"{dim} Distribution: Cycle 1 vs Cycle 2 vs National",
        xaxis_title="Score",
        yaxis_title="Percentage (%)",
        height=430,
        paper_bgcolor="white",
        plot_bgcolor="rgba(240,240,240,0.35)",
        legend=dict(orientation="h", y=1.08),
    )
    return pio.to_html(fig, full_html=False, include_plotlyjs=False)


def headline_from_dims(stats: Dict[str, Dict[str, float]]) -> str:
    deltas_pct = {}
    for k, v in stats.items():
        if k == "Overall":
            continue
        pc = pct_change(v["c1_mean"], v["c2_mean"])
        if not np.isnan(pc):
            deltas_pct[k] = pc
    if not deltas_pct:
        return "We have limited matched data, so the key priority is improving completion across both cycles."
    sorted_dims = sorted(deltas_pct.items(), key=lambda x: x[1])
    best = sorted_dims[-1]
    lowest = sorted_dims[0]
    second_lowest = sorted_dims[1] if len(sorted_dims) > 1 else sorted_dims[0]

    if lowest[1] < 0:
        return (
            f"The areas needing most attention are {lowest[0]} ({lowest[1]:+.1f}%) and "
            f"{second_lowest[0]} ({second_lowest[1]:+.1f}%), while {best[0]} is strongest ({best[1]:+.1f}%)."
        )

    return (
        f"This school is holding or improving across all dimensions. "
        f"Strongest movement is in {best[0]} ({best[1]:+.1f}%); "
        f"the smallest change is in {lowest[0]} ({lowest[1]:+.1f}%)."
    )


def quick_wins(stats: Dict[str, Dict[str, float]], statements: List[Dict]) -> List[str]:
    dim_deltas = {k: v["delta_matched"] for k, v in stats.items() if k != "Overall" and not np.isnan(v["delta_matched"])}
    if not dim_deltas:
        return [
            "Prioritise improving matched completion so Cycle 1 to Cycle 2 comparisons stay robust.",
            "Use tutor check-ins to identify students who completed only one cycle and support full participation in the next cycle.",
            "Keep reinforcement focused on consistent routines while matched sample grows.",
        ]
    weakest_dims = [k for k, _ in sorted(dim_deltas.items(), key=lambda x: x[1])[:2]]
    if len(weakest_dims) == 1:
        weakest_dims.append(weakest_dims[0])
    biggest_dip = statements[0]["statement"] if statements else "key study habit statements"
    return [
        f"In tutor time, run a short weekly routine on {weakest_dims[0]} habits for the next 6 weeks.",
        f"Use low-stakes retrieval starters in lessons to support {weakest_dims[1]} and confidence.",
        f"Address the weakest statement directly: \"{biggest_dip}\" with explicit modelling and check-ins.",
    ]


def completion_block(df_scope: pd.DataFrame) -> str:
    total = int(df_scope["Email"].nunique())
    c1 = int(pd.to_numeric(df_scope["V1_calc"], errors="coerce").notna().sum())
    c2 = int(pd.to_numeric(df_scope["V2_calc"], errors="coerce").notna().sum())
    both = int(df_scope[["V1_calc", "V2_calc"]].apply(pd.to_numeric, errors="coerce").dropna().shape[0])
    c1_rate = (c1 / total * 100) if total else 0
    c2_rate = (c2 / total * 100) if total else 0
    both_rate = (both / total * 100) if total else 0
    return (
        f"<p><strong>Coverage:</strong> {total} students in scope | "
        f"C1: {c1} ({c1_rate:.1f}%) | C2: {c2} ({c2_rate:.1f}%) | Matched journey cohort: {both} ({both_rate:.1f}%).</p>"
    )


def cohort_validity_block(df_scope: pd.DataFrame) -> str:
    total = int(df_scope["Email"].nunique())
    o1 = pd.to_numeric(df_scope["O1_calc"], errors="coerce")
    o2 = pd.to_numeric(df_scope["O2_calc"], errors="coerce")
    matched = int((o1.notna() & o2.notna()).sum())
    c1_only = int((o1.notna() & o2.isna()).sum())
    c2_only = int((o1.isna() & o2.notna()).sum())
    neither = int((o1.isna() & o2.isna()).sum())
    matched_rate = (matched / total * 100.0) if total else 0.0
    return f"""
    <div style="margin-top:10px; padding:14px; background:#ffffff; border:1px solid #dbeafe; border-radius:10px;">
      <h3 style="margin:0 0 6px 0;">Cohort validity check</h3>
      <p style="margin:0 0 6px 0;"><strong>Matched cohort:</strong> {matched}/{total} ({matched_rate:.1f}%)</p>
      <p style="margin:0; color:#4b5563;">Unmatched breakdown: C1-only {c1_only} | C2-only {c2_only} | Neither {neither}</p>
    </div>
"""


def section_journey_overview(stats: Dict[str, Dict[str, float]], title: str, subtext: str) -> str:
    cards = ""
    for dim in ["Vision", "Effort", "Systems", "Practice", "Attitude", "Overall"]:
        v = stats[dim]
        delta = v["delta_matched"]
        delta_pct = pct_change(v["c1_mean"], v["c2_mean"])
        cls = "positive" if delta >= 0 else "negative"
        dim_color = THEME_HEX.get(dim, "#667eea")
        bg_1 = hex_to_rgba(dim_color, 0.82)
        bg_2 = hex_to_rgba(dim_color, 0.62)
        chip_bg = "rgba(16,185,129,0.2)" if delta_pct >= 0 else "rgba(239,68,68,0.2)"
        chip_fg = "#ecfdf5" if delta_pct >= 0 else "#fef2f2"
        chip_border = "rgba(16,185,129,0.45)" if delta_pct >= 0 else "rgba(239,68,68,0.45)"
        cards += f"""
            <div class="stat-card" style="background:linear-gradient(135deg,{bg_1},{bg_2}); color:#ffffff; border:none; box-shadow: 0 4px 10px rgba(15,23,42,0.14); filter:saturate(0.70) brightness(0.92);">
                <h4>{dim}</h4>
                <div class="value">{v['c2_mean']:.2f}</div>
                <small style="color:rgba(255,255,255,0.92);">C1: {v['c1_mean']:.2f}</small>
                <div class="{cls}" style="margin-top:8px; display:inline-block; padding:4px 10px; border-radius:999px; background:{chip_bg}; color:{chip_fg}; border:1px solid {chip_border}; font-weight:700;">Change from Cycle 1: {delta_pct:+.1f}%</div>
                <small style="display:block; margin-top:8px; color:rgba(255,255,255,0.92);">Matched n={v['n_matched']}</small>
            </div>
"""
    return f"""
    <div class="section">
      <h2>{title}</h2>
      <p>{subtext}</p>
      <div class="stats-grid">{cards}</div>
    </div>
"""


def section_distributions(df: pd.DataFrame) -> str:
    charts = ""
    for dim in ["Vision", "Effort", "Systems", "Practice", "Attitude", "Overall"]:
        charts += f'<div class="chart-container">{chart_distribution(df, dim)}</div>'
    return f"""
    <div class="section">
      <h2>Score Distributions: Cycle 1 vs Cycle 2 vs National</h2>
      <p>These charts help you see whether movement is only in average score, or whether the full response pattern is shifting. Read these alongside the journey cards to spot where stronger habits are spreading and where inconsistency remains.</p>
      {charts}
    </div>
"""


def section_insights(insights: List[Dict], school_name: str) -> str:
    cards = ""
    rows = ""
    modals = ""

    def clean_question_text(q: str) -> str:
        t = (q or "").strip()
        t = t.rstrip("?").strip()
        return t

    for r in sorted(insights, key=lambda x: x["c2_pct"], reverse=True):
        c2 = r["c2_pct"]
        delta = r["delta"]
        modal_id = f"insight-modal-{r['id']}"
        if c2 >= 75:
            cls = "excellent"
            color = "#10b981"
            label = "Strong"
        elif c2 >= 60:
            cls = "good"
            color = "#3b82f6"
            label = "Good"
        elif c2 >= 40:
            cls = "average"
            color = "#f59e0b"
            label = "Mixed"
        else:
            cls = "poor"
            color = "#ef4444"
            label = "Priority"

        cards += f"""
            <button class="insight-card {cls} insight-card-button" onclick="openInsightModal('{modal_id}')">
                <div class="insight-header">
                    <div class="insight-icon">{r['icon']}</div>
                    <div class="insight-title">{r['title']}</div>
                </div>
                <div class="insight-percentage {cls}">{c2:.1f}%</div>
                <div class="insight-label">Cycle 2 Agreement ({label})</div>
                <div class="insight-meta">Change from Cycle 1: <span style="color:{color};font-weight:700;">{delta:+.1f}%</span></div>
                <div class="insight-meta" style="margin-top:6px;color:#475569;">Click to view questions</div>
            </button>
"""
        q_html = "".join([f"<li>{clean_question_text(q)}</li>" for q in r.get("questions", [])]) or "<li>No mapped questions found.</li>"
        modals += f"""
        <div id="{modal_id}" class="insight-modal-overlay" onclick="closeInsightModal('{modal_id}')">
          <div class="insight-modal" onclick="event.stopPropagation();">
            <div class="target-modal-header">
              <h3>{r['icon']} {r['title']}</h3>
              <button class="target-modal-close" onclick="closeInsightModal('{modal_id}')">&times;</button>
            </div>
            <p><strong>Cycle 2 agreement:</strong> {r['c2_pct']:.1f}%</p>
            <p><strong>Change from Cycle 1:</strong> {r['delta']:+.1f}%</p>
            <p><strong>Scoring rule:</strong> percentage of responses at {INSIGHT_AGREE_THRESHOLD}-5 on a 5-point scale.</p>
            <h4 style="margin-top:10px;">Questions included in this insight</h4>
            <ul>{q_html}</ul>
          </div>
        </div>
"""

        cls_row = "positive" if delta >= 0 else "negative"
        rows += f"""
        <tr>
          <td><button class="insight-link" onclick="openInsightModal('{modal_id}')">{r['icon']} {r['title']}</button></td>
          <td style="text-align:center;">{r['c1_pct']:.1f}%</td>
          <td style="text-align:center;">{r['c2_pct']:.1f}%</td>
          <td class="{cls_row}" style="text-align:center;">{delta:+.1f}%</td>
        </tr>
"""

    rising = sorted(insights, key=lambda x: x["delta"], reverse=True)[:3]
    falling = sorted(insights, key=lambda x: x["delta"])[:2]
    rising_txt = ", ".join([f"{i['title']} ({i['delta']:+.1f}%)" for i in rising])
    falling_txt = ", ".join([f"{i['title']} ({i['delta']:+.1f}%)" for i in falling])
    return f"""
    <div class="section insights-section">
      <h2>12 Insight Areas</h2>
      <p>These show where habits are improving most and where pressure is building. Biggest gains are in <strong>{rising_txt}</strong>, while the main watch areas are <strong>{falling_txt}</strong>.</p>
      <p><strong>Tip:</strong> click any insight card, or the insight name in the table, to view the exact questions used in that insight.</p>
      <p>Each insight uses a small group of related questions and reports the % of responses at <strong>{INSIGHT_AGREE_THRESHOLD}-5</strong> (agree/strongly agree).</p>
      <p><strong>Why this can differ from VESPA scores:</strong> VESPA scores show an average position on a 1-10 scale, while insight % shows the share reaching agreement on specific questions.</p>
      <div style="background: #e8f4f8; padding: 20px; border-radius: 10px; margin-bottom: 25px; border-left: 4px solid #06b6d4;">
        <h3 style="color: #2c3e50; margin-bottom: 12px;">What this means for teachers</h3>
        <p style="margin-bottom: 10px;">Use these insight areas to see where students are settling in and where support needs to be sharper.</p>
        <p style="margin-bottom: 10px;">A dip between cycles can happen mid-year. The key thing is to focus support before Cycle 3.</p>
      </div>
      <div style="margin: 25px 0; padding: 20px; background: linear-gradient(to right, #f8f9fa, #ffffff); border-radius: 10px; border-left: 4px solid #667eea;">
        <h4 style="color: #2c3e50; margin-bottom: 10px;">Understanding the Ratings</h4>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-top: 15px;">
          <div style="padding: 10px; background: rgba(16, 185, 129, 0.1); border-radius: 5px; border-left: 3px solid #10b981;"><strong style="color:#10b981;">75%+ Strong</strong><br><small>Most responses are agree/strongly agree</small></div>
          <div style="padding: 10px; background: rgba(59, 130, 246, 0.1); border-radius: 5px; border-left: 3px solid #3b82f6;"><strong style="color:#3b82f6;">60-74% Good</strong><br><small>Mostly positive, but not yet secure for all</small></div>
          <div style="padding: 10px; background: rgba(245, 158, 11, 0.1); border-radius: 5px; border-left: 3px solid #f59e0b;"><strong style="color:#f59e0b;">40-59% Mixed</strong><br><small>Views are split across students</small></div>
          <div style="padding: 10px; background: rgba(239, 68, 68, 0.1); border-radius: 5px; border-left: 3px solid #ef4444;"><strong style="color:#ef4444;">&lt;40% Priority</strong><br><small>Few students are currently agreeing</small></div>
        </div>
      </div>
      <div class="insights-grid">{cards}</div>
      {modals}
      <h3 style="margin-top:25px;">Insight Score Changes</h3>
      <table>
        <thead><tr><th>Insight</th><th style="text-align:center;">Cycle 1</th><th style="text-align:center;">Cycle 2</th><th style="text-align:center;">Change in agreement</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
"""


def section_statements(statements: List[Dict]) -> str:
    declines = statements[:8]
    gains = sorted(statements, key=lambda x: x["delta"], reverse=True)[:8]
    l1 = "".join([f"<li><strong>{s['statement']}</strong><br><small>C1 {s['c1_mean']:.2f} -> C2 {s['c2_mean']:.2f} ({s['delta']:+.2f})</small></li>" for s in declines])
    l2 = "".join([f"<li><strong>{s['statement']}</strong><br><small>C1 {s['c1_mean']:.2f} -> C2 {s['c2_mean']:.2f} ({s['delta']:+.2f})</small></li>" for s in gains])
    return f"""
    <div class="section">
      <h2>Statement Journey Analysis</h2>
      <p>The statement-level shifts show what students are actually experiencing. Dips are often practical and routine-based, while gains indicate where habits are maturing.</p>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:24px;">
        <div style="background:#fff;border:2px solid #dc3545;border-radius:10px;padding:16px;"><h3 style="color:#dc3545;">Largest Dips</h3><ol>{l1}</ol></div>
        <div style="background:#fff;border:2px solid #28a745;border-radius:10px;padding:16px;"><h3 style="color:#28a745;">Strongest Gains</h3><ol>{l2}</ol></div>
      </div>
    </div>
"""


def top_target_students(df_matched: pd.DataFrame, max_rows: int = 10) -> str:
    if df_matched.empty:
        return """
        <h3 style="margin-top:20px;">Top 10 target students (matched cohort)</h3>
        <p>No matched students available to rank for targeted support.</p>
        """

    qmap = statement_map()
    rev = {norm_text(v): k for k, v in qmap.items()}
    target_statements = [
        "I plan and organise my time to get my work done",
        "My books/files are organised",
        "I complete all my homework on time",
        "I always meet deadlines ",
    ]
    target_qs = [rev.get(norm_text(s)) for s in target_statements]
    target_qs = [q for q in target_qs if q]

    rows = []
    for _, r in df_matched.iterrows():
        name = str(r.get("Name", "")).strip() or str(r.get("Email", "")).strip()
        email = str(r.get("Email", "")).strip()
        o1 = float(pd.to_numeric(pd.Series([r.get("O1_calc")]), errors="coerce").iloc[0]) if pd.notna(pd.to_numeric(pd.Series([r.get("O1_calc")]), errors="coerce").iloc[0]) else np.nan
        o2 = float(pd.to_numeric(pd.Series([r.get("O2_calc")]), errors="coerce").iloc[0]) if pd.notna(pd.to_numeric(pd.Series([r.get("O2_calc")]), errors="coerce").iloc[0]) else np.nan
        if pd.isna(o1) or pd.isna(o2):
            continue

        overall_delta = o2 - o1
        risk = max(0.0, -overall_delta) * 3.0
        risk += max(0.0, 6.0 - o2) * 1.2

        pressure_hits = 0
        pressure_txt = []
        for q in target_qs:
            c1 = question_col(df_matched, 1, q)
            c2 = question_col(df_matched, 2, q)
            if not c1 or not c2:
                continue
            v1 = clean_likert_series(pd.Series([r.get(c1)])).iloc[0]
            v2 = clean_likert_series(pd.Series([r.get(c2)])).iloc[0]
            if pd.isna(v1) or pd.isna(v2):
                continue
            d = float(v2 - v1)
            if d <= -1 or v2 <= 2:
                pressure_hits += 1
                risk += 1.0
                pressure_txt.append(f"{qmap[q]}: C1 {v1:.1f} -> C2 {v2:.1f} ({d:+.1f})")

        # Volatility signal: large opposite shifts can hide behind small overall movement.
        volatility = 0
        volatile_items = []
        for q, st in qmap.items():
            c1 = question_col(df_matched, 1, q)
            c2 = question_col(df_matched, 2, q)
            if not c1 or not c2:
                continue
            v1 = clean_likert_series(pd.Series([r.get(c1)])).iloc[0]
            v2 = clean_likert_series(pd.Series([r.get(c2)])).iloc[0]
            if pd.isna(v1) or pd.isna(v2):
                continue
            d = float(v2 - v1)
            if abs(d) >= 2.0:
                volatility += 1
                volatile_items.append((st, v1, v2, d))
        risk += min(3.0, volatility * 0.4)
        volatile_items.sort(key=lambda x: abs(x[3]), reverse=True)

        dim_pairs = [
            ("Vision", "V1_calc", "V2_calc"),
            ("Effort", "E1_calc", "E2_calc"),
            ("Systems", "S1_calc", "S2_calc"),
            ("Practice", "P1_calc", "P2_calc"),
            ("Attitude", "A1_calc", "A2_calc"),
        ]
        dim_lines = []
        for dn, c1c, c2c in dim_pairs:
            d1 = pd.to_numeric(pd.Series([r.get(c1c)]), errors="coerce").iloc[0]
            d2 = pd.to_numeric(pd.Series([r.get(c2c)]), errors="coerce").iloc[0]
            if pd.notna(d1) and pd.notna(d2):
                dim_lines.append(f"{dn}: {d1:.2f} -> {d2:.2f} ({pct_change(d1, d2):+.1f}%)")

        reasons = []
        if overall_delta < 0:
            reasons.append(f"overall {pct_change(o1, o2):+.1f}%")
        if pressure_hits:
            reasons.append(f"{pressure_hits} routine flags")
        if volatility >= 3:
            reasons.append(f"{volatility} volatile item shifts")
        if not reasons:
            reasons.append("low C2 profile with mixed item pattern")

        rows.append(
            {
                "name": name,
                "email": email,
                "c1": o1,
                "c2": o2,
                "delta_pct": pct_change(o1, o2),
                "risk": risk,
                "pressure": "; ".join(pressure_txt[:2]),
                "reasons": ", ".join(reasons),
                "routine_details": pressure_txt,
                "volatile_details": volatile_items,
                "dimension_details": dim_lines,
                "routine_count": pressure_hits,
                "volatile_count": volatility,
            }
        )

    rows = sorted(rows, key=lambda x: x["risk"], reverse=True)[:max_rows]
    if not rows:
        return """
        <h3 style="margin-top:20px;">Top 10 target students (matched cohort)</h3>
        <p>No matched students available to rank for targeted support.</p>
        """

    body = ""
    modals = ""
    for i, r in enumerate(rows, start=1):
        modal_id = f"target-modal-{i}"
        routine_html = "".join([f"<li>{x}</li>" for x in r["routine_details"]]) or "<li>No routine flags triggered.</li>"
        volatile_html = "".join(
            [f"<li>{st}<br><small>C1 {v1:.1f} -> C2 {v2:.1f} ({d:+.1f})</small></li>" for st, v1, v2, d in r["volatile_details"]]
        ) or "<li>No volatile item shifts (>=2 points) detected.</li>"
        dim_html = "".join([f"<li>{x}</li>" for x in r["dimension_details"]]) or "<li>No dimension-level detail available.</li>"
        body += f"""
        <tr>
          <td style="text-align:center;">{i}</td>
          <td><button class="target-link" onclick="openTargetModal('{modal_id}')">{r['name']}</button></td>
          <td>{r['email']}</td>
          <td style="text-align:center;">{r['c1']:.2f}</td>
          <td style="text-align:center;">{r['c2']:.2f}</td>
          <td style="text-align:center;">{r['delta_pct']:+.1f}%</td>
          <td>{r['reasons']}</td>
        </tr>
        """
        modals += f"""
        <div id="{modal_id}" class="target-modal-overlay" onclick="closeTargetModal('{modal_id}')">
          <div class="target-modal" onclick="event.stopPropagation();">
            <div class="target-modal-header">
              <h3>{r['name']}</h3>
              <button class="target-modal-close" onclick="closeTargetModal('{modal_id}')">&times;</button>
            </div>
            <p><strong>Email:</strong> {r['email']}</p>
            <p><strong>Overall score:</strong> C1 {r['c1']:.2f} -> C2 {r['c2']:.2f} ({r['delta_pct']:+.1f}%)</p>
            <p><strong>Why this student is in top 10:</strong> {r['reasons']}</p>
            <div class="target-modal-grid">
              <div>
                <h4>Routine flags (full)</h4>
                <ul>{routine_html}</ul>
              </div>
              <div>
                <h4>Volatile item shifts (full)</h4>
                <ul>{volatile_html}</ul>
              </div>
            </div>
            <h4 style="margin-top:12px;">VESPA theme profile (C1 -> C2)</h4>
            <ul>{dim_html}</ul>
          </div>
        </div>
        """

    return f"""
    <h3 style="margin-top:20px;">Top 10 target students (matched cohort)</h3>
    <p>Ranked by combined risk signal: overall VESPA drop, low current profile, and routine/statement pressure indicators.</p>
    <p><strong>What the flags mean:</strong> <strong>Routine Flags</strong> show repeated issues in core organisation/time-management habits (for example planning time, meeting deadlines, keeping materials organised). <strong>Volatile Item Shifts</strong> show large statement-level movement (2+ points up/down) between cycles, suggesting unstable habits even when overall scores look steady.</p>
    <table>
      <thead>
        <tr>
          <th style="text-align:center;">Rank</th>
          <th>Name</th>
          <th>Email</th>
          <th style="text-align:center;">C1 Overall</th>
          <th style="text-align:center;">C2 Overall</th>
          <th style="text-align:center;">Change</th>
          <th>Why prioritise</th>
        </tr>
      </thead>
      <tbody>{body}</tbody>
    </table>
    {modals}
    """


def students_of_interest(df_matched: pd.DataFrame) -> str:
    if df_matched.empty:
        return """
        <div class="section">
          <h2>Students of Interest (Matched Cohort)</h2>
          <p>No matched students available for this section.</p>
        </div>
"""
    df = df_matched.copy()
    for col in ["V1_calc", "E1_calc", "S1_calc", "P1_calc", "A1_calc", "O1_calc", "V2_calc", "E2_calc", "S2_calc", "P2_calc", "A2_calc", "O2_calc"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["overall_delta"] = df["O2_calc"] - df["O1_calc"]
    delta_std = float(df["overall_delta"].std()) if len(df) > 1 else 0.0
    # Keep a practical threshold so schools always see meaningful flags.
    sig_thr = min(max(1.0, 0.9 * delta_std), 2.0)

    pos = df[df["overall_delta"] >= sig_thr].sort_values("overall_delta", ascending=False).head(8)
    neg = df[df["overall_delta"] <= -sig_thr].sort_values("overall_delta", ascending=True).head(8)

    qmap = statement_map()
    q_pairs = []
    for q_num in qmap:
        c1 = question_col(df, 1, q_num)
        c2 = question_col(df, 2, q_num)
        if c1 and c2:
            q_pairs.append((q_num, c1, c2))

    stable = df[df["overall_delta"].abs() < 0.30].copy()
    anomaly_rows = []
    for _, r in stable.iterrows():
        deltas = []
        for q_num, c1, c2 in q_pairs:
            v1 = clean_likert_series(pd.Series([r.get(c1)])).iloc[0]
            v2 = clean_likert_series(pd.Series([r.get(c2)])).iloc[0]
            if pd.isna(v1) or pd.isna(v2):
                continue
            d = float(v2 - v1)
            deltas.append((q_num, d))
        if not deltas:
            continue
        big = [(q, d) for q, d in deltas if abs(d) >= 2.0]
        if not big:
            continue
        big_sorted = sorted(big, key=lambda x: abs(x[1]), reverse=True)
        highlights = "; ".join([f"{qmap[q]} ({d:+.0f})" for q, d in big_sorted[:3]])
        anomaly_rows.append(
            {
                "name": str(r.get("Name", "")).strip() or str(r.get("Email", "")).strip(),
                "email": str(r.get("Email", "")).strip(),
                "overall_delta": float(r["overall_delta"]),
                "big_count": len(big),
                "highlights": highlights,
            }
        )
    anomaly_rows = sorted(anomaly_rows, key=lambda x: (x["big_count"], abs(x["overall_delta"])), reverse=True)[:10]

    def render_trend_rows(sub: pd.DataFrame, label: str) -> str:
        rows = ""
        for _, r in sub.iterrows():
            name = str(r.get("Name", "")).strip() or str(r.get("Email", "")).strip()
            rows += f"<tr><td>{name}</td><td>{str(r.get('Email','')).strip()}</td><td style='text-align:center;'>{r['O1_calc']:.2f}</td><td style='text-align:center;'>{r['O2_calc']:.2f}</td><td style='text-align:center;'>{pct_change(r['O1_calc'], r['O2_calc']):+.1f}%</td><td>{label}</td></tr>"
        return rows or "<tr><td colspan='6'>None flagged at current significance threshold.</td></tr>"

    anomaly_html = ""
    for r in anomaly_rows:
        anomaly_html += f"<tr><td>{r['name']}</td><td>{r['email']}</td><td style='text-align:center;'>{r['overall_delta']:+.2f} pts</td><td style='text-align:center;'>{r['big_count']}</td><td>{r['highlights']}</td></tr>"
    if not anomaly_html:
        anomaly_html = "<tr><td colspan='5'>None flagged for high item-level volatility with stable overall score.</td></tr>"

    return f"""
    <div class="section">
      <h2>Students of Interest (Matched Cohort)</h2>
      <p>This section highlights students for follow-up, not judgement. We flag clear overall score movement and also students with steady overall scores but big changes in individual responses.</p>
      {top_target_students(df_matched, max_rows=10)}
      <h3>1) Significant overall movement (positive or negative)</h3>
      <table>
        <thead><tr><th>Name</th><th>Email</th><th style="text-align:center;">C1 Overall</th><th style="text-align:center;">C2 Overall</th><th style="text-align:center;">Change</th><th>Flag</th></tr></thead>
        <tbody>{render_trend_rows(pos, 'Positive trend')}{render_trend_rows(neg, 'Negative trend')}</tbody>
      </table>
      <h3 style="margin-top:20px;">2) Stable overall score but unexpected item-level changes</h3>
      <table>
        <thead><tr><th>Name</th><th>Email</th><th style="text-align:center;">Overall Change</th><th style="text-align:center;">Count of large item shifts (>=2)</th><th>Largest item-level shifts</th></tr></thead>
        <tbody>{anomaly_html}</tbody>
      </table>
    </div>
"""


def target_student_pattern_summary(df_matched: pd.DataFrame, max_rows: int = 10) -> Dict:
    # Reuse the same ranking logic indirectly by rebuilding row metadata quickly.
    if df_matched.empty:
        return {"count": 0, "avg_routine": 0.0, "avg_volatile": 0.0, "top_routine": []}

    qmap = statement_map()
    rev = {norm_text(v): k for k, v in qmap.items()}
    target_statements = [
        "I plan and organise my time to get my work done",
        "My books/files are organised",
        "I complete all my homework on time",
        "I always meet deadlines ",
    ]
    target_qs = [rev.get(norm_text(s)) for s in target_statements]
    target_qs = [q for q in target_qs if q]

    scored_rows = []
    routine_counter: Dict[str, int] = {}
    for _, r in df_matched.iterrows():
        o1 = pd.to_numeric(pd.Series([r.get("O1_calc")]), errors="coerce").iloc[0]
        o2 = pd.to_numeric(pd.Series([r.get("O2_calc")]), errors="coerce").iloc[0]
        if pd.isna(o1) or pd.isna(o2):
            continue

        risk = max(0.0, float(o1 - o2)) * 3.0 + max(0.0, float(6.0 - o2)) * 1.2
        routine_hits = 0
        for q in target_qs:
            c1 = question_col(df_matched, 1, q)
            c2 = question_col(df_matched, 2, q)
            if not c1 or not c2:
                continue
            v1 = clean_likert_series(pd.Series([r.get(c1)])).iloc[0]
            v2 = clean_likert_series(pd.Series([r.get(c2)])).iloc[0]
            if pd.isna(v1) or pd.isna(v2):
                continue
            d = float(v2 - v1)
            if d <= -1 or v2 <= 2:
                routine_hits += 1
                risk += 1.0
                st = qmap.get(q, "")
                if st:
                    routine_counter[st] = routine_counter.get(st, 0) + 1

        volatility = 0
        for q in qmap:
            c1 = question_col(df_matched, 1, q)
            c2 = question_col(df_matched, 2, q)
            if not c1 or not c2:
                continue
            v1 = clean_likert_series(pd.Series([r.get(c1)])).iloc[0]
            v2 = clean_likert_series(pd.Series([r.get(c2)])).iloc[0]
            if pd.isna(v1) or pd.isna(v2):
                continue
            if abs(float(v2 - v1)) >= 2.0:
                volatility += 1
        risk += min(3.0, volatility * 0.4)
        scored_rows.append({"risk": risk, "routine_count": routine_hits, "volatile_count": volatility})

    scored_rows = sorted(scored_rows, key=lambda x: x["risk"], reverse=True)[:max_rows]
    if not scored_rows:
        return {"count": 0, "avg_routine": 0.0, "avg_volatile": 0.0, "top_routine": []}

    avg_routine = float(np.mean([r["routine_count"] for r in scored_rows]))
    avg_volatile = float(np.mean([r["volatile_count"] for r in scored_rows]))
    top_routine = sorted(routine_counter.items(), key=lambda x: x[1], reverse=True)[:3]
    return {
        "count": len(scored_rows),
        "avg_routine": avg_routine,
        "avg_volatile": avg_volatile,
        "top_routine": top_routine,
    }


def top_commentary(org_name: str, stats: Dict[str, Dict[str, float]], insights: List[Dict], statements: List[Dict], quickwins: List[str], headline: str, df_scope: pd.DataFrame) -> str:
    top_ins = sorted(insights, key=lambda x: x["delta"], reverse=True)[:5]
    watch_ins = sorted(insights, key=lambda x: x["delta"])[:3]
    low_stmt = sorted(statements, key=lambda x: x["delta"])[:2]
    top_items = "".join([f"<li><strong>{i['title']}</strong>: {i['delta']:+.1f}% ({i['c1_pct']:.1f}% -> {i['c2_pct']:.1f}%)</li>" for i in top_ins])
    watch_txt = "; ".join([f"<strong>{i['title']}</strong>: {i['delta']:+.1f}%" for i in watch_ins])
    low_txt = "<br>".join([f"\"{s['statement']}\" <strong>{s['delta']:+.2f} pts</strong>" for s in low_stmt])
    wins = "".join([f"<li>{q}</li>" for q in quickwins])
    dim_signals = {k: v["delta_matched"] for k, v in stats.items() if k in ["Vision", "Effort", "Systems", "Practice", "Attitude"]}
    strongest_dim = max(dim_signals, key=dim_signals.get) if dim_signals else "Practice"
    weakest_dim = min(dim_signals, key=dim_signals.get) if dim_signals else "Systems"
    second_weakest_dim = sorted(dim_signals.items(), key=lambda x: x[1])[1][0] if len(dim_signals) > 1 else weakest_dim
    strongest_val = pct_change(stats[strongest_dim]["c1_mean"], stats[strongest_dim]["c2_mean"]) if strongest_dim in stats else 0.0
    weakest_val = pct_change(stats[weakest_dim]["c1_mean"], stats[weakest_dim]["c2_mean"]) if weakest_dim in stats else 0.0
    effort_val = pct_change(stats["Effort"]["c1_mean"], stats["Effort"]["c2_mean"]) if "Effort" in stats else 0.0
    top_insight = top_ins[0] if top_ins else {"title": "Vision & Purpose", "delta": 0.0}
    top_insight_theme = INSIGHT_TO_THEME.get(top_insight.get("id", ""), "Practice")
    strongest_theme_hex = THEME_HEX.get(strongest_dim, "#667eea")
    weakest_theme_hex = THEME_HEX.get(weakest_dim, "#667eea")
    effort_theme_hex = THEME_HEX.get("Effort", "#667eea")
    insight_theme_hex = THEME_HEX.get(top_insight_theme, "#667eea")
    top_suggestions = choose_flagship_activities(
        [weakest_dim, second_weakest_dim, strongest_dim],
        weakest_dim,
        second_weakest_dim,
        strongest_dim,
        watch_ins,
        statements,
        n=3,
    )
    top_sugg_html = ""
    for a in top_suggestions:
        primary_link = a.get("url") or ""
        full_context = a.get("context", "")
        why = a.get("why", "")
        if primary_link:
            top_sugg_html += (
                f"<li><strong>{a['category']}:</strong> "
                f"<a href=\"{primary_link}\" target=\"_blank\">{a['title']}</a>"
                f"<br><small><strong>Why this activity:</strong> {why}</small>"
                f"<br><small><strong>Context:</strong> {full_context}</small></li>"
            )
        else:
            top_sugg_html += (
                f"<li><strong>{a['category']}:</strong> {a['title']}"
                f"<br><small><strong>Why this activity:</strong> {why}</small>"
                f"<br><small><strong>Context:</strong> {full_context}</small></li>"
            )
    if not top_sugg_html:
        top_sugg_html = "<li>No activity links found in the current activity bank file.</li>"
    return f"""
    <div class="section summary-hero">
      <div class="summary-kicker">Executive summary</div>
      <h2>Cycle 1 to Cycle 2: key outcomes</h2>
      <p><strong>Method note:</strong> all journey comparisons below use matched students who completed both Cycle 1 and Cycle 2.</p>
      {cohort_validity_block(df_scope)}
      <div class="summary-grid">
        <div class="summary-main">
          <h3>The headline story</h3>
          <p class="summary-lead"><strong>{headline}</strong></p>
          <p class="summary-lead" style="margin-top:10px;">The strongest movement is in <strong>{strongest_dim} ({strongest_val:+.1f}%)</strong>. The main pressure point is <strong>{weakest_dim} ({weakest_val:+.1f}%)</strong>. <strong>Effort ({effort_val:+.1f}%)</strong> should be interpreted as a stability signal rather than a stand-alone concern.</p>
          <div class="highlight-row">
            <div class="highlight-card" style="background:linear-gradient(135deg,{hex_to_rgba(strongest_theme_hex, 0.95)},{hex_to_rgba(strongest_theme_hex, 0.75)});">
              <h4>Strongest gain</h4>
              <div class="card-tag">VESPA theme</div>
              <div class="big">{strongest_dim}<br>{strongest_val:+.1f}%</div>
              <div class="sub">Largest relative change from Cycle 1.</div>
            </div>
            <div class="highlight-card" style="background:linear-gradient(135deg,{hex_to_rgba(insight_theme_hex, 0.95)},{hex_to_rgba(insight_theme_hex, 0.72)});">
              <h4>Most improved insight</h4>
              <div class="card-tag">Questionnaire insight</div>
              <div class="big">{top_insight['title']}<br>{top_insight['delta']:+.1f}%</div>
              <div class="sub">Largest increase in 4-5 agreement.</div>
            </div>
            <div class="highlight-card" style="background:linear-gradient(135deg,{hex_to_rgba(weakest_theme_hex, 0.95)},{hex_to_rgba(weakest_theme_hex, 0.72)});">
              <h4>Main pressure point</h4>
              <div class="card-tag">VESPA theme</div>
              <div class="big">{weakest_dim}<br>{weakest_val:+.1f}%</div>
              <div class="sub">This area needs tight follow-through.</div>
            </div>
            <div class="highlight-card" style="background:linear-gradient(135deg,{hex_to_rgba(effort_theme_hex, 0.95)},{hex_to_rgba(effort_theme_hex, 0.72)});">
              <h4>Important nuance</h4>
              <div class="card-tag">VESPA theme</div>
              <div class="big">Effort<br>{effort_val:+.1f}%</div>
              <div class="sub">Read as stable unless a wider dip appears.</div>
            </div>
          </div>
          <div class="callout-band">
            <strong>Best-fit interpretation:</strong> this is a journey pattern, not a fixed endpoint. Keep gains visible and target the routine-based blockers.
          </div>
        </div>
        <div class="summary-side">
          <div class="summary-panel">
            <h3>What has improved most</h3>
            <ol class="mini-list">{top_items}</ol>
          </div>
          <div class="summary-panel">
            <h3>Key areas to spotlight next</h3>
            <p><strong>Insights to watch:</strong> {watch_txt}</p>
            <p style="margin-top:12px;"><strong>Most useful statement-level clues:</strong><br>{low_txt}</p>
          </div>
          <div class="summary-panel">
            <h3>What schools should do with this</h3>
            <p>Protect the strongest gains, then make the weakest routine-based area the next coaching priority.</p>
          </div>
        </div>
      </div>
      <div class="priority-strip">
        <div class="priority-box"><h4>1. Protect the gains</h4><p>Name progress and keep effective habits visible in lessons and tutor time.</p></div>
        <div class="priority-box"><h4>2. Tighten routines</h4><p>Use short, repeatable routines around planning, deadlines and organisation.</p></div>
        <div class="priority-box"><h4>3. Watch silent overload</h4><p>Track whether support-seeking falls while pressure rises.</p></div>
      </div>
      <h3 style="margin-top:16px;">Suggested Activities / Quick Wins</h3>
      <ul>{wins}</ul>
      <ul>{top_sugg_html}</ul>
      <p style="margin-top:10px;">Browse the full activity set in the <a href="https://vespaacademy.knack.com/vespa-academy#curriculum-builder/" target="_blank">VESPA Activity Library</a>.</p>
      {completion_block(df_scope)}
    </div>
"""


def section_action_plan(
    stats: Dict[str, Dict[str, float]],
    insights: List[Dict],
    statements: List[Dict],
    school_name: str,
    df_matched: pd.DataFrame,
) -> str:
    dim_deltas = {k: v["delta_matched"] for k, v in stats.items() if k in ["Vision", "Effort", "Systems", "Practice", "Attitude"]}
    if not dim_deltas:
        return """
        <div class="section">
          <h2>Strategic Recommendations</h2>
          <p>Matched sample is currently too small for reliable strategic interpretation. Priority is improving repeat completion before drawing stronger journey conclusions.</p>
        </div>
"""
    strongest = max(dim_deltas, key=dim_deltas.get)
    weakest = min(dim_deltas, key=dim_deltas.get)
    second_weakest = sorted(dim_deltas.items(), key=lambda x: x[1])[1][0] if len(dim_deltas) > 1 else weakest
    top_ins = sorted(insights, key=lambda x: x["delta"], reverse=True)[:3]
    low_ins = sorted(insights, key=lambda x: x["delta"])[:3]
    low_stmt = sorted(statements, key=lambda x: x["delta"])[:2]
    top_ins_html = "".join([f"<li><strong>{i['title']}</strong> ({i['delta']:+.1f}%)</li>" for i in top_ins])
    low_ins_html = "".join([f"<li><strong>{i['title']}</strong> ({i['delta']:+.1f}%)</li>" for i in low_ins])
    low_stmt_html = "".join([f"<li><strong>{s['statement']}</strong> ({s['delta']:+.2f})</li>" for s in low_stmt])
    target_summary = target_student_pattern_summary(df_matched, max_rows=10)
    routine_txt = ", ".join([f"\"{s}\" ({n})" for s, n in target_summary.get("top_routine", [])]) or "No strong routine concentration yet."
    suggestions = choose_flagship_activities(
        [weakest, second_weakest, strongest],
        weakest,
        second_weakest,
        strongest,
        low_ins,
        statements,
        n=3,
    )
    sugg_html = ""
    for a in suggestions:
        justification = a.get("why", "")
        full_context = a.get("context", "")
        primary_link = a.get("url") or ""
        if primary_link:
            sugg_html += (
                f"<li><strong>{a['category']}:</strong> "
                f"<a href=\"{primary_link}\" target=\"_blank\">{a['title']}</a>"
                f"<br><small><strong>Why this activity:</strong> {justification}</small>"
                f"<br><small><strong>Context:</strong> {full_context}</small></li>"
            )
        else:
            sugg_html += (
                f"<li><strong>{a['category']}:</strong> {a['title']}"
                f"<br><small><strong>Why this activity:</strong> {justification}</small>"
                f"<br><small><strong>Context:</strong> {full_context}</small></li>"
            )
    if not sugg_html:
        sugg_html = "<li>No activity links found in the current activity bank file.</li>"
    return f"""
        <div style="background: #f0f4f8; padding: 30px 0; margin-top: 30px;">
            <h1 style="text-align: center; color: #2c3e50; border-bottom: 3px solid #667eea; padding-bottom: 10px; margin: 0 auto 30px; max-width: 500px;">
                RECOMMENDATIONS & ACTION PLAN
            </h1>
        </div>
        <div class="section" contenteditable="true" style="border: 2px dashed transparent; transition: border 0.3s;"
             onmouseover="this.style.borderColor='#667eea'" onmouseout="this.style.borderColor='transparent'">
            <div style="background: linear-gradient(135deg, rgba(102, 126, 234, 0.1), rgba(118, 75, 162, 0.1)); padding: 15px; border-radius: 8px; margin-bottom: 25px;">
                <p style="margin: 0; color: #667eea; font-weight: 600;">This section is editable - tailor to local context.</p>
            </div>
            <h2>Strategic Recommendations for {school_name}</h2>
            <p style="font-size:1.05em; line-height:1.8;">The key pattern is not simple decline or growth. This cohort shows strongest movement in <strong>{strongest}</strong> while <strong>{weakest}</strong> is the clearest drag on consistency. Prioritise routines that convert intent into reliable day-to-day execution.</p>
            <div style="margin: 25px 0;">
                <h3 style="color: #667eea; margin-bottom: 15px;">1. Protect and scale strongest gains</h3>
                <div style="background: rgba(16, 185, 129, 0.08); padding: 20px; border-radius: 8px; border-left: 4px solid #10b981;">
                    <ul style="line-height: 1.8;">{top_ins_html}</ul>
                </div>
            </div>
            <div style="margin: 25px 0;">
                <h3 style="color: #667eea; margin-bottom: 15px;">2. Make the pressure-point dimension a coaching priority</h3>
                <div style="background: rgba(245, 158, 11, 0.08); padding: 20px; border-radius: 8px; border-left: 4px solid #f59e0b;">
                    <p><strong>{weakest}</strong> needs immediate routine-level support and consistent staff follow-through.</p>
                    <ul style="line-height: 1.8;">{low_stmt_html}</ul>
                </div>
            </div>
            <div style="margin: 25px 0;">
                <h3 style="color: #667eea; margin-bottom: 15px;">3. Monitor risk indicators in Cycle 3</h3>
                <div style="background: rgba(59, 130, 246, 0.08); padding: 20px; border-radius: 8px; border-left: 4px solid #3b82f6;">
                    <ul style="line-height: 1.8;">{low_ins_html}</ul>
                    <p style="margin-top: 10px;">Use these as early-warning indicators when exam pressure rises.</p>
                </div>
            </div>
            <div style="margin: 25px 0;">
                <h3 style="color: #667eea; margin-bottom: 15px;">4. Target-student pattern snapshot (Top 10 list)</h3>
                <div style="background: rgba(139, 92, 246, 0.08); padding: 20px; border-radius: 8px; border-left: 4px solid #8b5cf6;">
                    <p><strong>Average routine flags per target student:</strong> {target_summary.get('avg_routine', 0.0):.1f}</p>
                    <p><strong>Average volatile item shifts per target student:</strong> {target_summary.get('avg_volatile', 0.0):.1f}</p>
                    <p><strong>Most common routine-pressure statements:</strong> {routine_txt}</p>
                    <p style="margin-top: 8px;"><strong>Interpretation:</strong> where routine flags are high, prioritise systems coaching; where volatility is high, prioritise consistency and frequent check-ins.</p>
                </div>
            </div>
            <div style="margin: 25px 0;">
                <h3 style="color: #667eea; margin-bottom: 15px;">5. Suggested Activities / Quick Wins</h3>
                <div style="background: rgba(16, 185, 129, 0.08); padding: 20px; border-radius: 8px; border-left: 4px solid #10b981;">
                    <ul style="line-height: 1.8;">{sugg_html}</ul>
                    <p style="margin-top:10px;">Browse the full activity set in the <a href="https://vespaacademy.knack.com/vespa-academy#curriculum-builder/" target="_blank">VESPA Activity Library</a>.</p>
                </div>
            </div>
        </div>
"""


def trust_school_comparison_rows(df_scope: pd.DataFrame) -> List[Dict]:
    rows: List[Dict] = []
    for school in SCHOOLS:
        d = df_scope[df_scope["VESPA Customer"] == school].copy()
        if d.empty:
            continue
        m = matched_cohort(d)
        if m.empty:
            continue
        stats = calc_dimension_stats(m)
        overall_c1 = float(stats["Overall"]["c1_mean"])
        overall_c2 = float(stats["Overall"]["c2_mean"])
        overall_change = pct_change(overall_c1, overall_c2)
        dim_pct = {}
        for dim in ["Vision", "Effort", "Systems", "Practice", "Attitude"]:
            dim_pct[dim] = pct_change(stats[dim]["c1_mean"], stats[dim]["c2_mean"])
        strongest = max(dim_pct, key=lambda k: dim_pct[k]) if dim_pct else "n/a"
        weakest = min(dim_pct, key=lambda k: dim_pct[k]) if dim_pct else "n/a"
        matched_rate = (len(m) / len(d) * 100.0) if len(d) else 0.0
        rows.append(
            {
                "school": school,
                "n_scope": int(len(d)),
                "n_matched": int(len(m)),
                "matched_rate": matched_rate,
                "overall_c1": overall_c1,
                "overall_c2": overall_c2,
                "overall_change": overall_change,
                "strongest": strongest,
                "strongest_change": dim_pct.get(strongest, 0.0),
                "weakest": weakest,
                "weakest_change": dim_pct.get(weakest, 0.0),
            }
        )
    rows.sort(key=lambda x: x["overall_change"], reverse=True)
    return rows


def section_trust_exec_summary(stats: Dict[str, Dict[str, float]], school_rows: List[Dict], df_scope: pd.DataFrame) -> str:
    if not school_rows:
        return f"""
        <div class="section summary-hero">
          <div class="summary-kicker">Executive summary</div>
          <h2>Executive Summary</h2>
          <p>No matched school-level comparison is available yet.</p>
          {cohort_validity_block(df_scope)}
        </div>
"""
    top_school = school_rows[0]
    low_school = school_rows[-1]
    trust_c1 = float(stats["Overall"]["c1_mean"]) if "Overall" in stats else 0.0
    trust_c2 = float(stats["Overall"]["c2_mean"]) if "Overall" in stats else 0.0
    trust_change = pct_change(trust_c1, trust_c2) if "Overall" in stats else 0.0
    top3 = "".join(
        [
            f"<li><strong>{r['school']}</strong>: {r['overall_change']:+.1f}% "
            f"(matched {r['n_matched']}/{r['n_scope']}, {r['matched_rate']:.1f}%)</li>"
            for r in school_rows[:3]
        ]
    )
    return f"""
    <div class="section summary-hero">
      <div class="summary-kicker">Executive summary</div>
      <h2>Executive Summary</h2>
      <p><strong>Method note:</strong> this trust view compares schools using matched Cycle 1 to Cycle 2 cohorts only.</p>
      {cohort_validity_block(df_scope)}
      <div class="summary-grid">
        <div class="summary-main">
          <h3>Trust-level picture</h3>
          <p class="summary-lead"><strong>Overall trust movement:</strong> C1 {trust_c1:.2f} to C2 {trust_c2:.2f} ({trust_change:+.1f}%).</p>
          <p class="summary-lead" style="margin-top:10px;">
            Highest relative movement is <strong>{top_school['school']} ({top_school['overall_change']:+.1f}%)</strong>.
            The lowest relative movement is <strong>{low_school['school']} ({low_school['overall_change']:+.1f}%)</strong>.
          </p>
        </div>
        <div class="summary-side">
          <div class="summary-panel">
            <h3>Leading schools by journey movement</h3>
            <ol class="mini-list">{top3}</ol>
          </div>
          <div class="summary-panel">
            <h3>Board-level implication</h3>
            <p>Use this report to compare patterns between schools, identify where momentum is strongest, and target cross-school support where movement is weakest.</p>
          </div>
        </div>
      </div>
    </div>
"""


def section_trust_journey_narrative(
    stats: Dict[str, Dict[str, float]],
    insights: List[Dict],
    statements: List[Dict],
    school_rows: List[Dict],
) -> str:
    dim_rows = ""
    dim_changes = {}
    for dim in ["Vision", "Effort", "Systems", "Practice", "Attitude", "Overall"]:
        if dim not in stats:
            continue
        c1 = float(stats[dim]["c1_mean"])
        c2 = float(stats[dim]["c2_mean"])
        ch = pct_change(c1, c2)
        dim_changes[dim] = ch
        dim_rows += (
            f"<tr><td>{dim}</td><td style='text-align:center;'>{c1:.2f}</td>"
            f"<td style='text-align:center;'>{c2:.2f}</td><td style='text-align:center;'>{ch:+.1f}%</td></tr>"
        )
    if not dim_rows:
        dim_rows = "<tr><td colspan='4'>No trust dimension journey data available.</td></tr>"

    top_dim = max(dim_changes, key=dim_changes.get) if dim_changes else "n/a"
    low_dim = min(dim_changes, key=dim_changes.get) if dim_changes else "n/a"
    top_dim_val = dim_changes.get(top_dim, 0.0)
    low_dim_val = dim_changes.get(low_dim, 0.0)

    rising_ins = sorted(insights, key=lambda x: x["delta"], reverse=True)[:3]
    falling_ins = sorted(insights, key=lambda x: x["delta"])[:3]
    rising_txt = ", ".join([f"{i['title']} ({i['delta']:+.1f}%)" for i in rising_ins]) or "No clear rising insight pattern."
    falling_txt = ", ".join([f"{i['title']} ({i['delta']:+.1f}%)" for i in falling_ins]) or "No clear pressure insight pattern."

    statement_dips = sorted(statements, key=lambda x: x["delta"])[:3]
    statement_txt = "; ".join([f"\"{s['statement']}\" ({s['delta']:+.2f})" for s in statement_dips]) or "No statement-level dips identified."

    top_school = school_rows[0] if school_rows else None
    low_school = school_rows[-1] if school_rows else None
    spread_txt = (
        f"Highest school movement: {top_school['school']} ({top_school['overall_change']:+.1f}%). "
        f"Lowest school movement: {low_school['school']} ({low_school['overall_change']:+.1f}%)."
        if top_school and low_school
        else "School-level movement spread is not available."
    )

    return f"""
    <div class="section">
      <h2>📈 Trust Journey Insights (Cycle 1 to Cycle 2)</h2>
      <p>This section summarises what changed across the trust between cycles, using matched cohorts.</p>
      <div style="display:grid; grid-template-columns:1fr 1fr; gap:18px; margin-bottom:18px;">
        <div style="background: rgba(16,185,129,0.08); border-left:4px solid #10b981; padding:14px; border-radius:8px;">
          <p style="margin:0;"><strong>Strongest trust movement:</strong> {top_dim} ({top_dim_val:+.1f}%)</p>
        </div>
        <div style="background: rgba(245,158,11,0.08); border-left:4px solid #f59e0b; padding:14px; border-radius:8px;">
          <p style="margin:0;"><strong>Main trust pressure point:</strong> {low_dim} ({low_dim_val:+.1f}%)</p>
        </div>
      </div>
      <p><strong>Biggest rising insights:</strong> {rising_txt}</p>
      <p><strong>Main pressure insights:</strong> {falling_txt}</p>
      <p><strong>Most useful statement-level signals:</strong> {statement_txt}</p>
      <p><strong>Cross-school spread:</strong> {spread_txt}</p>
      <h3 style="margin-top:20px;">Trust Dimension Journey Table (C1 vs C2)</h3>
      <table>
        <thead><tr><th>Dimension</th><th style="text-align:center;">Cycle 1</th><th style="text-align:center;">Cycle 2</th><th style="text-align:center;">Change</th></tr></thead>
        <tbody>{dim_rows}</tbody>
      </table>
    </div>
"""


def section_trust_school_comparison(school_rows: List[Dict]) -> str:
    if not school_rows:
        return """
        <div class="section">
          <h2>School Comparison</h2>
          <p>No matched school-level comparison data available.</p>
        </div>
"""
    body = ""
    for r in school_rows:
        body += f"""
        <tr>
          <td>{r['school']}</td>
          <td style="text-align:center;">{r['n_matched']}/{r['n_scope']} ({r['matched_rate']:.1f}%)</td>
          <td style="text-align:center;">{r['overall_c1']:.2f}</td>
          <td style="text-align:center;">{r['overall_c2']:.2f}</td>
          <td style="text-align:center;">{r['overall_change']:+.1f}%</td>
          <td>{r['strongest']} ({r['strongest_change']:+.1f}%)</td>
          <td>{r['weakest']} ({r['weakest_change']:+.1f}%)</td>
        </tr>
"""
    return f"""
    <div class="section">
      <h2>School Comparison Insights</h2>
      <p>Comparison across schools on matched cohorts, including strongest and weakest theme movement for each school.</p>
      <table>
        <thead>
          <tr>
            <th>School</th>
            <th style="text-align:center;">Matched Cohort</th>
            <th style="text-align:center;">C1 Overall</th>
            <th style="text-align:center;">C2 Overall</th>
            <th style="text-align:center;">Change</th>
            <th>Strongest Theme</th>
            <th>Main Pressure Theme</th>
          </tr>
        </thead>
        <tbody>{body}</tbody>
      </table>
    </div>
"""


def section_trust_strategic_priorities(school_rows: List[Dict]) -> str:
    if not school_rows:
        return """
        <div class="section">
          <h2>Strategic Priorities</h2>
          <p>No school comparison rows available.</p>
        </div>
"""
    weakest_counts: Dict[str, int] = {}
    for r in school_rows:
        w = r["weakest"]
        weakest_counts[w] = weakest_counts.get(w, 0) + 1
    top_pressure = sorted(weakest_counts.items(), key=lambda x: x[1], reverse=True)[:2]
    pressure_txt = ", ".join([f"{k} ({v} schools)" for k, v in top_pressure]) if top_pressure else "No clear concentration yet"
    return f"""
    <div class="section">
      <h2>Strategic Priorities for 2025/26</h2>
      <ul style="line-height:1.9;">
        <li><strong>Cross-school comparison focus:</strong> use the school table to monitor relative movement each cycle, not just trust averages.</li>
        <li><strong>Shared pressure areas:</strong> {pressure_txt} should be treated as trust-wide implementation priorities.</li>
        <li><strong>Replication pathway:</strong> capture practical approaches from strongest-movement schools and transfer them through trust-wide staff development.</li>
      </ul>
    </div>
"""


def calc_eri_for_group(df_group: pd.DataFrame, cycle: int) -> float:
    col = f"c{cycle}_prep"
    if col not in df_group.columns:
        return float("nan")
    s = clean_likert_series(df_group[col]).dropna()
    return float(s.mean()) if len(s) else float("nan")


def section_trust_distribution_comparison(df_matched: pd.DataFrame) -> str:
    if df_matched.empty:
        return """
        <div class="section">
          <h2>📈 Histogram Performance Comparison (Journey Indicators)</h2>
          <p>No matched data available for trust histogram comparison indicators.</p>
        </div>
"""
    rows = ""
    for dim in ["Vision", "Effort", "Systems", "Practice", "Attitude", "Overall"]:
        c1_col, c2_col = DIM_COLS[dim]
        c1 = pd.to_numeric(df_matched[c1_col], errors="coerce").dropna()
        c2 = pd.to_numeric(df_matched[c2_col], errors="coerce").dropna()
        if len(c1) == 0 or len(c2) == 0:
            continue
        c1_high = float((c1 >= 7).mean() * 100.0)
        c2_high = float((c2 >= 7).mean() * 100.0)
        c1_low = float((c1 <= 4).mean() * 100.0)
        c2_low = float((c2 <= 4).mean() * 100.0)
        rows += (
            f"<tr><td>{dim}</td><td style='text-align:center;'>{c1_high:.1f}%</td>"
            f"<td style='text-align:center;'>{c2_high:.1f}%</td><td style='text-align:center;'>{(c2_high-c1_high):+.1f}%</td>"
            f"<td style='text-align:center;'>{c1_low:.1f}%</td><td style='text-align:center;'>{c2_low:.1f}%</td>"
            f"<td style='text-align:center;'>{(c2_low-c1_low):+.1f}%</td></tr>"
        )
    if not rows:
        rows = "<tr><td colspan='7'>No histogram comparison indicators available.</td></tr>"
    return f"""
    <div class="section">
      <h2>📈 Histogram Performance Comparison (Journey Indicators)</h2>
      <p>This translates the histograms into journey indicators: movement in the high-score band (7-10) and low-score band (1-4) from Cycle 1 to Cycle 2.</p>
      <table>
        <thead>
          <tr>
            <th>Dimension</th>
            <th style="text-align:center;">C1 High (7-10)</th>
            <th style="text-align:center;">C2 High (7-10)</th>
            <th style="text-align:center;">High-band Change</th>
            <th style="text-align:center;">C1 Low (1-4)</th>
            <th style="text-align:center;">C2 Low (1-4)</th>
            <th style="text-align:center;">Low-band Change</th>
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
"""


def section_trust_detailed_performance_matrix(df_scope: pd.DataFrame) -> str:
    def change_chip(delta_pct: float) -> str:
        pos = delta_pct >= 0
        bg = "rgba(16,185,129,0.14)" if pos else "rgba(239,68,68,0.14)"
        fg = "#047857" if pos else "#b91c1c"
        sign = "+" if delta_pct >= 0 else ""
        return f"<span style='display:inline-block;padding:2px 8px;border-radius:999px;background:{bg};color:{fg};font-weight:700;font-size:0.82rem;'>{sign}{delta_pct:.1f}%</span>"

    def metric_cell(c1: float, c2: float) -> str:
        d = pct_change(c1, c2)
        return (
            f"<div style='display:flex;flex-direction:column;gap:4px;align-items:center;'>"
            f"<span>{c1:.2f} -> {c2:.2f}</span>"
            f"{change_chip(d)}"
            f"</div>"
        )

    body = ""
    for school in SCHOOLS:
        d = df_scope[df_scope["VESPA Customer"] == school].copy()
        m = matched_cohort(d)
        if m.empty:
            continue
        stats = calc_dimension_stats(m)
        eri_c1 = calc_eri_for_group(m, 1)
        eri_c2 = calc_eri_for_group(m, 2)
        vision = metric_cell(float(stats["Vision"]["c1_mean"]), float(stats["Vision"]["c2_mean"]))
        effort = metric_cell(float(stats["Effort"]["c1_mean"]), float(stats["Effort"]["c2_mean"]))
        systems = metric_cell(float(stats["Systems"]["c1_mean"]), float(stats["Systems"]["c2_mean"]))
        practice = metric_cell(float(stats["Practice"]["c1_mean"]), float(stats["Practice"]["c2_mean"]))
        attitude = metric_cell(float(stats["Attitude"]["c1_mean"]), float(stats["Attitude"]["c2_mean"]))
        overall = metric_cell(float(stats["Overall"]["c1_mean"]), float(stats["Overall"]["c2_mean"]))
        eri_txt = "<span style='color:#64748b;'>n/a</span>"
        if not np.isnan(eri_c1) and not np.isnan(eri_c2):
            eri_txt = metric_cell(eri_c1, eri_c2)
        body += (
            f"<tr>"
            f"<td><strong>{school}</strong></td>"
            f"<td style='text-align:center;'>{len(m)}</td>"
            f"<td style='text-align:center;'>{vision}</td>"
            f"<td style='text-align:center;'>{effort}</td>"
            f"<td style='text-align:center;'>{systems}</td>"
            f"<td style='text-align:center;'>{practice}</td>"
            f"<td style='text-align:center;'>{attitude}</td>"
            f"<td style='text-align:center;'>{overall}</td>"
            f"<td style='text-align:center;'>{eri_txt}</td>"
            f"</tr>"
        )
    if not body:
        body = "<tr><td colspan='9'>No school-level matched matrix available.</td></tr>"
    return f"""
    <div class="section">
      <h2>Detailed Performance Matrix (Journey)</h2>
      <p>School-level C1 to C2 movement shown clearly by dimension. Each cell shows C1 -> C2 and a color-coded journey change.</p>
      <table>
        <thead>
          <tr>
            <th>School</th>
            <th style="text-align:center;">Matched n</th>
            <th style="text-align:center;">Vision</th>
            <th style="text-align:center;">Effort</th>
            <th style="text-align:center;">Systems</th>
            <th style="text-align:center;">Practice</th>
            <th style="text-align:center;">Attitude</th>
            <th style="text-align:center;">Overall</th>
            <th style="text-align:center;">ERI</th>
          </tr>
        </thead>
        <tbody>{body}</tbody>
      </table>
    </div>
"""


def section_trust_year_group_analysis(df_scope: pd.DataFrame) -> str:
    year_col = None
    for c in ["Year Gp", "Year Group", "Year"]:
        if c in df_scope.columns:
            year_col = c
            break
    if not year_col:
        return """
        <div class="section">
          <h2>Year Group Journey Analysis</h2>
          <p>No year-group column found in the current dataset.</p>
        </div>
"""
    cards = ""
    body = ""
    d_all = df_scope.copy()
    groups = sorted([g for g in d_all[year_col].dropna().astype(str).unique() if g.strip()])
    for yg in groups:
        d = d_all[d_all[year_col].astype(str) == yg].copy()
        m = matched_cohort(d)
        if m.empty:
            continue
        stats = calc_dimension_stats(m)
        c1 = float(stats["Overall"]["c1_mean"])
        c2 = float(stats["Overall"]["c2_mean"])
        ch = pct_change(c1, c2)
        eri_c1 = calc_eri_for_group(m, 1)
        eri_c2 = calc_eri_for_group(m, 2)
        eri_txt = "n/a"
        if not np.isnan(eri_c1) and not np.isnan(eri_c2):
            eri_txt = f"{eri_c1:.2f}->{eri_c2:.2f} ({pct_change(eri_c1, eri_c2):+.1f}%)"
        cards += f"""
        <div class="stat-card">
            <h4>{yg}</h4>
            <div class="value">{c2:.2f}</div>
            <small>C1 baseline: {c1:.2f}</small>
            <div class="{'positive' if ch >= 0 else 'negative'}" style="margin-top:6px;">Change: {ch:+.1f}%</div>
            <small>Matched n={len(m)}</small>
        </div>
"""
        body += (
            f"<tr><td>{yg}</td><td style='text-align:center;'>{len(m)}</td>"
            f"<td style='text-align:center;'>{stats['Vision']['c1_mean']:.2f}->{stats['Vision']['c2_mean']:.2f}</td>"
            f"<td style='text-align:center;'>{stats['Effort']['c1_mean']:.2f}->{stats['Effort']['c2_mean']:.2f}</td>"
            f"<td style='text-align:center;'>{stats['Systems']['c1_mean']:.2f}->{stats['Systems']['c2_mean']:.2f}</td>"
            f"<td style='text-align:center;'>{stats['Practice']['c1_mean']:.2f}->{stats['Practice']['c2_mean']:.2f}</td>"
            f"<td style='text-align:center;'>{stats['Attitude']['c1_mean']:.2f}->{stats['Attitude']['c2_mean']:.2f}</td>"
            f"<td style='text-align:center;'>{c1:.2f}->{c2:.2f} ({ch:+.1f}%)</td>"
            f"<td style='text-align:center;'>{eri_txt}</td></tr>"
        )
    if not cards:
        return """
        <div class="section">
          <h2>Year Group Journey Analysis</h2>
          <p>No matched year-group journey data available.</p>
        </div>
"""
    return f"""
    <div class="section">
      <h2>Year Group Journey Analysis</h2>
      <p>Year-group C1 to C2 comparison to show cohort-specific journey movement.</p>
      <div class="stats-grid">{cards}</div>
      <h3 style="margin-top:20px;">Detailed Year Group Comparison (C1 -> C2)</h3>
      <table>
        <thead>
          <tr>
            <th>Year Group</th>
            <th style="text-align:center;">Matched n</th>
            <th style="text-align:center;">Vision</th>
            <th style="text-align:center;">Effort</th>
            <th style="text-align:center;">Systems</th>
            <th style="text-align:center;">Practice</th>
            <th style="text-align:center;">Attitude</th>
            <th style="text-align:center;">Overall</th>
            <th style="text-align:center;">ERI</th>
          </tr>
        </thead>
        <tbody>{body}</tbody>
      </table>
    </div>
"""


def render_report(
    org_name: str,
    subtitle: str,
    df_scope: pd.DataFrame,
    df_matched: pd.DataFrame,
    stats: Dict[str, Dict[str, float]],
    insights: List[Dict],
    statements: List[Dict],
    headline: str,
    quickwins: List[str],
    is_trust_exec: bool = False,
    trust_school_rows: List[Dict] | None = None,
) -> str:
    report_date = datetime.now().strftime("%B %d, %Y")
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{org_name} - {subtitle}</title>
  <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
  <style>{ber.get_css_styles()}{ber.get_insights_css()}
        body {{
            background: #f3f5f8 !important;
            color: #1f2937;
        }}
        .container {{
            max-width: 1250px;
            margin: 20px auto;
            padding: 0 14px 26px;
        }}
        .report-header {{
            border-radius: 10px !important;
            box-shadow: 0 6px 18px rgba(15,23,42,0.08) !important;
        }}
        .executive-summary, .section {{
            border-radius: 10px !important;
            box-shadow: 0 5px 14px rgba(15,23,42,0.06) !important;
            padding: 22px 24px !important;
            margin-bottom: 16px !important;
            border: 1px solid #e5e7eb !important;
        }}
        .section h2 {{
            color: #334155 !important;
            margin-bottom: 10px;
            font-size: 1.55rem;
            letter-spacing: 0.01em;
        }}
        .section h3 {{
            color: #475569 !important;
            font-size: 1.08rem;
            margin-bottom: 8px;
        }}
        .chart-container {{
            border-radius: 8px !important;
            border: 1px solid #e2e8f0 !important;
            background: #ffffff !important;
            box-shadow: 0 2px 8px rgba(15,23,42,0.04) !important;
        }}
        th {{
            background: #5b6fb3 !important;
        }}
        td {{
            border-bottom: 1px solid #e5e7eb !important;
        }}
        tr:hover {{
            background: #f8fafc !important;
        }}
        .insights-section .callout-band {{
            background: #f8fafc !important;
            border: 1px solid #e2e8f0 !important;
        }}
        .summary-hero {{
            background: linear-gradient(135deg, #eff3f8 0%, #f6f8fb 58%, #ffffff 100%);
            border-left: 4px solid #64748b;
            position: relative;
            overflow: hidden;
            border-radius: 10px;
        }}
        .summary-kicker {{
            display: inline-block;
            background: rgba(71,85,105,0.12);
            color: #334155;
            font-weight: 700;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            font-size: 0.8rem;
            padding: 6px 11px;
            border-radius: 999px;
            margin-bottom: 12px;
        }}
        .summary-grid {{ display: grid; grid-template-columns: 1.35fr 0.95fr; gap: 22px; margin-top: 18px; }}
        .summary-main {{ background: rgba(255,255,255,0.90); border: 1px solid #e2e8f0; border-radius: 10px; padding: 20px; }}
        .summary-side {{ display: grid; gap: 16px; }}
        .summary-panel {{ background: white; border: 1px solid #e2e8f0; border-radius: 10px; padding: 16px; box-shadow: 0 2px 8px rgba(15,23,42,0.04); }}
        .summary-panel h3, .summary-main h3 {{ margin: 0 0 10px 0; color: #334155; font-size: 1.05rem; }}
        .summary-lead {{ font-size: 1.08rem; line-height: 1.75; color: #1f2937; }}
        .highlight-row {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-top: 18px; }}
        .highlight-card {{ border-radius: 8px; padding: 14px; color: white; box-shadow: 0 4px 12px rgba(15,23,42,0.08); filter: saturate(0.68) brightness(0.92); }}
        .highlight-card h4 {{ font-size: 0.86rem; letter-spacing: 0.02em; opacity: 0.9; margin-bottom: 8px; }}
        .highlight-card .card-tag {{
            display: inline-block;
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            background: rgba(255,255,255,0.20);
            border: 1px solid rgba(255,255,255,0.28);
            border-radius: 999px;
            padding: 4px 9px;
            margin-bottom: 8px;
        }}
        .highlight-card .big {{ font-size: 1.55rem; font-weight: 700; line-height: 1.2; margin-bottom: 8px; min-height: 88px; }}
        .highlight-card .sub {{ font-size: 0.92rem; opacity: 0.96; line-height: 1.45; min-height: 44px; }}
        .mini-list {{ margin: 10px 0 0 18px; line-height: 1.8; }}
        .target-link {{
            background: none;
            border: none;
            color: #2563eb;
            text-decoration: underline;
            cursor: pointer;
            font: inherit;
            text-align: left;
            padding: 0;
        }}
        .target-link:hover {{ color: #1d4ed8; }}
        .target-modal-overlay {{
            display: none;
            position: fixed;
            z-index: 9999;
            inset: 0;
            background: rgba(15, 23, 42, 0.55);
            padding: 20px;
            overflow-y: auto;
        }}
        .target-modal {{
            max-width: 920px;
            margin: 30px auto;
            background: #fff;
            border-radius: 14px;
            padding: 20px;
            box-shadow: 0 18px 45px rgba(15, 23, 42, 0.28);
        }}
        .target-modal-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }}
        .target-modal-close {{
            border: none;
            background: none;
            font-size: 1.8rem;
            line-height: 1;
            cursor: pointer;
            color: #334155;
        }}
        .target-modal-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
            margin-top: 10px;
        }}
        .insight-card-button {{
            width: 100%;
            text-align: left;
            border: none;
            cursor: pointer;
            font: inherit;
        }}
        .insight-modal-overlay {{
            display: none;
            position: fixed;
            z-index: 9998;
            inset: 0;
            background: rgba(15, 23, 42, 0.45);
            padding: 20px;
            overflow-y: auto;
        }}
        .insight-modal {{
            max-width: 760px;
            margin: 30px auto;
            background: #fff;
            border-radius: 14px;
            padding: 20px;
            box-shadow: 0 18px 45px rgba(15, 23, 42, 0.2);
        }}
        .insight-link {{
            background: none;
            border: none;
            color: #2563eb;
            text-decoration: underline;
            cursor: pointer;
            font: inherit;
            text-align: left;
            padding: 0;
        }}
        .insight-link:hover {{ color: #1d4ed8; }}
        @media (max-width: 900px) {{
            .target-modal-grid {{ grid-template-columns: 1fr; }}
        }}
        .callout-band {{ margin-top: 18px; background: #f8fafc; border: 1px solid #dbe1ea; border-radius: 8px; padding: 14px 16px; }}
        .priority-strip {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-top: 20px; }}
        .priority-box {{ border-radius: 8px; padding: 14px; background: #f8fafc; border: 1px solid #e2e8f0; }}
        .priority-box h4 {{ margin-bottom: 8px; font-size: 1rem; }}
        @media (max-width: 980px) {{ .summary-grid, .priority-strip, .highlight-row {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <div class="container">
    {ber.generate_header(report_date, org_name, subtitle, show_logo=(org_name=="E-ACT Academy Trust"), school_name=org_name if org_name!="E-ACT Academy Trust" else None)}
    {section_trust_exec_summary(stats, trust_school_rows or [], df_scope) if is_trust_exec else top_commentary(org_name, stats, insights, statements, quickwins, headline, df_scope)}
    {section_journey_overview(stats, "📊 Baseline Scores Journey (Cycle 1 to Cycle 2)", "Each card shows the Cycle 2 score, the Cycle 1 baseline, and the change between them for matched students.") if is_trust_exec else section_journey_overview(stats, "Journey Overview: Cycle 1 to Cycle 2", "Each card shows the Cycle 2 score and the change from Cycle 1 for students who completed both cycles.")}
    {section_trust_school_comparison(trust_school_rows or []) if is_trust_exec else ""}
    {section_distributions(df_matched)}
    {section_trust_distribution_comparison(df_matched) if is_trust_exec else ""}
    {section_trust_detailed_performance_matrix(df_scope) if is_trust_exec else ""}
    {section_trust_year_group_analysis(df_scope) if is_trust_exec else ""}
    {section_insights(insights, org_name)}
    {section_trust_journey_narrative(stats, insights, statements, trust_school_rows or []) if is_trust_exec else ""}
    {"" if is_trust_exec else section_statements(statements)}
    {"" if is_trust_exec else students_of_interest(df_matched)}
    {section_trust_strategic_priorities(trust_school_rows or []) if is_trust_exec else section_action_plan(stats, insights, statements, org_name, df_matched)}
    <div class="footer">
      <p>© 2026 VESPA Education Analytics | {org_name} - Confidential Report</p>
      <p style="margin-top: 10px; font-size: 0.9em;">Journey Edition (Cycle 1 to Cycle 2) | Academic Year 2025/26</p>
    </div>
  </div>
  <script>
    function openTargetModal(id) {{
      var el = document.getElementById(id);
      if (el) el.style.display = "block";
    }}
    function closeTargetModal(id) {{
      var el = document.getElementById(id);
      if (el) el.style.display = "none";
    }}
    function openInsightModal(id) {{
      var el = document.getElementById(id);
      if (el) el.style.display = "block";
    }}
    function closeInsightModal(id) {{
      var el = document.getElementById(id);
      if (el) el.style.display = "none";
    }}
  </script>
</body>
</html>
"""


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    df_raw = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    df_raw = df_raw[df_raw["VESPA Customer"].isin(SCHOOLS)].copy()
    df_raw = dedupe_students(df_raw)
    df_raw = derive_cycle_scales_from_questions(df_raw, 1)
    df_raw = derive_cycle_scales_from_questions(df_raw, 2)
    c1_agg = load_c1_aggregates()
    df_raw = apply_c1_aggregates(df_raw, c1_agg)

    # Trust
    df_trust_matched = matched_cohort(df_raw)
    trust_stats = calc_dimension_stats(df_trust_matched)
    trust_statements = calc_statement_journey(df_trust_matched)
    trust_insights = calc_insights_journey(df_trust_matched)
    trust_headline = headline_from_dims(trust_stats)
    trust_qw = quick_wins(trust_stats, trust_statements)
    trust_rows = trust_school_comparison_rows(df_raw)
    trust_html = render_report(
        "E-ACT Academy Trust",
        "VESPA Journey Executive Summary (Cycle 1 to Cycle 2)",
        df_raw,
        df_trust_matched,
        trust_stats,
        trust_insights,
        trust_statements,
        trust_headline,
        trust_qw,
        is_trust_exec=True,
        trust_school_rows=trust_rows,
    )
    (REPORTS_DIR / TARGET_FILES["EXEC"]).write_text(trust_html, encoding="utf-8")

    # Schools
    for school in SCHOOLS:
        df_school = df_raw[df_raw["VESPA Customer"] == school].copy()
        if len(df_school) == 0:
            continue
        df_school_matched = matched_cohort(df_school)
        stats = calc_dimension_stats(df_school_matched)
        statements = calc_statement_journey(df_school_matched)
        insights = calc_insights_journey(df_school_matched)
        headline = headline_from_dims(stats)
        qwins = quick_wins(stats, statements)
        html = render_report(
            school,
            "VESPA Journey Report (Cycle 1 to Cycle 2)",
            df_school,
            df_school_matched,
            stats,
            insights,
            statements,
            headline,
            qwins,
        )
        (REPORTS_DIR / TARGET_FILES[school]).write_text(html, encoding="utf-8")

    print("Journey reports rebuilt and published:", REPORTS_DIR)
    for k, v in TARGET_FILES.items():
        print("-", v)


if __name__ == "__main__":
    main()

