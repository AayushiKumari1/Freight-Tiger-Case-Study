import pandas as pd


def make_shipments(spec):
    """spec: list of (route 'A-B', route_type, week_index, cost_per_tonne_km). One 10t x 100km shipment each."""
    rows = []
    base = pd.Timestamp("2024-01-01")  # a Monday
    for i, (route, rtype, wk, cpk) in enumerate(spec):
        o, d = route.split("-")
        rows.append({"shipment_id": f"S{i}", "origin": o, "destination": d, "route_type": rtype,
                     "material": "x", "quantity_tonnes": 10.0, "distance_km": 100.0,
                     "freight_cost_inr": cpk * 1000.0,
                     "shipment_date": (base + pd.Timedelta(weeks=wk, days=2)).strftime("%Y-%m-%d"),
                     "transporter": "t"})
    return pd.DataFrame(rows)
