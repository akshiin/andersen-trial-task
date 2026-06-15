import json

from securehealth.data.fixtures import create_all_claims, create_base_policy
from securehealth.services.settlement import calculate_single_claim


def main() -> None:
    policy = create_base_policy()
    claim = next(c for c in create_all_claims() if c.claim_id == "C1")

    try:
        applicable_benefit_rules = policy.benefits[claim.benefit_name]
    except KeyError:
        raise KeyError(
            f"Benefit rule configuration missing for: '{claim.benefit_name}'"
        )

    settlement_report = calculate_single_claim(
        claim=claim, policy_benefit=applicable_benefit_rules
    )

    print("\n========================================================")
    print("      Q3 RUNTIME VERIFICATION: CLAIM C1 SETTLEMENT      ")
    print("========================================================\n")
    print(json.dumps(settlement_report, indent=4))
    print("\n" + "-" * 56)


if __name__ == "__main__":
    main()
