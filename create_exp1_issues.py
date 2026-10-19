#!/usr/bin/env python3
"""Create Experiment 1 labels, milestones, and issues in ga4gh/gif-project-federated-learning.

Dry run (default) prints what would be created. Pass --create to do it.
Requires an authenticated `gh` CLI with write access to the repo.

    python3 create_exp1_issues.py            # preview
    python3 create_exp1_issues.py --create   # create
    python3 create_exp1_issues.py --create --skip-gaps   # leave the candidate API gaps out
"""
import argparse
import json
import subprocess
import sys

REPO = "ga4gh/gif-project-federated-learning"

LABELS = [
    ("api-gap", "d93f0b", "A GA4GH spec can't express something or forced a workaround"),
    ("api:drs", "1d76db", "Data Repository Service"),
    ("api:wes", "1d76db", "Workflow Execution Service"),
    ("api:tes", "1d76db", "Task Execution Service"),
    ("api:passport", "1d76db", "Passports / AAI"),
    ("api:trs", "1d76db", "Tool Registry Service"),
    ("api:service-info", "1d76db", "service-info"),
    ("gap:blocker", "b60205", "Can't proceed without a spec change"),
    ("gap:workaround", "fbca04", "Worked around it; the workaround should be replaced"),
    ("gap:nice-to-have", "c2e0c6", "Works today; a spec change would make it cleaner"),
    ("ws:science", "5319e7", "Workstream 1: data, model, evaluation"),
    ("ws:node", "5319e7", "Workstream 2: node-in-a-box"),
    ("ws:coordinator", "5319e7", "Workstream 3: coordinator"),
    ("ws:auth", "5319e7", "Workstream 4: auth"),
    ("ws:sites", "5319e7", "Workstream 5: sites and reporting"),
    ("epic", "000000", "Workstream epic"),
    ("exp1", "0e8a16", "Experiment 1: federated variant pathogenicity classification"),
    ("good-first-issue", "7057ff", "Sized to finish in an afternoon"),
]

MILESTONES = [
    ("M1: Science works in simulation", "2026-11-20", "Synthetic partitions with the planted signal. On one machine, federated training beats local-only. Training step packaged as a container."),
    ("M2: One node in a box", "2027-01-15", "`docker compose up` gives a working DRS + WES/TES node. The coordinator runs one full round against it."),
    ("M3: Multi-site", "2027-03-05", "Two or three real nodes run 10+ rounds over the internet with static bearer tokens. Result reproduced."),
    ("M4: Driver onboarding + blog", "2027-04-15", "Onboarding runbook, first external Driver Project joins without hand-holding, blog post published."),
]

# Each issue: key, title, labels, milestone (title prefix or None), epic key (or None), body.
# Epics are created first so children can reference them.
EPICS = [
    ("E1", "[Epic] WS1 Science: data, model, evaluation", ["epic", "exp1", "ws:science"], "M1",
     """Synthetic data generator and planted signal, the classifier (MLP baseline per Montalvo et al. 2025), federated vs. local-only evaluation, and DP-SGD configuration (epsilon sweep deferred until after M3).

**Champion:** needed
**Exit (M1):** federated beats every local-only model on a held-out set, in simulation, using the training container.

Child issues are linked below as they're created."""),
    ("E2", "[Epic] WS2 Node-in-a-box", ["epic", "exp1", "ws:node"], "M2",
     """The compose stack (WES/TES, DRS + object store, auth), site configuration, deploy docs, and the onboarding runbook.

**Champion:** needed
**Exit (M2):** `docker compose up` on a clean VM gives a node that passes the `evaluations/08-round-trip` acceptance test."""),
    ("E3", "[Epic] WS3 Coordinator", ["epic", "exp1", "ws:coordinator"], "M2",
     """The FL loop: FedAvg, WES/TES and DRS clients, round bookkeeping, failure and dropout handling.

**Champion:** Venkat Malladi (proposed)
**Exit (M2):** one full round against one node. **Exit (M3):** N sites × 10 rounds."""),
    ("E4", "[Epic] WS4 Auth", ["epic", "exp1", "ws:auth"], "M3",
     """Static bearer tokens for M2–M3; then Passports, visas, and machine-to-machine delegation for automated rounds (post-M3).

**Champion:** needed (active from M3)"""),
    ("E5", "[Epic] WS5 Sites and reporting", ["epic", "exp1", "ws:sites"], "M3",
     """Recruiting and onboarding Driver Projects, the site readiness matrix, the API gap log and triage, the blog post, and the final report.

**Champion:** Brian O'Connor"""),
]

