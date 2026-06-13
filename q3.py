import json
from datetime import date
from enum import Enum
from typing import Dict, Optional
from pydantic import BaseModel, Field


class NetworkType(str, Enum):
    IN_NETWORK = "In-Network"
    OUT_OF_NETWORK = "Out-of-Network"


class BenefitTerms(BaseModel):
    benefit_name: str = Field(..., description="Name of the medical benefit")
    annual_sub_limit: float = Field(
        ..., description="Maximum sub-limit ceiling for the benefit year"
    )
    coinsurance_in_network: float = Field(
        ..., description="Member share decimal for In-Network (e.g. 0.10)"
    )
    coinsurance_out_of_network: float = Field(
        ..., description="Member share decimal for Out-of-Network"
    )
    deductible_per_visit: float = Field(
        0.0, description="Deductible flat fee applied per visit"
    )
    requires_pre_auth: bool = Field(
        False, description="True if benefit mandates pre-authorisation"
    )
    is_covered_out_of_network: bool = Field(
        True, description="False if explicitly excluded out-of-network"
    )


class PolicyConfig(BaseModel):
    policy_ref: str
    annual_aggregate_limit: float
    benefits: Dict[str, BenefitTerms] = Field(
        ..., description="Dictionary mapping benefit categories to terms"
    )


class Claim(BaseModel):
    claim_id: str
    service_date: date
    benefit_name: str = Field(
        ..., description="Must map directly to keys in PolicyConfig benefits"
    )
    network: NetworkType
    billed_amount: float
    pre_auth_obtained: bool
    is_chronic_related: bool
    diagnosis_note: str


def calculate_single_claim(claim: Claim, policy_benefit) -> dict:
    """
    Executes the exact GC-1 Order of Calculation:
    (a) Cap at Eligible Amount -> (b) Subtract Deductible -> (c) Apply Coinsurance
    """
    billed = claim.billed_amount

    # Step (a): Cap billed amount at Eligible Amount (R&C Check)
    # Per prompt instructions, all billed amounts are within R&C unless noted.
    eligible_amount = billed

    # Step (b): Determine and subtract Deductible
    # Deductible applies only to Outpatient Consultation per GC-4
    deductible = 0.0
    if claim.benefit_name == "Outpatient Consultation":
        deductible = policy_benefit.deductible_per_visit

    # Deductible cannot exceed the eligible amount of the bill
    deductible_applied = min(deductible, eligible_amount)
    remainder_after_deductible = eligible_amount - deductible_applied

    # Step (c): Apply Member Coinsurance percentage to the remainder
    coinsurance_pct = (
        policy_benefit.coinsurance_in_network
        if claim.network == "In-Network"
        else policy_benefit.coinsurance_out_of_network
    )
    coinsurance_applied = remainder_after_deductible * coinsurance_pct

    # Step (d): Insurer pays the balance
    tentative_insurer_pay = remainder_after_deductible - coinsurance_applied

    # Total member out-of-pocket for this specific sequence
    member_share = deductible_applied + coinsurance_applied

    return {
        "claim_id": claim.claim_id,
        "billed": round(billed, 2),
        "eligible": round(eligible_amount, 2),
        "deductible_applied": round(deductible_applied, 2),
        "coinsurance_applied": round(coinsurance_applied, 2),
        "insurer_pays": round(tentative_insurer_pay, 2),
        "member_pays": round(member_share, 2),
    }


if __name__ == "__main__":

    policy = PolicyConfig(
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
                annual_sub_limit=2500.00,
                coinsurance_in_network=0.20,
                coinsurance_out_of_network=0.30,
            ),
        },
    )

    claim_c1 = Claim(
        claim_id="C1",
        service_date=date(2025, 2, 15),
        benefit_name="Outpatient Consultation",
        network=NetworkType.IN_NETWORK,
        billed_amount=300.00,
        pre_auth_obtained=False,
        is_chronic_related=False,
        diagnosis_note="Acute viral illness (influenza)",
    )

    try:
        applicable_benefit_rules = policy.benefits[claim_c1.benefit_name]
    except KeyError:
        raise KeyError(
            f"Benefit rule configuration missing for: '{claim_c1.benefit_name}'"
        )

    settlement_report = calculate_single_claim(
        claim=claim_c1, policy_benefit=applicable_benefit_rules
    )

    print("\n========================================================")
    print("      Q3 RUNTIME VERIFICATION: CLAIM C1 SETTLEMENT      ")
    print("========================================================\n")
    print(json.dumps(settlement_report, indent=4))
    print("\n" + "-" * 56)
