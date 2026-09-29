# Federated learning primer

Background for the [evaluations](README.md), written for people who know genomics infrastructure well but haven't done federated learning. It covers the core mechanics, the kinds of problems FL fits in genomics and EHR work, and the approaches a real project typically combines. The framework-specific primers build on it: [Flower](01-flower/README.md#flower-in-one-page) and [NVIDIA FLARE](02-flare/README.md#flare-architecture-primer).

## The core idea

Federated learning (FL) trains one model across data held by several parties without moving the data. The model goes to the data; only model updates come back.

- A **model** is a set of numeric **weights** (parameters). Training nudges them, a little at a time, to reduce error on training examples. One full pass over a dataset is an **epoch**.
- Each participant (a **client**, in our case a **site**) holds its own data and trains the shared model locally.
- A **server** (the **aggregator**, our **coordinator**) combines the clients' updates into a new **global model**.
- One cycle is a **round**: the server sends the global weights; each client trains for a few **local epochs** and returns updated weights (plus how many examples it trained on); the server aggregates. Repeat for tens to hundreds of rounds.
- **FedAvg** (McMahan et al., 2017) is the baseline aggregation: the new global weights are the average of the clients' weights, weighted by each client's example count. It's a few lines of NumPy.
- A **strategy** is the server-side policy for a round: which clients to use, how to aggregate, when to evaluate, and what to do when a client drops out.

What moves over the network is the model, typically kilobytes to a few MB for the classifiers we're discussing and gigabytes for foundation models, once per client per round. Raw records never move.

## How FL relates to things you already know

