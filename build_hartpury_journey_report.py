#!/usr/bin/env python3
"""
Generate Hartpury College VESPA Journey Report (Cycle 1 -> Cycle 2).

CRITICAL REQUIREMENT:
- Preserve the original report's section structure and styling, but update all copy/metrics/charts
  to describe the Journey from Cycle 1 to Cycle 2.
- Output is written IN-PLACE to the existing file:
  VESPA WEBISTE FILES/vespa-academy-new/public/reports/Hartpury_VESPAREPORT_2025_Cycle1.html
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio


# --- Paths ---
ROOT = Path(r"C:\Users\tonyd\OneDrive - 4Sight Education Ltd\Apps\DASHBOARD\DASHBOARD")
CSV_PATH = ROOT / "HartpuryJourney_merged_with_VESPA.csv"
OUT_PATH = Path(
    r"C:\Users\tonyd\OneDrive - 4Sight Education Ltd\VESPA WEBISTE FILES\vespa-academy-new\public\reports\Hartpury_VESPAREPORT_2025_Cycle1.html"
)

# A shareable, non-overwriting copy (for client URL sharing).
SHARE_BASENAME = f"HARTPURY_VESPA_JOURNEY_2025-26_MATCHED_{datetime.now().strftime('%Y-%m-%d')}.html"
SHARE_PATH = OUT_PATH.parent / SHARE_BASENAME


# --- National benchmarks (kept from baseline report for continuity) ---
NATIONAL_AVERAGES = {
    "Vision": 6.1,
    "Effort": 5.49,
    "Systems": 5.27,
    "Practice": 5.75,
    "Attitude": 5.59,
    "Overall": 5.64,
}

NATIONAL_DISTRIBUTIONS = {
    "Vision": {1: 1.65, 2: 4.63, 3: 10.98, 4: 8.29, 5: 10.50, 6: 21.72, 7: 10.58, 8: 16.81, 9: 6.33, 10: 8.50},
    "Effort": {1: 5.51, 2: 3.75, 3: 15.47, 4: 11.72, 5: 13.32, 6: 14.87, 7: 12.60, 8: 8.88, 9: 11.00, 10: 2.89},
    "Systems": {1: 5.94, 2: 6.73, 3: 11.79, 4: 17.16, 5: 9.29, 6: 19.20, 7: 9.10, 8: 13.03, 9: 4.11, 10: 3.65},
    "Practice": {1: 3.55, 2: 4.61, 3: 8.95, 4: 13.63, 5: 18.24, 6: 10.03, 7: 16.30, 8: 11.81, 9: 7.73, 10: 5.16},
    "Attitude": {1: 3.77, 2: 6.76, 3: 11.72, 4: 10.00, 5: 12.01, 6: 20.62, 7: 11.84, 8: 13.23, 9: 6.69, 10: 3.36},
    "Overall": {1: 0.74, 2: 2.60, 3: 8.48, 4: 14.87, 5: 20.08, 6: 21.72, 7: 16.11, 8: 10.20, 9: 3.92, 10: 1.27},
}

COLORS = {
    "Vision": "#e59437",
    "Effort": "#86b4f0",
    "Systems": "#72cb44",
    "Practice": "#7f31a4",
    "Attitude": "#f032e6",
    "Overall": "#ffd700",
}

# Deterministic palette for multi-series radars (so traces never look identical).
RADAR_PALETTE = [
    "#2563eb",  # blue
    "#16a34a",  # green
    "#dc2626",  # red
    "#7c3aed",  # violet
    "#0ea5e9",  # sky
    "#f97316",  # orange
    "#db2777",  # pink
    "#64748b",  # slate
]


# --- VESPA column mapping in merged file ---
DIM_COLS: Dict[str, Tuple[str, str]] = {
    "Vision": ("V1", "V2"),
    "Effort": ("E1", "E2"),
    "Systems": ("S1", "S2"),
    "Practice": ("P1", "P2"),
    "Attitude": ("A1", "A2"),
    "Overall": ("O1", "O2"),
}


STATEMENTS: List[str] = [
    "I've worked out the next steps in my life",
    "I plan and organise my time to get my work done",
    "I give a lot of attention to my career planning",
    "I complete all my homework on time",
    "No matter who you are, you can change your intelligence a lot",
    "I use all my independent study time effectively",
    "I test myself on important topics until I remember them",
    "I have a positive view of myself",
    "I am a hard working student",
    "I am confident in my academic ability",
    "I always meet deadlines",
    "I spread out my revision, rather than cramming at the last minute.",
    "I don't let a poor test/assessment result get me down for too long",
    "I strive to achieve the goals I set for myself",
    "I summarise important information in diagrams, tables or lists",
    "I enjoy learning new things",
    "I'm not happy unless my work is the best it can be",
    "I take good notes in class which are useful for revision",
    "When revising I mix different kinds of topics/subjects in one study session",
    "I feel I can cope with the pressure at school/college/University",
    "I work as hard as I can in most classes",
    "My books/files are organised",
    "I study by explaining difficult topics out loud",
    "I'm happy to ask questions in front of a group.",
    "When revising, I work under timed conditions answering exam-style questions",
    "Your intelligence is something about you that you can change very much",
    "I like hearing feedback about how I can improve",
    "I can control my nerves in tests/practical assessments.",
    "I know what grades I want to achieve",
]

LETTER_TO_DIM = {"v": "Vision", "e": "Effort", "s": "Systems", "p": "Practice", "a": "Attitude"}


def fmt(v: float, dp: int = 2) -> str:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "-"
    return f"{float(v):.{dp}f}"

def pct_change(c1: float, c2: float) -> float:
    if c1 is None or (isinstance(c1, float) and np.isnan(c1)) or c1 == 0:
        return 0.0
    return ((c2 - c1) / c1) * 100.0

def hex_to_rgb(h: str) -> Tuple[int, int, int]:
    s = (h or "").lstrip("#")
    return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)

def rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02x}{g:02x}{b:02x}"

def tint(hex_color: str, t: float) -> str:
    """
    Mix hex_color with white by factor t (0..1).
    t=0 returns original color, t=1 returns white.
    """
    r, g, b = hex_to_rgb(hex_color)
    r2 = int(round(r + (255 - r) * t))
    g2 = int(round(g + (255 - g) * t))
    b2 = int(round(b + (255 - b) * t))
    return rgb_to_hex(r2, g2, b2)


def clean_scale(series: pd.Series, lo: int, hi: int) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce")
    return s.where((s >= lo) & (s <= hi))


def calculate_distribution(series: pd.Series) -> Dict[int, float]:
    s = series.dropna()
    total = len(s)
    out: Dict[int, float] = {}
    for score in range(1, 11):
        out[score] = (s.round().eq(score).sum() / total * 100.0) if total > 0 else 0.0
    return out


def journey_direction_pct(delta: pd.Series) -> Tuple[float, float, float]:
    d = delta.dropna()
    if len(d) == 0:
        return 0.0, 0.0, 0.0
    above = (d > 0).mean() * 100.0
    on = (d == 0).mean() * 100.0
    below = (d < 0).mean() * 100.0
    return above, on, below


def normalize_gender(x: str) -> str:
    s = ("" if pd.isna(x) else str(x)).strip()
    s = {"12": "Prefer not to say", "2": "Prefer not to say", "13": "Prefer not to say"}.get(s, s)
    s = s.title()
    if s in {"Male", "Female"}:
        return s
    if s == "Prefer Not To Say":
        return "Prefer not to say"
    return "Unknown"


def normalize_residential(x: str) -> str:
    s = ("" if pd.isna(x) else str(x)).strip().lower()
    if s == "yes":
        return "Residential"
    if s == "no":
        return "Non-Residential"
    return "Unknown"


def normalize_year_group(x: str) -> str:
    s = ("" if pd.isna(x) else str(x)).strip()
    if s.isdigit():
        return f"Year {s}"
    if s.lower().startswith("year"):
        return s.title().replace("  ", " ")
    return s or "Unknown"


@dataclass(frozen=True)
class QuestionCols:
    c1: str
    c2: str
    category: str


def extract_question_cols(columns: List[str]) -> Dict[int, QuestionCols]:
    # expected: c1_Q12p, c2_Q12p (letter indicates category)
    patt = re.compile(r"^c([12])_Q([1-9]|1[0-9]|2[0-9])([a-zA-Z])$")
    tmp: Dict[int, Dict[int, Tuple[str, str]]] = {}
    for col in columns:
        m = patt.match(col)
        if not m:
            continue
        cyc = int(m.group(1))
        qid = int(m.group(2))
        letter = m.group(3).lower()
        tmp.setdefault(qid, {})[cyc] = (col, letter)
    out: Dict[int, QuestionCols] = {}
    for qid in range(1, 30):
        if qid in tmp and 1 in tmp[qid] and 2 in tmp[qid]:
            c1_col, letter = tmp[qid][1]
            c2_col, _ = tmp[qid][2]
            out[qid] = QuestionCols(c1=c1_col, c2=c2_col, category=LETTER_TO_DIM.get(letter, ""))
    return out


def score_status_vs_national(score: float, dim_name: str) -> Tuple[str, str, str]:
    nat = NATIONAL_AVERAGES[dim_name]
    diff = score - nat
    if diff > 0.2:
        return "#28a745", "↑", "Above National"
    if diff < -0.2:
        return "#dc3545", "↓", "Below National"
    return "#666", "•", "On Par with National"


def create_distribution_chart_journey(df: pd.DataFrame, dim: str, div_id: str) -> str:
    c1, c2 = DIM_COLS[dim]
    d1 = calculate_distribution(df[c1])
    d2 = calculate_distribution(df[c2])
    x = list(range(1, 11))

    fig = go.Figure()
    fig.add_trace(go.Bar(x=x, y=[d1[i] for i in x], name="Cycle 1", marker_color=tint(COLORS[dim], 0.72), opacity=0.92))
    fig.add_trace(go.Bar(x=x, y=[d2[i] for i in x], name="Cycle 2", marker_color=COLORS[dim], opacity=0.78))
    fig.add_trace(
        go.Scatter(
            x=x,
            y=[NATIONAL_DISTRIBUTIONS[dim][i] for i in x],
            name="National",
            line=dict(color="red", width=2),
            marker=dict(size=6),
            mode="lines+markers",
        )
    )

    m1 = df[c1].mean()
    m2 = df[c2].mean()
    nat = NATIONAL_AVERAGES[dim]
    fig.add_annotation(
        x=5.5,
        y=max([d1[i] for i in x] + [d2[i] for i in x] + [NATIONAL_DISTRIBUTIONS[dim][i] for i in x]) * 1.08,
        text=f"C1: {m1:.1f} → C2: {m2:.1f}<br>National: {nat}",
        showarrow=False,
        font=dict(size=10),
    )

    fig.update_layout(
        title=f"{dim} Score Distribution — Cycle 1 vs Cycle 2 Journey",
        xaxis=dict(title="Score", range=[0.5, 10.5]),
        yaxis=dict(title="Percentage (%)"),
        height=400,
        barmode="group",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        paper_bgcolor="white",
        plot_bgcolor="rgba(240,240,240,0.3)",
    )
    return pio.to_html(fig, include_plotlyjs=False, full_html=False, div_id=div_id)


def create_faculty_journey_chart(faculty_stats: List[dict]) -> str:
    faculties = [f["faculty"] for f in faculty_stats]
    fig = go.Figure()
    for dim in ["Vision", "Effort", "Systems", "Practice", "Attitude"]:
        fig.add_trace(
            go.Bar(
                name=dim,
                x=faculties,
                y=[f[f"{dim.lower()}_delta"] for f in faculty_stats],
                marker_color=COLORS[dim],
            )
        )
    fig.update_layout(
        title="Faculty Journey Change by Dimension (C2 − C1)",
        xaxis_title="Faculty",
        yaxis=dict(title="Change (points)", zeroline=True, zerolinecolor="#94a3b8"),
        barmode="group",
        height=500,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        paper_bgcolor="white",
        plot_bgcolor="rgba(240,240,240,0.3)",
    )
    return pio.to_html(fig, include_plotlyjs=False, full_html=False, div_id="faculty-chart")


def create_group_journey_chart(group_rows: List[dict], div_id: str, title: str, x_title: str) -> str:
    fig = go.Figure()
    dims = ["Vision", "Effort", "Systems", "Practice", "Attitude", "Overall"]
    x = dims
    for row in group_rows:
        fig.add_trace(
            go.Bar(
                name=row["label"],
                x=x,
                y=[row[f"{d.lower()}_delta"] for d in dims],
                text=[fmt(row[f"{d.lower()}_delta"], 2) for d in dims],
                textposition="auto",
            )
        )
    fig.update_layout(
        title=title,
        xaxis_title=x_title,
        yaxis=dict(title="Change (points)", zeroline=True, zerolinecolor="#94a3b8"),
        barmode="group",
        height=420,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        paper_bgcolor="white",
        plot_bgcolor="rgba(240,240,240,0.3)",
    )
    return pio.to_html(fig, include_plotlyjs=False, full_html=False, div_id=div_id)


def create_above_below_line_chart(groups: List[Tuple[str, pd.DataFrame]], div_id: str, title: str) -> str:
    labels, above, on, below = [], [], [], []
    for label, gdf in groups:
        delta = gdf["O2"] - gdf["O1"]
        a, o, b = journey_direction_pct(delta)
        labels.append(label)
        above.append(a)
        on.append(o)
        below.append(b)
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Above line (improved)", x=labels, y=above, marker_color="#16a34a"))
    fig.add_trace(go.Bar(name="On line (unchanged)", x=labels, y=on, marker_color="#94a3b8"))
    fig.add_trace(go.Bar(name="Below line (declined)", x=labels, y=below, marker_color="#dc2626"))
    fig.update_layout(
        title=title,
        barmode="stack",
        yaxis_title="Students (%)",
        height=360,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        paper_bgcolor="white",
        plot_bgcolor="rgba(240,240,240,0.3)",
    )
    return pio.to_html(fig, include_plotlyjs=False, full_html=False, div_id=div_id)


def radar_cycle1_vs_cycle2(df: pd.DataFrame, groups: List[Tuple[str, pd.DataFrame]], div_id: str, title: str) -> str:
    theta = ["Vision", "Effort", "Systems", "Practice", "Attitude", "Vision"]
    fig = go.Figure()
    for idx, (label, gdf) in enumerate(groups):
        base = RADAR_PALETTE[idx % len(RADAR_PALETTE)]
        r1 = [gdf[DIM_COLS[d][0]].mean() for d in ["Vision", "Effort", "Systems", "Practice", "Attitude"]]
        r2 = [gdf[DIM_COLS[d][1]].mean() for d in ["Vision", "Effort", "Systems", "Practice", "Attitude"]]
        r1 = r1 + [r1[0]]
        r2 = r2 + [r2[0]]
        # Contrast: Cycle 1 dashed outline, Cycle 2 solid + fill (same colour).
        fig.add_trace(
            go.Scatterpolar(
                r=r1,
                theta=theta,
                fill=None,
                name=f"{label} (C1)",
                line=dict(color=base, width=2, dash="dash"),
                opacity=0.95,
            )
        )
        fig.add_trace(
            go.Scatterpolar(
                r=r2,
                theta=theta,
                fill="toself",
                name=f"{label} (C2)",
                line=dict(color=base, width=3),
                opacity=0.28,
            )
        )
    fig.update_layout(
        title=title,
        height=420,
        polar=dict(radialaxis=dict(visible=True, range=[0, 10])),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        paper_bgcolor="white",
    )
    return pio.to_html(fig, include_plotlyjs=False, full_html=False, div_id=div_id)


def build_target_students_by_faculty(df: pd.DataFrame, qcols: Dict[int, QuestionCols]) -> Tuple[str, str]:
    # Teacher-friendly: show top 5% risk per faculty, with modal evidence.
    routine_ids = {2, 4, 6, 11, 18, 21, 22}
    facs = sorted([f for f in df["faculty_norm"].dropna().unique() if f and not str(f).isdigit()])
    rows: List[str] = []
    modals: List[str] = []
    rank = 1

    fac_counts: List[Tuple[str, int]] = []
    for fac in facs:
        fdf = df[df["faculty_norm"] == fac].copy()
        if len(fdf) < 10:
            continue

        candidates = []
        for _, r in fdf.iterrows():
            o1, o2 = r.get("O1"), r.get("O2")
            if pd.isna(o1) or pd.isna(o2):
                continue
            drop = float(o2 - o1)

            routine_flags: List[str] = []
            volatile: List[Tuple[str, float, float, float]] = []
            for qid, qc in qcols.items():
                c1 = r.get(qc.c1)
                c2 = r.get(qc.c2)
                if pd.notna(c1) and pd.notna(c2):
                    d = float(c2 - c1)
                    if abs(d) >= 2:
                        volatile.append((STATEMENTS[qid - 1], float(c1), float(c2), d))
                    if qid in routine_ids and d <= -1:
                        routine_flags.append(f"{STATEMENTS[qid - 1]} (C1 {c1:.1f} → C2 {c2:.1f})")
                if qid in routine_ids and pd.notna(c2) and float(c2) <= 2:
                    if pd.notna(c1):
                        routine_flags.append(f"{STATEMENTS[qid - 1]} (C1 {c1:.1f} → C2 {c2:.1f}; low current)")
                    else:
                        routine_flags.append(f"{STATEMENTS[qid - 1]} (C2 {c2:.1f}; low current)")

            low_profile = (10.0 - float(o2))
            risk = low_profile * 1.8 + max(0.0, -drop) * 2.3 + len(routine_flags) * 0.85 + len(volatile) * 0.55
            candidates.append(
                dict(
                    name=str(r.get("student_name", "Student")).strip() or "Student",
                    email=str(r.get("Email", "")).strip(),
                    faculty=fac,
                    o1=float(o1),
                    o2=float(o2),
                    drop=drop,
                    risk=risk,
                    routine=routine_flags[:20],
                    volatile=sorted(volatile, key=lambda x: abs(x[3]), reverse=True)[:15],
                )
            )

        if not candidates:
            continue
        candidates.sort(key=lambda x: x["risk"], reverse=True)
        take_n = max(1, math.ceil(len(candidates) * 0.05))
        chosen = candidates[:take_n]
        fac_counts.append((fac, len(chosen)))

        for i, c in enumerate(chosen, 1):
            modal_id = f"target-{fac.replace(' ', '-').replace('/', '-')}-{i}"
            routine_html = "".join(f"<li>{x}</li>" for x in c["routine"]) or "<li>No routine flags triggered.</li>"
            volatile_html = (
                "".join(
                    f"<li>{st}<br><small>C1 {v1:.1f} → C2 {v2:.1f} ({d:+.1f})</small></li>"
                    for st, v1, v2, d in c["volatile"]
                )
                or "<li>No volatile item shifts (≥2 points) detected.</li>"
            )
            rows.append(
                f"""
                <tr>
                  <td style="padding: 10px; text-align:center;">{rank}</td>
                  <td style="padding: 10px;"><strong>{fac}</strong></td>
                  <td style="padding: 10px;">
                    <button class="target-link" onclick="openTargetModal('{modal_id}')">{c['name']}</button>
                    <div style="font-size:0.85em;color:#64748b;">{c['email']}</div>
                  </td>
                  <td style="padding: 10px; text-align:center;">{fmt(c['o2'],2)}</td>
                  <td style="padding: 10px; text-align:center;">{c['drop']:+.2f}</td>
                  <td style="padding: 10px; text-align:center;">{len(c['routine'])}</td>
                  <td style="padding: 10px; text-align:center;">{len(c['volatile'])}</td>
                </tr>
                """
            )
            modals.append(
                f"""
                <div id="{modal_id}" class="target-modal-overlay" onclick="closeTargetModal('{modal_id}')">
                  <div class="target-modal" onclick="event.stopPropagation();">
                    <div class="target-modal-header">
                      <h3 style="margin:0;">{c['name']} — {fac}</h3>
                      <button class="target-modal-close" onclick="closeTargetModal('{modal_id}')">&times;</button>
                    </div>
                    <p><strong>Overall Journey:</strong> {fmt(c['o1'],2)} → {fmt(c['o2'],2)} ({c['drop']:+.2f})</p>
                    <div class="target-modal-grid">
                      <div><h4>Routine flags (habits)</h4><ul>{routine_html}</ul></div>
                      <div><h4>Volatile shifts (big moves)</h4><ul>{volatile_html}</ul></div>
                    </div>
                    <p style="margin-top:12px;color:#64748b;font-size:0.9em;">Teacher view: click the name for evidence, then agree 1–2 priority habits to focus on over the next half-term.</p>
                  </div>
                </div>
                """
            )
            rank += 1

    fac_count_rows = "".join(f"<tr><td><strong>{fac}</strong></td><td style='text-align:center;'>{n}</td></tr>" for fac, n in sorted(fac_counts, key=lambda x: x[1], reverse=True))
    summary_table = f"""
      <table style="max-width:520px;margin:10px 0 18px 0;">
        <thead><tr><th>Faculty</th><th style="text-align:center;">Targeted students (top 5%)</th></tr></thead>
        <tbody>{fac_count_rows or '<tr><td colspan=\"2\">No faculties met the minimum size threshold.</td></tr>'}</tbody>
      </table>
    """

    main_table = f"""
      <table>
        <thead>
          <tr>
            <th style="text-align:center;">Rank</th>
            <th>Faculty</th>
            <th>Student</th>
            <th style="text-align:center;">C2 Overall</th>
            <th style="text-align:center;">C2−C1</th>
            <th style="text-align:center;">Routine flags</th>
            <th style="text-align:center;">Volatile shifts</th>
          </tr>
        </thead>
        <tbody>{''.join(rows) if rows else '<tr><td colspan=\"7\">No targeted students found (check matched cohort and statement columns).</td></tr>'}</tbody>
      </table>
    """
    return summary_table + main_table, "".join(modals)


def main() -> None:
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    df.columns = [c.strip() for c in df.columns]

    # Clean VESPA scales
    for dim, (c1, c2) in DIM_COLS.items():
        df[c1] = clean_scale(df.get(c1), 1, 10)
        df[c2] = clean_scale(df.get(c2), 1, 10)

    # Normalize demographics
    df["gender_norm"] = df.get("Gender", pd.Series(index=df.index, dtype=object)).apply(normalize_gender)
    df["res_norm"] = df.get("Residential", pd.Series(index=df.index, dtype=object)).apply(normalize_residential)
    df["faculty_norm"] = df.get("Faculty", pd.Series(index=df.index, dtype=object)).fillna("").astype(str).str.strip()
    df["year_norm"] = df.get("Year Gp", pd.Series(index=df.index, dtype=object)).apply(normalize_year_group)
    df["student_name"] = df.get("Name", pd.Series(index=df.index, dtype=object)).fillna("").astype(str).str.strip()

    # Matched cohort only (journey needs both cycles)
    matched = df.dropna(subset=["O1", "O2"]).copy()

    # Statement columns
    qcols = extract_question_cols(list(matched.columns))
    for qid, qc in qcols.items():
        matched[qc.c1] = clean_scale(matched[qc.c1], 1, 5)
        matched[qc.c2] = clean_scale(matched[qc.c2], 1, 5)

    # Whole-cohort means
    overall = {
        "n_students": int(len(matched)),
        "n_faculties": int(matched["faculty_norm"].replace("", np.nan).dropna().nunique()),
    }
    for dim, (c1, c2) in DIM_COLS.items():
        overall[dim.lower() + "_c1"] = float(matched[c1].mean())
        overall[dim.lower() + "_c2"] = float(matched[c2].mean())
        overall[dim.lower() + "_delta"] = float(matched[c2].mean() - matched[c1].mean())

    # Strongest/weakest based on Cycle 2 (current)
    dim_names = ["vision", "effort", "systems", "practice", "attitude"]
    strongest_dim = max(dim_names, key=lambda d: overall[f"{d}_c2"])
    weakest_dim = min(dim_names, key=lambda d: overall[f"{d}_c2"])

    # Faculty stats (matched)
    faculty_stats: List[dict] = []
    for fac in sorted([f for f in matched["faculty_norm"].unique() if f and not str(f).isdigit()]):
        fdf = matched[matched["faculty_norm"] == fac]
        if len(fdf) < 5:
            continue
        row = {"faculty": fac, "n": int(len(fdf))}
        for dim, (c1, c2) in DIM_COLS.items():
            row[f"{dim.lower()}_c1"] = float(fdf[c1].mean())
            row[f"{dim.lower()}_c2"] = float(fdf[c2].mean())
            row[f"{dim.lower()}_delta"] = float(fdf[c2].mean() - fdf[c1].mean())
        faculty_stats.append(row)
    faculty_stats.sort(key=lambda r: r["overall_c2"], reverse=True)

    # Gender stats (matched)
    gender_stats: List[dict] = []
    for g in ["Male", "Female"]:
        gdf = matched[matched["gender_norm"] == g]
        if len(gdf) < 10:
            continue
        row = {"label": g, "n": int(len(gdf))}
        for dim, (c1, c2) in DIM_COLS.items():
            row[f"{dim.lower()}_c1"] = float(gdf[c1].mean())
            row[f"{dim.lower()}_c2"] = float(gdf[c2].mean())
            row[f"{dim.lower()}_delta"] = float(gdf[c2].mean() - gdf[c1].mean())
        gender_stats.append(row)

    # Residential stats (matched)
    res_stats: List[dict] = []
    for rlab in ["Residential", "Non-Residential"]:
        rdf = matched[matched["res_norm"] == rlab]
        if len(rdf) < 10:
            continue
        row = {"label": rlab, "n": int(len(rdf))}
        for dim, (c1, c2) in DIM_COLS.items():
            row[f"{dim.lower()}_c1"] = float(rdf[c1].mean())
            row[f"{dim.lower()}_c2"] = float(rdf[c2].mean())
            row[f"{dim.lower()}_delta"] = float(rdf[c2].mean() - rdf[c1].mean())
        res_stats.append(row)

    # Year group stats (matched)
    year_stats: List[dict] = []
    for y in sorted(matched["year_norm"].dropna().unique()):
        ydf = matched[matched["year_norm"] == y]
        if len(ydf) < 20:
            continue
        row = {"year": y, "n": int(len(ydf))}
        for dim, (c1, c2) in DIM_COLS.items():
            row[f"{dim.lower()}_c1"] = float(ydf[c1].mean())
            row[f"{dim.lower()}_c2"] = float(ydf[c2].mean())
            row[f"{dim.lower()}_delta"] = float(ydf[c2].mean() - ydf[c1].mean())
        year_stats.append(row)
    year_stats.sort(key=lambda r: r["overall_c2"], reverse=True)

    # Statement stats (Cycle 2 + change)
    statement_rows: List[dict] = []
    for qid, qc in qcols.items():
        c1v = matched[qc.c1]
        c2v = matched[qc.c2]
        if c2v.dropna().empty:
            continue
        statement_rows.append(
            dict(
                q=qid,
                statement=STATEMENTS[qid - 1],
                category=qc.category,
                mean_c1=float(c1v.mean()),
                mean_c2=float(c2v.mean()),
                delta=float(c2v.mean() - c1v.mean()),
                var_c2=float(c2v.var(ddof=0)),
                n=int(c2v.notna().sum()),
            )
        )
    statement_rows.sort(key=lambda r: r["mean_c2"], reverse=True)
    top5 = statement_rows[:5]
    # Lowest agreement in Cycle 2 (referred to as "highest disagreement").
    bottom5 = list(reversed(statement_rows[-5:]))

    # Biggest statement movers (Cycle 2 - Cycle 1) for exec summary.
    by_delta = sorted(statement_rows, key=lambda r: r["delta"])
    worst_statement = by_delta[0] if by_delta else None
    best_statement = by_delta[-1] if by_delta else None

    # Gender statement diffs (Cycle 2)
    def top_statement_diffs(group_a: str, group_b: str, group_col: str) -> Tuple[List[dict], List[dict]]:
        adf = matched[matched[group_col] == group_a]
        bdf = matched[matched[group_col] == group_b]
        diffs = []
        for qid, qc in qcols.items():
            a2 = float(adf[qc.c2].mean())
            b2 = float(bdf[qc.c2].mean())
            if np.isnan(a2) or np.isnan(b2):
                continue
            diffs.append(
                dict(
                    statement=STATEMENTS[qid - 1],
                    category=qc.category,
                    a=a2,
                    b=b2,
                    diff=a2 - b2,
                )
            )
        diffs.sort(key=lambda r: r["diff"], reverse=True)
        a_higher = diffs[:3]
        b_higher = sorted(diffs, key=lambda r: r["diff"])[:3]
        return a_higher, b_higher

    male_higher, female_higher = top_statement_diffs("Male", "Female", "gender_norm")
    res_higher, nonres_higher = top_statement_diffs("Residential", "Non-Residential", "res_norm")

    # Targeted students (top 5% each faculty)
    target_table_html, target_modals_html = build_target_students_by_faculty(matched, qcols)
    # Count targeted students from table rows (minus header row).
    targeted_total = max(0, target_table_html.count("<tr>") - 1)

    # Charts (reusing original div IDs where possible)
    dist_charts = {
        "dist-vision": create_distribution_chart_journey(matched, "Vision", "dist-vision"),
        "dist-effort": create_distribution_chart_journey(matched, "Effort", "dist-effort"),
        "dist-systems": create_distribution_chart_journey(matched, "Systems", "dist-systems"),
        "dist-practice": create_distribution_chart_journey(matched, "Practice", "dist-practice"),
        "dist-attitude": create_distribution_chart_journey(matched, "Attitude", "dist-attitude"),
        "dist-overall": create_distribution_chart_journey(matched, "Overall", "dist-overall"),
    }
    faculty_chart = create_faculty_journey_chart(faculty_stats)
    gender_chart = create_group_journey_chart(gender_stats, "gender-chart", "Gender Journey Change by Dimension (C2 − C1)", "Dimension")
    res_chart = create_group_journey_chart(res_stats, "residential-chart", "Residential Journey Change by Dimension (C2 − C1)", "Dimension")

    # Radar charts (new)
    whole_radar = radar_cycle1_vs_cycle2(matched, [("Whole Cohort", matched)], "whole-radar", "Whole-Cohort Radar: Cycle 1 vs Cycle 2")
    large_faculties = sorted(faculty_stats, key=lambda r: r["n"], reverse=True)[:6]
    fac_radar = radar_cycle1_vs_cycle2(
        matched,
        [(f["faculty"], matched[matched["faculty_norm"] == f["faculty"]]) for f in large_faculties],
        "faculty-radar",
        "Largest Faculties Radar: Cycle 1 vs Cycle 2",
    )

    report_date = datetime.now().strftime("%B %d, %Y")

    # --- Build HTML: preserve original structure, but update copy to Journey ---
    # Report header section (same styling, updated text)
    header_html = f"""
        <div class="report-header">
            <div style="display: flex; align-items: center; justify-content: center; margin-bottom: 20px;">
                <img src="https://www.iagrm.com/content/large/agri_logos/hartpury_college_rev_on_red_(cmyk).jpg"
                     alt="Hartpury College Logo"
                     style="height: 100px; object-fit: contain; max-width: 400px;">
            </div>
            <h1 style="color: #dc143c; margin-bottom: 10px; text-align: center;">Hartpury College</h1>
            <h2 style="color: #8b0000; text-align: center;">VESPA Journey Report (Cycle 1 → Cycle 2)</h2>
            <p class="report-date" style="text-align: center;">Date of Report: {report_date}</p>

            <div style="margin-top: 20px; text-align: center;">
                <button onclick="window.print();" style="
                    background: linear-gradient(135deg, #dc143c, #8b0000);
                    color: white;
                    border: none;
                    padding: 12px 30px;
                    font-size: 1em;
                    font-weight: 600;
                    border-radius: 25px;
                    cursor: pointer;
                    box-shadow: 0 4px 15px rgba(220, 20, 60, 0.3);
                    transition: all 0.3s;
                " onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 20px rgba(220, 20, 60, 0.4)';"
                   onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 15px rgba(220, 20, 60, 0.3)';">
                    Download as PDF
                </button>
            </div>
        </div>
    """

    # Executive Summary (preserve layout, update content to journey)
    overall_vs_nat = overall["overall_c2"] - NATIONAL_AVERAGES["Overall"]
    overall_status = "above" if overall_vs_nat > 0.1 else "in line with" if overall_vs_nat > -0.1 else "below"
    top_fac = faculty_stats[0] if faculty_stats else {"faculty": "-", "overall_c2": float("nan"), "n": 0}
    biggest_dim = max(DIM_COLS.keys(), key=lambda d: overall[f"{d.lower()}_delta"])
    smallest_dim = min(DIM_COLS.keys(), key=lambda d: overall[f"{d.lower()}_delta"])
    most_improved_fac = max(faculty_stats, key=lambda r: r["overall_delta"]) if faculty_stats else None
    most_declined_fac = min(faculty_stats, key=lambda r: r["overall_delta"]) if faculty_stats else None
    exec_html = f"""
        <div class="executive-summary">
            <h2>Executive Summary</h2>
            <p>This VESPA <strong>Journey</strong> analysis for Hartpury College tracks how student mindset and study skills moved from
            <strong>Cycle 1 to Cycle 2</strong> across a matched cohort of <strong>{overall['n_students']:,} students</strong> in <strong>{overall['n_faculties']}</strong> faculties.</p>

            <p style="margin-top: 15px;"><strong>Overall Journey:</strong> Students moved from <strong>{overall['overall_c1']:.2f}</strong> in Cycle 1 to
            <strong>{overall['overall_c2']:.2f}</strong> in Cycle 2 ({overall['overall_delta']:+.2f} points). Current Cycle 2 performance remains {overall_status} national
            average ({overall['overall_c2']:.2f} vs {NATIONAL_AVERAGES['Overall']}).</p>

            <p style="margin-top: 15px;"><strong>Matched cohort note (important):</strong> This report analyses <strong>only students with both Cycle 1 and Cycle 2 VESPA scores</strong>.
            Any students missing either cycle are excluded so the journey comparisons are like-for-like. Where you see “matched n”, that is the number of students included for that subgroup.</p>

            <div class="key-insights" style="margin-top: 25px;">
                <h3 style="color: #dc143c; margin-bottom: 20px;">Key Journey Findings</h3>

                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-top: 20px;">
                    <div style="background: rgba(220, 20, 60, 0.08); padding: 20px; border-radius: 8px; border-left: 4px solid #dc143c;">
                        <h4 style="color: #2c3e50; margin-bottom: 10px;">Whole-Cohort Headline</h4>
                        <p><strong>Biggest dimension shift:</strong> {biggest_dim} ({overall[f'{biggest_dim.lower()}_delta']:+.2f}).<br>
                        <strong>Smallest/negative shift:</strong> {smallest_dim} ({overall[f'{smallest_dim.lower()}_delta']:+.2f}).</p>
                        <p style="margin-top:8px;">Cycle 2 profile is strongest in <strong>{strongest_dim.title()}</strong> ({overall[f'{strongest_dim}_c2']:.2f}) and lowest in
                        <strong>{weakest_dim.title()}</strong> ({overall[f'{weakest_dim}_c2']:.2f}).</p>
                    </div>

                    <div style="background: rgba(114, 203, 68, 0.08); padding: 20px; border-radius: 8px; border-left: 4px solid #72cb44;">
                        <h4 style="color: #2c3e50; margin-bottom: 10px;">Faculty Insights</h4>
                        <p><strong>Top Cycle 2 overall:</strong> {top_fac['faculty']} ({top_fac['overall_c2']:.2f}, matched n={top_fac['n']}).</p>
                        <p style="margin-top:8px;"><strong>Largest improvement:</strong> {most_improved_fac['faculty'] if most_improved_fac else '-'} ({most_improved_fac['overall_delta']:+.2f})<br>
                        <strong>Largest decline:</strong> {most_declined_fac['faculty'] if most_declined_fac else '-'} ({most_declined_fac['overall_delta']:+.2f})</p>
                    </div>

                    <div style="background: rgba(229, 148, 55, 0.08); padding: 20px; border-radius: 8px; border-left: 4px solid #e59437;">
                        <h4 style="color: #2c3e50; margin-bottom: 10px;">Journey Pattern</h4>
                        <p>The report highlights <strong>where change happened</strong> (faculty / gender / residential) and <strong>which habits shifted</strong> (statement journey), so leaders can target interventions rather than just comparing averages.</p>
                    </div>

                    <div style="background: rgba(134, 180, 240, 0.08); padding: 20px; border-radius: 8px; border-left: 4px solid #86b4f0;">
                        <h4 style="color: #2c3e50; margin-bottom: 10px;">Targeting for Action</h4>
                        <p><strong>Targeted students:</strong> top 5% within each faculty (proportional by size), with clickable evidence for teachers.<br>
                        <strong>Total flagged:</strong> {targeted_total}</p>
                    </div>

                    <div style="background: rgba(127, 49, 164, 0.08); padding: 20px; border-radius: 8px; border-left: 4px solid #7f31a4;">
                        <h4 style="color: #2c3e50; margin-bottom: 10px;">Year Group Journey</h4>
                        <p>Year group profiles are now reported as <strong>Cycle 1 → Cycle 2</strong> journey, enabling cohort-specific planning for Cycle 3.</p>
                    </div>

                    <div style="background: rgba(240, 50, 230, 0.08); padding: 20px; border-radius: 8px; border-left: 4px solid #f032e6;">
                        <h4 style="color: #2c3e50; margin-bottom: 10px;">Statement Journey</h4>
                        <p><strong>Most improved:</strong> {(best_statement['statement'][:52] + '…') if best_statement and len(best_statement['statement']) > 52 else (best_statement['statement'] if best_statement else '-') } ({best_statement['delta']:+.2f})<br>
                        <strong>Biggest drop:</strong> {(worst_statement['statement'][:52] + '…') if worst_statement and len(worst_statement['statement']) > 52 else (worst_statement['statement'] if worst_statement else '-') } ({worst_statement['delta']:+.2f})</p>
                    </div>
                </div>

                <div class="chart-container" style="margin-top: 25px;">
                    <div class="responsive-chart">
                        {whole_radar}
                    </div>
                    <p style="margin-top:10px;color:#64748b;">This radar overlays Cycle 1 and Cycle 2 to show whether improvements are broad-based or concentrated in specific dimensions.</p>
                </div>
            </div>
        </div>
    """

    # Journey Overview cards (preserve grid, show C1->C2 + national)
    def journey_card(dim: str) -> str:
        c1 = overall[f"{dim.lower()}_c1"]
        c2 = overall[f"{dim.lower()}_c2"]
        delta = overall[f"{dim.lower()}_delta"]
        color, arrow, status = score_status_vs_national(c2, dim)
        nat = NATIONAL_AVERAGES[dim]
        pct = pct_change(c1, c2)
        move_color = "#16a34a" if delta > 0 else ("#dc2626" if delta < 0 else "#64748b")
        move_arrow = "↑" if delta > 0 else ("↓" if delta < 0 else "•")
        bg = f"linear-gradient(135deg, {tint(COLORS[dim], 0.05)}, {tint(COLORS[dim], 0.28)})"
        return f"""
            <div class="stat-card" style="background: {bg}; color:#0f172a; border: 1px solid rgba(15,23,42,0.10);">
                <h4 style="color:#0f172a; opacity:0.9;">{dim}</h4>
                <div class="value" style="color:#0f172a;">{c1:.2f} → {c2:.2f}</div>
                <small style="color:#334155;">National: {nat} ({arrow} {status})</small>
                <div style="margin-top: 10px; display:flex; justify-content:center; gap:10px; flex-wrap:wrap;">
                  <span style="background: rgba(255,255,255,0.78); padding: 4px 10px; border-radius: 999px; border: 1px solid rgba(15,23,42,0.10);">
                    <strong style="color:{move_color};">{move_arrow} Δ {delta:+.2f}</strong>
                  </span>
                  <span style="background: rgba(255,255,255,0.78); padding: 4px 10px; border-radius: 999px; border: 1px solid rgba(15,23,42,0.10);">
                    <strong style="color:{move_color};">{pct:+.1f}%</strong>
                  </span>
                </div>
            </div>
        """

    overview_html = f"""
        <div class="section">
            <h2>📊 Cycle 1 → Cycle 2 Journey Overview</h2>
            <p style="margin-bottom: 20px;">
                Matched-cohort VESPA scores for Hartpury College, showing <strong>Cycle 1 → Cycle 2</strong> movement.
                National averages are shown for context (compared against Cycle 2).
            </p>
            <div class="stats-grid">
                {journey_card('Vision')}
                {journey_card('Effort')}
                {journey_card('Systems')}
                {journey_card('Practice')}
                {journey_card('Attitude')}
                {journey_card('Overall')}
            </div>
        </div>
    """

    # Distribution section (preserve containers/IDs)
    dist_html = f"""
        <div class="section">
            <h2>📈 Score Distribution Analysis</h2>
            <p>Distribution of VESPA scores for the matched cohort. Bars compare Cycle 1 vs Cycle 2; the red line shows national distribution.</p>

            <div class="chart-container"><div class="responsive-chart">{dist_charts['dist-vision']}</div></div>
            <div class="chart-container"><div class="responsive-chart">{dist_charts['dist-effort']}</div></div>
            <div class="chart-container"><div class="responsive-chart">{dist_charts['dist-systems']}</div></div>
            <div class="chart-container"><div class="responsive-chart">{dist_charts['dist-practice']}</div></div>
            <div class="chart-container"><div class="responsive-chart">{dist_charts['dist-attitude']}</div></div>
            <div class="chart-container"><div class="responsive-chart">{dist_charts['dist-overall']}</div></div>
        </div>
    """

    # Faculty cards (preserve style, show C1->C2)
    faculty_cards = []
    for idx, f in enumerate(faculty_stats, 1):
        rank_color = "#28a745" if idx <= 3 else "#dc143c" if idx <= 5 else "#dc3545"
        faculty_cards.append(
            f"""
            <div style="background: white; border-radius: 12px; padding: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.08); border-top: 4px solid {rank_color};">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h3 style="color: #2c3e50; margin: 0; font-size: 1.1em; max-width: 70%;">{f['faculty']}</h3>
                    <span style="background: {rank_color}; color: white; padding: 5px 12px; border-radius: 20px; font-size: 0.9em; font-weight: 600;">#{idx}</span>
                </div>

                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 15px;">
                    <div style="padding: 12px; background: linear-gradient(45deg, rgba(229,148,55,0.1), rgba(229,148,55,0.05)); border-radius: 8px; text-align: center;">
                        <div style="color: #e59437; font-size: 0.75em; font-weight: 600; text-transform: uppercase;">Vision</div>
                        <div style="font-size: 1.45em; font-weight: bold; color: #2c3e50; margin-top: 5px;">{f['vision_c1']:.2f} → {f['vision_c2']:.2f}</div>
                        <div style="font-size:0.85em;color:#64748b;">Δ {f['vision_delta']:+.2f}</div>
                    </div>
                    <div style="padding: 12px; background: linear-gradient(45deg, rgba(134,180,240,0.1), rgba(134,180,240,0.05)); border-radius: 8px; text-align: center;">
                        <div style="color: #5690d6; font-size: 0.75em; font-weight: 600; text-transform: uppercase;">Effort</div>
                        <div style="font-size: 1.45em; font-weight: bold; color: #2c3e50; margin-top: 5px;">{f['effort_c1']:.2f} → {f['effort_c2']:.2f}</div>
                        <div style="font-size:0.85em;color:#64748b;">Δ {f['effort_delta']:+.2f}</div>
                    </div>
                    <div style="padding: 12px; background: linear-gradient(45deg, rgba(114,203,68,0.1), rgba(114,203,68,0.05)); border-radius: 8px; text-align: center;">
                        <div style="color: #72cb44; font-size: 0.75em; font-weight: 600; text-transform: uppercase;">Systems</div>
                        <div style="font-size: 1.45em; font-weight: bold; color: #2c3e50; margin-top: 5px;">{f['systems_c1']:.2f} → {f['systems_c2']:.2f}</div>
                        <div style="font-size:0.85em;color:#64748b;">Δ {f['systems_delta']:+.2f}</div>
                    </div>
                    <div style="padding: 12px; background: linear-gradient(45deg, rgba(127,49,164,0.1), rgba(127,49,164,0.05)); border-radius: 8px; text-align: center;">
                        <div style="color: #7f31a4; font-size: 0.75em; font-weight: 600; text-transform: uppercase;">Practice</div>
                        <div style="font-size: 1.45em; font-weight: bold; color: #2c3e50; margin-top: 5px;">{f['practice_c1']:.2f} → {f['practice_c2']:.2f}</div>
                        <div style="font-size:0.85em;color:#64748b;">Δ {f['practice_delta']:+.2f}</div>
                    </div>
                </div>

                <div style="padding: 12px; background: linear-gradient(45deg, rgba(240,50,230,0.1), rgba(240,50,230,0.05)); border-radius: 8px; text-align: center; margin-bottom: 15px;">
                    <div style="color: #f032e6; font-size: 0.75em; font-weight: 600; text-transform: uppercase;">Attitude</div>
                    <div style="font-size: 1.45em; font-weight: bold; color: #2c3e50; margin-top: 5px;">{f['attitude_c1']:.2f} → {f['attitude_c2']:.2f}</div>
                    <div style="font-size:0.85em;color:#64748b;">Δ {f['attitude_delta']:+.2f}</div>
                </div>

                <div style="padding: 15px; background: linear-gradient(135deg, #dc143c, #8b0000); border-radius: 10px; text-align: center; color: white;">
                    <div style="font-size: 0.9em; font-weight: 600; opacity: 0.9; text-transform: uppercase;">Overall Score (Matched cohort)</div>
                    <div style="font-size: 2.2em; font-weight: bold; margin: 5px 0;">{f['overall_c1']:.2f} → {f['overall_c2']:.2f}</div>
                    <div style="font-size: 0.8em; opacity: 0.85;">Δ {f['overall_delta']:+.2f} | matched n = {f['n']}</div>
                </div>
            </div>
            """
        )

    # Faculty matrix (preserve table section; show C1->C2 with indicator vs national using C2)
    matrix_rows = []
    for f in faculty_stats:
        def cell(dim: str) -> str:
            c2 = f[f"{dim.lower()}_c2"]
            c1 = f[f"{dim.lower()}_c1"]
            _, arrow, _ = score_status_vs_national(c2, dim)
            color = "#28a745" if arrow == "↑" else "#dc3545" if arrow == "↓" else "#666"
            return f'<td style="padding: 14px; text-align: center;"><span style="color: {color}; font-weight: 600;">{arrow} {c1:.2f} → {c2:.2f}</span></td>'

        matrix_rows.append(
            f"""
            <tr style="border-bottom: 1px solid #e9ecef;">
                <td style="padding: 14px; font-weight: 600;">{f['faculty']} (n={f['n']})</td>
                {cell('Vision')}
                {cell('Effort')}
                {cell('Systems')}
                {cell('Practice')}
                {cell('Attitude')}
                <td style="padding: 14px; text-align: center; background: rgba(220, 20, 60, 0.05); font-size: 1.05em;">
                    <span style="color: #2c3e50; font-weight: 700;">{f['overall_c1']:.2f} → {f['overall_c2']:.2f}</span>
                    <div style="font-size:0.85em;color:#64748b;">Δ {f['overall_delta']:+.2f}</div>
                </td>
            </tr>
            """
        )

    # Whole-cohort averages (matched)
    avg_row = f"""
        <tr style="background: linear-gradient(135deg, #dc143c, #8b0000); color: white;">
            <td style="padding: 16px; font-weight: bold;">HARTPURY AVERAGE (matched)</td>
            <td style="padding: 16px; text-align: center; font-weight: bold;">{overall['vision_c1']:.2f} → {overall['vision_c2']:.2f}</td>
            <td style="padding: 16px; text-align: center; font-weight: bold;">{overall['effort_c1']:.2f} → {overall['effort_c2']:.2f}</td>
            <td style="padding: 16px; text-align: center; font-weight: bold;">{overall['systems_c1']:.2f} → {overall['systems_c2']:.2f}</td>
            <td style="padding: 16px; text-align: center; font-weight: bold;">{overall['practice_c1']:.2f} → {overall['practice_c2']:.2f}</td>
            <td style="padding: 16px; text-align: center; font-weight: bold;">{overall['attitude_c1']:.2f} → {overall['attitude_c2']:.2f}</td>
            <td style="padding: 16px; text-align: center; font-weight: bold; font-size: 1.1em;">{overall['overall_c1']:.2f} → {overall['overall_c2']:.2f}</td>
        </tr>
    """

    faculty_section = f"""
        <div class="section" style="padding: 40px;">
            <h2 style="color: #2c3e50; font-size: 2.2em; margin-bottom: 30px; border-bottom: 3px solid #dc143c; padding-bottom: 15px;">
                Faculty Performance Comparison — Journey (Cycle 1 → Cycle 2)
            </h2>
            <p style="font-size: 1.2em; color: #555; margin-bottom: 30px;">
                This section preserves the original faculty layout, but every metric now shows <strong>Cycle 1 → Cycle 2</strong> movement for the matched cohort.
            </p>

            <div class="faculty-cards-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 25px; margin-bottom: 50px;">
                {''.join(faculty_cards)}
            </div>

            <h3 style="color: #2c3e50; font-size: 1.6em; margin-top: 20px;">Detailed Performance Matrix (Cycle 1 → Cycle 2)</h3>
            <p style="color:#555;">Arrows indicate Cycle 2 vs national (±0.2), while each cell shows the journey from Cycle 1 to Cycle 2.</p>
            <div style="overflow-x:auto;">
                <table style="width:100%; border-collapse: collapse; margin: 20px 0; background: white; border-radius: 10px; overflow:hidden;">
                    <thead>
                        <tr style="background: #dc143c; color: white;">
                            <th style="padding: 14px; text-align:left;">Faculty</th>
                            <th style="padding: 14px; text-align:center;">VISION</th>
                            <th style="padding: 14px; text-align:center;">EFFORT</th>
                            <th style="padding: 14px; text-align:center;">SYSTEMS</th>
                            <th style="padding: 14px; text-align:center;">PRACTICE</th>
                            <th style="padding: 14px; text-align:center;">ATTITUDE</th>
                            <th style="padding: 14px; text-align:center;">OVERALL</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(matrix_rows)}
                        {avg_row}
                    </tbody>
                </table>
            </div>

            <div style="margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 8px; display: flex; align-items: center; gap: 30px; flex-wrap: wrap;">
                <span style="font-weight: 600; color: #2c3e50;">Performance Indicators vs National (Cycle 2):</span>
                <span style="color: #28a745;">↑ Above National (+0.2)</span>
                <span style="color: #666;">• On Par with National (±0.2)</span>
                <span style="color: #dc3545;">↓ Below National (-0.2)</span>
            </div>

            <div class="chart-container">
                <div class="responsive-chart">{faculty_chart}</div>
                <p style="margin-top:10px;color:#64748b;">This chart shows <strong>change</strong> (C2−C1). Positive bars mean that faculty improved in that dimension.</p>
            </div>

            <div class="chart-container">
                <div class="responsive-chart">{fac_radar}</div>
            </div>
        </div>
    """

    # Targeted students section (new, but fits the “action” step and uses the same section styling)
    targeted_section = f"""
        <div class="section">
            <h2>🎯 Targeted Students by Faculty (Top 5% per Faculty)</h2>
            <p style="margin-bottom: 10px;">
                This list is <strong>faculty-proportional</strong>: each faculty contributes its highest-priority top 5% (minimum 1 student), so larger faculties contribute more students.
                Click a student name to see evidence (routine flags + volatile shifts) that a teacher can act on.
            </p>
            {target_table_html}
            {target_modals_html}
        </div>
    """

    # Gender section (preserve divider and card layout, update to journey)
    if len(gender_stats) >= 2:
        male = next((g for g in gender_stats if g["label"] == "Male"), None)
        female = next((g for g in gender_stats if g["label"] == "Female"), None)
    else:
        male = female = None

    def diff_label(d: float) -> str:
        if d < 0.1:
            return "Minimal"
        if d < 0.2:
            return "Moderate"
        return "Notable"

    gender_overall_diff_c2 = abs((male["overall_c2"] if male else 0.0) - (female["overall_c2"] if female else 0.0))

    def statement_table_rows(items: List[dict], a_label: str, b_label: str) -> str:
        out = []
        for it in items:
            out.append(
                f"""
                <tr>
                    <td style="padding: 10px;">{it['statement']}</td>
                    <td style="padding: 10px; text-align: center;">{it['category']}</td>
                    <td style="padding: 10px; text-align: center;">{it['a']:.2f}</td>
                    <td style="padding: 10px; text-align: center;">{it['b']:.2f}</td>
                    <td style="padding: 10px; text-align: center;" class="positive">{it['diff']:+.2f}<br><small>({a_label if it['diff']>0 else b_label} higher)</small></td>
                </tr>
                """
            )
        return "".join(out)

    gender_section = f"""
        <div style="background: #f0f4f8; padding: 30px 0; margin-top: 30px;">
            <h1 style="text-align: center; color: #2c3e50; border-bottom: 3px solid #dc143c; padding-bottom: 10px; margin: 0 auto 30px; max-width: 400px;">
                GENDER ANALYSIS
            </h1>
        </div>

        <div class="section">
            <h2>👥 VESPA Scores by Gender</h2>
            <p style="margin-bottom: 20px;">
                Analysis of VESPA <strong>journey</strong> comparing male and female students. Values show Cycle 1 → Cycle 2 movement for the matched cohort.
            </p>

            <div class="stats-grid" style="grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));">
                <div class="stat-card">
                    <h4>Male Students</h4>
                    <div class="value">{(male['overall_c1'] if male else 0):.2f} → {(male['overall_c2'] if male else 0):.2f}</div>
                    <small>Matched n={male['n'] if male else 0} | Δ {(male['overall_delta'] if male else 0):+.2f}</small>
                </div>
                <div class="stat-card">
                    <h4>Female Students</h4>
                    <div class="value">{(female['overall_c1'] if female else 0):.2f} → {(female['overall_c2'] if female else 0):.2f}</div>
                    <small>Matched n={female['n'] if female else 0} | Δ {(female['overall_delta'] if female else 0):+.2f}</small>
                </div>
                <div class="stat-card" style="background: linear-gradient(135deg, #28a745, #20c997);">
                    <h4>Cycle 2 Gap</h4>
                    <div class="value">{gender_overall_diff_c2:.2f}</div>
                    <small>({diff_label(gender_overall_diff_c2)})</small>
                </div>
            </div>

            <div class="chart-container">
                <div class="responsive-chart">{gender_chart}</div>
                <p style="margin-top:10px;color:#64748b;">This chart shows <strong>change</strong> (C2−C1) by dimension for each gender.</p>
            </div>

            <h3>Statement-Level Gender Differences</h3>
            <p style="margin: 15px 0;">
                The following statements show the largest differences in agreement in <strong>Cycle 2</strong> between male and female students.
            </p>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 20px 0;">
                <div>
                    <h4 style="color: #2c3e50; margin-bottom: 15px; background: rgba(102, 126, 234, 0.1); padding: 10px; border-radius: 5px;">
                        🔵 Top 3 - Male Students Score Higher (Cycle 2)
                    </h4>
                    <table style="width: 100%;">
                        <thead><tr>
                            <th style="font-size: 0.85em;">Statement</th>
                            <th style="text-align: center; font-size: 0.85em;">Category</th>
                            <th style="text-align: center; font-size: 0.85em;">Male</th>
                            <th style="text-align: center; font-size: 0.85em;">Female</th>
                            <th style="text-align: center; font-size: 0.85em;">Diff</th>
                        </tr></thead>
                        <tbody>{statement_table_rows(male_higher, "Male", "Female")}</tbody>
                    </table>
                </div>

                <div>
                    <h4 style="color: #2c3e50; margin-bottom: 15px; background: rgba(240, 50, 230, 0.1); padding: 10px; border-radius: 5px;">
                        🟣 Top 3 - Female Students Score Higher (Cycle 2)
                    </h4>
                    <table style="width: 100%;">
                        <thead><tr>
                            <th style="font-size: 0.85em;">Statement</th>
                            <th style="text-align: center; font-size: 0.85em;">Category</th>
                            <th style="text-align: center; font-size: 0.85em;">Male</th>
                            <th style="text-align: center; font-size: 0.85em;">Female</th>
                            <th style="text-align: center; font-size: 0.85em;">Diff</th>
                        </tr></thead>
                        <tbody>{statement_table_rows(female_higher, "Female", "Male")}</tbody>
                    </table>
                </div>
            </div>
        </div>
    """

    # Residential section (preserve divider & layout, update)
    res_res = next((r for r in res_stats if r["label"] == "Residential"), None)
    res_non = next((r for r in res_stats if r["label"] == "Non-Residential"), None)
    res_gap = abs((res_res["overall_c2"] if res_res else 0.0) - (res_non["overall_c2"] if res_non else 0.0))

    residential_section = f"""
        <div style="background: #f0f4f8; padding: 30px 0; margin-top: 30px;">
            <h1 style="text-align: center; color: #2c3e50; border-bottom: 3px solid #dc143c; padding-bottom: 10px; margin: 0 auto 30px; max-width: 500px;">
                RESIDENTIAL STATUS ANALYSIS
            </h1>
        </div>

        <div class="section">
            <h2>🏠 VESPA Scores by Residential Status</h2>
            <p style="margin-bottom: 20px;">
                Analysis of VESPA <strong>journey</strong> comparing residential and non-residential students (Cycle 1 → Cycle 2 for the matched cohort).
            </p>

            <div class="stats-grid" style="grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));">
                <div class="stat-card">
                    <h4>Residential Students</h4>
                    <div class="value">{(res_res['overall_c1'] if res_res else 0):.2f} → {(res_res['overall_c2'] if res_res else 0):.2f}</div>
                    <small>Matched n={res_res['n'] if res_res else 0} | Δ {(res_res['overall_delta'] if res_res else 0):+.2f}</small>
                </div>
                <div class="stat-card">
                    <h4>Non-Residential Students</h4>
                    <div class="value">{(res_non['overall_c1'] if res_non else 0):.2f} → {(res_non['overall_c2'] if res_non else 0):.2f}</div>
                    <small>Matched n={res_non['n'] if res_non else 0} | Δ {(res_non['overall_delta'] if res_non else 0):+.2f}</small>
                </div>
                <div class="stat-card" style="background: linear-gradient(135deg, #28a745, #20c997);">
                    <h4>Cycle 2 Gap</h4>
                    <div class="value">{res_gap:.2f}</div>
                    <small>({diff_label(res_gap)})</small>
                </div>
            </div>

            <div class="chart-container">
                <div class="responsive-chart">{res_chart}</div>
                <p style="margin-top:10px;color:#64748b;">This chart shows <strong>change</strong> (C2−C1) by dimension for each residential group.</p>
            </div>

            <h3>Statement-Level Residential Differences</h3>
            <p style="margin: 15px 0;">
                The following statements show the largest differences in agreement in <strong>Cycle 2</strong> between residential and non-residential students.
            </p>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 20px 0;">
                <div>
                    <h4 style="color: #2c3e50; margin-bottom: 15px; background: rgba(114, 203, 68, 0.1); padding: 10px; border-radius: 5px;">
                        🟢 Top 3 - Residential Students Score Higher (Cycle 2)
                    </h4>
                    <table style="width: 100%;">
                        <thead><tr>
                            <th style="font-size: 0.85em;">Statement</th>
                            <th style="text-align: center; font-size: 0.85em;">Category</th>
                            <th style="text-align: center; font-size: 0.85em;">Res</th>
                            <th style="text-align: center; font-size: 0.85em;">Non-Res</th>
                            <th style="text-align: center; font-size: 0.85em;">Diff</th>
                        </tr></thead>
                        <tbody>{statement_table_rows(res_higher, "Residential", "Non-Residential")}</tbody>
                    </table>
                </div>

                <div>
                    <h4 style="color: #2c3e50; margin-bottom: 15px; background: rgba(229, 148, 55, 0.1); padding: 10px; border-radius: 5px;">
                        🟠 Top 3 - Non-Residential Students Score Higher (Cycle 2)
                    </h4>
                    <table style="width: 100%;">
                        <thead><tr>
                            <th style="font-size: 0.85em;">Statement</th>
                            <th style="text-align: center; font-size: 0.85em;">Category</th>
                            <th style="text-align: center; font-size: 0.85em;">Res</th>
                            <th style="text-align: center; font-size: 0.85em;">Non-Res</th>
                            <th style="text-align: center; font-size: 0.85em;">Diff</th>
                        </tr></thead>
                        <tbody>{statement_table_rows(nonres_higher, "Non-Residential", "Residential")}</tbody>
                    </table>
                </div>
            </div>
        </div>
    """

    # Year group section (preserve, update)
    year_cards = []
    for i, y in enumerate(year_stats, 1):
        year_cards.append(
            f"""
            <div class="stat-card">
                <h4>{y['year']}</h4>
                <div class="value">{y['overall_c1']:.2f} → {y['overall_c2']:.2f}</div>
                <small>n={y['n']} students</small>
                <div style="margin-top: 8px; font-size: 0.75em;">Rank (Cycle 2): #{i} of {len(year_stats)}</div>
            </div>
            """
        )

    year_table_rows = []
    for y in sorted(year_stats, key=lambda r: r["year"]):
        year_table_rows.append(
            f"""
            <tr>
              <td style="padding: 12px; font-weight: 600;">{y['year']}</td>
              <td style="padding: 12px; text-align:center;">{y['n']}</td>
              <td style="padding: 12px; text-align:center;">{y['vision_c1']:.2f} → {y['vision_c2']:.2f}</td>
              <td style="padding: 12px; text-align:center;">{y['effort_c1']:.2f} → {y['effort_c2']:.2f}</td>
              <td style="padding: 12px; text-align:center;">{y['systems_c1']:.2f} → {y['systems_c2']:.2f}</td>
              <td style="padding: 12px; text-align:center;">{y['practice_c1']:.2f} → {y['practice_c2']:.2f}</td>
              <td style="padding: 12px; text-align:center;">{y['attitude_c1']:.2f} → {y['attitude_c2']:.2f}</td>
              <td style="padding: 12px; text-align:center; background: rgba(220, 20, 60, 0.05); font-weight:700;">{y['overall_c1']:.2f} → {y['overall_c2']:.2f}</td>
            </tr>
            """
        )

    year_section = f"""
        <div style="background: #f0f4f8; padding: 30px 0; margin-top: 30px;">
            <h1 style="text-align: center; color: #2c3e50; border-bottom: 3px solid #dc143c; padding-bottom: 10px; margin: 0 auto 30px; max-width: 500px;">
                YEAR GROUP ANALYSIS
            </h1>
        </div>

        <div class="section">
            <h2>📚 VESPA Scores by Year Group</h2>
            <p style="margin-bottom: 20px;">
                Year group journey from Cycle 1 to Cycle 2 for the matched cohort. Use this to plan cohort-specific interventions ahead of Cycle 3.
            </p>

            <h3>Year Group Performance Overview</h3>
            <div class="stats-grid">{''.join(year_cards) if year_cards else ''}</div>

            <h3>Detailed Year Group Comparison</h3>
            <table>
                <thead>
                    <tr>
                        <th>Year Group</th>
                        <th style="text-align:center;">Students</th>
                        <th style="text-align:center;">Vision</th>
                        <th style="text-align:center;">Effort</th>
                        <th style="text-align:center;">Systems</th>
                        <th style="text-align:center;">Practice</th>
                        <th style="text-align:center;">Attitude</th>
                        <th style="text-align:center;">Overall</th>
                    </tr>
                </thead>
                <tbody>{''.join(year_table_rows) if year_table_rows else ''}</tbody>
            </table>
        </div>
    """

    # Statement level analysis (preserve section, update to journey)
    def statement_row_html(r: dict) -> str:
        return f"""
        <div style="margin: 12px 0; padding: 14px; background: #fff; border-radius: 10px; border: 1px solid #e5e7eb;">
          <div style="display:flex; justify-content:space-between; gap:12px; flex-wrap:wrap;">
            <div style="font-weight:700;color:#2c3e50;">{r['statement']}</div>
            <div style="color:#64748b;">{r['category']} | n={r['n']}</div>
          </div>
          <div style="margin-top:6px;color:#334155;">
            <strong>C2 mean:</strong> {r['mean_c2']:.2f} (C1 {r['mean_c1']:.2f} → C2 {r['mean_c2']:.2f}, Δ {r['delta']:+.2f}) |
            <strong>C2 variance:</strong> {r['var_c2']:.2f}
          </div>
        </div>
        """

    statement_section = f"""
        <div style="background: #f0f4f8; padding: 30px 0; margin-top: 30px;">
            <h1 style="text-align: center; color: #2c3e50; border-bottom: 3px solid #dc143c; padding-bottom: 10px; margin: 0 auto 30px; max-width: 560px;">
                STATEMENT LEVEL ANALYSIS
            </h1>
        </div>

        <div class="section">
            <h2>📝 VESPA Statement Analysis — Journey</h2>
            <p>Statements are shown with Cycle 2 agreement and how they changed since Cycle 1. This makes it easier to identify where habits strengthened or slipped mid-year.</p>

            <h3>Top 5 — Students Strongly Agree (Cycle 2)</h3>
            {''.join(statement_row_html(r) for r in top5)}

            <h3 style="margin-top:20px;">Bottom 5 — Statements with Highest Disagreement (Cycle 2)</h3>
            {''.join(statement_row_html(r) for r in bottom5)}

            <h3 style="margin-top:25px;">Interpretation Guide</h3>
            <p><strong>Mean Scores:</strong> Statements range from 1–5. Higher means stronger agreement. Journey Δ shows how agreement moved from Cycle 1 to Cycle 2.</p>
            <p><strong>Variance:</strong> Low variance means consistent responses; higher variance means mixed experiences and suggests differentiated support.</p>
        </div>
    """

    # Final HTML (reusing the same CSS style block structure as original)
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hartpury College - VESPA Journey Report (Cycle 1 → Cycle 2)</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #dc143c 0%, #8b0000 100%);
            min-height: 100vh;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; padding: 20px; }}
        .report-header {{
            background: white; border-radius: 15px; padding: 40px; margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }}
        .executive-summary, .section {{
            background: white; border-radius: 15px; padding: 30px; margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }}
        .section h2, .executive-summary h2 {{ color: #dc143c; margin-bottom: 20px; font-size: 1.8em; }}
        .section h3 {{ color: #8b0000; margin: 20px 0 10px 0; font-size: 1.4em; }}
        .key-insights {{ background: #f8f9fa; border-left: 4px solid #dc143c; padding: 20px; margin: 20px 0; border-radius: 5px; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }}
        .stat-card {{
            background: linear-gradient(135deg, #dc143c 0%, #8b0000 100%);
            color: white; padding: 20px; border-radius: 10px; text-align: center;
        }}
        .stat-card h4 {{ font-size: 0.9em; opacity: 0.9; margin-bottom: 10px; }}
        .stat-card .value {{ font-size: 1.55em; font-weight: bold; }}
        .stat-card small {{ font-size: 0.8em; opacity: 0.85; display: block; margin-top: 6px; }}
        .chart-container {{ margin: 30px 0; padding: 20px; background: #f8f9fa; border-radius: 10px; }}
        .responsive-chart {{ width: 100%; overflow-x: auto; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th {{ background: #dc143c; color: white; padding: 12px; text-align: left; }}
        td {{ padding: 12px; border-bottom: 1px solid #e5e7eb; }}
        .positive {{ color: #28a745; font-weight: 600; }}
        .target-link {{ background:none; border:none; color:#2563eb; text-decoration:underline; cursor:pointer; font:inherit; padding:0; text-align:left; }}
        .target-modal-overlay {{ display:none; position:fixed; z-index:9999; inset:0; background:rgba(15,23,42,.55); padding:20px; overflow-y:auto; }}
        .target-modal {{ max-width:920px; margin:30px auto; background:#fff; border-radius:14px; padding:20px; box-shadow:0 18px 45px rgba(15,23,42,.28); }}
        .target-modal-header {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; }}
        .target-modal-close {{ border:none; background:none; font-size:1.8rem; line-height:1; cursor:pointer; color:#334155; }}
        .target-modal-grid {{ display:grid; grid-template-columns: 1fr 1fr; gap:16px; margin-top:10px; }}
        @media(max-width: 900px) {{ .target-modal-grid {{ grid-template-columns: 1fr; }} }}
        @media print {{
            body {{ background: #fff !important; }}
            .chart-container, .section, .executive-summary, .report-header {{ box-shadow:none !important; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        {header_html}
        {exec_html}
        {overview_html}
        {dist_html}
        {faculty_section}
        {targeted_section}
        {gender_section}
        {residential_section}
        {year_section}
        {statement_section}
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
    </script>
</body>
</html>
"""

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(html, encoding="utf-8")
    print(f"Wrote journey report (in-place): {OUT_PATH}")

    SHARE_PATH.write_text(html, encoding="utf-8")
    print(f"Wrote shareable copy: {SHARE_PATH}")


if __name__ == "__main__":
    main()

