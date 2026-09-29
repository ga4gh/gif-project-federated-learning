# 04: DRS with Syfon

**Time box:** 60 minutes
**Evaluator of record:** Kyle (Brian following along)
**Goal:** run Syfon against MinIO in local mode and test the write-back path: can we register an object that a TES task already wrote to storage, and get a DRS URI back?

[Syfon](https://calypr.org/tools/syfon/) ([repo](https://github.com/calypr/syfon)) is a Go implementation of GA4GH DRS (1.6) from CALYPR. It has a bulk register endpoint, presigned and multipart uploads, and S3-compatible backends including MinIO. Local mode uses SQLite and optional basic auth.

## Step 1: MinIO (5 min)

Use the MinIO from [03](../03-tes-funnel/#step-1-start-minio-5-min). It runs on port 9000 with user `minio-user`, password `minio-pass`, and bucket `fl-eval`.

## Step 2: Install Syfon (10 min)

Pick one:

```bash
# Option A: install script (read it first)
curl -sSL https://calypr.org/syfon/install.sh -o syfon-install.sh && less syfon-install.sh && bash syfon-install.sh

# Option B: from source (needs Go)
git clone https://github.com/calypr/syfon.git && cd syfon
```

**Record:** whether a prebuilt arm64 binary or a container image exists. We'll need one for the compose file.

## Step 3: Configure and start (10 min)

Create `local.yaml`, pointing the S3 credentials at our MinIO:

```yaml
port: 8080
auth:
  mode: local
  basic:
    username: "drs-user"
    password: "drs-pass"
database:
  sqlite:
    file: "drs_local.db"
s3_credentials:
  - bucket: "fl-eval"
    region: "us-east-1"
    access_key: "minio-user"
    secret_key: "minio-pass"
    endpoint: "http://localhost:9000"
```

```bash
syfon serve --config local.yaml        # or, from source: go run . serve --config local.yaml
curl -s http://localhost:8080/healthz
curl -s -u drs-user:drs-pass http://localhost:8080/ga4gh/drs/v1/service-info | jq .
```

## Step 4: Read path (10 min)

Upload a file with the Syfon CLI, then read it back through the DRS API:

```bash
syfon upload --file part.txt --org example --project example   # note the object ID it prints
syfon ls

curl -s -u drs-user:drs-pass http://localhost:8080/ga4gh/drs/v1/objects/<object-id> | jq .
# Take an access_id from access_methods, then:
curl -s -u drs-user:drs-pass http://localhost:8080/ga4gh/drs/v1/objects/<object-id>/access/<access-id> | jq .
curl -s "<the signed URL returned>" -o roundtrip.txt && diff part.txt roundtrip.txt
```

## Step 5: Write-back path (15–20 min). This is the key test.

In the training loop, a TES task writes `s3://fl-eval/out/weights.txt`, and *then* it needs to become a DRS object. Test registering an object that is already in storage, without re-uploading it:

1. Put a file in MinIO directly (or reuse `out/weights.txt` from [03](../03-tes-funnel/)).
2. Register it with `POST /ga4gh/drs/v1/objects/register`. Work out the request body from Syfon's API docs or OpenAPI spec. You'll need at least the name, size, checksum, and the `s3://` location.
3. Resolve the returned ID through `GET /objects/{id}` and download it through its access URL.

**Record:**

- The exact request that worked, pasted into FINDINGS.md.
- Who would have to make that call in our architecture: the task itself (so it needs DRS credentials inside the container) or the coordinator after the task completes.
- Whether register is part of the DRS spec version Syfon implements, or a Syfon-specific extension. That matters for the [gap log](../../README.md#tracking-api-gaps): if write-back only works through an implementation-specific endpoint, that is the gap.

## Answer the scorecard in FINDINGS.md

- **Q1:** DRS version from `service-info`
- **Q2:** write-back: exact working call sequence, and whether it's spec or extension
- **Q3:** minutes to first successful call; arm64; container image available?
- **Q4:** activity and contact
- **Q5:** recommendation for the node-in-a-box
- **Also:** auth modes (local basic vs. Gen3/Fence); how signed URLs behave when MinIO is on `localhost` versus another container name