ISSUES = [
    # --- Close out M0 (overdue: target was Oct 9) ---
    ("I01", "Decide D1–D5 and record them in decisions/", ["exp1", "ws:sites"], "M1", "E5",
     """The Oct 2 hackathon went to getting the Reference Cloud set up, so D1–D5 in `decisions/README.md` are still open. Decide each one and write a `decisions/NNNN-*.md` note using the template there.

- [ ] D1 FL framework for the first slice (lean: plain FedAvg or a Flower strategy)
- [ ] D2 Compute dispatch, WES vs. TES (lean: TES for one container per round)
- [ ] D3 DRS implementation: Syfon vs. Reference Cloud vs. Starter Kit (lean: whichever does write-back with the least glue; fed by #I10)
- [ ] D4 WES/TES implementation: Funnel vs. Starter Kit WES vs. proWES/TESK (fed by #I03)
- [ ] D5 Auth for M2–M3 (lean: static bearer tokens; Passports after M3)

D1, D2, and D5 can be settled at the next sync on the starting leans. D3 and D4 need evaluation results first. Target: all five decided before M1."""),
    ("I02", "Decide D6: push vs. pull network model", ["exp1", "ws:sites", "ws:coordinator"], "M1", "E5",
     """Decide from the site readiness survey (#I19) whether sites can accept inbound HTTPS from the coordinator (push) or need a pull model. Record as a `decisions/` note. This blocks the node deploy docs and the M3 site choice."""),
    ("I03", "Fill in evaluation FINDINGS and the scorecard summary", ["exp1", "ws:node"], "M1", "E2",
     """All `evaluations/*/FINDINGS.md` files and both summary tables in `evaluations/README.md` are still empty in the repo. Run the remaining evaluations and record results (Funnel, Syfon, Starter Kit, GSoC stack, Flower, FLARE), and write up the Reference Cloud work from the hackathon in `06-drs-reference-cloud/FINDINGS.md`. These feed D1–D4 (#I01), so later contributors can see why each went the way it did."""),
    ("I04", "Name champions for WS1 (Science), WS2 (Node), WS4 (Auth)", ["exp1", "ws:sites"], "M1", "E5",
     """Update the workstreams table in the README and each epic once confirmed. WS1 is the most urgent since M1 depends on it."""),

    # --- WS1 Science (M1) ---
    ("I05", "Run the FedLearnVar simulation notebook and document it", ["exp1", "ws:science", "good-first-issue"], "M1", "E1",
     """Get [FL_simulation.ipynb](https://github.com/RausellLab/FedLearnVar/blob/main/FL_simulation.ipynb) running. Write a short note in the repo covering the input features, the model, the FedAvg loop, and the metrics they report, so the generator and training step can match them."""),
    ("I06", "Synthetic partition generator with planted signal (D7)", ["exp1", "ws:science"], "M1", "E1",
     """One script, run centrally, that writes N ClinVar-derived variant partitions plus a held-out test set.

- Starting lean: 3 partitions, allele frequencies skewed by gnomAD subpopulation
- A planted pathogenicity signal with a known spec, written to a README next to the generator
- Output CSV matches the `train_round.py` data contract: numeric features plus a 0/1 `label` column
- Deterministic given a seed

Record the D7 choices in `decisions/`."""),
    ("I07", "Port train_round.py to PyTorch + Opacus, keeping the interface", ["exp1", "ws:science"], "M1", "E1",
     """Replace the NumPy MLP in `evaluations/08-round-trip/training/` with a PyTorch MLP trained with Opacus DP-SGD. Keep the CLI (`--data-in --weights-in --weights-out --metrics-out`), `.npz` weights, and the metrics JSON fields (`n_examples`, loss/accuracy before and after, `sha256`, size). Add epsilon/delta/clip-norm flags; a single sensible default is fine for M1."""),
    ("I08", "M1 result: federated beats local-only in simulation", ["exp1", "ws:science"], "M1", "E1",
     """On one machine, using the generator (#I06) and the training step (#I07): run FedAvg over the partitions for 10+ rounds and compare against each site trained alone, on the held-out set. Report the metrics and a plot. This is the M1 exit criterion."""),
    ("I09", "Publish a multi-arch training container", ["exp1", "ws:science", "ws:node"], "M1", "E1",
     """Build the training image for linux/amd64 and linux/arm64 and push it to a public registry (e.g. ghcr.io/ga4gh/...) with versioned tags, so TES/WES tasks at any site can pull it. Note the digest in the repo."""),

    # --- WS2 Node-in-a-box (M2) ---
    ("I10", "Run the 08 round-trip acceptance test against the DRS candidates", ["exp1", "ws:node"], "M1", "E2",
     """`evaluations/08-round-trip` has only been run against fake servers. Run it end to end with Funnel against each DRS candidate still in the running (Syfon, and the Reference Cloud now that it is set up locally). Comparing write-back between the two is the main input to D3 (#I01). For each run, paste the `results/*.md` into `FINDINGS.md`, and file each confirmed gap with the `api-gap` template (see the candidate gaps in the 08 README, \"What we expect to find\")."""),
    ("I11", "Promote 08-round-trip into a node-in-a-box compose stack", ["exp1", "ws:node"], "M2", "E2",
     """Turn the eval kit into `node/` (or similar): one `docker compose up` on a single VM that brings up DRS, object storage, and WES/TES. Funnel currently runs natively because its local worker drives the host Docker; decide how to package it (socket mount, DinD, or documented native install) and fix the signed-URL host problem noted in the 08 README troubleshooting section."""),
    ("I12", "Single-VM deploy guide: TLS, ports, tokens, site config", ["exp1", "ws:node"], "M2", "E2",
     """What a Driver Project does to bring up a node the coordinator can reach: VM size, TLS termination, which ports, where the bearer token goes, and how to register their partition. Depends on D6. This becomes the basis of the M4 onboarding runbook."""),
    ("I13", "File upstream bugs for DRS implementation quirks found in the round trip", ["exp1", "ws:node", "api:drs"], "M2", "E2",
     """Expected from the 08 README: Syfon rejects `POST /upload-request`, rejects `mime_type` on register, and returns `self_uri` as `drs://<id>` without a hostname. Confirm on a real run (#I10), and record anything similar from the Reference Cloud run. Anything the DRS spec already covers goes to that implementation's repo as a bug, linked here, not as an `api-gap`."""),

    # --- WS3 Coordinator (M2/M3) ---
    ("I14", "Coordinator: one full round against one node", ["exp1", "ws:coordinator"], "M2", "E3",
     """Using `roundtrip/ga4gh_client.py`: init global weights, register them in the coordinator's DRS, submit a task to the node with DRS URIs (or resolved URLs, per D2/D4), poll, fetch and verify the output weights, run FedAvg, register the new global weights. M2 exit criterion."""),
    ("I15", "Coordinator: N sites × R rounds with round bookkeeping", ["exp1", "ws:coordinator"], "M3", "E3",
     """Generalize #I14 to a site list and a round count. Persist per-round state (task IDs, DRS URIs in and out, checksums, n_examples, metrics) so a run can be audited and resumed. Evaluate on the held-out set each round."""),
    ("I16", "Coordinator: handle task failure and site dropout", ["exp1", "ws:coordinator"], "M3", "E3",
     """Timeouts, retries, and a policy for aggregating when a site fails or is slow in a round (skip vs. wait). Log each event so it feeds the telemetry and gap report."""),

    # --- WS4 Auth (M3) ---
    ("I17", "Static per-site bearer token scheme for M3", ["exp1", "ws:auth"], "M3", "E4",
     """How the coordinator authenticates to each site's DRS and WES/TES, and how tasks get credentials for the coordinator's DRS (global weights). Document issuance, rotation, and where tokens live. Note anything that would be visible in task definitions."""),
    ("I18", "Design note: Passport and machine-to-machine delegation path", ["exp1", "ws:auth", "api:passport"], "M4", "E4",
     """Post-M3. Write up how automated rounds would be authorized with Passports/visas and M2M token delegation, what the spec covers today, and what it doesn't. Expected to produce `api-gap` issues."""),

    # --- WS5 Sites and reporting ---
    ("I19", "Run the site readiness survey and compile docs/sites.md", ["exp1", "ws:sites"], "M1", "E5",
     """Send the survey in HACKATHON.md (it wasn't run on Oct 2) to each Driver Project and compile one row per site: contact, compute, containers, inbound networking, GPU, existing GA4GH services, governance lead time, timing, ancestry context. Chase anyone who hasn't returned it."""),
    ("I20", "Select M3 sites and schedule node bring-up", ["exp1", "ws:sites"], "M3", "E5",
     """Pick two or three sites (e.g. Nimbus, Verily, one Driver Project) from the matrix. Get each node up and passing the acceptance test by mid-February so M3 rounds can start."""),
    ("I21", "Set up biweekly sync and api-gap triage", ["exp1", "ws:sites"], "M1", "E5",
     """Calendar slot, a running notes location, and a standing agenda item to review new `api-gap` issues. Blockers go to the relevant spec repo right away, linked back."""),
]

