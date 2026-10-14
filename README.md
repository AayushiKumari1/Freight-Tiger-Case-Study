# Freight Cost Watch

A Python tool to identify unusual weekly freight costs, compare routes against historical and peer baselines, and determine whether context notes explain the increase.

## Setup and Run

```bash
pip install -r requirements.txt
python -m freight_watch
```

## Approach

- **Weekly aggregation:** Group shipments by route and week (Monday–Sunday).
- **Cost metric:** Total freight cost divided by total tonne-kilometres.
- **Historical comparison:** Compare against the route's previous eight weeks, using available prior weeks when fewer exist.
- **Peer comparison:** Compare against other routes of the same type in the same week.
- **Anomaly detection:** Flag route-weeks that exceed both configured historical and peer thresholds.
- **Context verification:** Match notes by route, date, and cost impact. Cite a note only when it supports the increase; otherwise, mark it unexplained.

## Output

The pipeline generates `outputs/output.csv` with the required eight columns, including route, week, cost per tonne-km, historical and peer comparisons, flag status, matched note ID, and explanation.

Additional outputs include weekly metrics, run logs, reproducibility results, and threshold sensitivity analysis.

## Evaluation

Run the tests and labelled evaluation:

```bash
python -m pytest -q
python eval/run_eval.py
```

Results on the supplied dataset:

- 2,940 shipments processed into 728 route-weeks.
- 13 route-weeks flagged: 3 justified and 10 unexplained.
- 31 tests passed.
- 22/22 labelled evaluation cases correct.

## Reproducibility and Cost

Run the reproducibility script:

```bash
bash scripts/repro_check.sh
```

On Windows, use:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/repro_check.ps1
```

Three runs produced identical output files and run logs.

The solution uses deterministic Python rules and TF-IDF retrieval, with **zero LLM calls and $0 model cost**. See `COST_LOG.md` for details.

## Project Structure

- `freight_watch/` — Core pipeline and detection logic
- `tests/` — Automated tests
- `eval/` — Labelled evaluation
- `scripts/` — Reproducibility and sensitivity checks
- `data/` — Input data
- `outputs/` — Generated results
- `COST_LOG.md` — Token and cost accounting

## Limitations

Thresholds are configurable heuristics. Small peer groups, gradual cost changes, and ambiguous context notes can affect detection. The system conservatively leaves increases unexplained when the supplied notes do not justify them.
