from scipy.optimize import brentq
from backend.core.bsm import bs_price

def implied_volatility(price: float, S: float, K: float, T: float, r: float, option_type: str) -> float:
    """
    Solve for implied volatility (sigma) using Brent's method (scipy.optimize.brentq).
    
    Parameters:
        price (float): The market price of the option.
        S (float): Spot price.
        K (float): Strike price.
        T (float): Time to expiry in years.
        r (float): Risk-free rate.
        option_type (str): 'call' or 'put'.

    Returns:
        float: Implied volatility (sigma).

    Raises:
        ValueError: If market price is out of bounds or brentq fails to converge.
    """
    # Objective function to find root of: bs_price(sigma) - price = 0
    def objective(sigma: float) -> float:
        return bs_price(S, K, T, r, sigma, option_type) - price

    # Search bracket for volatility (sigma) from 0.1% to 500%
    low_bracket = 0.001
    high_bracket = 5.0

    try:
        # Check signs of brackets to ensure there is a root in between
        f_low = objective(low_bracket)
        f_high = objective(high_bracket)
        
        if f_low * f_high > 0:
            raise ValueError(
                f"Implied volatility solver bracket [{low_bracket}, {high_bracket}] does not contain a root. "
                f"Market price: {price:.4f}, low bound price: {price + f_low:.4f}, high bound price: {price + f_high:.4f}."
            )
            
        iv = brentq(objective, low_bracket, high_bracket, xtol=1e-6)
        return float(iv)
    except Exception as e:
        if isinstance(e, ValueError):
            raise e
        raise ValueError(f"Brent's method failed to converge for implied volatility calculation: {str(e)}")
