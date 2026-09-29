"""Minimal GA4GH DRS and TES clients (standard library only).

Deliberately small and spec-shaped so the same calls can be pointed at any
implementation. Implementation quirks are handled by the caller, not hidden here.
"""
import base64
import hashlib
import json
import time
import urllib.error
import urllib.request


class HTTPError(Exception):
    def __init__(self, method, url, status, body):
        super().__init__(f"{method} {url} -> HTTP {status}: {body[:500]}")
        self.status, self.body = status, body


def _request(method, url, body=None, headers=None, timeout=30):
    data = None
    hdrs = {"Accept": "application/json"}
    hdrs.update(headers or {})
    if body is not None:
        data = json.dumps(body).encode()
        hdrs["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raise HTTPError(method, url, e.code, e.read().decode(errors="replace")) from None


def sha256_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def download(url, headers=None, timeout=60):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


class DRS:
    """GA4GH Data Repository Service client (paths per DRS 1.5)."""

    def __init__(self, base_url, user=None, password=None, token=None):
        self.base = base_url.rstrip("/") + "/ga4gh/drs/v1"
        self.headers = {}
        if token:
            self.headers["Authorization"] = f"Bearer {token}"
        elif user:
            cred = base64.b64encode(f"{user}:{password}".encode()).decode()
            self.headers["Authorization"] = f"Basic {cred}"

    def service_info(self):
        return _request("GET", f"{self.base}/service-info", headers=self.headers)

    def upload_request(self, name, size, sha256, types=("s3", "https")):
        body = {"requests": [{"name": name, "size": size,
                              "checksums": [{"type": "sha256", "checksum": sha256}],
                              "upload_method_types": list(types)}]}
        return _request("POST", f"{self.base}/upload-request", body, self.headers)

    def register(self, name, size, sha256, url, method_type="s3", description=None):
        """POST /objects/register for data already in storage. Returns the DrsObject."""
        cand = {"name": name, "size": size,
                "checksums": [{"type": "sha256", "checksum": sha256}],
                "access_methods": [{"type": method_type, "access_url": {"url": url}}]}
        if description:
            cand["description"] = description
        resp = _request("POST", f"{self.base}/objects/register", {"candidates": [cand]}, self.headers)
        return resp["objects"][0]

    def get_object(self, object_id):
        return _request("GET", f"{self.base}/objects/{object_id}", headers=self.headers)

    def access_url(self, object_id, prefer=("https", "s3")):
        """Resolve an object to a fetchable URL. Returns (url, headers, access_method)."""
        obj = self.get_object(object_id)
        methods = obj.get("access_methods") or []
        methods = sorted(methods, key=lambda m: prefer.index(m["type"]) if m.get("type") in prefer else 99)
        for m in methods:
            if m.get("access_id"):
                au = _request("GET", f"{self.base}/objects/{object_id}/access/{m['access_id']}",
                              headers=self.headers)
                if au and au.get("url", "").startswith("http"):
                    return au["url"], _hdr_list(au.get("headers")), m
            au = m.get("access_url") or {}
            if au.get("url", "").startswith("http"):
                return au["url"], _hdr_list(au.get("headers")), m
        raise RuntimeError(f"no http(s)-fetchable access method for {object_id}: {methods}")


def _hdr_list(hs):
    out = {}
    for h in hs or []:
        if ":" in h:
            k, v = h.split(":", 1)
            out[k.strip()] = v.strip()
    return out


TERMINAL = {"COMPLETE", "EXECUTOR_ERROR", "SYSTEM_ERROR", "CANCELED", "CANCELLED", "PREEMPTED"}


class TES:
    """GA4GH Task Execution Service client (paths per TES 1.1)."""

    def __init__(self, base_url, token=None):
        self.base = base_url.rstrip("/") + "/ga4gh/tes/v1"
        self.headers = {"Authorization": f"Bearer {token}"} if token else {}

    def service_info(self):
        return _request("GET", f"{self.base}/service-info", headers=self.headers)

    def create(self, task):
        return _request("POST", f"{self.base}/tasks", task, self.headers)["id"]

    def get(self, task_id, view="FULL"):
        return _request("GET", f"{self.base}/tasks/{task_id}?view={view}", headers=self.headers)

    def wait(self, task_id, timeout=600, poll=2):
        t0 = time.time()
        while True:
            t = self.get(task_id)
            if t.get("state") in TERMINAL:
                return t
            if time.time() - t0 > timeout:
                return t
            time.sleep(poll)
