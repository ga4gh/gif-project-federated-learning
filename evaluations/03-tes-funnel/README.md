# 03: TES with Funnel

**Time box:** 60 minutes
**Evaluator of record:** Kyle (Brian following along)
**Goal:** run Funnel locally with its Docker executor and MinIO as object storage, and find out whether a TES task can take a DRS URI as input.

Funnel is a Go implementation of GA4GH TES from OHSU, now maintained under [calypr/funnel](https://github.com/calypr/funnel) (the old `ohsu-comp-bio/funnel` repo redirects there). Docs: [calypr.org/tools/funnel](https://calypr.org/tools/funnel/). It runs as a single binary, and its local worker runs task containers with Docker.

## Step 1: Start MinIO (5 min)

Use the same MinIO for every building-block evaluation so later steps can share it:

```bash
docker network create fl-eval 2>/dev/null || true
docker run -d --name minio --network fl-eval \
  -p 9000:9000 -p 9001:9001 \
  -e MINIO_ROOT_USER=minio-user -e MINIO_ROOT_PASSWORD=minio-pass \
  minio/minio server /data --console-address ":9001"

docker run --rm --network fl-eval --entrypoint sh minio/mc -c \
  'mc alias set local http://minio:9000 minio-user minio-pass && mc mb -p local/fl-eval'
```

The MinIO console is at http://localhost:9001 (user `minio-user`, password `minio-pass`).

## Step 2: Install and start Funnel (10–15 min)

Download the latest release for your platform from the [releases page](https://github.com/ohsu-comp-bio/funnel/releases) (`darwin` + `arm64` for Apple Silicon), unpack it, and put `funnel` on your `PATH`.

```bash
funnel version
funnel server run
```

By default the server serves HTTP on port 8000 and uses a local worker with the Docker executor. Confirm the address in the startup log, then check `service-info`:

```bash
curl -s http://localhost:8000/service-info | jq .
```

**Record:** release version and date; whether an arm64 binary existed; whether a Docker image exists and for which architectures.

## Step 3: Hello world task (10 min)

```bash
cat > hello.json <<'EOF'
{
  "name": "hello",
  "executors": [{ "image": "alpine", "command": ["echo", "hello from TES"] }]
}
EOF

funnel task create hello.json          # prints a task ID
funnel task get <task-id>              # or: funnel task list
# The same thing through the plain TES API:
curl -s -X POST http://localhost:8000/ga4gh/tes/v1/tasks -d @hello.json | jq .
```

Wait for state `COMPLETE` and find the stdout in the task logs.

## Step 4: S3 input and output via MinIO (15–20 min)

This is how a training task will read a partition and write weights. Configure Funnel's S3-compatible storage to point at MinIO. Funnel supports S3, GCS, Swift, HTTP(S), and FTP. Take the exact config keys from Funnel's storage docs for your version (the S3-compatible "generic S3" backend needs the endpoint `localhost:9000` and the MinIO key and secret). Then restart with `funnel server run --config funnel.yaml`.

```bash
echo "partition data" > part.txt
docker run --rm --network fl-eval -v "$PWD":/w --entrypoint sh minio/mc -c \
  'mc alias set local http://minio:9000 minio-user minio-pass && mc cp /w/part.txt local/fl-eval/part.txt'

cat > s3io.json <<'EOF'
{
  "name": "s3-io",
  "inputs":  [{ "url": "s3://fl-eval/part.txt", "path": "/in/part.txt" }],
  "outputs": [{ "url": "s3://fl-eval/out/weights.txt", "path": "/out/weights.txt" }],
  "executors": [{ "image": "alpine",
                  "command": ["sh", "-c", "cat /in/part.txt > /out/weights.txt && echo trained >> /out/weights.txt"] }]
}
EOF
funnel task create s3io.json
```

Check that `out/weights.txt` appears in MinIO.

Funnel's worker downloads inputs and uploads outputs itself, outside the task container. So `localhost:9000` is resolved from your machine, not from inside the container.

## Step 5: DRS URI as input (10 min)

Once a DRS server is running ([04](../04-drs-syfon/) or [05](../05-drs-starter-kit/)), register `part.txt` there and try the DRS URI directly as a TES input:

```json
"inputs": [{ "url": "drs://localhost:8080/<object-id>", "path": "/in/part.txt" }]
```

**Record exactly what happens.** If Funnel doesn't resolve `drs://`, note what the caller has to do instead: resolve the DRS object to an access URL first and pass that. Either way this is a data point for the [API gap log](../../README.md#tracking-api-gaps). TES doesn't define how a task's inputs relate to DRS.

## Answer the scorecard in FINDINGS.md

- **Q1:** TES version (from `service-info`)
- **Q2:** DRS input: worked natively, needed the caller to resolve first, or failed?
- **Q3:** minutes to first successful task; arm64 availability
- **Q4:** release cadence and contact
- **Q5:** recommendation for the node-in-a-box
- **Also:** auth options on the TES endpoint; anything odd about Docker Desktop on macOS (volume paths, networking)
