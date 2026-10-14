import pandas as pd

from freight_watch.metrics import add_baselines, load_shipments, weekly_route_costs
from tests.helpers import make_shipments


def _metrics(spec, tmp_path):
    p = tmp_path / "s.csv"
    make_shipments(spec).to_csv(p, index=False)
    return add_baselines(weekly_route_costs(load_shipments(str(p))), 8)


def _spec():
    spec = [("A-B", "Short", w, 2.0 if w < 9 else 3.0) for w in range(10)]
    spec += [("C-D", "Short", w, 2.5) for w in range(10)]
    spec += [("E-F", "Long", w, 1.0) for w in range(10)]
    return spec


def test_hand_computed_baselines(tmp_path):
    m = _metrics(_spec(), tmp_path)
    row = m[(m.route == "A-B") & (m.week_of == "2024-03-04")].iloc[0]  # week index 9
    assert abs(row.own_avg - 2.0) < 1e-9          # mean of the 8 weeks BEFORE this one (current week excluded)
    assert abs(row.pct_vs_own - 50.0) < 1e-9
    assert abs(row.peer_avg - 2.5) < 1e-9         # only C-D (A-B excludes itself)
    assert abs(row.pct_vs_peers - 20.0) < 1e-9


def test_fewer_than_eight_prior_weeks_uses_what_exists(tmp_path):
    m = _metrics(_spec(), tmp_path)
    first = m[(m.route == "A-B")].sort_values("week_of").iloc[0]
    third = m[(m.route == "A-B")].sort_values("week_of").iloc[2]
    assert pd.isna(first.own_avg) and first.own_weeks == 0
    assert third.own_weeks == 2 and abs(third.own_avg - 2.0) < 1e-9


def test_no_peers_gives_nan(tmp_path):
    m = _metrics(_spec(), tmp_path)
    assert m[m.route == "E-F"].peer_avg.isna().all()  # only Long route in the toy data


def test_week_boundaries_monday_to_sunday(tmp_path):
    spec = [("A-B", "Short", 0, 2.0)]
    df = make_shipments(spec)
    df = pd.concat([df.assign(shipment_date="2024-01-07"),   # Sunday -> belongs to week of 01-01
                    df.assign(shipment_date="2024-01-08", shipment_id="S9")])  # Monday -> next week
    p = tmp_path / "s.csv"
    df.to_csv(p, index=False)
    s = load_shipments(str(p))
    assert sorted(s.week_of.dt.strftime("%Y-%m-%d").unique()) == ["2024-01-01", "2024-01-08"]


def test_cost_is_weighted_total_not_average_of_ratios(tmp_path):
    df = make_shipments([("A-B", "Short", 0, 1.0), ("A-B", "Short", 0, 1.0)])
    df.loc[1, ["quantity_tonnes", "freight_cost_inr"]] = [30.0, 6000.0]  # 30t*100km, cost 6000 -> 2.0/tkm
    p = tmp_path / "s.csv"
    df.to_csv(p, index=False)
    w = weekly_route_costs(load_shipments(str(p)))
    assert abs(w.cost_per_tonne_km.iloc[0] - (1000 + 6000) / (1000 + 3000)) < 1e-9
