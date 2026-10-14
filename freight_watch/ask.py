"""Stretch goal: ask questions about the findings in plain English.

Deliberately deterministic: it parses the route / month / year out of the question and answers ONLY
from outputs/output.csv and outputs/weekly_metrics.csv. If nothing matches, it says so instead of guessing.

    python -m freight_watch.ask "why did Chennai-Bangalore get pricier in March?"
"""
from __future__ import annotations

import argparse
import calendar
import re

import pandas as pd

from .config import Config

MONTHS = {m.lower(): i for i, m in enumerate(calendar.month_name) if m}
MONTHS.update({m.lower(): i for i, m in enumerate(calendar.month_abbr) if m})


def _find_routes(question: str, routes: list[str]) -> list[str]:
    q = question.lower()
    exact = [r for r in routes if r.lower() in q]
    if exact:
        return exact
    hits = []
    for r in routes:
        a, b = (c.lower() for c in r.split("-"))
        if a in q or b in q:
            hits.append(r)
    return hits


def answer(question: str, out_dir: str = "outputs") -> str:
    flagged = pd.read_csv(f"{out_dir}/output.csv", keep_default_na=False)
    metrics = pd.read_csv(f"{out_dir}/weekly_metrics.csv")
    routes = sorted(metrics["route"].unique())

    found = _find_routes(question, routes)
    if not found:
        return "I couldn't tell which route you mean. Known routes: " + ", ".join(routes) + "."
    words = re.findall(r"[a-z]+", question.lower())
    month = next((MONTHS[w] for w in words if w in MONTHS), None)
    year = next((int(y) for y in re.findall(r"\b(20\d\d)\b", question)), None)

    lines = []
    for route in found:
        f = flagged[flagged["route"] == route].copy()
        m = metrics[metrics["route"] == route].copy()
        for df in (f, m):
            d = pd.to_datetime(df["week_of"])
            keep = pd.Series(True, index=df.index)
            if month:
                keep &= d.dt.month == month
            if year:
                keep &= d.dt.year == year
            df.drop(df.index[~keep], inplace=True)
        when = (calendar.month_name[month] if month else "any month") + (f" {year}" if year else "")
        if f.empty:
            if m.empty:
                lines.append(f"{route}: I have no data for {when}.")
            else:
                lo, hi = m["cost_per_tonne_km"].min(), m["cost_per_tonne_km"].max()
                lines.append(f"{route}, {when}: no week was flagged (cost per tonne-km ranged {lo:.2f}-{hi:.2f}, "
                             f"never meeting both the +{Config.min_pct_vs_own:g}% vs own history and "
                             f"+{Config.min_pct_vs_peers:g}% vs peers rules).")
            continue
        for r in f.itertuples():
            verdict = ("justified by " + r.matched_note_id) if r.matched_note_id else "UNEXPLAINED"
            lines.append(f"{route}, week of {r.week_of}: {r.cost_per_tonne_km}/tonne-km, "
                         f"{r.vs_own_history}, {r.vs_similar_routes}. Verdict: {verdict}. {r.reason}")
    return "\n".join(lines)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("question")
    ap.add_argument("--out", default="outputs")
    a = ap.parse_args()
    print(answer(a.question, a.out))
