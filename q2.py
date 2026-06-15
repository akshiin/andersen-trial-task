from securehealth.data.fixtures import ANNUAL_AGGREGATE_LIMIT, POLICY_REF
from securehealth.models.policy import PolicyConfig


def main() -> None:
    policy = PolicyConfig(
        policy_ref=POLICY_REF,
        annual_aggregate_limit=ANNUAL_AGGREGATE_LIMIT,
    )
    policy.initialize_policy_year()

    print(f"Policy Reference: {policy.policy_ref}")
    print(f"Annual Aggregate Limit: AED {policy.annual_aggregate_limit:,.2f}")
    print(f"Remaining Aggregate Limit: AED {policy.get_remaining_limit():,.2f}")

    print("\nFINAL ANSWER FOR Q2:")
    print(
        f"  * The Annual Aggregate Limit of the plan is: AED {policy.annual_aggregate_limit:,.2f}"
    )


if __name__ == "__main__":
    main()
