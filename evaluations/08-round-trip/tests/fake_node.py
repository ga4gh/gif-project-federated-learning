#!/usr/bin/env python3
"""Fake DRS + TES servers for testing roundtrip.py without Docker.

NOT an evaluation of anything: this exists so the test script's logic can be
checked on a machine with no containers. It mimics the behaviors we observed in
Syfon and Funnel source code (DRS: register supported, upload-request rejected,
self_uri without hostname; TES: no drs:// input support), runs task commands as
local processes, and uses an S3 endpoint (e.g., moto_server) for storage.

    moto_server -p 9000 &
    python tests/fake_node.py            # DRS on :8080, TES on :8000
"""
import base64, hashlib, json, os, re, shutil, subprocess, sys, tempfile, threading, urllib.request, uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import boto3
from botocore.config import Config

S3 = boto3.client("s3", endpoint_url=os.environ.get("S3_ENDPOINT", "http://localhost:9000"),
                  aws_access_key_id="minio-user", aws_secret_access_key="minio-pass", region_name="us-east-1",
                  config=Config(s3={"addressing_style": "path"}))
BUCKET = os.environ.get("S3_BUCKET", "fl-eval")
TRAINING = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "training")
AUTH = "Basic " + base64.b64encode(b"drs-user:drs-pass").decode()
OBJECTS, TASKS = {}, {}


class Base(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, body):
        raw = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n)) if n else {}


class DRSHandler(Base):
    P = "/ga4gh/drs/v1"

    def authed(self):
        if self.headers.get("Authorization") != AUTH:
            self.send(401, {"msg": "unauthorized"})
            return False
        return True

    def do_GET(self):
        if not self.authed():
            return
        if self.path == f"{self.P}/service-info":
            return self.send(200, {"type": {"group": "org.ga4gh", "artifact": "drs", "version": "1.5.0"},
                                   "drs": {"objectRegistrationSupported": True, "uploadRequestSupported": False}})
        m = re.match(rf"{self.P}/objects/([^/]+)/access/([^/]+)$", self.path)
        if m:
            obj = OBJECTS.get(m.group(1))
            if not obj:
                return self.send(404, {"msg": "not found"})
            url = obj["access_methods"][0]["access_url"]["url"]
            b, k = url[len("s3://"):].split("/", 1)
            signed = S3.generate_presigned_url("get_object", Params={"Bucket": b, "Key": k}, ExpiresIn=900)
            return self.send(200, {"url": signed})
        m = re.match(rf"{self.P}/objects/([^/]+)$", self.path)
        if m:
            obj = OBJECTS.get(m.group(1))
            return self.send(200, obj) if obj else self.send(404, {"msg": "not found"})
        self.send(404, {"msg": "no route"})

    def do_POST(self):
        if not self.authed():
            return
        if self.path == f"{self.P}/upload-request":
            return self.send(400, {"msg": "upload-request requires explicit upload routing"})
        if self.path == f"{self.P}/objects/register":
            out = []
            for c in self.body()["candidates"]:
                if "mime_type" in c:
                    return self.send(400, {"msg": "mime_type cannot be persisted"})
                oid = str(uuid.uuid4())
                am = [dict(m, access_id=m["type"]) for m in c["access_methods"]]
                obj = dict(c, id=oid, self_uri=f"drs://{oid}", access_methods=am)
                OBJECTS[oid] = obj
                out.append(obj)
            return self.send(201, {"objects": out})
        self.send(404, {"msg": "no route"})


def run_task(tid):
    t = TASKS[tid]
    t["state"] = "RUNNING"
    work = tempfile.mkdtemp(prefix="faketes-")
    sys_logs = []
    try:
        for inp in t.get("inputs", []):
            if not inp["url"].startswith("http"):
                raise RuntimeError(f"unsupported protocol for input {inp['url']}")
            dest = os.path.join(work, inp["path"].lstrip("/"))
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with urllib.request.urlopen(inp["url"]) as r, open(dest, "wb") as f:
                f.write(r.read())
        os.makedirs(os.path.join(work, "out"), exist_ok=True)
        ex = t["executors"][0]
        roots = {"app": TRAINING, "in": work + "/in", "out": work + "/out"}
        cmd = [re.sub(r"(?<![\w./-])/(app|in|out)(?=/|\b)", lambda m: roots[m.group(1)], a)
               for a in ex["command"]]
        if cmd[0] == "python":
            cmd[0] = sys.executable
        p = subprocess.run(cmd, capture_output=True, text=True)
        exlog = {"exit_code": p.returncode, "stdout": p.stdout[-2000:], "stderr": p.stderr[-2000:]}
        if p.returncode != 0:
            t["state"] = "EXECUTOR_ERROR"
            t["logs"] = [{"logs": [exlog], "system_logs": sys_logs}]
            return
        outs = []
        for o in t.get("outputs", []):
            src = os.path.join(work, o["path"].lstrip("/"))
            b, k = o["url"][len("s3://"):].split("/", 1)
            S3.upload_file(src, b, k)
            outs.append({"url": o["url"], "path": o["path"], "size_bytes": str(os.path.getsize(src))})
        t["logs"] = [{"logs": [exlog], "outputs": outs, "system_logs": sys_logs}]
        t["state"] = "COMPLETE"
    except Exception as e:
        sys_logs.append(f"system error: {e}")
        t["logs"] = [{"logs": [], "system_logs": sys_logs}]
        t["state"] = "SYSTEM_ERROR"
    finally:
        shutil.rmtree(work, ignore_errors=True)


class TESHandler(Base):
    P = "/ga4gh/tes/v1"

    def do_GET(self):
        if self.path == f"{self.P}/service-info":
            return self.send(200, {"type": {"group": "org.ga4gh", "artifact": "tes", "version": "1.1.0"}})
        m = re.match(rf"{self.P}/tasks/([^/?]+)", self.path)
        if m and m.group(1) in TASKS:
            return self.send(200, TASKS[m.group(1)])
        self.send(404, {"msg": "not found"})

    def do_POST(self):
        if self.path == f"{self.P}/tasks":
            tid = uuid.uuid4().hex[:12]
            TASKS[tid] = dict(self.body(), id=tid, state="QUEUED")
            threading.Thread(target=run_task, args=(tid,), daemon=True).start()
            return self.send(200, {"id": tid})
        self.send(404, {"msg": "no route"})


if __name__ == "__main__":
    try:
        S3.create_bucket(Bucket=BUCKET)
    except Exception:
        pass
    for port, h in ((8080, DRSHandler), (8000, TESHandler)):
        threading.Thread(target=ThreadingHTTPServer(("127.0.0.1", port), h).serve_forever, daemon=True).start()
    print("fake DRS on :8080, fake TES on :8000", flush=True)
    threading.Event().wait()
