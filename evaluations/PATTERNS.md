# Integration patterns: where the FL framework meets the GA4GH APIs

A question for the Friday decisions block (D1 and D2). The hello worlds in [`01-flower`](01-flower/) and [`02-flare`](02-flare/) are the fastest way to get a feel for it.

## The tension

Our [architecture diagram](../docs/architecture.png) shows **one WES/TES submission per site per round**: the coordinator launches a short-lived training job, the job reads weights and data through DRS, writes updated weights back, and exits.

Flower and NVIDIA FLARE aren't built that way. In both, each site runs a **long-lived client process** that connects *outbound* to the server and stays connected for the whole training session. The framework moves weights over its own channel (gRPC) and runs the round loop itself. In Flower, a SuperNode connects to the SuperLink's Fleet API (port 9092 by default). In FLARE, a provisioned client connects to the FL server using its startup kit.

So there are two ways to combine them.

## Pattern A: per-round dispatch

The coordinator owns the round loop. Each round it submits a TES task (or WES run) to every site, passing DRS URIs for the global weights and the local data. The task trains for one round, writes updated weights to object storage, and they're registered in DRS. The coordinator fetches them, aggregates, and repeats.

- **FL framework's role:** aggregation only. Plain-Python FedAvg is enough; a framework's strategy classes are optional.
- **GA4GH exercise:** heavy. Every round goes through TES/WES and DRS, which is what surfaces gaps.
- **Networking:** sites must accept an inbound TES/WES call every round.
- **Likely gaps:** DRS write-back, TES tasks consuming DRS URIs, per-round overhead, auth for automated submission.

## Pattern B: session launch

The coordinator runs the framework's server (Flower SuperLink / FLARE server). At the start of a training session it submits **one long-running TES task per site** that starts the framework's client. The client reads its local partition via DRS, connects out to the server, and runs every round over the framework's own channel. At the end, the final model is registered in DRS.

- **FL framework's role:** runs the rounds; this is how the frameworks are meant to be used.
- **GA4GH exercise:** light. TES for the launch, DRS for data in and model out.
- **Networking:** FL traffic is outbound from sites; only the one-time launch is inbound.
- **Likely gaps:** TES isn't designed for long-running services (no service endpoint, health, or graceful stop); there's no standard way to hand a site's client its server address and credentials.

## Starting lean

Build Pattern A first. It needs no framework, it's the purest demonstration of GA4GH APIs doing the work, and it's the one the gap report benefits from most. Keep Pattern B as the comparison that shows what a production deployment would more likely do, and try it once the Pattern A slice works. Whichever we choose, the gaps each pattern exposes belong in the report.

## Questions to settle Friday

1. Are we demonstrating that GA4GH APIs *can carry* FL (Pattern A), or that GA4GH APIs *can deploy and feed* existing FL frameworks (Pattern B)? Or both, in order?
2. If Pattern A, do we need Flower or FLARE at all for the first slice?
3. Can Driver Project sites accept inbound calls? (Track D site survey.) If not, Pattern B, or a pull-based variant of A, becomes more attractive.
