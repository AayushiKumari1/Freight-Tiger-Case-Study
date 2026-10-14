"""All tunable knobs in one place, so every threshold can be explained in the README."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    # --- baselines (fixed by the case-study brief; do not change) ---
    history_weeks: int = 8  # trailing window for "vs own history"

    # --- flag rule (our choice; calibrated in README, section "Choosing the thresholds") ---
    min_pct_vs_own: float = 7.0     # must be at least this far above own trailing average
    min_pct_vs_peers: float = 15.0  # AND at least this far above same-type peers

    # --- notes layer ---
    note_horizon_weeks: int = 8        # a note counts as "nearby" if its window is within this many weeks
    persistent_note_weeks: int = 8     # an onset note ("starting this week") stays applicable this long
    magnitude_tolerance_pp: float = 3.0  # slack (pct points) over a note's stated upper bound
    top_k: int = 5                     # notes retrieved per flagged row
