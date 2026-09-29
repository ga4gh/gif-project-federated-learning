#!/usr/bin/env python3
"""Toy partitions for exercising the plumbing. NOT the experiment's synthetic data.

Writes N CSV partitions with a few numeric features loosely named after variant
annotations and a 0/1 label driven by a simple planted rule, with a per-site shift
so partitions are non-IID. Track A replaces this with the real ClinVar-derived
generator (see the proposal and FedLearnVar).

    make_toy_data.py --out-dir data --sites 3 --n 600 --seed 7
"""
import argparse, os
import numpy as np

FEATURES = ["cadd", "revel", "phylop", "log10_af", "splice_dist"]


def site_data(rng, n, shift):
    cadd = rng.normal(15 + 5 * shift, 8, n).clip(0, 60)
    revel = rng.beta(2, 5, n)
    phylop = rng.normal(1, 2.5, n)
    log10_af = rng.normal(-3.5 - shift, 1.2, n).clip(-7, 0)
    splice = rng.exponential(50, n)
    # planted rule: high CADD, rare, near a splice site => pathogenic
    score = 0.12 * (cadd - 20) - 0.9 * (log10_af + 4) - 0.02 * (splice - 20) + 3 * (revel - 0.3)
    p = 1 / (1 + np.exp(-score))
    label = (rng.random(n) < p).astype(int)
    X = np.column_stack([cadd / 10, revel, phylop / 3, log10_af / 2, splice / 50])
    return X, label


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="data")
    ap.add_argument("--sites", type=int, default=3)
    ap.add_argument("--n", type=int, default=600)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args(argv)
    rng = np.random.default_rng(a.seed)
    os.makedirs(a.out_dir, exist_ok=True)
    for i in range(a.sites):
        shift = (i - (a.sites - 1) / 2) / max(1, a.sites - 1)
        X, y = site_data(rng, a.n, shift)
        path = os.path.join(a.out_dir, f"site{i}.csv")
        np.savetxt(path, np.column_stack([X, y]), delimiter=",", fmt="%.6g",
                   header=",".join(FEATURES + ["label"]), comments="")
        print(path, f"n={len(y)} positives={int(y.sum())}")


if __name__ == "__main__":
    main()
