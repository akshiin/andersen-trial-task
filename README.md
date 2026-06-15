# SecureHealth Adjudication Engine

## Conceptual Approach & Architecture

### 1. Rules-as-Data Architecture

Policy parameters (like a 10% coinsurance rate or an AED 50 deductible) are not written directly into the code logic. Instead, this engine stores all policy settings as structured, read-only data objects using **Pydantic v2**. The calculation functions never depend on specific values. To change an endorsement or switch to a different plan, you just create a new data object — the math code stays the same and works for any member.

### 2. Hybrid Automation Strategy

This engine is built to scale in the real world using a **Hybrid Architecture**:

* **The Input Layer (Deterministic Schemas):** Raw data from medical bills or invoices is read and checked against strict typed `Claim` schemas. This removes errors from manual input or AI-generated guesses on important fields like service dates and network types.

* **The Processing Core (Deterministic Python Logic):** All financial calculations follow a fixed, step-by-step pipeline that matches the policy's **GC-1 Order of Calculation** (Base Eligibility $\rightarrow$ Deductible Subtraction $\rightarrow$ Coinsurance Splits $\rightarrow$ Dynamic Limit Checks).

* **The Output Layer (User Explanation Generation):** The engine produces a structured JSON settlement record with `rule_justifications` generated directly by the code. This output is easy to pass into an LLM to create plain-language letters or explanation dashboards for customers.

---

## Why Naive Vector-Search/RAG Approaches Fail on This Task

A standard vector-search (RAG) or LLM-agent approach is too unreliable for health-insurance claim adjudication and will not produce the accurate audit trails this work requires. Here is why:

1. **Context Window Fragmentation & Shadow Overrides:** RAG splits documents into chunks. If the engine picks up a base benefit limit (e.g., the Physiotherapy cap) from one chunk, it will likely miss an Endorsement clause in a different chunk that changes that value.


2. **Lack of Chronological State Awareness:** Policy limits and annual caps decrease over time as claims are processed. LLMs have no built-in mechanism to track running totals and balances across multiple separate claim calculations.


3. **Mathematical Instability:** LLMs are text prediction models, not calculators. They often produce wrong numbers or fail entirely when asked to perform chained operations like deductible subtractions, coinsurance splits, and sliding-scale cap checks in sequence.

---

## Project Structure Overview

All shared engine logic lives in the `securehealth/` package, split into three layers: **Models $\rightarrow$ Services $\rightarrow$ Data**. The top-level scripts use this package to run each question and print results.

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

The top-level scripts (`q1.py` through `q6.py`) are simple runners. They load the fixture data, pass it through the right service functions, and print the results (JSON output for questions 3 to 5; file output for question 6).

| Script | Question Target | Internal Modules Called | Primary Objective |
| --- | --- | --- | --- |
| `q1.py` | Endorsement Resolution | `endorsement.resolve_q1_terms` | Shows the Physiotherapy sub-limit and coinsurance values before and after Endorsement E1 is applied.
| `q2.py` | Aggregate Initialisation | `models.policy.PolicyConfig` | Creates a fresh policy config and prints the base aggregate limit (AED 250,000).
| `q3.py` | Single-Claim Settlement | `settlement.calculate_single_claim` | Runs Claim **C1** through the GC-1 calculation steps and shows the deductible and 10% coinsurance split.
| `q4.py` | Batch Exclusions | `adjudication.process_all_claims` | Processes all claims (C1–C6) one by one, marking which ones are not payable using the chronic condition filter (Exclusion 4.2) and late-submission penalty (GC-3).
| `q5.py` | Stateful Adjudication | `stateful_adjudication.StatefulAdjudicationEngine` | Runs all six claims in order, updating sub-limits and the aggregate balance after each claim.
| `q6.py` | Settlement Statement | `stateful_adjudication.build_settlement_statement` | Builds a full settlement report per claim (billed, eligible, deductible, coinsurance, insurer-paid, member-paid, decision/reason) with year-end totals, saved to `settlement_statement.json` and `settlement_statement.csv`.

### Running the Engine Locally

This project uses `uv` for fast and reliable dependency management. Run the steps below to set up your environment and execute any question script:

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

Each layer only depends on the layer below it, keeping the code clean and easy to change:

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