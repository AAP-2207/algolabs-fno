import numpy as np
from scipy.stats import norm

def delta(S: float, K: float, T: float, r: float, sigma: float, option_type: str) -> float:
    """
    Calculate Delta of a European option.
    Delta measures the rate of change of the option price with respect to changes in the underlying price.
    """
    option_type = option_type.lower()
    if option_type not in ('call', 'put'):
        raise ValueError("option_type must be either 'call' or 'put'")

    if T <= 0 or S <= 0 or K <= 0 or sigma <= 0:
        if S == K:
            return 0.5 if option_type == 'call' else -0.5
        if option_type == 'call':
            return 1.0 if S > K else 0.0
        else:
            return -1.0 if S < K else 0.0

    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    
    if option_type == 'call':
        return float(norm.cdf(d1))
    else:
        return float(norm.cdf(d1) - 1.0)

def gamma(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """
    Calculate Gamma of a European option.
    Gamma measures the rate of change of Delta with respect to changes in the underlying price.
    Gamma is identical for call and put options.
    """
    if T <= 0 or S <= 0 or K <= 0 or sigma <= 0:
        return 0.0

    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    gamma_val = norm.pdf(d1) / (S * sigma * np.sqrt(T))
    return float(gamma_val)

def theta(S: float, K: float, T: float, r: float, sigma: float, option_type: str) -> float:
    """
    Calculate Theta of a European option, returned as per-day decay (annual theta / 365).
    Theta measures the sensitivity of the option price to the passage of time.
    """
    option_type = option_type.lower()
    if option_type not in ('call', 'put'):
        raise ValueError("option_type must be either 'call' or 'put'")

    if T <= 0 or S <= 0 or K <= 0 or sigma <= 0:
        return 0.0

    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)

    term1 = -(S * norm.pdf(d1) * sigma) / (2 * np.sqrt(T))
    
    if option_type == 'call':
        term2 = -r * K * np.exp(-r * T) * norm.cdf(d2)
        annual_theta = term1 + term2
    else:
        term2 = r * K * np.exp(-r * T) * norm.cdf(-d2)
        annual_theta = term1 + term2

    return float(annual_theta / 365.0)

def vega(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """
    Calculate Vega of a European option, expressed per 1 percentage point
    change in implied volatility (the industry-standard convention used by
    brokers/terminals), NOT per a full 100-percentage-point (1.0) change in
    sigma. This is why the result is divided by 100 — the raw Black-Scholes
    partial derivative dV/dsigma gives the per-100-point figure, which reads
    as wildly oversized (e.g. thousands) compared to what any real options
    screen displays (typically single or double digits for index options).
    Vega is identical for call and put options.
    """
    if T <= 0 or S <= 0 or K <= 0 or sigma <= 0:
        return 0.0
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    vega_val = S * np.sqrt(T) * norm.pdf(d1) / 100
    return float(vega_val)
