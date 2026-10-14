"""All tunable knobs in one place, so every threshold can be explained in the README."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
   
    history_weeks: int = 8 

    min_pct_vs_own: float = 7.0 
    min_pct_vs_peers: float = 15.0

    note_horizon_weeks: int = 8     
    persistent_note_weeks: int = 8 
    magnitude_tolerance_pp: float = 3.0 
    top_k: int = 5                
