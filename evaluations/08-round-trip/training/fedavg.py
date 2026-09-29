#!/usr/bin/env python3
"""FedAvg over .npz weight files: weighted average by each site's example count.

    fedavg.py --out global.npz  siteA.npz:1200  siteB.npz:800  [...]

This is the whole aggregation step of plain FedAvg (McMahan et al., 2017).
"""
import argparse, hashlib, io, json
import numpy as np


def fedavg(pairs):
    total = sum(n for _, n in pairs)
    out = None
    for path, n in pairs:
        with np.load(path) as z:
            w = {k: z[k].astype(float) for k in z.files}
        if out is None:
            out = {k: np.zeros_like(v) for k, v in w.items()}
        for k in out:
            out[k] += w[k] * (n / total)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("inputs", nargs="+", help="path:n_examples")
    a = ap.parse_args(argv)
    pairs = []
    for s in a.inputs:
        p, n = s.rsplit(":", 1)
        pairs.append((p, int(n)))
    w = fedavg(pairs)
    buf = io.BytesIO(); np.savez(buf, **w); raw = buf.getvalue()
    with open(a.out, "wb") as f:
        f.write(raw)
    print(json.dumps({"out": a.out, "sha256": hashlib.sha256(raw).hexdigest(), "size": len(raw),
                      "n_total": sum(n for _, n in pairs)}))


if __name__ == "__main__":
    main()
