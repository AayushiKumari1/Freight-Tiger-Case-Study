# Freight Cost Watch

Flags routes whose cost per tonne-km is rising in a way that does not look justified, and explains each
flag from the notes file - without making anything up.

```
python -m freight_watch                       # writes outputs/output.csv (+ weekly_metrics.csv, run_log.json)
python -m pytest -q                           # 31 unit/integration tests
python eval/run_eval.py                       # scores output against hand-labelled route-weeks + citation audit
bash scripts/repro_check.sh                                         # Linux/macOS/Git Bash: 3 untouched runs, byte-for-byte comparison
powershell -ExecutionPolicy Bypass -File scripts/repro_check.ps1    # Windows: same check
python -m freight_watch.ask "why did Chennai-Bangalore get pricier in March?"   # stretch: Q&A over the findings
```
Needs Python 3.10+ and pandas only (`pip install -r requirements.txt`).

## Result on the supplied data
2,940 shipments -> 728 route-weeks (7 routes x 104 weeks). 13 route-weeks meet the flag rule:
**3 justified** (N002 once, N001 twice) and **10 unexplained** (2 Delhi-Jaipur, 2 Chennai-Bangalore, 6 Mumbai-Pune).
The three example rows in `sample_output_format_v2.csv` are reproduced exactly (same numbers, same verdicts).

Two patterns stand out:
- **Mumbai-Pune is creeping up with no reason on file.** Weekly cost went from 3.41 (2024 average) to 4.42 in Dec 2025
  (+30%). Most routes rose about 5-6% after May 2025, which fits the diesel note (N003); Mumbai-Pune rose 15.5% in
  H2-2025 vs 2024 and its gap to its only same-type peer (Delhi-Jaipur) widened from ~+10% to ~+38%.
  Only 6 of its ~30 recent weeks cross the flag rule because the 8-week rolling baseline slowly "learns" the creep -
  a known limitation of the baseline the brief mandates (see Limitations).
- **Chennai-Bangalore:** the flood note justifies the weeks of 24 Feb and 3 Mar, but not 10 Mar or 17 Mar (see Judgment calls).

## How it works
1. **Weekly cost** (`metrics.py`): group by route (origin-destination) and the supplied `route_type`; week = Monday-Sunday
   (`week_of` = Monday). Cost per tonne-km = total cost / total (tonnes x km) for the week (a weighted ratio, not an
   average of per-shipment ratios).
2. **Baselines, exactly as the brief defines them:**
   *vs own history* = mean of the route's weekly values over the 8 calendar weeks strictly before the current week
   (shifted before rolling, so no look-ahead; fewer than 8 prior weeks -> use those available, no padding; the first
   week of each route has no history and can never be flagged). *vs similar routes* = mean of the *other* routes with
   the same `route_type` in the same week (self excluded).
3. **Flag rule:** `pct_vs_own >= +7%` **and** `pct_vs_peers >= +15%` (`config.py`).
4. **Notes layer** (`notes.py`, `retrieval.py`, `judge.py`), for each flagged row:
   - *Parse* each note into facts: route scope, time window (explicit "from Feb 24 to Mar 8" if stated, otherwise the
     Monday-Sunday week it is dated in; an onset note like "starting this week" applies for 8 weeks), effect
     (cost increase / no cost impact / out of scope), and any stated magnitude ("5-7%").
   - *Retrieve*: metadata filter (right route or "All Routes", within 8 weeks) then TF-IDF ranking, top 5.
   - *Verify* each retrieved note. It justifies a rise only if **all** hold: applies to this route; says costs went
     **up**; its window overlaps this week; and if it states a magnitude, the observed rise is not far beyond it
     (+3 pp tolerance).
   - *Verdict*: a verifying note is cited in `matched_note_id`, and `reason` gives its id, dates and the note's own first sentence
     (exact quote); otherwise the row stays unexplained, `matched_note_id` is blank, and `reason` names the nearest notes
     and why each was rejected (wrong dates, no cost rise described, etc.). Reasons are kept to 1-2 sentences.
   Wording is assembled from the note's own fields, so it cannot invent a cause.

## Choosing the thresholds (`outputs/threshold_sensitivity.txt`)
- In the quiet period (Mar-Oct 2024) week-to-week noise vs own history had std 2-3.7% and never exceeded **6.6%**, so
  +7% sits just above normal noise. The peer test is +15% because some routes are structurally pricier than their peers
  (Mumbai-Pune ~+10%, up to +16.6% in a single quiet week) and we want deviation beyond that.
