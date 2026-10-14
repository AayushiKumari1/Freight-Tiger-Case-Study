# Freight Cost Watch

A Python-based tool to detect unusual weekly freight costs, compare historical and peer costs, and verify whether context notes explain the increase.

## Setup and Execution

```bash
pip install -r requirements.txt
python -m freight_watch
```

## Approach

- **Weekly aggregation:** Group shipment records by route and Monday–Sunday week.
- **Cost calculation:** Total freight cost divided by total tonne-kilometres.
- **Historical baseline:** Compare against the route's previous eight weeks, using available prior weeks when fewer exist.
- **Peer baseline:** Compare against other routes of the same type in the same week.
- **Anomaly detection:** Flag route-weeks exceeding both configured historical and peer thresholds.
- **Context verification:** Match notes by route, date, and cost impact. Cite supporting notes only when justified; otherwise, mark the increase unexplained.

## Output

The pipeline generates `outputs/output.csv` using the required eight-column format, including cost metrics, comparisons, flag status, matched note ID, and explanation.

## Evaluation

Run the automated tests and labelled evaluation:

```bash
python -m pytest -q
python eval/run_eval.py
```

Results on the supplied dataset:

- 2,940 shipments processed into 728 route-weeks.
- 13 route-weeks flagged: 3 justified and 10 unexplained.
- 31 tests passed.
- 22/22 labelled evaluation cases correct.

## Reproducibility

Run the reproducibility check:

```bash
bash scripts/repro_check.sh
```

On Windows:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/repro_check.ps1
```

Three runs produced byte-identical output files and run logs.

## Token and Cost Log

The solution uses deterministic Python rules and TF-IDF retrieval, with **zero LLM calls and $0 model cost**. Detailed accounting is provided in `COST_LOG.md`.
