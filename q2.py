from pydantic import BaseModel, Field


class PolicyConfig(BaseModel):
    policy_ref: str
    annual_aggregate_limit: float = Field(
        ..., description="The absolute maximum the Insurer will pay in a Policy Year"
    )

    _remaining_aggregate_balance: float = None

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
        else:
            # The remaining balance is less than the calculated payout
            allowed_payout = remaining
            self._remaining_aggregate_balance = 0.0
            return allowed_payout


if __name__ == "__main__":
    policy = PolicyConfig(
        policy_ref="GF-SH-B/2025",
        annual_aggregate_limit=250000.00,  # Stated in Section 2
    )

    # Initialize the tracking state
    policy.initialize_policy_year()

    print("--- Q2 Audit Trail & Global State Configuration ---")
    print(f"Policy Reference: {policy.policy_ref}")
    print(f"Parsed Annual Aggregate Limit: AED {policy.annual_aggregate_limit:,.2f}")
    print(f"Initial Active Tracking Balance: AED {policy.get_remaining_limit():,.2f}")

    print("\nFINAL ANSWER FOR Q2:")
    print(
        f"  * The Annual Aggregate Limit of the plan is: AED {policy.annual_aggregate_limit:,.2f}"
    )
