import pytest
from backend.core.bsm import bs_price
from backend.core.iv_solver import implied_volatility

def test_iv_solver_round_trip():
    # Known inputs
    S, K, T, r, original_sigma = 100.0, 100.0, 0.5, 0.05, 0.25
    
    for option_type in ('call', 'put'):
        price = bs_price(S, K, T, r, original_sigma, option_type)
        recovered_sigma = implied_volatility(price, S, K, T, r, option_type)
        assert recovered_sigma == pytest.approx(original_sigma, abs=0.001)

def test_iv_solver_bounds_error():
    S, K, T, r = 100.0, 100.0, 0.5, 0.05
    
    # Market price 0.0 is below theoretical minimum price for sigma >= 0.001
    with pytest.raises(ValueError) as exc_info:
        implied_volatility(0.0, S, K, T, r, 'call')
    assert "does not contain a root" in str(exc_info.value)
    
    # Market price 1000.0 is above maximum price for sigma <= 5.0
    with pytest.raises(ValueError) as exc_info:
        implied_volatility(1000.0, S, K, T, r, 'call')
    assert "does not contain a root" in str(exc_info.value)
