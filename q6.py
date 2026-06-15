import csv
import json

from securehealth.data.fixtures import (
    POLICY_INCEPTION_DATE,
    create_all_claims,
    create_resolved_policy,
)
from securehealth.services.stateful_adjudication import build_settlement_statement

JSON_PATH = "settlement_statement.json"
CSV_PATH = "settlement_statement.csv"


def main() -> None:
    statement = build_settlement_statement(
        claims=create_all_claims(),
        policy=create_resolved_policy(),
        inception_date=POLICY_INCEPTION_DATE,
    )

    with open(JSON_PATH, "w", encoding="utf-8") as fh:
        json.dump(statement, fh, indent=4)

    totals = statement["year_totals"]
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=statement["csv_fields"])
        writer.writeheader()
        writer.writerows(statement["claims"])
        writer.writerow(
            {
                "claim_id": "YEAR TOTAL",
                "service_date": "",
                "benefit_name": "",
                "network": "",
                "billed_amount": totals["total_billed"],
                "eligible_amount": totals["total_eligible"],
                "deductible": totals["total_deductible"],
                "coinsurance_member_share": totals["total_coinsurance_member_share"],
                "insurer_paid": totals["total_insurer_paid"],
                "member_paid": totals["total_member_paid"],
                "decision": "",
                "reason": f"Remaining aggregate limit: AED {totals['remaining_aggregate_limit']:,.2f}",
            }
        )

    print(f"Settlement statement written to {JSON_PATH} and {CSV_PATH}")


if __name__ == "__main__":
    main()