# Candidate API gaps expected from the 08 round trip. Confirm on a real run before filing (#I10).
GAPS = [
    ("G1", "[API gap] TES: no defined handling of drs:// URIs in task inputs", ["api-gap", "exp1", "api:tes", "gap:workaround"], "M2", "E2",
     """**API and version:** TES 1.1

**Implementation used:** Funnel (calypr/funnel)

**What we were trying to do**
Pass the DRS URIs for the global weights and the local partition directly as TES task inputs (08 step A4a).

**What the spec says, or doesn't**
TES input `url` is scheme-agnostic and says nothing about DRS. Funnel's storage backends don't include DRS.

**Workaround (if any)**
The coordinator resolves each DRS URI to a signed access URL and passes that (A4b). Signed URLs can expire before a queued task starts.

**Proposed change (optional)**
Define DRS URI resolution for TES inputs (including auth for the resolution call).

**Is this a spec gap or an implementation bug?**
Spec gap. Confirm on the real run (#I10) before triage."""),
    ("G2", "[API gap] TES: output logs carry no checksum", ["api-gap", "exp1", "api:tes", "gap:workaround"], "M2", "E2",
     """**API and version:** TES 1.1

**Implementation used:** Funnel

**What we were trying to do**
Register task outputs in DRS, which requires a checksum.

**What the spec says, or doesn't**
`OutputFileLog` has `url`, `path`, and `size_bytes`; no checksum.

**Workaround (if any)**
The task writes a sidecar metrics file with the sha256; the coordinator reads it.

**Proposed change (optional)**
Add checksums to `OutputFileLog`, using DRS checksum types.

**Is this a spec gap or an implementation bug?**
Spec gap. Confirm on the real run (#I10)."""),
    ("G3", "[API gap] TES/DRS: no way to register task outputs in DRS", ["api-gap", "exp1", "api:tes", "api:drs", "gap:workaround"], "M2", "E2",
     """**API and version:** TES 1.1, DRS 1.5

**What we were trying to do**
Get updated weights from a finished task into DRS with a URI the coordinator can resolve (08 step A6).

**What the spec says, or doesn't**
TES outputs land in storage; nothing links them to a DRS object. DRS 1.5 `POST /objects/register` exists but something outside TES has to call it.

**Workaround (if any)**
The coordinator registers outputs after the task completes (A6b).

**Proposed change (optional)**
Question for the Federated Analysis Work Stream: should TES support \"register these outputs in this DRS\"?

**Is this a spec gap or an implementation bug?**
Spec gap. Confirm on the real run (#I10)."""),
    ("G4", "[API gap] TES: no standard way to pass secrets to a task", ["api-gap", "exp1", "api:tes", "gap:nice-to-have"], "M3", "E4",
     """**API and version:** TES 1.1

**What we were trying to do**
Let a task register its own output in DRS (08 step A6a), or read from a token-protected DRS.

**What the spec says, or doesn't**
The only way to pass credentials is environment variables in the task definition, which anyone who can read the task can see.

**Workaround (if any)**
Coordinator-side registration (A6b) and pre-signed URLs.

**Proposed change (optional)**
A secrets reference mechanism in the task model, resolved by the server.

**Is this a spec gap or an implementation bug?**
Spec gap. Severity may rise when static tokens are introduced at M3."""),
]


