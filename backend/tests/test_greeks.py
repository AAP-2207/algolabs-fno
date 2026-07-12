import pytest
from backend.core.greeks import delta, gamma, theta, vega

def test_greeks_atm():
    # S=100, K=100, T=1, r=0.05, sigma=0.2
    S, K, T, r, sigma = 100.0, 100.0, 1.0, 0.05, 0.2
    
    # Call and put deltas
    call_delta = delta(S, K, T, r, sigma, 'call')
    put_delta = delta(S, K, T, r, sigma, 'put')
    
    # ATM call delta should be roughly 0.5-0.65
    assert 0.5 <= call_delta <= 0.65
    # Put delta should be call delta - 1.0
    assert put_delta == pytest.approx(call_delta - 1.0, abs=1e-6)

    # Gamma should be positive
    g = gamma(S, K, T, r, sigma)
    assert g > 0

    # Vega should be positive
    v = vega(S, K, T, r, sigma)
    assert v > 0
    
    # Theta checks
    t_call = theta(S, K, T, r, sigma, 'call')
    t_put = theta(S, K, T, r, sigma, 'put')
    # Time decay is negative
    assert t_call < 0
    assert t_put < 0
