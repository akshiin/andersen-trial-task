from pydantic import BaseModel, Field


class BenefitTerms(BaseModel):
    benefit_name: str = Field(..., description="Name of the medical benefit")
    annual_sub_limit: float = Field(
        ..., description="Maximum sub-limit ceiling for the benefit year"
    )
    coinsurance_in_network: float = Field(
        ..., description="Member share decimal for In-Network (e.g. 0.10)"
    )
    coinsurance_out_of_network: float = Field(
        ..., description="Member share decimal for Out-of-Network"
    )
    deductible_per_visit: float = Field(
        0.0, description="Deductible flat fee applied per visit"
    )
    requires_pre_auth: bool = Field(
        False, description="True if benefit mandates pre-authorisation"
    )
    is_covered_out_of_network: bool = Field(
        True, description="False if explicitly excluded out-of-network"
    )
