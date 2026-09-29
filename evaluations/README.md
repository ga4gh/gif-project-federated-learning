# Evaluations

Hands-on pre-work for the [October 2 hackathon](../HACKATHON.md), done in the open so anyone can follow along, repeat a step on their own machine, or add findings.

There are two kinds of evaluation here:

1. **FL framework basics** (`01`, `02`). A hello world in Flower and in NVIDIA FLARE, run to understand how federated learning frameworks are structured and what they expect from a site. These feed decision D1 (framework) and the integration question in [PATTERNS.md](PATTERNS.md).
2. **GA4GH building blocks** (`03`–`07`). Stand up candidate implementations of TES and DRS and score each against the same rubric. These feed decisions D2–D4 and the evaluator readouts on Friday.

`08` ties the two together. It's an implementation-neutral acceptance test for the node-in-a-box: one Pattern A round trip through TES and DRS that any candidate stack can be scored against.

## Schedule

| When | Evaluation | Lead | Others welcome? |
|---|---|---|---|
| Tue Sep 29 | [01 Flower hello world](01-flower/) | Brian | Yes, especially if you haven't done FL before |
| Tue Sep 29 | [02 NVIDIA FLARE hello world](02-flare/) | Brian | Yes |
| Wed Sep 30 | [03 TES: Funnel](03-tes-funnel/) | Kyle (evaluator), Brian | Yes |
| Wed Sep 30 | [04 DRS: Syfon](04-drs-syfon/) | Kyle (evaluator), Brian | Yes |
| Wed Sep 30 | [05 DRS: Starter Kit](05-drs-starter-kit/) | Brian | Yes |
| Wed Sep 30 | [06 DRS: Reference Cloud](06-drs-reference-cloud/) | Brian | Yes |
| Wed Sep 30 | [07 GSoC stack](07-gsoc-stack/) | Andrew | Yes |
| Thu Oct 1 | [08 Round trip (acceptance test)](08-round-trip/) | Brian | Yes |

Not yet assigned (grab one if you know it): Starter Kit WES, ELIXIR proWES / cwl-WES, TESK.

## How to take part

1. Pick an evaluation and follow its `README.md`. Each is written to be done in 30–90 minutes.
2. Record what you found in that folder's `FINDINGS.md`. Add your own section (name, date, machine) rather than editing someone else's. Commit directly or open a PR, whichever you prefer.
3. **Time-box strictly.** If a component isn't working inside its time box, stop and write down where you got stuck. "A Driver Project couldn't stand this up in an evening" is a useful finding, not a failure.
4. Anything a spec can't express, or that forces a workaround, gets an [API gap issue](../README.md#tracking-api-gaps). Link it from `FINDINGS.md`.

## Prerequisites

- Docker Desktop (or another Docker engine), running
- Python 3.11 or 3.12. Some ML libraries lag behind the newest Python releases, so 3.13+ may fail to install.
- `git`, `curl`, and `jq`
- About 10 GB free disk (PyTorch, container images, a CIFAR-10 download)
- Go 1.22+ only if you build Syfon from source

**Apple Silicon Macs.** Some images are published for `linux/amd64` only. Check with `docker image inspect <image> --format '{{.Architecture}}'`. If an image is amd64-only, it will usually run under emulation with `--platform linux/amd64`, but slower. Record which images needed emulation; Driver Projects on ARM hardware will hit the same thing.

**Install scripts.** Read any `curl ... | bash` script before running it.

## Building-block scorecard

Each building-block evaluation (`03`–`07`) answers the same questions. They match the evaluator readout questions in [HACKATHON.md](../HACKATHON.md).

| # | Question | What a good answer looks like |
|---|---|---|
| Q1 | Which APIs and versions does it implement? | Named spec versions, confirmed from `service-info`, not just the docs |
| Q2 | **Write-back:** can a job register a new object and get a DRS URI back? (TES: can a task consume a DRS URI as input?) | A working call sequence you actually ran |
| Q3 | How hard is it to bring up with `docker compose` on one machine? | Minutes to first successful API call; images for amd64 and arm64 |
| Q4 | Is it maintained? Who do we call when it breaks? | Recent releases or commits; a named contact |
| Q5 | Recommendation for the node-in-a-box | Use / use with caveats / don't use, and why |

Also note the auth model (none, basic, bearer token, Passport) and any API gaps filed.

### Summary (fill in as evaluations complete)

| Component | API / version | Q2 write-back or DRS input | Q3 time to first call | arm64 | Q4 maintained | Q5 recommendation |
|---|---|---|---|---|---|---|
| Funnel (TES) | | | | | | |
| Syfon (DRS) | | | | | | |
| Starter Kit DRS | | | | | | |
| Reference Cloud (DRS) | | | | | | |
| GSoC stack | | | | | | |

### FL frameworks summary

| Question | Flower | NVIDIA FLARE |
|---|---|---|
| Where does the round loop live? | | |
| What has to run at a site, and for how long? | | |
| Network direction and ports | | |
| How does a client find its local data? | | |
| Could the client be a one-shot job per round (Pattern A)? | | |
| How much code is framework-specific vs. plain PyTorch? | | |
