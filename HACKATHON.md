# Hackathon: Friday, October 2, 2026

**Experiment 1: Federated variant pathogenicity classification over GA4GH APIs**
**Format:** 3 hours, hybrid (in person and virtual)
**Hosts:** Brian O'Connor, Venkat Malladi
**Slides:** [`docs/hackathon-2026-10-02.pptx`](docs/hackathon-2026-10-02.pptx)

## What we want to leave with

1. **Decisions** on the stack for the first slice: FL framework, WES vs. TES, DRS and WES/TES implementations, and auth (D1–D5 in [`decisions/`](decisions/README.md)).
2. **Something running** in each technical track, even if it's rough.
3. **Names on workstreams:** a champion (or at least a candidate) for each of the five [workstreams](README.md#workstreams-champions-needed), plus completed site readiness surveys from every Driver Project in the room.

We're not trying to build the whole system today. The target for the next 10 weeks is in the [near-term plan](README.md#near-term-plan-next-10-weeks).

## Agenda

| Time | Block | Lead |
|---|---|---|
| 0:00–0:15 | Welcome and framing | Brian |
| 0:15–0:40 | Evaluator readouts (3 × 6 min + questions) | Andrew, Kyle, Brian |
| 0:40–1:00 | Decisions | Venkat facilitates |
| 1:00–1:05 | Form tracks | Brian |
| 1:05–2:25 | Track work (5-minute check-in at ~1:45) | Track leads |
| 2:25–2:50 | Report-outs (4 × 5 min) and gap capture | Track leads |
| 2:50–3:00 | Champions, next steps, close | Brian, Venkat |

### 0:00–0:15 Welcome and framing

- Why we're here: FL across institutions is blocked by plumbing, not by the math. GA4GH APIs are the plumbing many sites already run.
- The end-to-end picture: node-in-a-box at each site, synthetic partitions handed out, the coordinator runs rounds over WES/TES and DRS, federated beats local-only, blog post, gap report. See the [architecture](README.md#architecture).
- The 10-week target (M3 by December 11) and what's deliberately out of scope until then.
- How we log API gaps (today included): use the `api-gap` issue template.

### 0:15–0:40 Evaluator readouts

Each evaluator gets 6 minutes, then a few minutes of questions. Please cover:

1. Which APIs and versions the stack implements (DRS, WES, TES, Passport)
2. **DRS write-back:** can a job register a new object (updated model weights) and get a DRS URI back? How?
3. How hard it is to bring up with `docker compose` on a single VM
4. Whether it's actively maintained, and who we'd call when it breaks
5. Your recommendation for the node-in-a-box

| Evaluator | Stack |
|---|---|
| Andrew | GSoC stack |
| Kyle | Syfon (DRS 1.6) + Funnel (TES) |
| Brian | Starter Kit and Reference Cloud (DRS 1.5 target) |

### 0:40–1:00 Decisions

Work through D1–D5 in [`decisions/README.md`](decisions/README.md). The aim is a decision good enough to build on for 10 weeks, not a permanent one. If a decision can't be made in the room, name who makes it and by when (no later than October 9). Someone takes notes directly into `decisions/NNNN-*.md` files.

| # | Decision | Starting lean |
|---|---|---|
| D1 | FL framework | Plain FedAvg or Flower strategy for the first slice; revisit FLARE later |
| D2 | Dispatch: WES or TES | Based on readouts; TES is simplest for one container per round |
| D3 | DRS implementation | Whichever supports write-back today |
| D4 | WES/TES implementation | Based on readouts |
| D5 | Auth for M2–M3 | Static bearer tokens; Passports after M3 |

### 1:05–2:25 Parallel tracks

Four tracks. In-person people sit at track tables; virtual people join the track's breakout room. Each track posts progress in its own issue thread so the report-out writes itself. At about 1:45 each track posts a one-line status in the main channel.

#### Track A: Science (data, model, evaluation)

- **Lead:** needed (Workstream 1 champion candidate)
- **Goal:** get the [FedLearnVar simulation](https://github.com/RausellLab/FedLearnVar/blob/main/FL_simulation.ipynb) running and turn it into our data generator and training step.
- **Done today:**
  - The notebook runs, and we understand its features, model, and FedAvg loop
  - A first script that writes 3 synthetic partitions (ancestry-skewed allele frequencies) to files
  - Stretch: federated beats local-only on those partitions, in simulation
  - Stretch: the local training step as a standalone script that takes `weights_in`, `data_in`, `weights_out` paths (the container's future interface)
- **Who should join:** anyone comfortable with Python, PyTorch, or pandas; ML and statistical genetics folks.

#### Track B: Node-in-a-box

- **Lead:** Kyle (proposed)
- **Goal:** a `docker compose` stack on a laptop that proves the round trip we need from a site.
- **Done today:**
  - DRS server + object store up; register a file and resolve it by DRS URI
  - TES (or WES) up; run a hello-world container
  - Stretch: the container reads an input by DRS URI and writes an output that ends up registered in DRS with a new URI. This is the write-back step, and whatever doesn't work here is our first `api-gap` issue.
- **Who should join:** implementers and infrastructure folks; anyone who has run Funnel, Syfon, the Starter Kit, or the Reference Cloud.

#### Track C: Coordinator spike

- **Lead:** Venkat
- **Goal:** a FedAvg loop in which "train on client" is a WES/TES submission.
- **Done today:**
  - A FedAvg round loop (plain Python or Flower Strategy) with a mocked client call
  - A thin client module: submit a task with DRS URIs, poll for status, read the output DRS URI
  - Stretch: run one mocked round against Track B's node
- **Who should join:** Python developers; anyone who has used Flower or FLARE.

#### Track D: Driver sites

- **Lead:** Brian
- **Goal:** know what each Driver Project can actually run, so we pick sites for M3 and see blockers early.
- **Done today:** a completed [site readiness survey](#site-readiness-survey) for every Driver Project in the room, compiled into a site matrix (issue or `docs/sites.md`). Governance or network concerns get logged as issues.
- **Who should join:** Driver Project representatives. This track is valuable for people who won't be writing code today.

### 2:25–2:50 Report-outs

Five minutes per track, same four questions:

1. What runs? (Demo it if you can.)
2. What API gaps did you hit? (File each as an `api-gap` issue before leaving.)
3. What's the next concrete step?
4. Who owns it?

### 2:50–3:00 Champions and next steps

- Confirm or collect names for the five workstream champions.
- Confirm the M1 date (October 30) and the biweekly sync slot.
- Any open decisions: owner and date (no later than October 9).

## Site readiness survey

For each Driver Project (Track D):

1. **Contact:** name and email of the technical person who'd run the node
2. **Compute:** where would the node run? (cloud VM, on-prem VM, Kubernetes, HPC only)
3. **Containers:** Docker available? Or only Singularity/Apptainer?
4. **Networking:** can the node expose an HTTPS endpoint the coordinator can reach from the internet? If not, what's allowed (outbound only, VPN, allowlisted IPs)?
5. **GPU:** available? (Not required for the MLP baseline.)
6. **Existing GA4GH services:** already running DRS, WES, TES, or a Passport broker? Which implementations?
7. **Governance:** anything needed before hosting synthetic data and running external jobs? (Security review, approvals, and how long they take.)
8. **Timing:** could you bring up a node by mid-November for M3, or January for M4?
9. **Ancestry context:** which population context should your synthetic partition reflect?

## Before Friday (hosts' checklist)

- [ ] README, HACKATHON.md, and decisions list merged
- [ ] Labels created: `api-gap`, `api:*`, `gap:*`, `ws:*`, `good-first-issue`
- [ ] One epic issue per workstream, plus 2–3 starter issues per track
- [ ] One issue per track for live notes during the session
- [ ] Track leads confirmed (Track A still needs one)
- [ ] Evaluators briefed on the five readout questions
- [ ] Breakout rooms (or channels) set up for virtual attendees, one per track
- [ ] Note-taker for the decisions block
