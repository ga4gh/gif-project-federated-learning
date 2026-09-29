# 08: Round trip (node-in-a-box acceptance test)

**Time:** about 90 minutes the first time; about 5 minutes per rerun
**Lead:** Brian
**Goal:** prove that one Pattern A training round can go through a site using only GA4GH APIs, and find every place we have to hand-glue it. This is the test any candidate node-in-a-box stack gets scored against. The first stack here is **MinIO + Syfon (DRS) + Funnel (TES)**, the most promising combination from `03`–`04`.

## The round trip

Each step is phrased in terms of the APIs, not a specific implementation, so any stack can be tested the same way.

| Step | What happens | Stands in for |
|---|---|---|
| **A1** | Bring up the node from a clean clone. Time it. | A Driver Project installing the box |
| **A2** | Put an input file in object storage and register it in DRS. Keep the DRS URI. | The site's synthetic partition |
| **A3** | Put a second file in storage and register it. Keep the DRS URI. | The current global weights |
| **A4** | Submit a TES task whose inputs are the two objects. Variant **a**: pass the DRS URIs directly. Variant **b**: resolve each to a signed access URL first and pass those. | The coordinator dispatching a round |
| **A5** | The task reads both inputs and writes updated weights plus a small metrics file to storage. | Local training producing updated weights |
| **A6** | Register the output in DRS. Variant **a**: from inside the task (needs credentials in the container; not automated). Variant **b**: the coordinator does it after the task completes. | Write-back of updated weights |
| **A7** | Resolve the new DRS object, download it, and check its checksum. | The coordinator fetching weights to aggregate |
| **A8** | Confirm the task did a real training step (loss went down). | An actual FL round |

## What's in this folder

| Path | What it is |
|---|---|
| `docker-compose.yml` | MinIO (object storage, bucket `fl-eval`) and Syfon (DRS) |
| `config/syfon.yaml` | Syfon local-mode config: basic auth `drs-user` / `drs-pass`, SQLite, the MinIO bucket |
| `config/funnel.yaml` | Funnel config: TES on port 8000, local Docker worker, MinIO as S3 storage |
| `training/` | The training step: `train_round.py` (one local round; the interface below), `fedavg.py` (aggregation), `make_toy_data.py` (toy partitions), and a Dockerfile |
| `roundtrip/` | `roundtrip.py` runs A2–A8 and records results; `ga4gh_client.py` is a small, standard-library DRS and TES client |
| `acceptance-test.sh` | Checks the services, builds the training image, and runs `roundtrip.py` |
| `tests/fake_node.py` | Stand-in DRS and TES servers for testing the script without Docker. Not an evaluation of anything |

### The training-step interface

This is the contract Tracks A, B, and C plug into on Friday:

```
train_round.py --data-in DATA.csv --weights-in W.npz --weights-out W.npz --metrics-out M.json [--epochs N]
train_round.py --init --n-features N --weights-out GLOBAL0.npz          # coordinator, once
fedavg.py --out GLOBAL_NEXT.npz siteA.npz:1200 siteB.npz:800             # coordinator, each round
```

- **Data:** CSV with a header, numeric feature columns, and a 0/1 `label` column.
- **Weights:** `.npz` (named NumPy arrays). It's framework-neutral and trivial to average.
- **Metrics:** JSON with `n_examples` (FedAvg needs it), loss and accuracy before and after training, and the `sha256` and size of the weights file (DRS registration needs them).

The model is a small NumPy MLP so the image stays small and builds for both amd64 and arm64. Track A replaces the internals with PyTorch + Opacus (DP-SGD) and the real synthetic data, keeping this interface.

## Run it

### 1. Start storage and DRS (5 min)

```bash
cd evaluations/08-round-trip
docker compose up -d
docker compose ps                  # minio and syfon running; minio-init exited 0
curl -s -u drs-user:drs-pass http://localhost:8080/ga4gh/drs/v1/service-info | jq .
```

The MinIO console is at http://localhost:9001 (`minio-user` / `minio-pass`).

### 2. Install and start Funnel (10 min)

Funnel runs natively on your machine, not in compose, because its local worker launches task containers with your Docker. (Its published image drives containerd for Kubernetes instead.)

