"""End-to-end run: shipments + notes -> output.csv (+ weekly_metrics.csv, run_log.json)."""
from __future__ import annotations

import hashlib
import json
import os

import pandas as pd

from .config import Config
from .judge import judge
from .metrics import add_baselines, flag_candidates, load_shipments, weekly_route_costs
from .notes import load_notes
from .retrieval import Retriever

OUTPUT_COLUMNS = ["route", "week_of", "cost_per_tonne_km", "vs_own_history",
                  "vs_similar_routes", "flagged", "matched_note_id", "reason"]


def _sha256(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def run(shipments_path: str, notes_path: str, out_dir: str, cfg: Config = Config()) -> pd.DataFrame:
    os.makedirs(out_dir, exist_ok=True)

    shipments = load_shipments(shipments_path)
    metrics = add_baselines(weekly_route_costs(shipments), cfg.history_weeks)
    candidates = flag_candidates(metrics, cfg.min_pct_vs_own, cfg.min_pct_vs_peers)

    notes = load_notes(notes_path, cfg)
    index = Retriever({n.note_id: n.text for n in notes})
    ends = shipments.drop_duplicates("route").set_index("route")[["origin", "destination"]]

    rows, audit = [], []
    for r in candidates.itertuples(index=False):
        v = judge(r.route, ends.at[r.route, "origin"], ends.at[r.route, "destination"],
                  r.week_of.date(), float(r.pct_vs_own), notes, index, cfg)
        rows.append({
            "route": r.route,
            "week_of": r.week_of.date().isoformat(),
            "cost_per_tonne_km": f"{r.cost_per_tonne_km:.2f}",
            "vs_own_history": f"{r.pct_vs_own:+.1f}% vs this route's past average",
            "vs_similar_routes": f"{r.pct_vs_peers:+.1f}% vs similar-length routes this week",
            "flagged": v.flagged,
            "matched_note_id": v.matched_note_id,
            "reason": v.reason,
        })
        audit.append({"route": r.route, "week_of": r.week_of.date().isoformat(),
                      "retrieved_notes": list(v.retrieved)})

    out = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    out.to_csv(os.path.join(out_dir, "output.csv"), index=False)

    # Full weekly table (every route-week) for transparency and for the Q&A helper.
    full = metrics.copy()
    full["week_of"] = full["week_of"].dt.date.astype(str)
    full = full[["route", "route_type", "week_of", "shipments", "total_cost", "tonne_km", "cost_per_tonne_km",
                 "own_avg", "own_weeks", "peer_avg", "peer_n", "pct_vs_own", "pct_vs_peers"]]
    full.round(4).to_csv(os.path.join(out_dir, "weekly_metrics.csv"), index=False)

    # Deterministic run log (no timestamps) so repeated runs are byte-identical. No LLM is used.
    log = {
        "llm_calls": 0, "input_tokens": 0, "output_tokens": 0, "estimated_cost_usd": 0.0,
        "retriever": "in-process TF-IDF (no model, no network)",
        "route_weeks_total": int(len(metrics)), "route_weeks_flagged_by_rule": int(len(candidates)),
        "verdicts": out["flagged"].value_counts().to_dict(),
        "config": cfg.__dict__,
        "input_sha256": {"shipments": _sha256(shipments_path), "notes": _sha256(notes_path)},
        "retrieval_audit": audit,
    }
    with open(os.path.join(out_dir, "run_log.json"), "w") as f:
        json.dump(log, f, indent=2, sort_keys=True)
    return out
