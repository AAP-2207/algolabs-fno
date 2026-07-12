import logging
import yfinance as yf
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def get_spot_price(ticker: str) -> float:
    """
    Fetch the latest regular market spot price for a given ticker from Yahoo Finance.
    Raises ValueError or other Exceptions if data fetching fails.
    """
    try:
        logger.info(f"Fetching spot price for ticker: {ticker}")
        ticker_obj = yf.Ticker(ticker)
        
        # Try history first as it is very reliable
        hist = ticker_obj.history(period="1d")
        if not hist.empty:
            price = hist['Close'].iloc[-1]
            return float(price)
            
        # Fallback to fast_info
        fast_info = getattr(ticker_obj, "fast_info", None)
        if fast_info and "last_price" in fast_info and fast_info["last_price"] is not None:
            return float(fast_info["last_price"])
            
        # Fallback to general info dictionary
        info = ticker_obj.info
        if info and "regularMarketPrice" in info and info["regularMarketPrice"] is not None:
            return float(info["regularMarketPrice"])
        if info and "currentPrice" in info and info["currentPrice"] is not None:
            return float(info["currentPrice"])

        raise ValueError(f"No regularMarketPrice or currentPrice found for ticker {ticker}.")
        
    except Exception as e:
        logger.error(f"Error fetching spot price for {ticker}: {str(e)}")
        raise e

def get_historical_ohlcv(ticker: str, period: str = "1mo", interval: str = "1d") -> List[Dict[str, Any]]:
    """
    Fetch historical candle data for a given ticker.
    Returns a list of dicts (date, open, high, low, close, volume).
    """
    try:
        logger.info(f"Fetching historical OHLCV for ticker: {ticker}, period: {period}, interval: {interval}")
        ticker_obj = yf.Ticker(ticker)
        hist = ticker_obj.history(period=period, interval=interval)
        
        if hist.empty:
            raise ValueError(f"No historical data found for {ticker} with period={period}, interval={interval}.")
            
        result = []
        for index, row in hist.iterrows():
            date_str = index.strftime("%Y-%m-%d %H:%M:%S") if hasattr(index, "strftime") else str(index)
            result.append({
                "date": date_str,
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": int(row["Volume"])
            })
            
        return result
        
    except Exception as e:
        logger.error(f"Error fetching historical OHLCV for {ticker}: {str(e)}")
        raise e
