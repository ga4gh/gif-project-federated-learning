# 02: NVIDIA FLARE hello world

**Time:** about 60–75 minutes
**Goal:** run FLARE's `hello-pt` example, compare its structure with Flower's, and see what a FLARE site has to run.
**Tested against:** NVIDIA FLARE 2.7 (September 2026). If a command fails, the linked docs for your version are authoritative.

Do [01 Flower](../01-flower/) first; its "federated learning in five minutes" section applies here too.

## FLARE vocabulary

| Term | What it is |
|---|---|
| **Job** | The unit you submit: server-side workflow plus client-side training script |
| **Recipe / Job API** | Python used to define a job (e.g., a FedAvg recipe) instead of hand-written JSON configs |
| **Client API** | The few calls your training script makes: `flare.init()`, `flare.receive()`, `flare.send()` |
| **Simulator** | Runs the server and N clients on your laptop, like Flower's simulation |
| **POC mode** | Separate server and client processes on one machine, closer to a real deployment |
| **Provisioning / startup kits** | In production, each site gets a generated kit (certificates plus config) that its client uses to connect to the server |

## Step 1: Set up (10 min)

Use a separate virtual environment from Flower so the two don't conflict:

```bash
cd ~/fl-eval
python3.11 -m venv .venv-flare && source .venv-flare/bin/activate
pip install -U pip
pip install "nvflare[PT]"
nvflare --version
```

## Step 2: Get the example (5 min)

```bash
git clone --depth 1 https://github.com/NVIDIA/NVFlare.git
cd NVFlare/examples/hello-world/hello-pt
pip install -r requirements.txt
```

Make sure the example's branch matches your installed version. If `nvflare --version` isn't the version on `main`, check out the matching release tag instead of `--depth 1` on `main`.

## Step 3: Read the code (15 min)

- `model.py`: a plain PyTorch model.
- `client.py`: the training script. Find the `flare.init()` → loop { `flare.receive()` → load weights → train → `flare.send(FLModel(...))` } structure. The loop is *inside the client script*, which is a clue about how FLARE expects clients to live.
- `job.py`: the FedAvg recipe (rounds, number of clients, which script runs on clients) and the call that runs it in the simulator.
- `prepare_data.py`: data download and partitioning.

**Compare with Flower:** In Flower the framework calls your `train` function once per round. In FLARE your script calls `receive()` and `send()` in a loop. Same idea, but it changes what "one round as a job" would mean.

## Step 4: Run it in the simulator (10–15 min)

```bash
python job.py
```

The first run downloads CIFAR-10 (about 170 MB). Results land in `/tmp/nvflare/simulation/hello-pt`. Look at the per-round logs for the server and each client.

## Step 5: Poke at it (10 min)

In `job.py`, change the number of rounds and the number of clients, then rerun. Same questions as in Flower: how do accuracy and wall time change?

## Step 6 (stretch): POC mode (20 min)

POC mode runs a real server and real client processes on your machine, provisioned the way a production deployment would be. See the [FLARE docs](https://nvflare.readthedocs.io/en/main/) for your version (search "POC"). In outline:

```bash
nvflare poc prepare -n 2   # generate a server and two client "sites" locally
nvflare poc start          # start them
# submit the hello-pt job to the running system (see docs), then:
nvflare poc stop
```

**Watch for:** which process listens on a port and which ones connect to it; what's in each client's startup kit; how long the client processes stay up.

## Questions to answer in FINDINGS.md

Same questions as 01, so the two can be compared in the [summary table](../README.md#fl-frameworks-summary):

1. Where does the round loop live?
2. What has to run at a site, and for how long?
3. Which direction do network connections go, and on which ports?
4. How does a client find its local data?
5. Could the client be a one-shot job per round, launched by TES ([Pattern A](../PATTERNS.md))? What would you have to write yourself?
6. Roughly how many lines are FLARE-specific versus plain PyTorch?
7. What does FLARE's provisioning (certificates, startup kits) provide that overlaps with what GA4GH Passports and TES would provide?