- **Meta-analysis / summary statistics.** Each site computes statistics once, and they're combined. Fine for GWAS-style association testing. FL is *iterative*: many rounds of back-and-forth, which is what lets it fit models that can't be decomposed into one-shot summaries (neural networks, and statistical models that need shared LD or covariate structure, as in Experiment 2's fine-mapping).
- **Federated analysis.** The broader GA4GH term: sending any computation to the data (queries, workflows, statistics). FL is the machine-learning subset of it.
- **Distributed training in one data center.** It uses the same math, but assumes data you control, fast networks, and identical hardware. FL assumes none of those.

## Flavors of FL

- **Cross-silo vs. cross-device.** Cross-device FL runs on millions of phones (keyboard prediction). **Cross-silo** FL runs across a handful to a few dozen institutions, each with a lot of data, reliable servers, and a governance agreement. Genomics and EHR work is almost always cross-silo, which is the setting Flower and FLARE target for institutional use.
- **Horizontal FL.** Sites hold the *same kinds of features* for *different individuals*. Our Experiment 1 is horizontal: every site has the same variant annotation features for different variants and patients. This is the common case and what FedAvg is built for.
- **Vertical FL.** Sites hold *different features* for the *same individuals*: say, genotypes at a sequencing center and clinical outcomes in a hospital EHR. It needs privacy-preserving record linkage first (**private set intersection**, PSI) and different algorithms (split learning, vertical logistic regression). It's harder, and rarer in practice.
- **Federated evaluation.** Test an existing model on every site's held-out data without moving that data. It's often the first, low-risk step before federated training.
- **Personalization.** Train a global model, then fine-tune it locally at each site. Useful when sites differ a lot.

## Where it gets hard

**Heterogeneous (non-IID) data.** Sites differ systematically. In genomics that means ancestry and population structure, sequencing platform and pipeline batch effects, and ascertainment (a rare disease clinic versus a population biobank). In EHR it means coding practices, local lab units, and patient mix. Clients' models then pull in different directions, and plain FedAvg converges slower or to a worse model. Common remedies: **FedProx** (penalizes drifting far from the global model), **SCAFFOLD** (corrects for client drift), server-side optimizers like **FedAdam/FedYogi** (FedOpt), and personalization. Our planted-signal design deliberately makes the data non-IID so the demo exercises this.

**Unequal data sizes and dropouts.** A small site's update gets less weight under FedAvg. Sites go offline mid-run, so strategies set minimum client counts and timeouts. Montalvo et al. (2025) tested dropout robustness for exactly our variant classifier.

**Harmonization.** FL doesn't fix inconsistent data. Every site must produce the same features in the same format: consistent variant annotation (the same VEP/CADD/REVEL versions, the same reference build) for genomics, and a common data model such as OMOP for EHR. In practice this is often the largest share of the work. Synthetic data lets us sidestep it for the demo, and we should say so plainly in the write-up.

## Privacy: what FL does and doesn't protect

Keeping data at the site is necessary but not sufficient. Model updates can leak information about the training data: **membership inference** (was this patient in the training set?) and **gradient inversion** (reconstructing training examples from updates) are both demonstrated attacks. The standard defenses, often combined:

- **Differential privacy (DP).** Add calibrated noise so no single record measurably changes the output. **DP-SGD** (implemented by Opacus for PyTorch) clips each example's gradient and adds noise during local training. The privacy budget **ε (epsilon)** is the knob: lower ε means more privacy and a less accurate model. Values of about 1–8 are common in the genomic FL literature. Measuring that trade-off against our planted signal is one of Experiment 1's outputs.
- **Secure aggregation.** Clients mask their updates so the server only ever sees the *sum*, never an individual site's update (Bonawitz et al., 2017).
- **Homomorphic encryption (HE).** The server aggregates encrypted updates without decrypting them. It's stronger, but costs more compute and bandwidth.
- **Trusted execution environments.** The aggregator runs in attested confidential-computing hardware.

The usual threat model is an "honest but curious" server plus possibly curious peer sites. None of this replaces governance. Sites still need agreements about what may leave (updates, final models), who can submit jobs, and for what purpose. That's where GA4GH Passports, visas, and DUO come in.

## Genomics and EHR use cases

| Use case | Typical model | Examples |
|---|---|---|
| Variant pathogenicity classification | MLP or gradient-boosted trees on annotation features | Montalvo et al., *Bioinformatics* 2025 (FedLearnVar), the basis of our Experiment 1 |
| Phenotype / polygenic risk prediction across biobanks and ancestries | Neural networks, penalized regression | Kolobkov et al., *Frontiers in Big Data* 2024; federated transfer learning for multi-ancestry PRS (Tian et al.) |
| Federated GWAS and fine-mapping | Iterative logistic or linear models; Bayesian fine-mapping | sPLINK (Nasirigerdeh et al., *Genome Biology* 2022); Argonne's APPFL federated GWAS and fine-mapping (our Experiment 2) |
| Clinical outcome prediction from EHR | Logistic regression, gradient-boosted trees, neural networks | EXAM: 20 institutions predicting COVID-19 oxygen needs (Dayan et al., *Nature Medicine* 2021, built on NVIDIA's FL stack) |
| Medical imaging | CNN segmentation / classification | FeTS: 71 sites, brain tumor segmentation (Pati et al., *Nature Communications* 2022) |
| Fine-tuning foundation models | Parameter-efficient fine-tuning (e.g., LoRA) of genomic or clinical language models | Emerging; both Flower and FLARE ship examples |

Two observations. Gradient-boosted trees (e.g., federated XGBoost) are often the strongest choice for tabular EHR and annotation features, and both major frameworks support them. And the EHR world has a mature federated *analysis* culture (OHDSI network studies over OMOP) that FL builds on rather than replaces.

## What a typical project looks like

1. **Harmonize.** Agree on the data model and feature pipeline every site runs (reference build, annotation versions, OMOP concepts).
2. **Baselines.** Train local-only models at each site, and a centralized model where that's allowed (on public or synthetic data). These define "did federation help?"
3. **Pick the model and strategy.** Start with FedAvg; move to FedProx, FedOpt, or personalization if the non-IID data hurts.
4. **Privacy controls, matched to governance.** DP, secure aggregation, or HE, and a written statement of what leaves each site.
5. **Evaluate federatedly.** Test every model (local, federated, centralized) on every site's held-out data. Report per-site results, not just the average; the per-site view is where the ancestry story shows up.
6. **Operate.** Provisioning, identity and authorization, networking, monitoring, reproducibility (versioned code, containers, data snapshots). This is where GA4GH APIs come in, and it's what this project tests.

## How this maps to our project

| FL concept | Experiment 1 |
|---|---|
| Client / site | A Driver Project running the node-in-a-box |
| Local data | A synthetic, ancestry-skewed variant partition, registered in the site's DRS |
| Server / aggregator | The coordinator |
| Moving the model each round | DRS (weights in and out); TES/WES to launch training ([Pattern A](PATTERNS.md)), or the framework's own channel (Pattern B) |
| Strategy | FedAvg to start |
| Privacy | Opacus DP-SGD at the sites; ε sweep after M3 |
| Governance | Static tokens for now; Passports and DUO later |
| Evaluation | Federated vs. local-only on held-out data, and recovery of the planted signal |