def gh(args, input_json=None):
    cmd = ["gh"] + args
    res = subprocess.run(cmd, input=json.dumps(input_json) if input_json else None,
                         capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)}\n{res.stderr}")
    return res.stdout


def milestone_numbers():
    out = gh(["api", f"repos/{REPO}/milestones?state=all&per_page=100"])
    return {m["title"].split(":")[0]: m["number"] for m in json.loads(out)}


def existing_labels():
    out = gh(["api", f"repos/{REPO}/labels?per_page=100"])
    return {l["name"] for l in json.loads(out)}


def create_issue(title, labels, milestone_no, body):
    payload = {"title": title, "body": body, "labels": labels}
    if milestone_no:
        payload["milestone"] = milestone_no
    out = gh(["api", f"repos/{REPO}/issues", "--method", "POST", "--input", "-"], payload)
    data = json.loads(out)
    return data["number"], data["html_url"]


def resolve_refs(body, numbers):
    # Replace #I05-style placeholders with real issue numbers.
    for key, num in sorted(numbers.items(), key=lambda kv: -len(kv[0])):
        body = body.replace(f"#{key}", f"#{num}")
    return body


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--create", action="store_true", help="actually create (default is dry run)")
    ap.add_argument("--skip-gaps", action="store_true", help="don't file the candidate API gap issues")
    args = ap.parse_args()

    issues = ISSUES + ([] if args.skip_gaps else GAPS)

    if not args.create:
        print(f"DRY RUN against {REPO}\n")
        print(f"Labels ({len(LABELS)}): " + ", ".join(l[0] for l in LABELS))
        print("Milestones: " + "; ".join(f"{m[0]} (due {m[1]})" for m in MILESTONES))
        print(f"\nEpics ({len(EPICS)}):")
        for k, t, *_ in EPICS:
            print(f"  {k}  {t}")
        print(f"\nIssues ({len(issues)}):")
        for k, t, labels, ms, epic, _ in issues:
            print(f"  {k}  [{ms}] {t}  ({', '.join(labels)}; epic {epic})")
        print("\nRe-run with --create to create these.")
        return

    have = existing_labels()
    for name, color, desc in LABELS:
        if name in have:
            continue
        gh(["label", "create", name, "--repo", REPO, "--color", color, "--description", desc])
        print(f"label  {name}")

    ms = milestone_numbers()
    for title, due, desc in MILESTONES:
        key = title.split(":")[0]
        if key in ms:
            continue
        out = gh(["api", f"repos/{REPO}/milestones", "--method", "POST", "--input", "-"],
                 {"title": title, "due_on": f"{due}T23:59:59Z", "description": desc})
        ms[key] = json.loads(out)["number"]
        print(f"milestone  {title}")

    numbers = {}
    children = {}
    for key, title, labels, m, body in EPICS:
        n, url = create_issue(title, labels, ms.get(m), body)
        numbers[key] = n
        children[key] = []
        print(f"#{n}  {title}")

    for key, title, labels, m, epic, body in issues:
        full_body = f"Part of #{numbers[epic]}\n\n{body}"
        n, url = create_issue(title, labels, ms.get(m), full_body)
        numbers[key] = n
        children[epic].append((n, title))
        print(f"#{n}  {title}")

    # Second pass: fix cross-references and append child checklists to epics.
    for key, title, labels, m, epic, body in issues:
        if "#I" in body or "#G" in body:
            full_body = resolve_refs(f"Part of #{numbers[epic]}\n\n{body}", numbers)
            gh(["api", f"repos/{REPO}/issues/{numbers[key]}", "--method", "PATCH", "--input", "-"],
               {"body": full_body})
    for key, title, labels, m, body in EPICS:
        tasks = "\n".join(f"- [ ] #{n}" for n, _ in children[key])
        gh(["api", f"repos/{REPO}/issues/{numbers[key]}", "--method", "PATCH", "--input", "-"],
           {"body": f"{body}\n\n### Issues\n{tasks}"})

    print("\nDone.")


if __name__ == "__main__":
    sys.exit(main())
