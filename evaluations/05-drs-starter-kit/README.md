# 05: DRS with the GA4GH Starter Kit

**Time box:** 30 minutes (strict)
**Evaluator of record:** Brian
**Goal:** confirm whether the Starter Kit DRS is a viable node-in-a-box component today, and whether it can do write-back.

The [Starter Kit DRS](https://github.com/ga4gh/ga4gh-starter-kit-drs) is a Java/Spring implementation. Per its README it reports DRS `1.3.0experimental` and "does not match any published DRS Specification". It exposes a public DRS API on port 4500 and a non-standard admin API on port 4501 for creating, updating, and deleting objects. It uses SQLite by default, with PostgreSQL available via docker-compose.

We expect this to be a "don't use", given its DRS version and how rarely it's been updated. The point of the 30 minutes is to confirm that with evidence rather than assume it.

## Step 1: Run it (10 min)

```bash
docker pull ga4gh/ga4gh-starter-kit-drs:latest
docker image inspect ga4gh/ga4gh-starter-kit-drs:latest --format '{{.Architecture}} {{.Created}}'
docker run -d --name sk-drs -p 4500:4500 -p 4501:4501 ga4gh/ga4gh-starter-kit-drs:latest
# If the image is amd64-only on Apple Silicon, add: --platform linux/amd64

curl -s http://localhost:4500/ga4gh/drs/v1/service-info | jq .
```

If it needs a database initialized first (the README mentions `make sqlite-db-refresh` for development), note how much setup that took.

## Step 2: Write path via the admin API (15 min)

Create an object through the admin port for a file in MinIO (`s3://fl-eval/out/weights.txt` from [03](../03-tes-funnel/)), then resolve it on the public port. Take the admin endpoint path and request body from the repo's docs or OpenAPI spec.

```bash
curl -s -X POST http://localhost:4501/admin/ga4gh/drs/v1/objects -H 'Content-Type: application/json' -d @object.json | jq .
curl -s http://localhost:4500/ga4gh/drs/v1/objects/<id> | jq .
```

**Record:** whether it worked; whether the object can point at an S3/MinIO location or only local files; and whether the access method gives a URL a TES task could actually fetch.

## Step 3: Maintenance check (5 min)

On GitHub, note the date of the last release and last commit, open issues and PRs, and who responds.

## Answer the scorecard in FINDINGS.md

- **Q1:** DRS version from `service-info`
- **Q2:** write-back via the admin API: does it work, and is it non-standard? (Yes, by design; record it.)
- **Q3:** minutes to first successful call; arm64 or emulation
- **Q4:** last release and commit dates
- **Q5:** recommendation
