import pandas as pd

from freight_watch.config import Config
from freight_watch.pipeline import OUTPUT_COLUMNS, run
from tests.helpers import make_shipments


def test_output_header_matches_sample_contract():
    with open("data/sample_output_format_v2.csv") as f:
        header = f.readline().strip().split(",")
    assert header == OUTPUT_COLUMNS


def test_real_data_is_deterministic(tmp_path):
    a = run("data/shipment_records.csv", "data/context_notes.csv", str(tmp_path / "a"))
    b = run("data/shipment_records.csv", "data/context_notes.csv", str(tmp_path / "b"))
    pd.testing.assert_frame_equal(a, b)
    for f in ["output.csv", "weekly_metrics.csv", "run_log.json"]:
        assert (tmp_path / "a" / f).read_bytes() == (tmp_path / "b" / f).read_bytes()


def test_sample_rows_numbers_are_reproduced(tmp_path):
    out = run("data/shipment_records.csv", "data/context_notes.csv", str(tmp_path))
    r = out[(out.route == "Delhi-Jaipur") & (out.week_of == "2024-11-11")].iloc[0]
    assert r.cost_per_tonne_km == "4.17" and r.vs_own_history.startswith("+35.5%") and r.vs_similar_routes.startswith("+21.0%")
    r = out[(out.route == "Mumbai-Pune") & (out.week_of == "2025-09-15")].iloc[0]
    assert r.vs_own_history.startswith("+9.2%") and r.vs_similar_routes.startswith("+23.6%")


def test_planted_anomaly_on_synthetic_data_is_found_and_diesel_step_is_not(tmp_path):
    """Independent of the real data: flat costs, a +6% all-route step at week 15, a +40% spike on R1 at week 25."""
    spec = []
    for route, rtype, base in [("R1-X", "Short", 2.0), ("R2-X", "Short", 2.2), ("R3-X", "Short", 2.4)]:
        for w in range(30):
            c = base * (1.06 if w >= 15 else 1.0)
            if route == "R1-X" and w == 25:
                c = base * 1.06 * 1.40
            spec.append((route, rtype, w, c))
    make_shipments(spec).to_csv(tmp_path / "s.csv", index=False)
    pd.DataFrame([{"note_id": "N1", "date": "2024-01-01", "applies_to": "All Routes",
                   "note": "Nothing relevant happened."}]).to_csv(tmp_path / "n.csv", index=False)
    out = run(str(tmp_path / "s.csv"), str(tmp_path / "n.csv"), str(tmp_path / "o"), Config())
    assert list(out.route) == ["R1-X"] and list(out.flagged) == ["Yes"]
    assert out.week_of.iloc[0] == (pd.Timestamp("2024-01-01") + pd.Timedelta(weeks=25)).strftime("%Y-%m-%d")
