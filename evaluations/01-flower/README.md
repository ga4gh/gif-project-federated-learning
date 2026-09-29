# 01: Flower hello world

**Time:** about 90 minutes, including reading
**Goal:** understand Flower's architecture, then run a federated training job twice, first as a simulation and then as real separate processes, and come away knowing what a site has to run.
**Tested against:** Flower 1.39 (September 2026). Flower's CLI changes between minor versions; if a command below fails, the linked docs for your version are authoritative.

New to federated learning? Read the [FL primer](../FL-PRIMER.md) first (about 15 minutes). The rest of this page assumes its vocabulary: rounds, clients, FedAvg, strategies, non-IID.

## Flower in one page

[Flower](https://flower.ai) (package `flwr`) is an open-source FL framework from Flower Labs, first described in Beutel et al., 2020 (arXiv:2007.14390), and licensed Apache 2.0. Its design goal is to be **framework-agnostic and light**: your training code stays plain PyTorch, TensorFlow, JAX, scikit-learn, XGBoost, or Hugging Face, and Flower handles the round loop, the messaging, and the deployment plumbing. It targets both research (simulation) and production cross-silo deployments.

**Your code: two apps.** A Flower project is a Python package with two entry points:

- **ServerApp**: server-side logic. Usually you pick a **strategy** (FedAvg, FedProx, FedAdam/FedYogi, FedAvgM, and others) and say how many rounds to run. The strategy decides which clients to sample, what to send them, and how to aggregate what comes back.
- **ClientApp**: site-side logic. It receives the global weights plus config (learning rate, local epochs), loads the site's data, trains, and returns updated weights, the number of examples, and metrics. Evaluation works the same way.

Recent Flower versions pass these as **Messages** carrying typed records (arrays for weights, metrics, config). Project settings (rounds, local epochs, federation addresses) live in `pyproject.toml`. `flwr run` builds the project into an app bundle and submits it.

**Infrastructure: two long-running services.**

| Component | Runs where | Role |
|---|---|---|
| **SuperLink** | Coordinator | Accepts runs from `flwr run` (the Control API), runs the ServerApp, and hosts the **Fleet API** (default port 9092) that sites connect to |
| **SuperNode** | Each site | Connects *outbound* to the SuperLink's Fleet API, pulls work for its site, runs the ClientApp, and returns results. Started with site-specific `--node-config` (e.g., which data partition or path to use) |

The ServerApp and ClientApp run as subprocesses of the SuperLink and SuperNode, or in separate processes or containers for isolation. Flower publishes Docker images (`flwr/superlink`, `flwr/supernode`, and others) and Helm charts. TLS and SuperNode authentication are available for real deployments; the `--insecure` flag used in this exercise turns them off.

**Simulation vs. deployment.** The same ServerApp and ClientApp run unchanged in both. **Simulation** fakes many SuperNodes inside one machine (using Ray) with data split by **Flower Datasets** partitioners, including Dirichlet partitioning to create non-IID splits. **Deployment** uses real SuperLink and SuperNode processes on real machines.

**Privacy and security features.** Client-side "mods" wrap the ClientApp: secure aggregation (SecAgg+) and differential-privacy wrappers for central or local DP (clipping plus noise). You can also use Opacus inside your own training loop, which is what our proposal plans.

**What this means for us.** Flower's unit of deployment at a site is the **SuperNode, a long-running service** that dials out to the coordinator and runs every round over Flower's own channel. That matches [Pattern B](../PATTERNS.md) (TES launches a SuperNode for a training session; DRS supplies its data). For [Pattern A](../PATTERNS.md) (a TES task per round) we would use only Flower's aggregation logic, or plain FedAvg, and write the round loop ourselves. Step 6 below lets you see the SuperNode's behavior directly.

### Flower vocabulary

| Term | What it is |
|---|---|
| **ServerApp** | Your server-side code: the strategy and round loop |
| **ClientApp** | Your client-side code: load local data, train, return weights |
| **SuperLink** | The long-running server process that ServerApps run on |
| **SuperNode** | The long-running process at each site that ClientApps run on. It connects *outbound* to the SuperLink |
| **Simulation** | Everything on one machine, with virtual clients |
| **Deployment** | A real SuperLink plus real SuperNodes, as separate processes or machines |

## Step 1: Set up (10 min)

```bash
mkdir -p ~/fl-eval && cd ~/fl-eval
python3.11 -m venv .venv-flower && source .venv-flower/bin/activate
pip install -U pip
pip install "flwr[simulation]"
flwr --version
```

## Step 2: Create the quickstart app (5 min)

In Flower 1.39, `flwr new` pulls app templates from Flower Hub:

```bash
flwr new @flwrlabs/quickstart-pytorch
cd quickstart-pytorch
pip install -e .
```

If Flower Hub isn't reachable, use the same example from the repo instead:

```bash
git clone --depth 1 https://github.com/flwrlabs/flower.git
cd flower/examples/quickstart-pytorch
pip install -e .
```

## Step 3: Read the code before running it (15 min)

Open these files and find the following:

- `pyproject.toml`: the `[tool.flwr.app.config]` section (number of rounds, local epochs, learning rate), and where the number of simulated clients (SuperNodes) is set.
- `task.py` (or similar): the model definition, how the dataset is **partitioned** across clients, and the plain-PyTorch `train` / `test` functions. This part isn't Flower-specific.
- `client_app.py`: receives weights, calls `train`, returns updated weights and the number of examples.
- `server_app.py`: builds the FedAvg strategy and starts the round loop.

**Write down:** which lines are Flower and which are plain PyTorch.

## Step 4: Run it as a simulation (10 min)

```bash
flwr run .
```

The first run downloads the dataset. Watch the log: you should see numbered rounds, clients being sampled, and loss or accuracy after each round.

## Step 5: Poke at it (15 min)

Change one thing at a time and rerun:

1. Set the number of rounds to 1, then 10. How does final accuracy change?
2. Change the number of simulated clients (e.g., 2 vs. 10).
3. Change local epochs. More local training per round means fewer rounds are needed, but on non-IID data clients drift apart.

You now have the intuition behind the planted-signal experiment: more rounds and more (diverse) sites should beat any single site training alone.

## Step 6: Run it as separate processes (20 min)

This is the part that matters for our architecture. Follow Flower's guide [Run Flower with the Deployment Runtime](https://flower.ai/docs/framework/how-to-run-flower-with-deployment-engine.html) for your version. In outline, in separate terminals (activate the venv in each):

```bash
# Terminal 1: the server side
flower-superlink --insecure

# Terminals 2 and 3: two "sites". Each gets its own partition via --node-config.
# Exact flag names vary by version; take them from the guide above.
flower-supernode --insecure --superlink 127.0.0.1:9092 \
  --node-config "partition-id=0 num-partitions=2" ...
flower-supernode --insecure --superlink 127.0.0.1:9092 \
  --node-config "partition-id=1 num-partitions=2" ...

# Terminal 4: submit the app to the running federation
flwr run . <deployment-federation-name> --stream
```

**Watch for:**

- The SuperNodes start *before* any training is submitted and stay up afterward. They're services, not jobs.
- Each SuperNode opens the connection to the SuperLink. Nothing connects *into* a site.
- Each site found its data through `--node-config`. In our project that's where a DRS URI or a local path would go.

## Questions to answer in FINDINGS.md

1. Where does the round loop live?
2. What has to run at a site, and for how long?
3. Which direction do network connections go, and on which ports?
4. How does a client find its local data?
5. Could the ClientApp be run as a one-shot job per round, launched by TES ([Pattern A](../PATTERNS.md))? What would you have to write yourself?
6. Roughly how many lines are Flower-specific versus plain PyTorch?
