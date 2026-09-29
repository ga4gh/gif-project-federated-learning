#!/usr/bin/env python3
"""Round-trip acceptance test for a GA4GH node-in-a-box (steps A2-A8).

Runs one Pattern A training round through a site using DRS and TES, and records
every step as PASS, GLUE (worked, but only with code the APIs don't cover), FAIL,
or SKIP. See ../README.md for what each step stands in for.

Configuration comes from environment variables (defaults match ../docker-compose.yml
and ../config/funnel.yaml):

  DRS_URL=http://localhost:8080   DRS_USER=drs-user   DRS_PASSWORD=drs-pass
  TES_URL=http://localhost:8000
  S3_ENDPOINT=http://localhost:9000  S3_KEY=minio-user  S3_SECRET=minio-pass  S3_BUCKET=fl-eval
  TRAIN_IMAGE=fl-train:dev

Usage:
  python roundtrip.py                 # full run with the training image (A2-A8)
  python roundtrip.py --hello         # plumbing only: alpine copies weights (skips A8)
  python roundtrip.py --skip-a4a      # don't try drs:// inputs directly
"""
import argparse
import datetime as dt
import io
import json
import os
import sys
import time
import traceback
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "training"))

from ga4gh_client import DRS, TES, HTTPError, download, sha256_bytes  # noqa: E402

try:
    import boto3
    from botocore.config import Config as BotoConfig
except ImportError:
    sys.exit("boto3 is required: pip install -r requirements.txt")


# --------------------------------------------------------------------------- helpers

class Results:
    def __init__(self, run_id):
        self.run_id = run_id
        self.steps = []
        self.glue = []
        self.info = {}

    def add(self, step, name, status, variant="", notes="", seconds=None):
        self.steps.append(dict(step=step, name=name, status=status, variant=variant,
                               notes=notes, seconds=None if seconds is None else round(seconds, 2)))
        mark = {"PASS": "✅", "GLUE": "🟡", "FAIL": "❌", "SKIP": "⏭️", "MANUAL": "📝"}.get(status, "")
        print(f"{mark} {step:<4} {status:<6} {name}" + (f" [{variant}]" if variant else ""))
        if notes:
            for line in notes.splitlines():
                print(f"          {line}")

    def add_glue(self, text):
        if text not in self.glue:
            self.glue.append(text)

    def to_markdown(self):
        lines = [f"### Round-trip run `{self.run_id}`", ""]
        for k, v in self.info.items():
            lines.append(f"- **{k}:** {v}")
        lines += ["", "| Step | Result | Variant | Seconds | Notes |", "|---|---|---|---|---|"]
        for s in self.steps:
            notes = s["notes"].replace("\n", "<br>").replace("|", "\\|")
            lines.append(f"| {s['step']} {s['name']} | {s['status']} | {s['variant']} | "
                         f"{'' if s['seconds'] is None else s['seconds']} | {notes} |")
        lines += ["", "**Glue we had to write (candidate API gaps):**", ""]
        lines += [f"{i}. {g}" for i, g in enumerate(self.glue, 1)] or ["(none)"]
        return "\n".join(lines) + "\n"


class Storage:
    """Direct object-storage access. Everything done here is outside GA4GH APIs."""

    def __init__(self, endpoint, key, secret, bucket):
        self.bucket = bucket
        self.s3 = boto3.client("s3", endpoint_url=endpoint, aws_access_key_id=key,
                               aws_secret_access_key=secret, region_name="us-east-1",
                               config=BotoConfig(s3={"addressing_style": "path"}))

    def url(self, key):
        return f"s3://{self.bucket}/{key}"

    def put(self, key, raw):
        self.s3.put_object(Bucket=self.bucket, Key=key, Body=raw)
        return self.url(key)

    def get(self, key):
        return self.s3.get_object(Bucket=self.bucket, Key=key)["Body"].read()

    def size(self, key):
        return self.s3.head_object(Bucket=self.bucket, Key=key)["ContentLength"]


def toy_partition_csv(seed=7, n=600):
    import numpy as np
    import make_toy_data as mtd
    rng = np.random.default_rng(seed)
    X, y = mtd.site_data(rng, n, 0.0)
    buf = io.StringIO()
    np.savetxt(buf, np.column_stack([X, y]), delimiter=",", fmt="%.6g",
               header=",".join(mtd.FEATURES + ["label"]), comments="")
    return buf.getvalue().encode(), len(mtd.FEATURES)


def initial_weights(n_features):
    import train_round
    w = train_round.init_weights(n_features, 16, 0)
    import numpy as np
    buf = io.BytesIO()
    np.savez(buf, **w)
    return buf.getvalue()