- Requiring **both** keeps out the May 2025 diesel step (own-history rise ~5-7%, but peers rose too) and the
  structural peer gaps. The count is 13 at the chosen point and 12-14 when the peer threshold moves between 10% and 20%
  or the own-history threshold drops to 6%; raising own-history to 8% drops it to 9, mainly losing Mumbai-Pune's creep
  weeks. These are heuristics I chose, not facts: change them in `config.py`.

## How I convinced myself it is right
1. **Matches the brief's own examples** - the three sample rows reproduce to the digit (test `test_sample_rows_numbers_are_reproduced`).
2. **Hand-computed unit tests** (`tests/test_metrics.py`): baseline excludes the current week, fewer-than-8-weeks case, peers
   exclude self, Sunday/Monday week boundary, weighted ratio.
3. **Adversarial note tests** (`tests/test_judge.py`): wrong route, week before/after a note's window, "costs not affected" notes,
   an expired note, a note whose stated 5-7% cannot explain a 20% rise, a note about routes outside the dataset.
4. **Labelled eval** (`eval/labels.csv`, `eval/run_eval.py`): 22 route-weeks (13 flagged + 9 should-not-be-flagged controls),
   **22/22 correct**, no unlabelled output rows, plus an independent **citation audit** (cited note exists, applies to the
   route, does not say costs were unaffected, and its first sentence appears in the reason).
5. **Synthetic ground truth** (`test_planted_anomaly_on_synthetic_data...`): flat costs + a +6% all-route step + one +40% spike;
   the system flags exactly the spike and nothing else.
6. **Mutation checks:** I deliberately broke the code (leak the current week into the baseline; ignore note windows; ignore
   route scope; accept "no cost impact" notes; drop the magnitude check) and each was caught by the tests or the eval.
   So the checks can fail - they are not decoration.

*Caveat:* labels were written by reading the data and notes, so they check consistency with a careful human reading rather
than a truly independent source. Items 2, 3 and 5 are the independent checks.

## Reproducibility
`scripts/repro_check.sh` (or `scripts/repro_check.ps1` on Windows) runs the pipeline 3 times from scratch with a different
`PYTHONHASHSEED` each time. Result in `outputs/repro_check.txt`: `output.csv`, `weekly_metrics.csv` and `run_log.json` are
**byte-identical** (same SHA-256), including reason text. Nothing is random and no LLM is called (so there is no temperature
to set).

## Cost of running it
0 LLM calls, 0 input tokens, 0 output tokens, $0.00 (details and a sizing for an optional LLM in `COST_LOG.md`).

## Judgment calls and limitations (please read)
- **Chennai-Bangalore, week of 10 Mar is left unexplained.** N001's flood window ends 8 Mar and says roads were passable from 9 Mar;
  N009 (17 Mar) says conditions were back to normal. Costs were still +22% that week, so a human might call it a flood aftermath,
  but no note says so, and the brief says a wrong window counts as fabricated. I chose "couldn't find one".
- **Retrieval is TF-IDF, not an embedding model / vector DB.** With 10 short notes the metadata filter does the real work; TF-IDF
  keeps runs deterministic and free. `Retriever.search()` is the one seam to swap in embeddings if the notes corpus grows.
- **Note parsing is rule-based** (keyword cues). It is transparent and exactly testable, but a note worded unlike these 10 could
  be classed "unclear" - which is treated safely as *not a justification*. An LLM classifier at temperature 0 with a cache is the
  natural upgrade.
- **Thin peer groups:** Short and Long each have only 2 routes, so the "peer average" is a single route; Medium has 3.
- **Slow drift is partly invisible to a trailing-8-week baseline** (Mumbai-Pune), and the peer test cannot separate "this route
  is drifting" from "the single peer improved". The README insight above comes from looking at the longer series.
- The supplied `sample_output_format_v2.csv` has an unquoted comma in its Mumbai-Pune row, so strict CSV parsers misread it.
  My output is properly quoted; the header is identical to the sample's.
- "Rising" is implemented as being >= 7% above the route's own recent average; it does not separately require week-on-week growth.

## Layout
```
freight_watch/  config.py metrics.py notes.py retrieval.py judge.py pipeline.py ask.py __main__.py
tests/          31 tests      eval/  labels.csv run_eval.py
scripts/        repro_check.sh repro_check.ps1 sensitivity.py
data/           inputs        outputs/  output.csv weekly_metrics.csv run_log.json repro_check.txt threshold_sensitivity.txt
```
