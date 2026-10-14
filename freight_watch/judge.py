"""Decide, for one flagged route-week, whether a note genuinely justifies the cost rise.

Pipeline per row:  retrieve candidate notes  ->  verify each against hard rules  ->  verdict.
A note only counts as a justification if ALL of these hold (otherwise the row stays "unexplained"):
  1. it applies to this route (or says "All Routes"),
  2. its text says costs went UP (not "unaffected", "stable", "absorbed", ...),
  3. its time window overlaps this Monday-Sunday week,
  4. if it states a magnitude (e.g. "5-7%"), the observed rise is not far beyond it.
The explanation text is built from the note's own fields and quoted text -- nothing is generated.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from .config import Config
from .notes import Note
from .retrieval import Retriever

QUERY_TEMPLATE = "{origin} {destination} higher freight cost increase surcharge disruption diesel toll flood festival"


@dataclass(frozen=True)
class Check:
    note: Note
    status: str   # supports | wrong_route | out_of_scope | no_cost_impact | outside_window | exceeds_magnitude
    gap_days: int


@dataclass(frozen=True)
class Verdict:
    flagged: str          # "Yes" or "No (justified)"
    matched_note_id: str  # "" when unexplained
    reason: str
    retrieved: tuple      # note ids that were retrieved and verified (for the audit trail)


def first_sentence(text: str) -> str:
    """The note's own first sentence (no trailing full stop) - a short, exact, grounded quote."""
    return text.split(". ")[0].rstrip(".")


def gap_days(note: Note, week_start: date) -> int:
    """Days between the note's window and the Mon-Sun week (0 if they overlap)."""
    week_end = week_start + timedelta(days=6)
    if note.window_end < week_start:
        return (week_start - note.window_end).days
    if note.window_start > week_end:
        return (note.window_start - week_end).days
    return 0


def check_note(note: Note, route: str, week_start: date, pct_vs_own: float, cfg: Config) -> Check:
    gap = gap_days(note, week_start)
    if note.scope is not None and note.scope != route:
        status = "wrong_route"
    elif note.effect == "out_of_scope":
        status = "out_of_scope"
    elif note.effect != "cost_increase":
        status = "no_cost_impact"
    elif gap > 0:
        status = "outside_window"
    elif note.max_effect_pct is not None and pct_vs_own > note.max_effect_pct + cfg.magnitude_tolerance_pp:
        status = "exceeds_magnitude"
    else:
        status = "supports"
    return Check(note, status, gap)


def _why_rejected(c: Check, week_start: date, pct_vs_own: float) -> str:
    n = c.note
    head = f"{n.note_id} ({n.date.isoformat()})"
    if c.status == "outside_window":
        return f"{head} covers {n.window_start.isoformat()} to {n.window_end.isoformat()}, not this week"
    if c.status == "no_cost_impact":
        return f"{head} does not describe a cost rise"
    if c.status == "out_of_scope":
        return f"{head} is about routes not in this dataset"
    if c.status == "exceeds_magnitude":
        return f"{head} explains at most ~{n.max_effect_pct:g}%, but the route is {pct_vs_own:+.1f}% up"
    return f"{head} does not apply"


def judge(route: str, origin: str, destination: str, week_start: date, pct_vs_own: float,
          notes: list[Note], index: Retriever, cfg: Config) -> Verdict:
    horizon = cfg.note_horizon_weeks * 7
    by_id = {n.note_id: n for n in notes}

    # Stage 1 - metadata filter: right route (or all routes) and close enough in time to matter.
    nearby = {n.note_id for n in notes
              if (n.scope is None or n.scope == route) and gap_days(n, week_start) <= horizon}
    if not nearby:
        return Verdict("Yes", "", "No matching note found for this route or date range. "
                                  "Flagged for review.", ())

    # Stage 2 - rank what is left by similarity to the anomaly; Stage 3 - verify every retrieved note.
    query = QUERY_TEMPLATE.format(origin=origin, destination=destination)
    hits = index.search(query, restrict_to=nearby, k=cfg.top_k)
    score = dict(hits)
    checks = [check_note(by_id[i], route, week_start, pct_vs_own, cfg) for i, _ in hits]
    retrieved = tuple(c.note.note_id for c in checks)

    supporting = [c for c in checks if c.status == "supports"]
    if supporting:
        # prefer route-specific over all-routes, then nearest in time, then highest similarity, then id
        best = sorted(supporting, key=lambda c: (c.note.scope is None, c.gap_days,
                                                 -score[c.note.note_id], c.note.note_id))[0]
        n = best.note
        mag = f" Note cites up to ~{n.max_effect_pct:g}%." if n.max_effect_pct else ""
        reason = (f"Matches note {n.note_id} ({n.date.isoformat()}, {n.applies_to}, covers "
                  f"{n.window_start.isoformat()} to {n.window_end.isoformat()}): "
                  f"\"{first_sentence(n.text)}\". Route is {pct_vs_own:+.1f}% above its own history.{mag}")
        return Verdict("No (justified)", n.note_id, reason, retrieved)

    nearest = sorted(checks, key=lambda c: (c.gap_days, c.note.scope is None, c.note.note_id))[:2]
    detail = "; ".join(_why_rejected(c, week_start, pct_vs_own) for c in nearest)
    reason = f"No supporting note, flagged for review. Nearest notes rejected: {detail}."
    return Verdict("Yes", "", reason, retrieved)
