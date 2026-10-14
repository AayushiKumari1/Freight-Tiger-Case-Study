"""Score output.csv against hand-labelled route-weeks and audit every citation.

    python eval/run_eval.py [outputs/output.csv]      (exit code 1 if anything fails)
"""
import re
import sys

import pandas as pd

out_path = sys.argv[1] if len(sys.argv) > 1 else "outputs/output.csv"
out = pd.read_csv(out_path, keep_default_na=False)
labels = pd.read_csv("eval/labels.csv", keep_default_na=False)
notes = pd.read_csv("data/context_notes.csv").set_index("note_id")
produced = {(r.route, r.week_of): r for r in out.itertuples()}
labelled = {(l.route, l.week_of) for l in labels.itertuples()}

fails, correct = [], 0
for l in labels.itertuples():
    got = produced.get((l.route, l.week_of))
    got_verdict = got.flagged if got else "not_flagged"
    got_note = got.matched_note_id if got else ""
    ok = got_verdict == l.expected and got_note == l.expected_note_id
    correct += ok
    if not ok:
        fails.append(f"  MISMATCH {l.route} {l.week_of}: expected {l.expected}/{l.expected_note_id or '-'} "
                     f"got {got_verdict}/{got_note or '-'}")

# anything the system flagged that we never labelled = potential false positive to review by hand
extra = sorted(set(produced) - labelled)
for k in extra:
    fails.append(f"  UNLABELLED OUTPUT ROW {k} -> {produced[k].flagged}")

# citation audit: every justified row must cite an existing note that applies to the route and says costs rose
NEG = ("not significantly", "no significant", "without a rate", "returned to normal", "remained stable", "not part of")
for r in out.itertuples():
    if r.flagged == "No (justified)":
        n = notes.loc[r.matched_note_id] if r.matched_note_id in notes.index else None
        if n is None:
            fails.append(f"  AUDIT {r.route} {r.week_of}: cites unknown note {r.matched_note_id}")
            continue
        if n.applies_to not in (r.route, "All Routes"):
            fails.append(f"  AUDIT {r.route} {r.week_of}: note {r.matched_note_id} is for {n.applies_to}")
        if any(c in n.note.lower() for c in NEG):
            fails.append(f"  AUDIT {r.route} {r.week_of}: note {r.matched_note_id} says costs were not affected")
        if n.note.split(". ")[0].rstrip(".") not in r.reason:
            fails.append(f"  AUDIT {r.route} {r.week_of}: reason does not quote the cited note")
    elif r.matched_note_id:
        fails.append(f"  AUDIT {r.route} {r.week_of}: unexplained row has a note id")

total = len(labels)
print(f"labelled route-weeks correct: {correct}/{total}")
print(f"output rows: {len(out)} | justified: {(out.flagged == 'No (justified)').sum()} | "
      f"unexplained: {(out.flagged == 'Yes').sum()} | unlabelled rows: {len(extra)}")
print("PASS" if not fails else "FAIL\n" + "\n".join(fails))
sys.exit(1 if fails else 0)
