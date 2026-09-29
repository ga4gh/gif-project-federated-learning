# 07: GSoC stack

**Time box:** 60 minutes
**Evaluator of record:** Andrew

Andrew: please replace this paragraph with a short description of the stack (components, repos, which GA4GH APIs and versions it implements) and the steps you used to bring it up, in the same shape as the other evaluations. Use MinIO from [03](../03-tes-funnel/#step-1-start-minio-5-min) if the stack needs object storage, so results are comparable.

## Tests to run

1. Bring it up locally with Docker or docker compose, and time it.
2. Call `service-info` on each API and record the versions.
3. If it includes DRS: the write-back test from [04, step 5](../04-drs-syfon/#step-5-write-back-path-1520-min-this-is-the-key-test). Register an object already in storage and get a DRS URI back.
4. If it includes TES or WES: a hello-world task, then a task with an S3 input and output, then a DRS URI as input (as in [03, steps 3–5](../03-tes-funnel/)).
5. Try the [round-trip acceptance test](../08-round-trip/) against it once that's available.

## Answer the scorecard in FINDINGS.md

- **Q1:** APIs and versions
- **Q2:** write-back and DRS-input results
- **Q3:** minutes to first successful call; arm64
- **Q4:** maintenance and contact
- **Q5:** recommendation for the node-in-a-box
