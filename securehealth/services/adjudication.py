from datetime import date
from typing import List

from securehealth.models.benefit import BenefitTerms
from securehealth.models.claim import Claim
from securehealth.models.enums import NetworkType
from securehealth.models.policy import PolicyConfig
from securehealth.services.settlement import compute_claim_finances


def evaluate_exclusions(
    claim: Claim, benefit_rules: BenefitTerms, inception_date: date
) -> dict:
    """
    Evaluates policy rules to identify if a claim is fully denied,
    partially penalized, or fully payable.
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

    if claim.is_chronic_related:
        months_elapsed = (claim.service_date.year - inception_date.year) * 12 + (
            claim.service_date.month - inception_date.month
        )

        if months_elapsed < 6:
            return {
                "status": "DENIED",
                "payout_modifier": 0.0,
                "reason": f"Section 4 — Clause 4.2: Treatment for declared Chronic/Pre-existing Condition ({claim.diagnosis_note}) is not covered during the first 6 months from the Inception Date.",
            }

    if benefit_rules.requires_pre_auth and not claim.pre_auth_obtained:
        return {
            "status": "PARTIALLY_DENIED",
            "payout_modifier": 0.80,
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
    """Evaluates coverage eligibility and calculates finances for each claim."""
    audit_log = []

    for claim in claims:
        benefit_rules = policy.benefits.get(claim.benefit_name)
        if not benefit_rules:
            raise KeyError(
                f"Benefit configuration rules missing for: '{claim.benefit_name}'"
            )

        rule_check = evaluate_exclusions(claim, benefit_rules, inception_date)
        finances = compute_claim_finances(
            billed=claim.billed_amount,
            benefit_name=claim.benefit_name,
            network=claim.network,
            policy_benefit=benefit_rules,
            payout_modifier=rule_check["payout_modifier"],
        )

        audit_log.append(
            {
                "claim_id": claim.claim_id,
                "diagnosis_note": claim.diagnosis_note,
                "adjudication_status": rule_check["status"],
                "financial_breakdown": {
                    "billed_amount": finances["billed"],
                    "insurer_pays": finances["insurer_pays"],
                    "member_pays": finances["member_pays"],
                },
                "rule_justification": rule_check["reason"],
            }
        )

    return audit_log
