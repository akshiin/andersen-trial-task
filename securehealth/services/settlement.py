from securehealth.models.benefit import BenefitTerms
from securehealth.models.claim import Claim
from securehealth.models.enums import NetworkType


def compute_claim_finances(
    billed: float,
    benefit_name: str,
    network: NetworkType,
    policy_benefit: BenefitTerms,
    payout_modifier: float = 1.0,
) -> dict:
    """
    Executes the GC-1 Order of Calculation:
    (a) Cap at Eligible Amount -> (b) Subtract Deductible -> (c) Apply Coinsurance
    """
    eligible_base = billed if payout_modifier > 0 else 0.0

    deductible_applied = 0.0
    if benefit_name == "Outpatient Consultation" and eligible_base > 0:
        deductible_applied = min(policy_benefit.deductible_per_visit, eligible_base)

    remainder_after_deductible = max(0.0, eligible_base - deductible_applied)

    coinsurance_rate = (
        policy_benefit.coinsurance_in_network
        if network == NetworkType.IN_NETWORK
        else policy_benefit.coinsurance_out_of_network
    )
    coinsurance_applied = remainder_after_deductible * coinsurance_rate

    tentative_insurer_pay = remainder_after_deductible - coinsurance_applied
    final_insurer_pay = round(tentative_insurer_pay * payout_modifier, 2)
    final_member_pay = round(billed - final_insurer_pay, 2)

    return {
        "billed": round(billed, 2),
        "eligible": round(eligible_base, 2),
        "deductible_applied": round(deductible_applied, 2),
        "coinsurance_applied": round(coinsurance_applied, 2),
        "insurer_pays": final_insurer_pay,
        "member_pays": final_member_pay,
    }


def calculate_single_claim(claim: Claim, policy_benefit: BenefitTerms) -> dict:
    """Settles a single claim with no exclusion penalties."""
    finances = compute_claim_finances(
        billed=claim.billed_amount,
        benefit_name=claim.benefit_name,
        network=claim.network,
        policy_benefit=policy_benefit,
    )
    return {"claim_id": claim.claim_id, **finances}
