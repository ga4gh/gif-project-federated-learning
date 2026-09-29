# 06: DRS in the GA4GH Reference Cloud

**Time box:** 45 minutes
**Evaluator of record:** Brian
**Goal:** find out whether a site could run the Reference Cloud's DRS itself as part of a node-in-a-box, and whether it supports write-back. It is actively developed, which makes it the most strategically interesting option, even if it's not ready for us yet.

What we know going in:

- [ga4gh-reference-cloud](https://github.com/ga4gh/ga4gh-reference-cloud) is a planning and issue-tracking repo. The services live in [refcloud-api](https://github.com/ga4gh/refcloud-api) (Java, Spring, Gradle), `refcloud-ui`, `ga4gh-reference-cloud-helm`, and `refcloud-docs` ([docs.refcloud.ga4gh.org](https://docs.refcloud.ga4gh.org)).
- The [2026 Plenary milestones](https://github.com/ga4gh/ga4gh-reference-cloud/blob/main/milestones/2026-09-28-GA4GH-Plenary-Milestones.md) cover Passport (the Passport JWT used as the access token for other APIs), DRS read access with signed URLs, and Data Connect or Beacon for discovery. No WES/TES, and no DRS write, is mentioned.
- The intended deployment is the hosted instance at refcloud.ga4gh.org, via Helm. `refcloud-api` has a `docker-compose.yml`. Local development needs Java 25+, Gradle 9.1+, and PostgreSQL 18+.

## Step 1: Local run (25 min)

```bash
git clone https://github.com/ga4gh/refcloud-api.git && cd refcloud-api
cat docker-compose.yml        # what does it start? Postgres only, or the API too?
docker compose up -d
# If compose only starts dependencies, try (needs Java 25 + Gradle 9.1, e.g., via sdkman):
./gradlew bootRun
curl -s http://localhost:8080/ga4gh/drs/v1/service-info | jq .
```

**Record:** what the compose file actually starts; the minutes to first successful call; whether images exist for arm64.

## Step 2: Write path (10 min)

Look through the API (OpenAPI spec, controllers, docs) for any way to create or register a DRS object: a DRS upload or register endpoint, an admin API, or only ingestion scripts. If there is one, try registering `s3://fl-eval/out/weights.txt` from [03](../03-tes-funnel/).

## Step 3: Roadmap check (10 min)

Skim the Reference Cloud issues, ADR, and milestones for anything about DRS write or upload, WES/TES, or self-hosted deployment. The post-Plenary planning window is a chance to raise our needs there. Note anything we should ask for. Jeremy Adams is the Reference Cloud technical contact.

## Answer the scorecard in FINDINGS.md

- **Q1:** DRS version from `service-info`; Passport support
- **Q2:** write-back: supported, planned, or absent?
- **Q3:** can a Driver Project run it locally at all? How long did it take?
- **Q4:** activity and contact
- **Q5:** recommendation, both now and for what we'd ask the Reference Cloud roadmap to add
