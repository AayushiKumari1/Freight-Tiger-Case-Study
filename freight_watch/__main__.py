import argparse
import time

from .config import Config
from .pipeline import run


def main() -> None:
    p = argparse.ArgumentParser(description="Flag unjustified freight cost rises.")
    p.add_argument("--shipments", default="data/shipment_records.csv")
    p.add_argument("--notes", default="data/context_notes.csv")
    p.add_argument("--out", default="outputs")
    a = p.parse_args()
    t0 = time.perf_counter()
    out = run(a.shipments, a.notes, a.out, Config())
    print(f"wrote {len(out)} rows to {a.out}/output.csv in {time.perf_counter() - t0:.2f}s")
    print(out["flagged"].value_counts().to_string())


if __name__ == "__main__":
    main()
