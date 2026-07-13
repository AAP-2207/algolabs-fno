import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_get_greeks_endpoint():
    response = client.get("/api/greeks?symbol=NIFTY")
    assert response.status_code == 200
    
    data = response.json()
    assert "fetched_at" in data
    assert "source" in data
    assert "age_minutes" in data
    assert "strikes" in data
    
    strikes = data["strikes"]
    assert len(strikes) > 0
    
    # Check shape of a single strike record
    first_record = strikes[0]
    assert "strike" in first_record
    assert isinstance(first_record["strike"], (int, float))
    
    # Verify CE or PE values if present
    if first_record["CE"] is not None:
        ce = first_record["CE"]
        for key in ("delta", "gamma", "theta", "vega", "computed_iv", "nse_iv", "ltp"):
            assert key in ce
            assert isinstance(ce[key], (int, float))
            
    if first_record["PE"] is not None:
        pe = first_record["PE"]
        for key in ("delta", "gamma", "theta", "vega", "computed_iv", "nse_iv", "ltp"):
            assert key in pe
            assert isinstance(pe[key], (int, float))
