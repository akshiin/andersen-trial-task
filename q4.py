import json
from datetime import date
from enum import Enum
from typing import Dict, List
from pydantic import BaseModel, Field


class NetworkType(str, Enum):
    IN_NETWORK = "In-Network"
    OUT_OF_NETWORK = "Out-of-Network"


class BenefitTerms(BaseModel):
    benefit_name: str
    annual_sub_limit: float
    coinsurance_in_network: float
    coinsurance_out_of_network: float
    deductible_per_visit: float = 0.0
    requires_pre_auth: bool = False
    is_covered_out_of_network: bool = True


class PolicyConfig(BaseModel):
    policy_ref: str
    annual_aggregate_limit: float
    benefits: Dict[str, BenefitTerms]


class Claim(BaseModel):
    claim_id: str
    service_date: date
    benefit_name: str
    network: NetworkType
    billed_amount: float
    pre_auth_obtained: bool
    is_chronic_related: bool
    diagnosis_note: str


def evaluate_exclusions(
    claim: Claim, benefit_rules: BenefitTerms, inception_date: date
) -> dict:
    """
    Evaluates policy rules to identify if a claim is fully denied,
    partially penalized, or fully payable.

    Returns a dictionary tracking status and an adjudication multiplier.
    """
    if (
        claim.network == NetworkType.OUT_OF_NETWORK
        and not benefit_rules.is_covered_out_of_network
    ):
        return {
            "status": "DENIED",
            "payout_modifier": 0.0,
            "reason": "Section 2 Table of Benefits: This benefit category is explicitly 'Not covered' when obtained Out-of-Network.",
        }

    # Rule B: Check Chronic / Pre-existing Waiting Period (e.g., Claim C2)
    if claim.is_chronic_related:
        # Calculate calendar months elapsed between policy inception and service date
        months_elapsed = (claim.service_date.year - inception_date.year) * 12 + (
            claim.service_date.month - inception_date.month
        )

        if months_elapsed < 6:
            return {
                "status": "DENIED",
                "payout_modifier": 0.0,
                "reason": f"Section 4 — Clause 4.2: Treatment for declared Chronic/Pre-existing Condition ({claim.diagnosis_note}) is not covered during the first 6 months from the Inception Date.",
            }

    # Rule C: Check Pre-authorisation Penalties (e.g., Claim C5)
    if benefit_rules.requires_pre_auth and not claim.pre_auth_obtained:
        return {
            "status": "PARTIALLY_DENIED",
            "payout_modifier": 0.80,  # 20% penalty reduction applied to insurer payout
            "reason": "Section 3 — General Condition GC-3: Elective treatment undertaken without mandatory 48-hour Pre-authorisation results in a 20% payment reduction.",
        }

    return {
        "status": "APPROVED",
        "payout_modifier": 1.0,
        "reason": "Meets all core policy coverage criteria.",
    }


def process_all_claims(
    claims: List[Claim], policy: PolicyConfig, inception_date: date
) -> List[dict]:
    """
    Iterates sequentially through all claims to evaluate coverage eligibility,
    calculate finances, and produce a complete audit log.
    """
    audit_log = []

    for claim in claims:
        # Extract corresponding benefit rule configuration
        benefit_rules = policy.benefits.get(claim.benefit_name)
        if not benefit_rules:
            raise KeyError(
                f"Benefit configuration rules missing for: '{claim.benefit_name}'"
            )

        # 1. Run the claim through the exclusion engine
        rule_check = evaluate_exclusions(claim, benefit_rules, inception_date)

        # 2. Calculate dynamic financial metrics using GC-1 Order of Calculation
        billed = claim.billed_amount

        # If fully denied by policy, eligible base is wiped to zero
        eligible_base = billed if rule_check["payout_modifier"] > 0 else 0.0

        # Evaluate Deductible (only applies to Outpatient Consultations)
        deductible_applied = 0.0
        if claim.benefit_name == "Outpatient Consultation" and eligible_base > 0:
            deductible_applied = min(benefit_rules.deductible_per_visit, eligible_base)

        remainder_after_deductible = max(0.0, eligible_base - deductible_applied)

        # Evaluate Coinsurance Share
        coinsurance_rate = (
            benefit_rules.coinsurance_in_network
            if claim.network == NetworkType.IN_NETWORK
            else benefit_rules.coinsurance_out_of_network
        )
        coinsurance_applied = remainder_after_deductible * coinsurance_rate

        # Calculate Insurer Share and apply any rule check modifiers (e.g., the 20% missing pre-auth penalty)
        tentative_insurer_pay = remainder_after_deductible - coinsurance_applied
        final_insurer_pay = round(
            tentative_insurer_pay * rule_check["payout_modifier"], 2
        )

        # The member absorbs the remaining costs (deductible, coinsurance, and any penalties/denials)
        final_member_pay = round(billed - final_insurer_pay, 2)

        # 3. Compile the structured claim settlement object
        audit_log.append(
            {
                "claim_id": claim.claim_id,
                "diagnosis_note": claim.diagnosis_note,
                "adjudication_status": rule_check["status"],
                "financial_breakdown": {
                    "billed_amount": round(billed, 2),
                    "insurer_pays": final_insurer_pay,
                    "member_pays": final_member_pay,
                },
                "rule_justification": rule_check["reason"],
            }
        )

    return audit_log


