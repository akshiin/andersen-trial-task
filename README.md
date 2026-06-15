# SecureHealth Adjudication Engine

## Conceptual Approach & Architecture

### 1. Rules-as-Data Architecture

Instead of hardcoding policy parameters (such as a 10% coinsurance rate or an AED 50 deductible) inside the logical code loops, this engine treats policy configurations purely as structured, immutable datasets using **Pydantic v2**. The adjudication functions are completely decoupled from individual values; modifying an endorsement or swapping to a different insurance plan is accomplished by instantiating a new data configuration block, leaving the mathematical core pristine and enabling the generalisation for unseen members.

### 2. Hybrid Automation Strategy

For real-world scalability, this engine is designed with a **Hybrid Architecture** mindset:

* **The Input Layer (Deterministic Schemas):** Raw, unstructured data from medical bills or invoices is parsed and validated into strictly typed `Claim` payloads, eliminating human input or LLM hallucination errors on critical data fields like service dates and network types.

* **The Processing Core (Deterministic Python Logic):** The actual mathematical ledger calculations follow a strict, sequential pipeline mirroring the policy wording's **GC-1 Order of Calculation** (Base Eligibility $\rightarrow$ Deductible Subtraction $\rightarrow$ Coinsurance Splits $\rightarrow$ Dynamic Limit Checks). A probabilistic LLM should never calculate financial payouts; this code guarantees 100% predictable, auditable figures down to the exact cent.

* **The Output Layer (User Explanation Generation):** The engine yields a highly structured JSON settlement ledger complete with native code-generated `rule_justifications`. This transparent output is structured to easily integrate into downstream LLMs to auto-generate empathetic, plain-language customer letters or explanation dashboards.

### 3. Progressive Capability Progression

The project is built sequentially. `q1` resolves policy changes via endorsements. `q3` handles standalone financial math. `q4` injects an operational exclusion filter (catching temporal waiting periods and pre-authorisation penalties). `q5` chains everything together inside a stateful ledger that depletes individual benefit sub-limits and the overarching annual aggregate ceiling chronologically. `q6` produces a structured settlement statement — one row per claim with the full financial breakdown — exported as both a machine-readable JSON file and a human-readable CSV table.

---

## Why Naive Vector-Search/RAG Approaches Fail on This Task

A typical vector-search (RAG) or an unstructured LLM-agent-router approach is highly brittle and will fail to deliver the rigorous audit trails required for health-insurance claim adjudication for the following reasons:

1. **Context Window Fragmentation & Shadow Overrides:** RAG divides documents into chunks. If an engine pulls a baseline benefit limit (e.g., Physiotherapy standard limit) from one page chunk, it will likely miss an Endorsement clause located on a separate page chunk that fundamentally overrides that value.


2. **Lack of Chronological State Awareness:** Policy limits and annual aggregate caps deplete continuously across a timeline. Linguistic LLMs do not possess an internal, stateful memory machine capable of tracking precise historical math accumulators across multiple distinct claim calculations.


3. **Mathematical Instability:** Large Language Models are fundamentally statistical language prediction models, not arithmetic processors. They easily hallucinate or fail when executing complex order-of-operations loops involving consecutive deductible subtractions, coinsurance percentages, and sliding-scale caps.

---

## Project Structure Overview

The shared engine logic is contained inside the internal library `securehealth/`, which is separated cleanly into three distinct structural layers: **Models $\rightarrow$ Services $\rightarrow$ Data**. The entry scripts sit above this library to orchestrate execution and output telemetry.

