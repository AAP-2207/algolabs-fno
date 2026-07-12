# risk-free rate r should be sourced as a MIBOR-based proxy (to be wired in a later phase),
# and these functions assume European-style index options.

import numpy as np
from scipy.stats import norm

def bs_price(S: float, K: float, T: float, r: float, sigma: float, option_type: str) -> float:
    """
    Price European options using the Black-Scholes-Merton formula.

    Formula:
        Call Price: C = S * N(d1) - K * e^(-r * T) * N(d2)
        Put Price:  P = K * e^(-r * T) * N(-d2) - S * N(-d1)

        where:
            d1 = (ln(S/K) + (r + (sigma^2)/2) * T) / (sigma * sqrt(T))
            d2 = d1 - sigma * sqrt(T)
            N(x) is the cumulative standard normal distribution function.

    Parameters:
        S (float): Spot price of the underlying asset
        K (float): Strike price
        T (float): Time to expiration in years (T > 0)
        r (float): Risk-free interest rate (annualized)
        sigma (float): Volatility of the underlying asset (annualized)
        option_type (str): 'call' or 'put' (case-insensitive)

    Returns:
        float: Option price
    """
    option_type = option_type.lower()
    if option_type not in ('call', 'put'):
        raise ValueError("option_type must be either 'call' or 'put'")

    # Boundary conditions
    if T <= 0:
        if option_type == 'call':
            return max(S - K, 0.0)
        else:
            return max(K - S, 0.0)

    if S <= 0 or K <= 0:
        return 0.0

    if sigma <= 0:
        # Zero volatility limit: discounted expected value
        discount = np.exp(-r * T)
        if option_type == 'call':
            return max(S - K * discount, 0.0)
        else:
            return max(K * discount - S, 0.0)

    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)

    if option_type == 'call':
        price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    else:
        price = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)

    return float(price)
