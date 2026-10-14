from datetime import date

from freight_watch.config import Config
from freight_watch.notes import load_notes

NOTES = {n.note_id: n for n in load_notes("data/context_notes.csv", Config())}


def test_effect_classification_of_every_given_note():
    expected = {"N001": "cost_increase", "N002": "cost_increase", "N003": "cost_increase",
                "N004": "out_of_scope", "N005": "no_cost_impact", "N006": "no_cost_impact",
                "N007": "no_cost_impact", "N008": "no_cost_impact", "N009": "no_cost_impact",
                "N010": "no_cost_impact"}
    assert {k: v.effect for k, v in NOTES.items()} == expected


def test_explicit_date_range_is_parsed():
    n = NOTES["N001"]
    assert (n.window_start, n.window_end) == (date(2025, 2, 24), date(2025, 3, 8))


def test_point_in_time_note_covers_its_own_week():
    n = NOTES["N002"]
    assert (n.window_start, n.window_end) == (date(2025, 1, 20), date(2025, 1, 26))


def test_onset_note_is_bounded_and_has_magnitude():
    n = NOTES["N003"]
    assert n.window_start == date(2025, 5, 5) and n.window_end == date(2025, 6, 29)
    assert n.max_effect_pct == 7.0 and n.scope is None


def test_route_scope():
    assert NOTES["N001"].scope == "Chennai-Bangalore" and NOTES["N006"].scope is None
