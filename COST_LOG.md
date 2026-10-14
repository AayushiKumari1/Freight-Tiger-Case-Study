# Token / cost log - one full run over the entire shipment file

| Item | Value |
|---|---|
| LLM calls | **0** |
| Total input tokens | **0** |
| Total output tokens | **0** |
| Cost at published rates | **$0.00** |
| Retriever | in-process TF-IDF (no model download, no network) |
| Wall-clock for a full run | ~0.1 s (2,940 shipments, 728 route-weeks, 13 flagged rows) |

**Why zero:** the verdict (justified / unexplained), the cited note id, and every number are produced by
deterministic rules over 10 short notes, and the explanation text is assembled from the note's own fields and
quoted text. A language model would add cost and randomness without improving a verdict that must be exact
and repeatable. `outputs/run_log.json` records `llm_calls: 0` for every run.

**If an LLM is added later** (e.g. to phrase explanations), the budget is small: at most one call per *flagged*
row (13 rows), roughly 400 input + 120 output tokens each, i.e. about 5k input / 1.6k output tokens per full
run - pennies on any hosted model, or free on a local open-source model run at temperature 0. The cited
note and verdict would still come from the rules, so the model could not change them.
