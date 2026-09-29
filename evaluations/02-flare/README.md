# 02: NVIDIA FLARE hello world

**Time:** about 90 minutes, including reading
**Goal:** run FLARE's `hello-pt` example, compare its structure with Flower's, and see what a FLARE site has to run.
**Tested against:** NVIDIA FLARE 2.7 (September 2026). If a command fails, the linked docs for your version are authoritative.

New to federated learning? Read the [FL primer](../FL-PRIMER.md) first. Doing [01 Flower](../01-flower/) before this one makes the comparison easier.

## FLARE architecture primer

**What it is.** [NVIDIA FLARE](https://nvflare.readthedocs.io/) (Federated Learning Application Runtime Environment, package `nvflare`) is an open-source, Apache 2.0 SDK and runtime for FL. It grew out of NVIDIA's Clara medical-imaging FL work, the stack behind the 20-hospital EXAM study mentioned in the primer, and it's built for **cross-silo deployments between institutions**. Compared with Flower, FLARE puts more of the operational machinery in the box: provisioning with certificates, site-level security and privacy policies, job scheduling, and an admin console. That makes it heavier to learn and closer to a product.

### The participants

A FLARE deployment is called a **project**. It has three kinds of participants:

| Participant | Runs where | Role (in primer terms) |
|---|---|---|
| **FL Server** | Coordinator | The aggregator. The only component that **listens** on the network. It accepts client connections, schedules jobs, and runs the server side of each job (the round loop and aggregation) |
| **FL Client** | Each site | A long-running process that **connects outbound** to the server, receives jobs, and runs the site side (local training and evaluation) against local data |
| **Admin client** | Anyone with an admin role | A console or Python API (FLARE API) used to submit jobs, check status, pull results, and manage the system |

Each server and client is split into a **parent process** that stays up (the site's permanent presence in the federation) and a **job process** started for each job and torn down afterward. So a FLARE site is a long-lived service that spawns short-lived work, which is useful to keep in mind when mapping it to TES.

### Provisioning: identity and trust

Before anything runs, a project admin runs **provisioning** (`nvflare provision` from a `project.yml`, or the web-based **FLARE Dashboard**). It generates a **startup kit** for every participant: certificates signed by the project's root CA, connection config, and start scripts. Sites and server authenticate each other with **mutual TLS**, and the server's address is baked into the kits. Adding a site means provisioning a new kit and handing it over.

In primer terms, this is FLARE's answer to identity and the "who is allowed in this federation" question. In GA4GH terms, it overlaps with what Passports and AAI would provide, which is one of the things to note in your findings.

### Jobs: how work gets to sites

The unit of work is a **job**: a folder with the server-side configuration and code, client-side configuration and code, and metadata (which sites participate, the minimum number of clients, resource needs). An admin submits it. The server's **job scheduler** checks that the required sites are connected and have resources, then **deploys the job's code to the server and each client** and starts their job processes.

This is FLARE's own version of what TES and TRS do in our architecture: shipping versioned code to a site and running it. In a FLARE deployment it happens entirely inside FLARE's channel, not through a site's TES endpoint.

### The programming model: controllers, executors, and the Client API

- On the server, a **controller** (workflow) drives the job. It sends **tasks** ("train", "validate") to clients and gathers results. Built-in controllers cover FedAvg (scatter-and-gather), cyclic training (weights passed site to site), cross-site evaluation (every model tested on every site's data), and more.
- On each client, an **executor** handles those tasks.
- Most users don't write executors. They use the **Client API**: a normal training script adds `flare.init()`, then loops `flare.receive()` → train → `flare.send(FLModel(params=..., metrics=...))`. FLARE wraps that script in an executor and runs it in-process or as a separate launched process.
- The **Job API and recipes** (e.g., a FedAvg recipe) define the whole job in a few lines of Python. That's what `hello-pt/job.py` uses.

Compared with Flower: in Flower the framework calls your `train` function once per round. In FLARE your script owns a loop and asks for the next model. Both reduce to "receive weights, train locally, send weights back."

### Communication

Messages move over FLARE's own layered messaging system (**CellNet**) on gRPC, HTTP, or TCP drivers, with streaming for large models and optional relays for awkward network topologies. The practical upshot is the same as Flower: **sites only make outbound connections to the server**.

### Privacy, security, and governance features

This is where FLARE maps most directly onto the primer's privacy section:

- **Filters** transform data leaving or entering a site. Built-in filters add differential-privacy noise, send only a subset of the weights, or apply **homomorphic encryption** (via TenSEAL) so the server aggregates encrypted updates.
- **Site privacy policies** let each site define which filters must apply to any job it runs, independent of what the job submitter asked for.
- **Site authorization policies** let each site decide which roles and organizations may submit jobs to it, and what they may do.
- **Audit logs** record who did what.

The site-level policies are the most distinctive part: governance is enforced by each site, not just the coordinator. For the gap report, compare this with what GA4GH Passports, visas, and DUO can express.

### Algorithms beyond FedAvg

FLARE ships FedProx, FedOpt, SCAFFOLD, and Ditto (personalization), plus several things the primer mentions that go beyond neural networks: **federated XGBoost** (tree-based models for tabular EHR and annotation data), **federated statistics** (histograms and summaries), **PSI** for vertical FL, split learning, **swarm learning** (no central aggregator), and LLM fine-tuning examples.

### Three ways to run it

| Mode | What runs | When to use it |
|---|---|---|
| **Simulator** | Server and N clients in one process on one machine | Development; this exercise's Step 4 |
| **POC** | Real, separately started server and client processes on one machine, provisioned like production | Seeing the real architecture locally; this exercise's Step 6 |
| **Production** | Server and clients on separate machines at separate institutions, with provisioned startup kits | Real deployments |

### What this means for us

- A FLARE site is a **long-lived, provisioned client** that dials out to the server. That matches [Pattern B](../PATTERNS.md): TES could start the FLARE client for a training session, and DRS could supply its data.
- FLARE's provisioning, job deployment, and site policies **overlap** with what we want GA4GH APIs to do (TES/TRS for shipping and running code, Passports for identity and authorization). If we choose FLARE, part of the finding is where GA4GH is redundant with it and where GA4GH adds something FLARE lacks (standard data access through DRS, portability across frameworks).
- FLARE also documents a **third-party integration** path, where an externally launched training process attaches to a FLARE client through an agent. That could be a bridge toward [Pattern A](../PATTERNS.md) and is worth a look if FLARE stays in the running.

### FLARE vocabulary

| Term | What it is |
|---|---|
| **Project** | One FLARE deployment: a server, its clients, and admins |
| **Job** | The unit you submit: server-side workflow plus client-side training script |
| **Controller / Executor** | Server-side workflow logic / client-side task handler |
| **Client API** | The few calls your training script makes: `flare.init()`, `flare.receive()`, `flare.send()` |
| **Recipe / Job API** | Python used to define a job (e.g., a FedAvg recipe) |
| **Startup kit** | Per-participant certificates, config, and start scripts produced by provisioning |
| **Filter** | Transforms model data leaving or entering a site (DP, HE, variable exclusion) |
| **Simulator / POC / Production** | The three ways to run FLARE, from one process to fully distributed |

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
