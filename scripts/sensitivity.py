"""How many route-weeks get flagged as the two thresholds move? (supports the README's threshold choice)"""
import pandas as pd
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from freight_watch.config import Config
from freight_watch.metrics import add_baselines, load_shipments, weekly_route_costs

m = add_baselines(weekly_route_costs(load_shipments("data/shipment_records.csv")), Config.history_weeks)
stable = m[(m.week_of >= "2024-03-01") & (m.week_of < "2024-11-01")]  # before any planted event
print("Week-to-week noise in the quiet period (Mar-Oct 2024), % vs own history:")
print(f"  std by route: {stable.groupby('route').pct_vs_own.std().round(1).to_dict()}")
print(f"  max across all routes: {stable.pct_vs_own.max():.1f}%   | max gap vs peers by route:")
print(f"  {stable.groupby('route').pct_vs_peers.max().round(1).to_dict()}\n")
rows = []
for own in (5, 6, 7, 8, 10):
    rows.append({"vs_own >=": own, **{f"vs_peers >= {p}": int(((m.pct_vs_own >= own) & (m.pct_vs_peers >= p)).sum())
                                      for p in (10, 15, 20, 25)}})
print("Route-weeks flagged by the rule (of", len(m), "):")
print(pd.DataFrame(rows).to_string(index=False))
