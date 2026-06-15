from securehealth.data.fixtures import ENDORSEMENT_E1_OVERRIDES
from securehealth.models.policy import PolicyConfig


def resolve_q1_terms(policy: PolicyConfig) -> dict:
    """Simulates auditing the policy terms before and after endorsement resolution."""
    base_physio = policy.benefits["Physiotherapy"]

    policy.apply_endorsement_override("Physiotherapy", ENDORSEMENT_E1_OVERRIDES)
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
