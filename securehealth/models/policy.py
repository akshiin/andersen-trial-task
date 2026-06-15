from typing import Dict, Optional

from pydantic import BaseModel, Field

from securehealth.models.benefit import BenefitTerms


class PolicyConfig(BaseModel):
    policy_ref: str
    annual_aggregate_limit: float = Field(
        ..., description="The absolute maximum the Insurer will pay in a Policy Year"
    )
    benefits: Dict[str, BenefitTerms] = Field(
        default_factory=dict,
        description="Map of benefit names to their standard terms",
    )

    _remaining_aggregate_balance: Optional[float] = None

    def apply_endorsement_override(self, benefit_name: str, overrides: dict) -> None:
        """Dynamically updates base policy terms when an endorsement applies."""
        if benefit_name in self.benefits:
            current_terms = self.benefits[benefit_name]
            updated_data = current_terms.model_dump()
            updated_data.update(overrides)
            self.benefits[benefit_name] = BenefitTerms(**updated_data)

    def initialize_policy_year(self) -> None:
        """Resets or initializes the annual limit tracking state."""
        self._remaining_aggregate_balance = self.annual_aggregate_limit

    def get_remaining_limit(self) -> float:
        """Returns how much the insurer can still pay before hitting the cap."""
        if self._remaining_aggregate_balance is None:
            self.initialize_policy_year()
        return self._remaining_aggregate_balance

    def deduct_insurer_payout(self, amount: float) -> float:
        """
        Deducts an adjudication payout from the global aggregate limit balance.
        Returns the actual allowed payout after capping at the remaining limit.
        """
        remaining = self.get_remaining_limit()

        if amount <= remaining:
            self._remaining_aggregate_balance -= amount
            return amount

        allowed_payout = remaining
        self._remaining_aggregate_balance = 0.0
        return allowed_payout
