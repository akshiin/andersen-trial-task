from datetime import date
from typing import Dict, List

from securehealth.models.claim import Claim
from securehealth.models.policy import PolicyConfig
from securehealth.services.adjudication import evaluate_exclusions
from securehealth.services.settlement import compute_claim_finances

_SETTLEMENT_CSV_FIELDS = [
    "claim_id",
    "service_date",
    "benefit_name",
    "network",
    "billed_amount",
    "eligible_amount",
    "deductible",
    "coinsurance_member_share",
    "insurer_paid",
    "member_paid",
    "decision",
    "reason",
]


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


def build_settlement_statement(
    claims: List[Claim],
    policy: PolicyConfig,
    inception_date: date,
) -> dict:
    """
    Runs the full GC-1 pipeline chronologically, capturing the complete financial
    breakdown per claim (eligible, deductible, coinsurance, insurer/member split)
    while depleting sub-limits and the aggregate ceiling in order.

    Returns a dict with ``claims`` (one row per claim) and ``year_totals``.
    The ``csv_fields`` key carries the canonical column order for CSV export.
    """
    sorted_claims = sorted(claims, key=lambda c: c.service_date)

    remaining_aggregate = policy.annual_aggregate_limit
    remaining_sub_limits: Dict[str, float] = {
        name: benefit.annual_sub_limit for name, benefit in policy.benefits.items()
    }

    claim_rows: List[dict] = []
    totals = dict.fromkeys(
        ["billed", "eligible", "deductible", "coinsurance", "insurer_paid", "member_paid"],
        0.0,
    )

    for claim in sorted_claims:
        benefit_rules = policy.benefits[claim.benefit_name]
        rule_check = evaluate_exclusions(claim, benefit_rules, inception_date)
        finances = compute_claim_finances(
            billed=claim.billed_amount,
            benefit_name=claim.benefit_name,
            network=claim.network,
            policy_benefit=benefit_rules,
            payout_modifier=rule_check["payout_modifier"],
        )

        final_insurer_pay = round(
            max(
                0.0,
                min(
                    finances["insurer_pays"],
                    remaining_sub_limits[claim.benefit_name],
                    remaining_aggregate,
                ),
            ),
            2,
        )
        final_member_pay = round(claim.billed_amount - final_insurer_pay, 2)

        remaining_sub_limits[claim.benefit_name] -= final_insurer_pay
        remaining_aggregate -= final_insurer_pay

        totals["billed"] += claim.billed_amount
        totals["eligible"] += finances["eligible"]
        totals["deductible"] += finances["deductible_applied"]
        totals["coinsurance"] += finances["coinsurance_applied"]
        totals["insurer_paid"] += final_insurer_pay
        totals["member_paid"] += final_member_pay

        claim_rows.append(
            {
                "claim_id": claim.claim_id,
                "service_date": claim.service_date.isoformat(),
                "benefit_name": claim.benefit_name,
                "network": claim.network.value,
                "billed_amount": round(claim.billed_amount, 2),
                "eligible_amount": finances["eligible"],
                "deductible": finances["deductible_applied"],
                "coinsurance_member_share": round(finances["coinsurance_applied"], 2),
                "insurer_paid": final_insurer_pay,
                "member_paid": final_member_pay,
                "decision": rule_check["status"],
                "reason": rule_check["reason"],
            }
        )

    year_totals = {
        "total_billed": round(totals["billed"], 2),
        "total_eligible": round(totals["eligible"], 2),
        "total_deductible": round(totals["deductible"], 2),
        "total_coinsurance_member_share": round(totals["coinsurance"], 2),
        "total_insurer_paid": round(totals["insurer_paid"], 2),
        "total_member_paid": round(totals["member_paid"], 2),
        "remaining_aggregate_limit": round(remaining_aggregate, 2),
    }

    return {
        "claims": claim_rows,
        "year_totals": year_totals,
        "csv_fields": _SETTLEMENT_CSV_FIELDS,
    }
