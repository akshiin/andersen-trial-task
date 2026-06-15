from datetime import date

from pydantic import BaseModel, Field

from securehealth.models.enums import NetworkType


class Claim(BaseModel):
    claim_id: str
    service_date: date
    benefit_name: str = Field(
        ..., description="Must map directly to keys in PolicyConfig benefits"
    )
    network: NetworkType
    billed_amount: float
    pre_auth_obtained: bool
    is_chronic_related: bool
    diagnosis_note: str
