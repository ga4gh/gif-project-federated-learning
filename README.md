# GIF Project: Federated Learning with GA4GH APIs

A GA4GH Implementation Forum (GIF) project hosting configs, tutorials, scripts, and documentation for federated learning (FL) demonstrations built on GA4GH APIs.

**GIF Co-lead Point of Contact:** Brian O'Connor (Nimbus Informatics, GIF co-lead)

**Project coordinators:** Brian O'Connor (Nimbus Informatics, GIF co-lead), Venkat Malladi (Verily), Ravi Madduri and Matthew Joel (Argonne National Laboratory)

## Background

### The problem

Much of the genomic data most useful for training models or running statistical analyses can't be pooled. Clinical variant interpretations, biobank genotypes, and LD matrices sit at individual hospitals, labs, and biobanks behind privacy law, consent terms, and institutional governance. Any single site's data is often too small, or too narrow in ancestry, to produce a model that generalizes.

Federated learning moves the computation to the data. Each site trains on (or computes statistics from) its local data, and only model updates, typically protected with differential privacy, go back to a central aggregator. After repeated rounds the aggregated model approaches what pooled training would produce, and the raw data never leaves any site.

FL frameworks such as NVIDIA FLARE, Flower, and APPFL handle orchestration and aggregation well, but each brings its own mechanisms for dispatching work, moving artifacts, and authenticating sites. That is what makes cross-institution deployments hard: every participating site has to adopt the framework's plumbing. GA4GH already defines standard APIs for these pieces, and many institutions are deploying them for other reasons:

- **WES / TES**: dispatch each round's training or compute task to a site
- **DRS**: register and read input datasets; write model weights and other per-round artifacts back
- **Passports / AAI**: authorize the orchestrator to submit work and access data at partner sites
- **TRS (Dockstore)**: versioned, checksummed workflow and container definitions
- **DUO**: machine-readable data-use conditions on each dataset

Over the past year the Federated AI/ML Working Group (FLWG) in the GA4GH Federated Analysis Work Stream mapped the core FL challenges (data access, compute orchestration, telemetry, governance) onto these standards. This project turns that conceptual work into running, multi-institution demonstrations. The goals are to show FL frameworks operating on top of GA4GH APIs, publish reproducible reference deployments, and produce evidence-based feedback on where the APIs fall short for iterative AI/ML workloads. Expected gap areas include DRS write-back, model artifact provenance metadata, machine-to-machine token delegation, and ML capability fields in service-info.

### Two experiments, one project

This project merges two GIF proposals submitted in 2026 that share the same goal and much of the same stack. They run as independent experiments with their own leads, use cases, and timelines, and share infrastructure, lessons learned, and the API gap analysis where they overlap.

Both experiments use fully synthetic data with a planted, known signal, so we can measure directly whether federation recovers what single-site analysis misses.

#### Experiment 1: Federated variant pathogenicity classification (NVIDIA FLARE / Flower)

**Leads:** Brian O'Connor (Nimbus Informatics), Venkat Malladi (Verily)

**Proposal:** [Federated Learning Demonstration Using GA4GH APIs](https://docs.google.com/document/d/1xbTro9lAqqdS9HEH6pi_1xYB6PAk--Jm_qbcXJRefPY/edit)

Trains a classifier that predicts whether a single nucleotide variant is pathogenic or benign, across sites that each hold a synthetic, ClinVar-derived variant dataset (CADD and REVEL scores, conservation, gnomAD allele frequencies, consequence annotations). Each site draws allele frequencies from a different gnomAD subpopulation so the data is non-IID. The design follows [Montalvo et al. (Bioinformatics, 2025)](https://academic.oup.com/bioinformatics/article/41/10/btaf523/8258608) and extends their [FedLearnVar](https://github.com/RausellLab/FedLearnVar) simulation into a real multi-site deployment. We shim an existing FL framework onto GA4GH APIs (NVIDIA FLARE or Flower; the choice is still open): local training jobs (PyTorch with Opacus DP-SGD) are dispatched through WES or TES, datasets and model weights are read from and written back to DRS, cross-site access is authorized with Passports, and the workflow is registered in Dockstore. We'll build on the GA4GH Starter Kit and other community implementations, evaluating which fit best. Outputs are a reproducible reference deployment, a privacy/utility characterization, and a WES/TES, DRS, and Passport gap analysis.

#### Experiment 2: Federated fine-mapping (APPFL)

**Leads:** Ravi Madduri and Matthew Joel (Argonne National Laboratory)

**Proposal:** [Federated AI/ML Analysis with APPFL framework](https://docs.google.com/document/d/1iFgc23-wd5LTWBLZKhBs9_xkNTpokVgIrCpRWorUgiw/edit)

Performs statistical fine-mapping of GWAS-significant loci across synthetic, 1000 Genomes-derived cohorts partitioned by ancestry, with genotypes and LD matrices never leaving their site. Fine-mapping is where federation should show the clearest advantage over meta-analysis, because substituting a shared-reference LD panel degrades causal-variant resolution. Argonne's APPFL framework handles orchestration, including a federated solver derived from SuSiEx. TES is the dispatch API over pluggable execution backends (Globus Compute on HPC, Kubernetes, Funnel), DRS registers inputs and per-round artifacts, and DUO encodes data-use terms. Planned sites are Argonne (US), Covenant University (Nigeria), and MBZUAI (UAE). Outputs include a turn-key federation node installer and a TES, DRS, and DUO gap analysis.

#### At a glance

| | Experiment 1 | Experiment 2 |
|---|---|---|
| Scientific task | Variant pathogenicity classification | Multi-ancestry fine-mapping |
| FL framework | NVIDIA FLARE or Flower (TBD) | APPFL |
| Compute dispatch | WES / TES | TES (Globus Compute, Kubernetes, Funnel backends) |
| Data access | DRS | DRS |
| Auth / governance | Passports | DUO (+ Globus Auth) |
| Workflow registry | TRS / Dockstore | TRS / Dockstore |
| Synthetic data source | ClinVar-derived variant features | 1000 Genomes Phase 3 genotypes |
| Leads | Brian O'Connor, Venkat Malladi | Ravi Madduri, Matthew Joel |

## Working notes

_Notes from early planning, to be reorganized as the README develops._

### Software we need

* Passports for auth
* WES or TES for execution
* DRS for data access
* maybe Data Connect for discovery of inputs/outputs

### Who's evaluating

* Andrew - GSOC stack
* Kyle - Syfon (https://calypr.org/tools/syfon/) and DRS 1.6, TES - funnel
* Brian - DRS starter kit
  * Starter Kit site: https://starterkit.ga4gh.org, https://starterkit.ga4gh.org/docs/starter-kit-apis/overview
  * Includes DRS (1.3 experimental only), WES, Data Connect, Passports UI, Passports broker
  * Reference Cloud is a bit different: https://docs.refcloud.ga4gh.org, https://github.com/ga4gh/ga4gh-reference-cloud/blob/main/milestones/2026-09-28-GA4GH-Plenary-Milestones.md
  * Seems to have DRS 1.5, or at least targeting it for the GA4GH Plenary. Has a UI too.
* Ravi - actively adding GA4GH APIs to APPFL
* WES - which workflow engine? Nextflow? Cromwell?
* Passports - can we get Tom's help? https://starterkit.ga4gh.org/docs/starter-kit-apis/passport/passport_overview/
