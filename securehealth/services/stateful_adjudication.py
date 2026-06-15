from datetime import date
from typing import Dict, List

from securehealth.models.claim import Claim
from securehealth.models.policy import PolicyConfig
from securehealth.services.adjudication import evaluate_exclusions
from securehealth.services.settlement import compute_claim_finances


class StatefulAdjudicationEngine:
    """Processes claims chronologically while tracking sub-limits and aggregate balance."""

    def __init__(self, policy: PolicyConfig, inception_date: date):
        self.policy = policy
        self.inception_date = inception_date
        self.remaining_aggregate_limit = policy.annual_aggregate_limit
        self.remaining_sub_limits: Dict[str, float] = {
            name: benefit.annual_sub_limit for name, benefit in policy.benefits.items()
        }

    def process_claims_pipeline(self, claims: List[Claim]) -> dict:
        sorted_claims = sorted(claims, key=lambda claim: claim.service_date)

        settled_claims_log = []
        running_insurer_total = 0.0
        running_member_total = 0.0
        running_billed_total = 0.0

        for claim in sorted_claims:
            benefit_rules = self.policy.benefits[claim.benefit_name]
            rule_check = evaluate_exclusions(
                claim, benefit_rules, self.inception_date
            )

            billed = claim.billed_amount
            running_billed_total += billed

            finances = compute_claim_finances(
                billed=billed,
                benefit_name=claim.benefit_name,
                network=claim.network,
                policy_benefit=benefit_rules,
                payout_modifier=rule_check["payout_modifier"],
            )

            tentative_insurer_pay = finances["insurer_pays"]
            available_sub_limit = self.remaining_sub_limits[claim.benefit_name]

            final_insurer_pay = min(
                tentative_insurer_pay,
                available_sub_limit,
                self.remaining_aggregate_limit,
            )
            final_insurer_pay = round(max(0.0, final_insurer_pay), 2)
            final_member_pay = round(billed - final_insurer_pay, 2)

            self.remaining_sub_limits[claim.benefit_name] -= final_insurer_pay
            self.remaining_aggregate_limit -= final_insurer_pay

            running_insurer_total += final_insurer_pay
            running_member_total += final_member_pay

            settled_claims_log.append(
                {
                    "claim_id": claim.claim_id,
                    "billed": round(billed, 2),
                    "insurer_pays": final_insurer_pay,
                    "member_pays": final_member_pay,
                    "adjudication": rule_check["status"],
                }
            )

        return {
            "annual_summary": {
                "total_billed_amount": round(running_billed_total, 2),
                "total_insurer_payable": round(running_insurer_total, 2),
                "total_member_out_of_pocket": round(running_member_total, 2),
                "remaining_global_aggregate_limit": round(
                    self.remaining_aggregate_limit, 2
                ),
            },
            "detailed_ledger": settled_claims_log,
        }


def process_stateful_claims(
    claims: List[Claim], policy: PolicyConfig, inception_date: date
) -> dict:
    engine = StatefulAdjudicationEngine(policy, inception_date)
    return engine.process_claims_pipeline(claims)
