from securehealth.data.fixtures import create_base_policy
from securehealth.services.endorsement import resolve_q1_terms


def main() -> None:
    policy = create_base_policy()
    results = resolve_q1_terms(policy)

    print(
        f"Initial Section 2 Terms -> Coinsurance: {results['base_terms']['coinsurance_in_network_pct']}, Sub-limit: AED {results['base_terms']['sub_limit_aed']:,}"
    )
    print("Applied Section 5 (Endorsement E1) -> Endorsement overrides Section 2")
    print("\nFINAL ANSWER FOR Q1:")
    print(
        f"  * Member Coinsurance % (In-Network): {results['resolved_terms']['coinsurance_in_network_pct']}"
    )
    print(
        f"  * Annual Sub-limit (Physiotherapy): AED {results['resolved_terms']['sub_limit_aed']:,}"
    )


if __name__ == "__main__":
    main()
