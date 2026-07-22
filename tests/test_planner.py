from retirement_planner.planner import estimate_years_until_depletion


def test_depletes_with_zero_return() -> None:
    years = estimate_years_until_depletion(
        starting_balance=100_000,
        annual_withdrawal=25_000,
        annual_return_rate=0.0,
    )
    assert years == 4


def test_invalid_withdrawal_raises() -> None:
    try:
        estimate_years_until_depletion(
            starting_balance=100_000,
            annual_withdrawal=0,
            annual_return_rate=0.03,
        )
    except ValueError as exc:
        assert "annual_withdrawal" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
