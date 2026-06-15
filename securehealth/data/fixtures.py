from datetime import date

from securehealth.models.benefit import BenefitTerms
from securehealth.models.claim import Claim
from securehealth.models.enums import NetworkType
from securehealth.models.policy import PolicyConfig

POLICY_REF = "GF-SH-B/2025"
ANNUAL_AGGREGATE_LIMIT = 250_000.00
POLICY_INCEPTION_DATE = date(2025, 1, 1)

ENDORSEMENT_E1_OVERRIDES = {
    "coinsurance_in_network": 0.10,
    "annual_sub_limit": 4000.00,
}


def _all_benefits() -> dict[str, BenefitTerms]:
    return {
        "Physiotherapy": BenefitTerms(
            benefit_name="Physiotherapy",
            annual_sub_limit=2500.00,
            coinsurance_in_network=0.20,
            coinsurance_out_of_network=0.30,
        ),
        "Outpatient Consultation": BenefitTerms(
            benefit_name="Outpatient Consultation",
            annual_sub_limit=8000.00,
            coinsurance_in_network=0.10,
            coinsurance_out_of_network=0.30,
            deductible_per_visit=50.00,
        ),
        "Inpatient & Surgery": BenefitTerms(
            benefit_name="Inpatient & Surgery",
            annual_sub_limit=250000.00,
            coinsurance_in_network=0.00,
            coinsurance_out_of_network=0.20,
            requires_pre_auth=True,
        ),
        "Prescribed Medication": BenefitTerms(
            benefit_name="Prescribed Medication",
            annual_sub_limit=6000.00,
            coinsurance_in_network=0.20,
            coinsurance_out_of_network=1.00,
            is_covered_out_of_network=False,
        ),
        "Diagnostics": BenefitTerms(
            benefit_name="Diagnostics",
            annual_sub_limit=10000.00,
            coinsurance_in_network=0.10,
            coinsurance_out_of_network=0.30,
        ),
    }


def create_base_policy() -> PolicyConfig:
    """Section 2 base policy before endorsements."""
    return PolicyConfig(
        policy_ref=POLICY_REF,
        annual_aggregate_limit=ANNUAL_AGGREGATE_LIMIT,
        benefits=_all_benefits(),
    )


def create_resolved_policy() -> PolicyConfig:
    """Full policy matrix with Section 5 Endorsement E1 applied (Q4)."""
    policy = create_base_policy()
    policy.apply_endorsement_override("Physiotherapy", ENDORSEMENT_E1_OVERRIDES)
    return policy


def create_all_claims() -> list[Claim]:
    return [
        Claim(
            claim_id="C1",
            service_date=date(2025, 2, 15),
            benefit_name="Outpatient Consultation",
            network=NetworkType.IN_NETWORK,
            billed_amount=300.00,
            pre_auth_obtained=False,
            is_chronic_related=False,
            diagnosis_note="Acute viral illness (influenza) — unrelated to asthma",
        ),
        Claim(
            claim_id="C2",
            service_date=date(2025, 3, 10),
            benefit_name="Outpatient Consultation",
            network=NetworkType.IN_NETWORK,
            billed_amount=400.00,
            pre_auth_obtained=False,
            is_chronic_related=True,
            diagnosis_note="Asthma review (declared chronic condition)",
        ),
        Claim(
            claim_id="C3",
            service_date=date(2025, 8, 5),
            benefit_name="Outpatient Consultation",
            network=NetworkType.IN_NETWORK,
            billed_amount=400.00,
            pre_auth_obtained=False,
            is_chronic_related=True,
            diagnosis_note="Asthma review (declared chronic condition)",
        ),
        Claim(
            claim_id="C4",
            service_date=date(2025, 12, 12),
            benefit_name="Physiotherapy",
            network=NetworkType.IN_NETWORK,
            billed_amount=3000.00,
            pre_auth_obtained=False,
            is_chronic_related=False,
            diagnosis_note="Lower-back strain (acute)",
        ),
        Claim(
            claim_id="C5",
            service_date=date(2025, 10, 3),
            benefit_name="Inpatient & Surgery",
            network=NetworkType.IN_NETWORK,
            billed_amount=18000.00,
            pre_auth_obtained=False,
            is_chronic_related=False,
            diagnosis_note="Elective knee arthroscopy (non-emergency)",
        ),
        Claim(
            claim_id="C6",
            service_date=date(2025, 11, 20),
            benefit_name="Prescribed Medication",
            network=NetworkType.OUT_OF_NETWORK,
            billed_amount=500.00,
            pre_auth_obtained=False,
            is_chronic_related=False,
            diagnosis_note="Pharmacy purchase at non-network pharmacy",
        ),
    ]
