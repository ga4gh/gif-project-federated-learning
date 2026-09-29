# 01: Flower hello world

**Time:** about 75 minutes
**Goal:** run a federated training job in Flower twice, first as a simulation and then as real separate processes, and come away knowing what a site has to run.
**Tested against:** Flower 1.39 (September 2026). Flower's CLI changes between minor versions; if a command below fails, the linked docs for your version are authoritative.

## Federated learning in five minutes

If you've already done FL, skip this section.

- A **model** is a set of numeric **weights**. Training means repeatedly nudging those weights to reduce error on training data.
- In **federated learning**, each site (a **client**) trains the same model on its own data. Only the weights leave the site, never the data.
- A **round** works like this. The **server** sends the current **global weights** to clients. Each client trains locally for a few passes over its data (**local epochs**) and sends back updated weights. The server combines them into new global weights.
- **FedAvg** is the standard way to combine them: a weighted average of the clients' weights, weighted by how many training examples each client has. It's a few lines of NumPy.
- A **strategy** is the server-side policy: which clients to pick each round, how to aggregate, and when to evaluate. FedAvg is the default strategy.
- **Non-IID** data means sites' data come from different distributions (in our case, different ancestry backgrounds). It's the realistic case, and it makes FL harder.
- **Differential privacy** (DP-SGD, via Opacus) adds calibrated noise during local training so the returned weights leak less about individual records. Not needed for this exercise.

Flower's vocabulary:

| Term | What it is |
|---|---|
| **ServerApp** | Your server-side code: the strategy and round loop |
| **ClientApp** | Your client-side code: load local data, train, return weights |
| **SuperLink** | The long-running server process that ServerApps run on |
| **SuperNode** | The long-running process at each site that ClientApps run on. It connects *outbound* to the SuperLink |
| **Simulation** | Everything in one process on your laptop, with virtual clients |
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
