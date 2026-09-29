# Decisions

One short file per decision: `NNNN-short-title.md` (e.g., `0001-dispatch-api.md`). Use this shape:

```markdown
# NNNN: Title

**Status:** proposed | decided | superseded by NNNN
**Date:** YYYY-MM-DD
**Decided by:** names

## Context
What we needed to decide and why it matters.

## Options considered
- Option A: trade-offs
- Option B: trade-offs

## Decision
What we chose.

## Consequences
What this commits us to, what it rules out, and any API gaps it creates (link `api-gap` issues).
```

## Open decisions (for the October 2 hackathon)

| # | Decision | Options | Starting lean | Decide by |
|---|---|---|---|---|
| D1 | FL framework for the first slice | Plain-Python FedAvg; Flower Strategy API; NVIDIA FLARE | Start with plain FedAvg or a Flower strategy. When WES/TES carries the rounds, most of a framework's own networking and provisioning goes unused. Revisit FLARE once the slice works. | Hackathon |
| D2 | Compute dispatch API | TES (one container per round per site); WES (workflow wrapper, fits the TRS/Dockstore story); WES backed by TES | TES is the simplest fit for one container per round. WES is the long-term target if a maintained implementation is ready. Choose based on evaluator readouts. | Hackathon |
| D3 | DRS implementation for the node | Syfon (DRS 1.6); Reference Cloud (targets DRS 1.5); Starter Kit (DRS 1.3 experimental); other | Whichever supports write-back of per-round weights today with the least custom code | Hackathon |
| D4 | WES/TES implementation for the node | Funnel (TES); Starter Kit WES; ELIXIR proWES / TESK; other | Based on evaluator readouts | Hackathon |
| D5 | Auth for M2–M3 | Static per-site bearer tokens; Passports from the start | Static tokens now; Passports after M3 | Hackathon |
| D6 | Network model | Push (coordinator calls site endpoints, so sites need inbound access); pull (sites poll for work) | Push if most sites can expose an endpoint; decide from the site readiness survey | Oct 9 |
| D7 | Synthetic data | Number of partitions, ancestry skew per partition, planted-signal spec | 3 partitions from the FedLearnVar setup, skewed by gnomAD subpopulation | M1 |