```bash
# Installs to ~/.local/bin. Read the script first.
curl -fsSL https://raw.githubusercontent.com/calypr/funnel/main/install.sh -o funnel-install.sh
less funnel-install.sh && bash funnel-install.sh
funnel version

# In a separate terminal, from this folder:
funnel server run --config config/funnel.yaml
```

### 3. Run the test

```bash
./acceptance-test.sh              # full run, A2–A8, builds fl-train:dev first
./acceptance-test.sh --hello      # plumbing only (alpine copies the weights; skips A8)
```

Each step prints ✅ PASS, 🟡 GLUE (worked only with code the APIs don't cover), ❌ FAIL, or ⏭️ SKIP, followed by a list of the glue it needed. It writes `results/<timestamp>.md`; paste that into `FINDINGS.md`. A FAIL on step A4 variant **a** is expected (see below) and doesn't fail the run.

## What we expect to find

Reading the Syfon and Funnel source suggests these outcomes. The run confirms or refutes each one.

1. **DRS write-back works, and it's in the spec.** DRS 1.5 defines `POST /objects/register` as optional functionality (advertised by `objectRegistrationSupported` in `service-info`), including registering data that's already in storage. Syfon implements it. So write-back is not a Syfon-specific extension.
2. **The DRS upload path doesn't.** DRS 1.5 also defines `POST /upload-request` for negotiating where to upload. Syfon rejects it (uploads go through its own API instead), so the test writes to MinIO with an S3 client and then registers. That's an implementation gap, not a spec gap.
3. **Syfon is strict about register requests.** It requires a sha256 checksum, rejects `mime_type` (which the spec lists), and returns `self_uri` as `drs://<id>` with no hostname. The script works around each of these and reports them.
4. **Funnel can't take `drs://` inputs.** Its storage backends are local, S3 (AWS and generic), GCS, Swift, HTTP(S), and FTP. So A4a fails and A4b (resolve to signed URLs first) is required. **TES says nothing about DRS URIs in inputs.** That's a spec gap worth raising.
5. **TES output logs report URL and size, not a checksum.** DRS registration needs a checksum, so the task writes a sidecar with the sha256 and the coordinator reads it. That's another candidate gap.
6. **Nothing links a TES output to a DRS object.** The coordinator has to register outputs after the task finishes. Whether TES should support "register outputs in this DRS" is a good question for the Federated Analysis Work Stream.
7. **Credentials inside tasks.** Variant A6a (the task registers its own output) needs DRS and storage credentials inside the container, and TES has no standard way to pass secrets. It's not automated. Try it by hand if there's time, and note that TES task definitions, including environment variables, are visible to anyone who can read the task.

## Troubleshooting

- **Signed URLs don't download.** Syfon builds signed URLs against the endpoint in `config/syfon.yaml` (`http://localhost:9000`), which works from your machine, where both Funnel and the script run. If you move Funnel into a container, it will need a URL host it can reach. Either use `http://minio:9000` in `syfon.yaml` and add `127.0.0.1 minio` to `/etc/hosts`, or use `host.docker.internal`. The host in a signed URL can't be rewritten afterward, because it's part of the signature.
- **`register` returns 401 or 403.** Check the basic-auth credentials. If local mode needs explicit permissions for create, see Syfon's `local_authz_csv` option in its [configuration docs](https://github.com/calypr/syfon/blob/development/docs/configuration.md).
- **The Syfon image won't pull, or runs under emulation.** Uncomment `build:` in `docker-compose.yml` to build from source.
- **A Funnel task fails before the executor runs.** Check the Funnel terminal. The `pull fl-train:dev` error is expected and harmless (the image is local); Funnel continues to `run`. Output upload errors usually mean the GenericS3 endpoint or credentials in `config/funnel.yaml` don't match MinIO.
- **Start over:** `docker compose down -v` removes MinIO and Syfon data. Delete `funnel-work-dir/` to reset Funnel.

## How this was tested

Written against the Syfon and Funnel source (Syfon `development`, Funnel `main`, September 2026) and run end to end against `tests/fake_node.py` plus a local S3 server (moto), which mimic the behaviors above. **It has not yet run against real Syfon and Funnel;** your Thursday run is the first. Expect some config tweaks, and please record them in `FINDINGS.md` so the next person doesn't hit them.

To rerun the no-Docker test:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r roundtrip/requirements.txt "moto[server]"
moto_server -p 9000 &
python tests/fake_node.py &
python roundtrip/roundtrip.py
```
