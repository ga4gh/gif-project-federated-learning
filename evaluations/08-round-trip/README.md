# 08: Round trip (node-in-a-box acceptance test)

**Time:** about 90 minutes
**Lead:** Brian
**Goal:** prove that one Pattern A training round can go through a site using only GA4GH APIs, and find every place we have to hand-glue it. This is the test any candidate node-in-a-box stack gets scored against, starting with the best combination from `03`–`07`.

A compose file (MinIO + a DRS server + a TES server) and a script that automates the steps below will be added to this folder. Until then, run the steps by hand with the components from `03` and `04`.

## The round trip

Each step is phrased in terms of the APIs, not a specific implementation, so any stack can be tested the same way.

| Step | What happens | Stands in for |
|---|---|---|
| **A1** | Bring up the node from a clean clone (`docker compose up`). Time it. | A Driver Project installing the box |
| **A2** | Put an input file in object storage and register it in DRS. Keep the DRS URI. | The site's synthetic partition |
| **A3** | Put a second file in storage and register it. Keep the DRS URI. | The current global weights |
| **A4** | Submit a TES task whose inputs are the two objects from A2 and A3. Try the DRS URIs directly first (variant **a**); if that fails, resolve each to an access URL and pass those (variant **b**). | The coordinator dispatching a round |
| **A5** | The task's command reads both inputs and writes an output file (e.g., input + "trained") to storage. | Local training producing updated weights |
| **A6** | Register the output in DRS and get a new DRS URI. Try it from inside the task (variant **a**: needs DRS credentials in the container), then from outside after the task completes (variant **b**: the coordinator does it). | Write-back of updated weights |
| **A7** | Resolve the new DRS URI, download the file, and check its checksum. | The coordinator fetching weights to aggregate |
| **A8** (stretch) | Replace the command in A5 with a real one-round training step: load weights, train one epoch on the partition, save weights. | An actual FL round |

## What to record in FINDINGS.md

- Which variants (a or b) worked at A4 and A6.
- Every piece of glue you had to write that the APIs didn't cover: resolving DRS before TES, passing credentials into a task, registering outputs, mapping a TES output URL to a DRS object, checksums. **Each one is a candidate [API gap issue](../../README.md#tracking-api-gaps).** File them before Friday.
- Total wall time for A2–A7, and how much of that was overhead rather than work.
- What a Driver Project would need to configure (ports, credentials, storage) to run this on their own VM.

## Why this matters for Friday

This test becomes Track B's definition of done at the hackathon. If it passes end to end, we have the core of M2. If it only passes with glue, the glue is our first set of findings for the gap report.