if __name__ == "__main__":
    policy_inception = date(2025, 1, 1)

    # Setup Complete Policy Matrix (Reflecting Section 2 Matrix + Section 5 Endorsement)
    securehealth_policy = PolicyConfig(
        policy_ref="GF-SH-B/2025",
        annual_aggregate_limit=250000.00,
        benefits={
            "Outpatient Consultation": BenefitTerms(
                benefit_name="Outpatient Consultation",
                annual_sub_limit=8000.00,
                coinsurance_in_network=0.10,
                coinsurance_out_of_network=0.30,
                deductible_per_visit=50.00,
            ),
            "Physiotherapy": BenefitTerms(
                benefit_name="Physiotherapy",
                annual_sub_limit=4000.00,  # Updated via Endorsement E1
                coinsurance_in_network=0.10,  # Updated via Endorsement E1
                coinsurance_out_of_network=0.30,
            ),
            "Inpatient & Surgery": BenefitTerms(
                benefit_name="Inpatient & Surgery",
                annual_sub_limit=250000.00,
                coinsurance_in_network=0.00,
                coinsurance_out_of_network=0.20,
                requires_pre_auth=True,  # Mandated via GC-3
            ),
            "Prescribed Medication": BenefitTerms(
                benefit_name="Prescribed Medication",
                annual_sub_limit=6000.00,
                coinsurance_in_network=0.20,
                coinsurance_out_of_network=1.00,
                is_covered_out_of_network=False,  # "Not covered" via Section 2 Matrix
            ),
        },
    )

    # Complete Dataset of Member Claims (C1 to C6)
    claims_dataset = [
        Claim(
            claim_id="C1",
            service_date=date(2025, 2, 15),
            benefit_name="Outpatient Consultation",
            network=NetworkType.IN_NETWORK,
            billed_amount=300.00,
            pre_auth_obtained=False,
            is_chronic_related=False,
            diagnosis_note="Acute viral illness (influenza)",
        ),
        Claim(
            claim_id="C2",
            service_date=date(2025, 3, 10),
            benefit_name="Outpatient Consultation",
            network=NetworkType.IN_NETWORK,
            billed_amount=400.00,
            pre_auth_obtained=False,
            is_chronic_related=True,
            diagnosis_note="Asthma review",
        ),
        Claim(
            claim_id="C3",
            service_date=date(2025, 8, 5),
            benefit_name="Outpatient Consultation",
            network=NetworkType.IN_NETWORK,
            billed_amount=400.00,
            pre_auth_obtained=False,
            is_chronic_related=True,
            diagnosis_note="Asthma review",
        ),
        Claim(
            claim_id="C4",
            service_date=date(2025, 12, 12),
            benefit_name="Physiotherapy",
            network=NetworkType.IN_NETWORK,
            billed_amount=3000.00,
            pre_auth_obtained=False,
            is_chronic_related=False,
            diagnosis_note="Lower-back strain",
        ),
        Claim(
            claim_id="C5",
            service_date=date(2025, 10, 3),
            benefit_name="Inpatient & Surgery",
            network=NetworkType.IN_NETWORK,
            billed_amount=18000.00,
            pre_auth_obtained=False,
            is_chronic_related=False,
            diagnosis_note="Elective knee arthroscopy",
        ),
        Claim(
            claim_id="C6",
            service_date=date(2025, 11, 20),
            benefit_name="Prescribed Medication",
            network=NetworkType.OUT_OF_NETWORK,
            billed_amount=500.00,
            pre_auth_obtained=False,
            is_chronic_related=False,
            diagnosis_note="Pharmacy prescription items",
        ),
    ]

    # Process all claims through the engine
    comprehensive_report = process_all_claims(
        claims=claims_dataset,
        policy=securehealth_policy,
        inception_date=policy_inception,
    )

    # Print out results for analysis
    print("\n========================================================")
    print("      Q4 COMPREHENSIVE SEQUENTIAL ADJUDICATION REPORT    ")
    print("========================================================\n")
    print(json.dumps(comprehensive_report, indent=4))