def drs_uri(drs_url, obj):
    """A hostname-based DRS URI for the object (drs://host/id)."""
    self_uri = obj.get("self_uri", "")
    if self_uri.startswith("drs://") and "/" in self_uri[len("drs://"):]:
        return self_uri, None
    host = urllib.parse.urlparse(drs_url).netloc
    note = (f"server returned self_uri {self_uri!r} without a hostname; "
            f"built drs://{host}/{obj['id']} instead") if self_uri else None
    return f"drs://{host}/{obj['id']}", note


def task_log_excerpt(task):
    parts = []
    for log in task.get("logs") or []:
        for sl in log.get("system_logs") or []:
            parts.append(sl)
        for el in log.get("logs") or []:
            if el.get("stderr"):
                parts.append("stderr: " + el["stderr"])
    text = "\n".join(parts).strip()
    return text[-600:] if text else "(no system or executor logs)"


# --------------------------------------------------------------------------- steps

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hello", action="store_true", help="use alpine to copy weights instead of training")
    ap.add_argument("--skip-a4a", action="store_true", help="skip trying drs:// URIs as TES inputs")
    ap.add_argument("--timeout", type=int, default=600, help="seconds to wait for each TES task")
    ap.add_argument("--a4a-timeout", type=int, default=120)
    ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--out-dir", default=os.path.join(HERE, "..", "results"))
    a = ap.parse_args(argv)

    env = os.environ.get
    drs_url = env("DRS_URL", "http://localhost:8080")
    tes_url = env("TES_URL", "http://localhost:8000")
    image = env("TRAIN_IMAGE", "fl-train:dev")
    run_id = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    prefix = f"roundtrip/{run_id}"

    drs = DRS(drs_url, env("DRS_USER", "drs-user"), env("DRS_PASSWORD", "drs-pass"))
    tes = TES(tes_url, env("TES_TOKEN"))
    st = Storage(env("S3_ENDPOINT", "http://localhost:9000"), env("S3_KEY", "minio-user"),
                 env("S3_SECRET", "minio-pass"), env("S3_BUCKET", "fl-eval"))
    R = Results(run_id)
    R.info.update({"DRS": drs_url, "TES": tes_url, "image": "alpine (hello mode)" if a.hello else image})

    # ---- preflight
    try:
        si = drs.service_info()
        drs_block = si.get("drs") or {}
        R.info["DRS service-info"] = (f"{si.get('type', {}).get('artifact', '?')} "
                                      f"{si.get('type', {}).get('version', '?')}, "
                                      f"objectRegistrationSupported={drs_block.get('objectRegistrationSupported')}, "
                                      f"uploadRequestSupported={drs_block.get('uploadRequestSupported')}")
    except Exception as e:
        R.add("pre", "DRS service-info", "FAIL", notes=str(e))
        return finish(R, a)
    try:
        ti = tes.service_info()
        R.info["TES service-info"] = f"{ti.get('type', {}).get('artifact', '?')} {ti.get('type', {}).get('version', '?')}"
    except Exception as e:
        R.add("pre", "TES service-info", "FAIL", notes=str(e))
        return finish(R, a)

    R.add("A1", "bring up node", "MANUAL", notes="Timed by hand; record minutes from clean clone in FINDINGS.md")

    # ---- A2 / A3: put inputs in storage and register them in DRS
    def put_and_register(step, name, key, raw, desc):
        t0 = time.time()
        sha, size = sha256_bytes(raw), len(raw)
        notes = []
        try:
            drs.upload_request(os.path.basename(key), size, sha)
            notes.append("DRS /upload-request answered, but this test still writes to storage directly")
        except HTTPError as e:
            notes.append(f"DRS /upload-request not usable (HTTP {e.status}); wrote to storage directly")
            R.add_glue("Getting bytes into storage: the DRS /upload-request path was not usable with this "
                       "implementation, so inputs were written with an S3 client and then registered.")
        url = st.put(key, raw)
        try:
            obj = drs.register(os.path.basename(key), size, sha, url, description=desc)
        except HTTPError as e:
            R.add(step, name, "FAIL", notes=f"register failed: {e}", seconds=time.time() - t0)
            return None
        uri, uri_note = drs_uri(drs_url, obj)
        if uri_note:
            notes.append(uri_note)
            R.add_glue("DRS URIs: the server's self_uri has no hostname (drs://<id>), so the test built "
                       "hostname-based URIs (drs://<host>/<id>) itself.")
        notes.append(f"{uri}  ({size} bytes)")
        R.add(step, name, "GLUE", notes="\n".join(notes), seconds=time.time() - t0)
        obj["_uri"] = uri
        return obj

    data_raw, n_features = toy_partition_csv()
    data_obj = put_and_register("A2", "register input partition", f"{prefix}/in/site0.csv", data_raw,
                                "round-trip test: toy partition")
    w_obj = put_and_register("A3", "register global weights", f"{prefix}/in/global0.npz",
                             initial_weights(n_features), "round-trip test: initial global weights")
    if not data_obj or not w_obj:
        return finish(R, a)

    out_key = f"{prefix}/out/weights.npz"
    met_key = f"{prefix}/out/metrics.json"

    def task_body(variant, data_url, w_url):
        if a.hello:
            cmd = ["sh", "-c",
                   "mkdir -p /out && cp /in/weights.npz /out/weights.npz && "
                   "s=$(sha256sum /out/weights.npz | cut -d' ' -f1) && z=$(stat -c %s /out/weights.npz) && "
                   "n=$(($(wc -l < /in/data.csv)-1)) && "
                   "echo \"{\\\"weights_sha256\\\":\\\"$s\\\",\\\"weights_size\\\":$z,\\\"n_examples\\\":$n}\" "
                   "> /out/metrics.json"]
            img = "alpine"
        else:
            cmd = ["python", "/app/train_round.py", "--data-in", "/in/data.csv", "--weights-in",
                   "/in/weights.npz", "--weights-out", "/out/weights.npz", "--metrics-out",
                   "/out/metrics.json", "--epochs", str(a.epochs)]
            img = image
        return {
            "name": f"fl-roundtrip-{run_id}-{variant}",
            "inputs": [{"name": "data", "url": data_url, "path": "/in/data.csv", "type": "FILE"},
                       {"name": "weights", "url": w_url, "path": "/in/weights.npz", "type": "FILE"}],
            "outputs": [{"name": "weights_out", "url": st.url(out_key), "path": "/out/weights.npz", "type": "FILE"},
                        {"name": "metrics", "url": st.url(met_key), "path": "/out/metrics.json", "type": "FILE"}],
            "executors": [{"image": img, "command": cmd}],
            "tags": {"experiment": "gif-fl-exp1", "test": "roundtrip", "variant": variant},
        }

    # ---- A4a: DRS URIs straight into TES
    if a.skip_a4a:
        R.add("A4", "submit task with drs:// inputs", "SKIP", "a")
    else:
        t0 = time.time()
        try:
            tid = tes.create(task_body("a4a", data_obj["_uri"], w_obj["_uri"]))
            t = tes.wait(tid, timeout=a.a4a_timeout)
            if t.get("state") == "COMPLETE":
                R.add("A4", "submit task with drs:// inputs", "PASS", "a",
                      notes=f"task {tid}: TES resolved DRS URIs itself", seconds=time.time() - t0)
            else:
                R.add("A4", "submit task with drs:// inputs", "FAIL", "a",
                      notes=f"task {tid} ended {t.get('state')}\n{task_log_excerpt(t)}", seconds=time.time() - t0)
                R.add_glue("TES inputs and DRS: the TES implementation could not take drs:// URIs as task "
                           "inputs, so the coordinator resolved each object to a signed URL first. TES does "
                           "not say how DRS URIs in inputs should be handled.")
        except HTTPError as e:
            R.add("A4", "submit task with drs:// inputs", "FAIL", "a", notes=f"rejected at submission: {e}",
                  seconds=time.time() - t0)
            R.add_glue("TES inputs and DRS: the TES server rejected drs:// input URLs at submission.")

    # ---- A4b: resolve to signed URLs, then submit
    t0 = time.time()
    try:
        d_url, d_hdr, _ = drs.access_url(data_obj["id"])
        w_url, w_hdr, _ = drs.access_url(w_obj["id"])
        notes = ["resolved both objects to signed URLs via DRS access endpoints"]
        if d_hdr or w_hdr:
            notes.append("access URLs require headers; TES inputs have no field to carry them")
            R.add_glue("Access URL headers: DRS can return headers that must accompany the URL, but TES "
                       "inputs carry only a URL.")
        R.add_glue("Signed-URL lifetime: URLs resolved at submission must outlive queueing and staging; "
                   "nothing in TES or DRS coordinates that.")
        tid = tes.create(task_body("a4b", d_url, w_url))
        R.add("A4", "submit task with resolved access URLs", "GLUE", "b", notes="\n".join(notes) + f"\ntask {tid}",
              seconds=time.time() - t0)
    except Exception as e:
        R.add("A4", "submit task with resolved access URLs", "FAIL", "b", notes=str(e), seconds=time.time() - t0)
        return finish(R, a)

    # ---- A5: task runs, writes outputs to storage
    t0 = time.time()
    t = tes.wait(tid, timeout=a.timeout)
    if t.get("state") != "COMPLETE":
        R.add("A5", "task reads inputs, writes outputs", "FAIL",
              notes=f"task {tid} ended {t.get('state')}\n{task_log_excerpt(t)}", seconds=time.time() - t0)
        return finish(R, a)
    out_logs = [o for log in t.get("logs") or [] for o in (log.get("outputs") or [])]
    has_checksum = any(k for o in out_logs for k in o if "checksum" in k.lower() or "sha" in k.lower())
    notes = [f"task {tid} COMPLETE",
             f"TES output logs: {len(out_logs)} entries, fields: "
             f"{sorted({k for o in out_logs for k in o}) or 'none'}"]
    if not has_checksum:
        R.add_glue("Output checksums: TES output logs don't carry checksums, and DRS registration requires "
                   "one, so the task wrote a sidecar metrics.json with the sha256 and the coordinator read "
                   "it from storage.")
    R.add("A5", "task reads inputs, writes outputs", "PASS", notes="\n".join(notes), seconds=time.time() - t0)

    # ---- A6a: registration from inside the task (not automated)
    R.add("A6", "task registers its own output", "SKIP", "a",
          notes="Not automated: needs DRS and storage credentials inside the task container, and TES has "
                "no standard way to pass secrets. Try by hand if time allows.")

    # ---- A6b: coordinator registers the output after the task completes
    t0 = time.time()
    try:
        metrics = json.loads(st.get(met_key))
        sha, size = metrics["weights_sha256"], int(metrics["weights_size"])
        actual = st.size(out_key)
        if actual != size:
            raise RuntimeError(f"size mismatch: metrics say {size}, storage has {actual}")
        new_obj = drs.register("weights.npz", size, sha, st.url(out_key),
                               description=f"round-trip test: updated weights (n_examples={metrics.get('n_examples')})")
        new_uri, uri_note = drs_uri(drs_url, new_obj)
        R.add("A6", "coordinator registers output", "GLUE", "b",
              notes=f"read sha256/size from task sidecar in storage, then POST /objects/register\n{new_uri}",
              seconds=time.time() - t0)
        R.add_glue("Linking TES outputs to DRS: nothing connects a TES output URL to a DRS object; the "
                   "coordinator had to register it after the task finished.")
    except Exception as e:
        R.add("A6", "coordinator registers output", "FAIL", "b", notes=str(e), seconds=time.time() - t0)
        return finish(R, a)

    # ---- A7: resolve the new object and verify
    t0 = time.time()
    try:
        url, hdr, _ = drs.access_url(new_obj["id"])
        raw = download(url, hdr)
        ok = sha256_bytes(raw) == sha
        R.add("A7", "resolve new DRS object and verify", "PASS" if ok else "FAIL",
              notes=f"downloaded {len(raw)} bytes; sha256 {'matches' if ok else 'DOES NOT match'}",
              seconds=time.time() - t0)
    except Exception as e:
        R.add("A7", "resolve new DRS object and verify", "FAIL", notes=str(e), seconds=time.time() - t0)

    # ---- A8: was it a real training step?
    if a.hello:
        R.add("A8", "real training step", "SKIP", notes="--hello mode")
    else:
        lb, la = metrics.get("loss_before"), metrics.get("loss_after")
        good = lb is not None and la is not None and la < lb
        R.add("A8", "real training step", "PASS" if good else "FAIL",
              notes=f"n_examples={metrics.get('n_examples')}, loss {lb:.4f} -> {la:.4f}, "
                    f"acc {metrics.get('acc_before'):.3f} -> {metrics.get('acc_after'):.3f}"
              if good else f"metrics: {metrics}")
    return finish(R, a)


def finish(R, a):
    os.makedirs(a.out_dir, exist_ok=True)
    base = os.path.join(a.out_dir, R.run_id)
    with open(base + ".json", "w") as f:
        json.dump({"run_id": R.run_id, "info": R.info, "steps": R.steps, "glue": R.glue}, f, indent=2)
    with open(base + ".md", "w") as f:
        f.write(R.to_markdown())
    print("\nGlue (candidate API gaps):")
    for i, g in enumerate(R.glue, 1):
        print(f"  {i}. {g}")
    print(f"\nWrote {base}.md (paste into FINDINGS.md) and {base}.json")
    failed = any(s["status"] == "FAIL" and s["variant"] != "a" for s in R.steps)
    return 1 if failed else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception:
        traceback.print_exc()
        sys.exit(2)