```
andersen-trial-task/
├── pyproject.toml         # Project metadata, dependencies, and Hatchling build backend
├── uv.lock                # Locked dependency versions for absolute build reproducibility
├── .python-version        # Pins environment execution to Python 3.11
├── .gitignore             # Standard Python and uv environment git ignores
├── README.md              # Project documentation and architectural overview
├── q1.py                  # Entry point: Endorsement resolution (Question 1)
├── q2.py                  # Entry point: Annual aggregate limit setup (Question 2)
├── q3.py                  # Entry point: Single-claim settlement calculation (Question 3)
├── q4.py                  # Entry point: Batch adjudication + policy exclusions (Question 4)
├── q5.py                  # Entry point: Stateful sequential adjudication engine (Question 5)
├── q6.py                  # Entry point: Structured settlement statement — JSON + CSV output (Question 6)
└── securehealth/          # Shared core domain package
    ├── __init__.py        # Re-exports public services and domain types
    ├── models/            # Pydantic domain models (Split by concept, not by question)
    │   ├── __init__.py    # Central entry point for core models
    │   ├── enums.py       # Type-safe enums (e.g., NetworkType)
    │   ├── benefit.py     # BenefitTerms schema (caps, sub-limits, network cover rules)
    │   ├── policy.py      # PolicyConfig schema (limits, endorsement appliers, ledger state)
    │   └── claim.py       # Claim schema (billed amounts, flags, notes, dates)
    ├── services/          # Business logic and financial calculation pipelines
    │   ├── __init__.py    # Central entry point for service classes and functions
    │   ├── endorsement.py # Endorsement E1 parameter transformation logic
    │   ├── settlement.py  # Core GC-1 calculation pipeline implementation
    │   ├── adjudication.py# Policy exclusion and penalty evaluation filters
    │   └── stateful_adjudication.py # Stateful adjudication engine + settlement statement builder
    └── data/              # Centralized testing data and policy fixtures
        ├── __init__.py    # Central entry point for centralized data
        └── fixtures.py    # Policy rules, Endorsement E1, and Claims C1–C6 datasets

```

---

## Entry Point Mapping & Execution

The top-level scripts (`q1.py` through `q6.py`) act as thin runnable interfaces. They extract centralized fixture data, route payloads through their designated service layers, and print structured outputs (clean JSON formatting for questions 3 to 5; file output for question 6).

| Script | Question Target | Internal Modules Called | Primary Objective |
| --- | --- | --- | --- |
| `q1.py` | Endorsement Resolution | `endorsement.resolve_q1_terms` | Compares and outputs Physiotherapy sub-limit and coinsurance rules before and after applying Endorsement E1.
| `q2.py` | Aggregate Initialisation | `models.policy.PolicyConfig` | Generates a clean policy configuration state and extracts the base aggregate limit (AED 250,000).
| `q3.py` | Single-Claim Settlement | `settlement.calculate_single_claim` | Processes Claim **C1** through the GC-1 order of calculation, computing the exact deductible and 10% network coinsurance split.
| `q4.py` | Batch Exclusions | `adjudication.process_all_claims` | Loops sequentially through all claims (C1–C6) to flag non-payable files, applying temporal chronic filters (Exclusion 4.2) and operational penalties (GC-3).
| `q5.py` | Stateful Adjudication | `stateful_adjudication.StatefulAdjudicationEngine` | Executes the complete chronological calculation loop across all six claims, updating dynamic sub-limits and the aggregate limit pool after each step.
| `q6.py` | Settlement Statement | `stateful_adjudication.build_settlement_statement` | Produces a full per-claim settlement statement (billed, eligible, deductible, coinsurance, insurer-paid, member-paid, decision/reason) plus year totals, written to `settlement_statement.json` and `settlement_statement.csv`.

### Running the Engine Locally

This project leverages `uv` for lightning-fast, predictable dependency management. Follow these steps to sync your virtual environment and execute any targeted trial question runner:

```bash
# Clone the repository and navigate to the project root
cd andersen-trial-task

# Synchronize virtual environment dependencies and lock state
uv sync

# Run specific question scripts to inspect formatted ledger console printouts
uv run python q1.py
uv run python q3.py
uv run python q5.py

# Run q6 to generate settlement_statement.json and settlement_statement.csv
uv run python q6.py

```

---

## Layered Architecture Pattern

The system's modular dependencies flow strictly downwards, guaranteeing a clean separation of concerns:

```
[Entry Points]            q1.py … q6.py (Orchestrate and output JSON to console; q6 writes JSON + CSV files)
                                │
                                ▼
[Business Logic]   securehealth/services/ (Pure functions for math & exclusion filters)
                                │
                                ▼
[Domain Models]     securehealth/models/ (Strict validation schemas via Pydantic v2)
                                ▲
                                │
[Data Ledger]         securehealth/data/ (Centralized ground-truth contract configurations)

```