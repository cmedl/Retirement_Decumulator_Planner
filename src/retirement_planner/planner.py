"""Core retirement decumulation calculations."""


def estimate_years_until_depletion(
    starting_balance: float,
    annual_withdrawal: float,
    annual_return_rate: float,
    max_years: int = 100,
) -> int:
    """Estimate how many full years a portfolio can support withdrawals.

    Returns the number of completed years before the balance is depleted,
    capped by ``max_years``.
    """
    if starting_balance < 0:
        raise ValueError("starting_balance must be non-negative")
    if annual_withdrawal <= 0:
        raise ValueError("annual_withdrawal must be positive")
    if max_years <= 0:
        raise ValueError("max_years must be positive")

    balance = starting_balance
    for year in range(max_years):
        balance *= 1 + annual_return_rate
        balance -= annual_withdrawal
        if balance <= 0:
            return year + 1

    return max_years
