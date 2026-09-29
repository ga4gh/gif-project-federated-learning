#!/usr/bin/env python3
"""One local training round for the round-trip acceptance test (step A8).

Interface (the contract Tracks A, B and C plug into):

    train_round.py --data-in DATA.csv [--weights-in W.npz] --weights-out W.npz [--metrics-out M.json]
    train_round.py --init --n-features N --weights-out GLOBAL0.npz      # coordinator: initial global model

- DATA.csv: header row, numeric feature columns, and a 0/1 column named "label".
- W.npz: model weights as named NumPy arrays (framework-neutral, easy to FedAvg).
  FedAvg needs every site to start round 1 from the same weights, so the coordinator
  creates them once with --init and distributes them like any other round's weights.
- M.json: n_examples (FedAvg needs it), loss/accuracy before and after training,
  and the sha256 and size of the weights file (DRS registration needs them).

The model is a one-hidden-layer MLP for binary classification, written in NumPy so
the image is small and runs anywhere. It is a stand-in: the real experiment swaps in
PyTorch + Opacus (DP-SGD) behind the same interface.
"""
import argparse, hashlib, io, json, os, sys
import numpy as np


def load_csv(path):
    with open(path) as f:
        header = f.readline().strip().split(",")
    data = np.loadtxt(path, delimiter=",", skiprows=1, ndmin=2)
    if "label" not in header:
        sys.exit(f"{path}: no 'label' column in header {header}")
    li = header.index("label")
    y = data[:, li]
    X = np.delete(data, li, axis=1)
    return X, y, [h for h in header if h != "label"]


def init_weights(n_features, hidden, seed):
    rng = np.random.default_rng(seed)
    return {
        "W1": rng.normal(0, np.sqrt(2.0 / n_features), (n_features, hidden)),
        "b1": np.zeros(hidden),
        "W2": rng.normal(0, np.sqrt(1.0 / hidden), (hidden, 1)),
        "b2": np.zeros(1),
    }


def forward(w, X):
    h = np.maximum(0, X @ w["W1"] + w["b1"])
    z = (h @ w["W2"] + w["b2"]).ravel()
    p = 1 / (1 + np.exp(-np.clip(z, -30, 30)))
    return h, p


def evaluate(w, X, y):
    _, p = forward(w, X)
    eps = 1e-9
    loss = float(-np.mean(y * np.log(p + eps) + (1 - y) * np.log(1 - p + eps)))
    acc = float(np.mean((p >= 0.5) == (y == 1)))
    return loss, acc


def train(w, X, y, epochs, lr, batch, seed):
    rng = np.random.default_rng(seed)
    n = len(y)
    for _ in range(epochs):
        idx = rng.permutation(n)
        for s in range(0, n, batch):
            b = idx[s:s + batch]
            xb, yb = X[b], y[b]
            h, p = forward(w, xb)
            dz = (p - yb)[:, None] / len(b)
            gW2 = h.T @ dz
            gb2 = dz.sum(0)
            dh = (dz @ w["W2"].T) * (h > 0)
            gW1 = xb.T @ dh
            gb1 = dh.sum(0)
            w["W1"] -= lr * gW1; w["b1"] -= lr * gb1
            w["W2"] -= lr * gW2; w["b2"] -= lr * gb2
    return w


def save_npz(w, path):
    buf = io.BytesIO()
    np.savez(buf, **w)
    raw = buf.getvalue()
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "wb") as f:
        f.write(raw)
    return hashlib.sha256(raw).hexdigest(), len(raw)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-in")
    ap.add_argument("--init", action="store_true", help="write initial weights and exit")
    ap.add_argument("--n-features", type=int, help="with --init")
    ap.add_argument("--weights-in")
    ap.add_argument("--weights-out", required=True)
    ap.add_argument("--metrics-out")
    ap.add_argument("--epochs", type=int, default=1)
    ap.add_argument("--lr", type=float, default=0.1)
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--hidden", type=int, default=16)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args(argv)

    if a.init:
        if not a.n_features:
            sys.exit("--init needs --n-features")
        sha, size = save_npz(init_weights(a.n_features, a.hidden, a.seed), a.weights_out)
        print(json.dumps({"weights_sha256": sha, "weights_size": size, "init": True}))
        return
    if not a.data_in:
        sys.exit("--data-in is required")
    X, y, features = load_csv(a.data_in)
    if a.weights_in:
        with np.load(a.weights_in) as z:
            w = {k: z[k].astype(float) for k in z.files}
        if w["W1"].shape[0] != X.shape[1]:
            sys.exit(f"weights expect {w['W1'].shape[0]} features, data has {X.shape[1]}")
    else:
        w = init_weights(X.shape[1], a.hidden, a.seed)

    loss0, acc0 = evaluate(w, X, y)
    w = train(w, X, y, a.epochs, a.lr, a.batch_size, a.seed)
    loss1, acc1 = evaluate(w, X, y)
    sha, size = save_npz(w, a.weights_out)

    metrics = {
        "n_examples": int(len(y)), "n_features": int(X.shape[1]),
        "epochs": a.epochs, "lr": a.lr,
        "loss_before": loss0, "acc_before": acc0, "loss_after": loss1, "acc_after": acc1,
        "weights_sha256": sha, "weights_size": size,
    }
    if a.metrics_out:
        os.makedirs(os.path.dirname(os.path.abspath(a.metrics_out)), exist_ok=True)
        with open(a.metrics_out, "w") as f:
            json.dump(metrics, f, indent=2)
    print(json.dumps(metrics))


if __name__ == "__main__":
    main()
