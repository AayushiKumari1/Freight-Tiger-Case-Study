"""Turn free-text notes into structured, checkable facts (scope, window, effect, magnitude).

Everything here is deterministic rules over the note text, so the same input always gives the same
parse. The limits of this approach are discussed in the README.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

import pandas as pd

from .config import Config

OUT_OF_SCOPE_CUES = ("not part of this dataset", "not in this dataset")
NO_IMPACT_CUES = (
    "not significantly affected", "no significant", "without a rate change", "no rate change",
    "returned to normal", "remained normal", "remained stable", "no major disruption",
    "improved road conditions",
)
INCREASE_CUES = (
    "surcharge", "higher trip costs", "higher costs", "pushing up", "push up",
    "cost increase", "price hike", "rose",
)
ONSET_CUES = ("starting this week", "starting from this week")

_RANGE = re.compile(r"from\s+([A-Z][a-z]{2})\s+(\d{1,2})\s+to\s+([A-Z][a-z]{2})\s+(\d{1,2})")
_PCT = re.compile(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*%")
_MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], start=1)}


@dataclass(frozen=True)
class Note:
    note_id: str
    date: date
    applies_to: str
    text: str
    scope: Optional[str]       
    window_start: date
    window_end: date
    effect: str               
    max_effect_pct: Optional[float] 


def _monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def parse_note(row: pd.Series, cfg: Config) -> Note:
    text = str(row["note"]).strip()
    low = text.lower()
    nd = pd.to_datetime(row["date"]).date()

    m = _RANGE.search(text)
    if m: 
        sm, sd, em, ed = _MONTHS[m.group(1)], int(m.group(2)), _MONTHS[m.group(3)], int(m.group(4))
        start = date(nd.year, sm, sd)
        end = date(nd.year + (1 if em < sm else 0), em, ed)
    elif any(c in low for c in ONSET_CUES):
        start = _monday(nd)
        end = start + timedelta(weeks=cfg.persistent_note_weeks) - timedelta(days=1)
    else:  
        start = _monday(nd)
        end = start + timedelta(days=6)

    if any(c in low for c in OUT_OF_SCOPE_CUES):
        effect = "out_of_scope"
    elif any(c in low for c in NO_IMPACT_CUES):
        effect = "no_cost_impact"
    elif any(c in low for c in INCREASE_CUES):
        effect = "cost_increase"
    else:
        effect = "unclear"  

    pct = _PCT.search(text)
    applies_to = str(row["applies_to"]).strip()
    return Note(
        note_id=str(row["note_id"]).strip(),
        date=nd,
        applies_to=applies_to,
        text=text,
        scope=None if applies_to.lower() == "all routes" else applies_to,
        window_start=start,
        window_end=end,
        effect=effect,
        max_effect_pct=float(pct.group(2)) if pct else None,
    )


def load_notes(path: str, cfg: Config) -> list[Note]:
    df = pd.read_csv(path)
    notes = [parse_note(r, cfg) for _, r in df.iterrows()]
    return sorted(notes, key=lambda n: n.note_id)
