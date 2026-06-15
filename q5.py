import json

from securehealth.data.fixtures import (
    POLICY_INCEPTION_DATE,
    create_all_claims,
    create_resolved_policy,
)
from securehealth.services.stateful_adjudication import process_stateful_claims


def main() -> None:
    policy = create_resolved_policy()
    claims = create_all_claims()

    results = process_stateful_claims(
        claims=claims,
        policy=policy,
        inception_date=POLICY_INCEPTION_DATE,
    )

    print("\n========================================================")
    print("      Q5 STATEFUL SEQUENTIAL ADJUDICATION REPORT        ")
    print("========================================================\n")
    print(json.dumps(results, indent=4))


if __name__ == "__main__":
    main()
