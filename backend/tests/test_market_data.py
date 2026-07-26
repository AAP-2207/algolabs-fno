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
    res_data = response.json()
    
    # Assert top-level keys
    assert "source" in res_data
    assert res_data["source"] in ("live-polled", "mock")
    assert "fetched_at" in res_data
    assert isinstance(res_data["fetched_at"], str)
    assert "age_minutes" in res_data
    assert isinstance(res_data["age_minutes"], (int, float))
    assert "data" in res_data
    
    # Assert content of the actual option chain data under the "data" key
    opt_chain = res_data["data"]
    assert "records" in opt_chain
    assert "underlyingValue" in opt_chain["records"]
    assert opt_chain["records"]["underlyingValue"] > 0
    assert "data" in opt_chain["records"]
    assert len(opt_chain["records"]["data"]) > 0

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

def test_get_vol_surface():
    response = client.get("/api/vol-surface?symbol=NIFTY")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "NIFTY"
    assert data["source"] == "simulated-multi-expiry"
    assert "note" in data
    assert "simulated" in data["note"].lower()
    assert data["distinct_expiries_count"] >= 4
    assert data["distinct_strikes_count"] >= 5
    assert data["filtered_points_count"] > 0
    assert len(data["points"]) == data["filtered_points_count"]
    
    # Check sample point
    sample = data["points"][0]
    assert "strike" in sample
    assert "expiry_date" in sample
    assert "days_to_expiry" in sample
    assert "computed_iv" in sample
    assert sample["computed_iv"] > 0

