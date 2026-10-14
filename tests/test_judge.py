from datetime import date

import pytest

from freight_watch.config import Config
from freight_watch.judge import first_sentence, judge
from freight_watch.notes import load_notes
from freight_watch.retrieval import Retriever

CFG = Config()
NOTES = load_notes("data/context_notes.csv", CFG)
INDEX = Retriever({n.note_id: n.text for n in NOTES})


def run(route, week, pct):
    o, d = route.split("-")
    return judge(route, o, d, date.fromisoformat(week), pct, NOTES, INDEX, CFG)


@pytest.mark.parametrize("route,week,pct,note", [
    ("Ahmedabad-Mumbai", "2025-01-20", 30.0, "N002"),
    ("Chennai-Bangalore", "2025-02-24", 31.0, "N001"),
    ("Chennai-Bangalore", "2025-03-03", 23.0, "N001"),
    ("Delhi-Chennai", "2025-05-12", 6.0, "N003"),   # all-routes diesel note, within its stated 5-7%
])
def test_justified_when_note_applies(route, week, pct, note):
    v = run(route, week, pct)
    assert v.flagged == "No (justified)" and v.matched_note_id == note


@pytest.mark.parametrize("route,week,pct", [
    ("Mumbai-Pune", "2025-01-20", 30.0),        # N002 is for Ahmedabad-Mumbai: wrong route
    ("Ahmedabad-Mumbai", "2025-01-13", 30.0),   # week BEFORE the festival note: wrong window
    ("Ahmedabad-Mumbai", "2025-01-27", 30.0),   # week AFTER: wrong window
    ("Chennai-Bangalore", "2025-03-10", 22.0),  # flood window ended Mar 8
    ("Chennai-Bangalore", "2025-03-17", 14.0),  # note says back to normal
    ("Mumbai-Delhi", "2024-07-29", 15.0),       # N005: "costs were not significantly affected"
    ("Kolkata-Bhubaneswar", "2025-06-09", 15.0),  # N008: no disruptions
    ("Mumbai-Pune", "2025-09-15", 9.2),         # only N006 (stable demand) nearby
    ("Delhi-Chennai", "2025-05-12", 20.0),      # diesel note says ~5-7%; 20% is far beyond it
    ("Delhi-Chennai", "2025-09-01", 6.0),       # diesel note long expired
    ("Delhi-Jaipur", "2024-11-11", 35.5),       # nothing nearby at all
])
def test_unexplained_when_no_valid_note(route, week, pct):
    v = run(route, week, pct)
    assert v.flagged == "Yes" and v.matched_note_id == ""


def test_never_cites_a_note_for_another_route():
    for route in ["Mumbai-Pune", "Delhi-Jaipur", "Delhi-Chennai"]:
        v = run(route, "2025-01-20", 30.0)
        assert v.matched_note_id in ("", "N003")  # only an all-routes note could ever apply


def test_justified_reason_quotes_the_notes_first_sentence():
    v = run("Ahmedabad-Mumbai", "2025-01-20", 30.0)
    n = next(n for n in NOTES if n.note_id == "N002")
    assert first_sentence(n.text) in v.reason and n.note_id in v.reason
