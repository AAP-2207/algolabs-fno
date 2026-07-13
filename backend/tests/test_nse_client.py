import pytest
from unittest.mock import patch, MagicMock
from backend.services.nse_client import get_option_chain

# A sample raw response structure from NSE containing 10 strikes
SAMPLE_NSE_RESPONSE = {
    "records": {
        "expiryDates": ["2026-07-16"],
        "underlyingValue": 24250.0,
        "timestamp": "14-Jul-2026 15:30:00",
        "data": [
            {
                "strikePrice": 24000 + i * 50,
                "expiryDate": "2026-07-16",
                "CE": {
                    "strikePrice": 24000 + i * 50,
                    "expiryDate": "2026-07-16",
                    "underlying": "NIFTY",
                    "identifier": f"OPTNIFTY16-07-2026CE{24000 + i * 50}",
                    "openInterest": 50000,
                    "changeinOpenInterest": 1000,
                    "totalTradedVolume": 20000,
                    "impliedVolatility": 12.5,
                    "lastPrice": 150.0,
                    "underlyingValue": 24250.0
                },
                "PE": {
                    "strikePrice": 24000 + i * 50,
                    "expiryDate": "2026-07-16",
                    "underlying": "NIFTY",
                    "identifier": f"OPTNIFTY16-07-2026PE{24000 + i * 50}",
                    "openInterest": 60000,
                    "changeinOpenInterest": 1200,
                    "totalTradedVolume": 25000,
                    "impliedVolatility": 13.0,
                    "lastPrice": 100.0,
                    "underlyingValue": 24250.0
                }
            } for i in range(10)
        ]
    },
    "filtered": {
        "data": []
    }
}

@patch("backend.services.nse_client.requests.Session")
def test_get_option_chain_live_parsing(mock_session_class):
    # Setup mock session and responses
    mock_session = MagicMock()
    mock_session_class.return_value = mock_session
    
    # Mock responses for Step A, Step C, and Step E
    mock_response_home = MagicMock()
    mock_response_home.status_code = 200
    mock_response_home.text = "Homepage HTML"
    
    mock_response_opt_chain = MagicMock()
    mock_response_opt_chain.status_code = 200
    mock_response_opt_chain.text = "Option Chain HTML"
    
    mock_response_api = MagicMock()
    mock_response_api.status_code = 200
    mock_response_api.json.return_value = SAMPLE_NSE_RESPONSE
    
    # Session.get side_effect to return mock responses in sequence
    mock_session.get.side_effect = [
        mock_response_home,
        mock_response_opt_chain,
        mock_response_api
    ]
    
    # Execute the client function
    result = get_option_chain("NIFTY")
    
    # Assertions
    assert result["source"] == "live"
    assert "records" in result
    assert "data" in result["records"]
    
    strikes = result["records"]["data"]
    assert len(strikes) == 10
    
    # Verify strike prices are extracted correctly
    for i, strike in enumerate(strikes):
        expected_strike = 24000 + i * 50
        assert strike["strikePrice"] == expected_strike
        assert strike["CE"]["strikePrice"] == expected_strike
        assert strike["PE"]["strikePrice"] == expected_strike
