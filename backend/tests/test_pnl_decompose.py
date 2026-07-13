import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_pnl_decompose_endpoint():
    payload = {
        "strike": 100.0,
        "option_type": "CE",
        "position": "buy",
        "quantity": 100,
        "entry_price": 10.0,
        "current_price": 12.5,
        "current_S": 105.0,
        "previous_S": 100.0,
        "days_elapsed": 1.0,
        "volatility": 0.20,
        "days_to_expiry": 30.0,
        "current_volatility": 0.20
    }
    
    response = client.post("/api/pnl-decompose", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert "total_pnl" in data
    assert "delta_pnl" in data
    assert "gamma_pnl" in data
    assert "theta_pnl" in data
    assert "vega_pnl" in data
    assert "residual" in data
    assert "summary" in data
    
    # Assert exact math for total_pnl: (12.5 - 10.0) * 100 = 250.0
    assert data["total_pnl"] == 250.0
    
    # Assert sanity check sum
    sum_components = data["delta_pnl"] + data["gamma_pnl"] + data["theta_pnl"] + data["vega_pnl"]
    assert abs(data["total_pnl"] - sum_components - data["residual"]) < 1e-5
    
    # Assert summary is a string and has content
    assert isinstance(data["summary"], str)
    assert "P&L" in data["summary"] or "P&L" in data["summary"] or "came from" in data["summary"]

def test_pnl_decompose_with_iv_change():
    payload = {
        "strike": 24300.0,
        "option_type": "CE",
        "position": "buy",
        "quantity": 100,
        "entry_price": 120.0,
        "current_price": 152.0,
        "previous_S": 24300.0,
        "current_S": 24350.0,
        "days_elapsed": 1.0,
        "volatility": 0.0786,  # 7.86% entry IV
        "current_volatility": 0.0894,  # 8.94% current IV
        "days_to_expiry": 7.0
    }
    response = client.post("/api/pnl-decompose", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert data["total_pnl"] == 3200.0
    
    # Assert vega contribution is positive and nonzero
    assert data["vega_pnl"] > 0
    
    # Assert residual error is under 10% of total_pnl (i.e. under 320.0)
    assert abs(data["residual"]) < 320.0

