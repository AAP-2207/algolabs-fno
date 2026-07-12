import pytest
import numpy as np
from backend.core.bsm import bs_price

def test_bsm_atm():
    # ATM case: S=100, K=100, T=1, r=0.05, sigma=0.2
    S, K, T, r, sigma = 100.0, 100.0, 1.0, 0.05, 0.2
    
    call_price = bs_price(S, K, T, r, sigma, 'call')
    put_price = bs_price(S, K, T, r, sigma, 'put')
    
    # Assert call price ≈ 10.4506 (tolerance 0.01)
    assert call_price == pytest.approx(10.4506, abs=0.01)
    
    # Assert put price ≈ 5.5735
    assert put_price == pytest.approx(5.5735, abs=0.01)

def test_put_call_parity():
    # C - P = S - K * e^(-r * T)
    S, K, T, r, sigma = 100.0, 100.0, 1.0, 0.05, 0.2
    
    call_price = bs_price(S, K, T, r, sigma, 'call')
    put_price = bs_price(S, K, T, r, sigma, 'put')
    
    parity_diff = call_price - put_price
    expected_diff = S - K * np.exp(-r * T)
    
    assert parity_diff == pytest.approx(expected_diff, abs=1e-6)

def test_bsm_sanity_checks():
    S, T, r, sigma = 100.0, 1.0, 0.05, 0.2
    
    # ITM and OTM call/put sanity checks
    # Call price should decrease as K increases
    call_itm = bs_price(S, 90.0, T, r, sigma, 'call')
    call_atm = bs_price(S, 100.0, T, r, sigma, 'call')
    call_otm = bs_price(S, 110.0, T, r, sigma, 'call')
    
    assert call_itm > 0
    assert call_atm > 0
    assert call_otm > 0
    assert call_itm > call_atm > call_otm  # Decreases as K increases
    
    # Put price should increase as K increases
    put_otm = bs_price(S, 90.0, T, r, sigma, 'put')
    put_atm = bs_price(S, 100.0, T, r, sigma, 'put')
    put_itm = bs_price(S, 110.0, T, r, sigma, 'put')
    
    assert put_otm > 0
    assert put_atm > 0
    assert put_itm > 0
    assert put_itm > put_atm > put_otm  # Increases as K increases
