from typing import Dict
from pydantic import BaseModel, Field


class BenefitTerms(BaseModel):
    benefit_name: str
    annual_sub_limit: float
    coinsurance_in_network: float
    coinsurance_out_of_network: float
    deductible_per_visit: float = 0.0


class PolicyConfig(BaseModel):
    policy_ref: str
    annual_aggregate_limit: float
    benefits: Dict[str, BenefitTerms] = Field(
        ..., description="Map of benefit names to their standard terms"
    )

    def apply_endorsement_override(self, benefit_name: str, overrides: dict) -> None:
        """Dynamically updates base policy terms when an endorsement applies."""
        if benefit_name in self.benefits:
            current_terms = self.benefits[benefit_name]
            updated_data = current_terms.model_dump()
            updated_data.update(overrides)
            self.benefits[benefit_name] = BenefitTerms(**updated_data)


# Base Policy Rules from Section 2 (Table of Benefits)
base_policy = PolicyConfig(
    policy_ref="GF-SH-B/2025",
    annual_aggregate_limit=250000.00,
    benefits={
        "Physiotherapy": BenefitTerms(
            benefit_name="Physiotherapy",
            annual_sub_limit=2500.00,  # Base limit from Section 2
            coinsurance_in_network=0.20,  # Base 20% from Section 2
            coinsurance_out_of_network=0.30,
        ),
        "Outpatient Consultation": BenefitTerms(
            benefit_name="Outpatient Consultation",
            annual_sub_limit=8000.00,
            coinsurance_in_network=0.10,
            coinsurance_out_of_network=0.30,
            deductible_per_visit=50.00,
        ),
    },
)

# Endorsement E1 Data from Section 5
endorsement_e1_overrides = {
    "coinsurance_in_network": 0.10,  # Reduced to 10% by E1
    "annual_sub_limit": 4000.00,  # Increased to AED 4,000 by E1
}


def resolve_q1_terms(policy: PolicyConfig) -> dict:
    """Simulates auditing the policy terms before and after endorsement resolution."""
    # 1. Inspect base terms
    base_physio = policy.benefits["Physiotherapy"]

    # 2. Apply Endorsement E1 (as dictated by Section 1 precedence rules)
    policy.apply_endorsement_override("Physiotherapy", endorsement_e1_overrides)
    resolved_physio = policy.benefits["Physiotherapy"]

    return {
        "base_terms": {
            "coinsurance_in_network_pct": f"{base_physio.coinsurance_in_network * 100}%",
            "sub_limit_aed": base_physio.annual_sub_limit,
        },
        "resolved_terms": {
            "coinsurance_in_network_pct": f"{resolved_physio.coinsurance_in_network * 100}%",
            "sub_limit_aed": resolved_physio.annual_sub_limit,
        },
    }


if __name__ == "__main__":
    results = resolve_q1_terms(base_policy)

    print("--- Q1 Audit Trails & Executed Derivations ---")
    print(
        f"Initial Section 2 Terms -> Coinsurance: {results['base_terms']['coinsurance_in_network_pct']}, Sub-limit: AED {results['base_terms']['sub_limit_aed']:,}"
    )
    print(
        f"Applied Section 5 (Endorsement E1) -> Precedence rule triggered (Endorsement overrides Section 2)."
    )
    print("\nFINAL ANSWER FOR Q1:")
    print(
        f"  * Member Coinsurance % (In-Network): {results['resolved_terms']['coinsurance_in_network_pct']}"
    )
    print(
        f"  * Annual Sub-limit (Physiotherapy): AED {results['resolved_terms']['sub_limit_aed']:,}"
    )
