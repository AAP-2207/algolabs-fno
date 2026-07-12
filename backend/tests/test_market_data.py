import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.services.yfinance_client import get_historical_ohlcv

client = TestClient(app)

def test_get_spot_price():
    # Request regular market spot price for Nifty index
    response = client.get("/api/spot?ticker=^NSEI")
    assert response.status_code == 200
    data = response.json()
    assert data["ticker"] == "^NSEI"
    assert isinstance(data["spot_price"], float)
    assert data["spot_price"] > 0

def test_get_option_chain():
    # Request option chain for NIFTY index
    response = client.get("/api/option-chain?symbol=NIFTY")
    assert response.status_code == 200
    data = response.json()
    assert "source" in data
    assert data["source"] in ("live", "mock")
    assert "records" in data
    assert "underlyingValue" in data["records"]
    assert data["records"]["underlyingValue"] > 0
    assert "data" in data["records"]
    assert len(data["records"]["data"]) > 0

def test_get_historical_ohlcv():
    # Verify historical data retrieval helper
    data = get_historical_ohlcv("^NSEI", period="5d", interval="1d")
    assert len(data) > 0
    first_row = data[0]
    assert "date" in first_row
    assert isinstance(first_row["open"], float)
    assert isinstance(first_row["high"], float)
    assert isinstance(first_row["low"], float)
    assert isinstance(first_row["close"], float)
    assert isinstance(first_row["volume"], int)
