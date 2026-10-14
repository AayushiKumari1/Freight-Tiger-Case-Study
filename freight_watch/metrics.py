"""Core numeric logic: weekly cost per tonne-km and the two baselines the brief defines."""
from __future__ import annotations

import pandas as pd

REQUIRED_COLUMNS = [
    "shipment_id", "origin", "destination", "route_type",
    "quantity_tonnes", "distance_km", "freight_cost_inr", "shipment_date",
]


def load_shipments(path: str) -> pd.DataFrame:
    """Read shipments, validate them, and add `route` and `week_of` (Monday of the ISO week)."""
    df = pd.read_csv(path)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"shipment file is missing columns: {missing}")

    df["origin"] = df["origin"].str.strip()
    df["destination"] = df["destination"].str.strip()
    df["route_type"] = df["route_type"].str.strip()
    df["route"] = df["origin"] + "-" + df["destination"]
    df["shipment_date"] = pd.to_datetime(df["shipment_date"])

    bad = (df["quantity_tonnes"] <= 0) | (df["distance_km"] <= 0) | (df["freight_cost_inr"] < 0)
    if bad.any():  # cost per tonne-km is undefined for these; drop loudly rather than silently
        print(f"[warn] dropping {int(bad.sum())} rows with non-positive quantity/distance or negative cost")
        df = df[~bad].copy()

    types_per_route = df.groupby("route")["route_type"].nunique()
    if (types_per_route > 1).any():
        raise ValueError(f"routes with more than one route_type: {list(types_per_route[types_per_route > 1].index)}")

    # Weeks run Monday..Sunday; week_of is that week's Monday.
    df["week_of"] = df["shipment_date"] - pd.to_timedelta(df["shipment_date"].dt.weekday, unit="D")
    return df


def weekly_route_costs(shipments: pd.DataFrame) -> pd.DataFrame:
    """Cost per tonne-km per route per week = total cost / total (tonnes x km) that week."""
    s = shipments.assign(tonne_km=shipments["quantity_tonnes"] * shipments["distance_km"])
    weekly = s.groupby(["route", "route_type", "week_of"], as_index=False).agg(
        total_cost=("freight_cost_inr", "sum"),
        tonne_km=("tonne_km", "sum"),
        shipments=("shipment_id", "count"),
    )
    weekly["cost_per_tonne_km"] = weekly["total_cost"] / weekly["tonne_km"]
    return weekly.sort_values(["route", "week_of"]).reset_index(drop=True)


def add_baselines(weekly: pd.DataFrame, history_weeks: int = 8) -> pd.DataFrame:
    """Add the two comparisons exactly as the brief defines them.

    own_avg   : mean weekly cost/tonne-km over the (up to) `history_weeks` calendar weeks strictly
                BEFORE this week. Fewer weeks available -> use what exists (own_weeks says how many).
    peer_avg  : mean cost/tonne-km, same week, over all OTHER routes with the same route_type.
    """
    wide = weekly.pivot(index="week_of", columns="route", values="cost_per_tonne_km")
    wide = wide.reindex(pd.date_range(wide.index.min(), wide.index.max(), freq="7D"))
    wide.index.name = "week_of"

    prior = wide.shift(1)  # shift first => the current week can never leak into its own baseline
    own_avg = prior.rolling(history_weeks, min_periods=1).mean()
    own_weeks = prior.notna().astype(int).rolling(history_weeks, min_periods=1).sum()

    route_type = weekly.drop_duplicates("route").set_index("route")["route_type"]
    peer_avg = pd.DataFrame(float("nan"), index=wide.index, columns=wide.columns)
    peer_n = pd.DataFrame(0, index=wide.index, columns=wide.columns)
    for route in wide.columns:
        mates = [r for r in wide.columns if r != route and route_type[r] == route_type[route]]
        if mates:
            peer_avg[route] = wide[mates].mean(axis=1)
            peer_n[route] = wide[mates].notna().sum(axis=1)

    def _long(frame: pd.DataFrame, name: str) -> pd.DataFrame:
        return frame.reset_index().melt(id_vars="week_of", var_name="route", value_name=name)

    out = weekly
    for frame, name in [(own_avg, "own_avg"), (own_weeks, "own_weeks"), (peer_avg, "peer_avg"), (peer_n, "peer_n")]:
        out = out.merge(_long(frame, name), on=["route", "week_of"], how="left")

    out["pct_vs_own"] = (out["cost_per_tonne_km"] / out["own_avg"] - 1) * 100
    out["pct_vs_peers"] = (out["cost_per_tonne_km"] / out["peer_avg"] - 1) * 100
    return out.sort_values(["route", "week_of"]).reset_index(drop=True)


def flag_candidates(metrics: pd.DataFrame, min_pct_vs_own: float, min_pct_vs_peers: float) -> pd.DataFrame:
    """Rows whose cost is rising vs own history AND out of line with similar routes."""
    mask = (metrics["pct_vs_own"] >= min_pct_vs_own) & (metrics["pct_vs_peers"] >= min_pct_vs_peers)
    return metrics[mask].sort_values(["week_of", "route"]).reset_index(drop=True)
