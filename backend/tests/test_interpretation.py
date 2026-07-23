"""
backend/tests/test_interpretation.py
"""

import pytest

from core.interpretation import (
    calculate_pcr,
    calculate_max_pain,
    interpret_pcr,
    interpret_max_pain,
    generate_dos_trade_card,
)


@pytest.fixture
def sample_strikes():
    """Hand-verifiable fixture: max pain = 110 (payout 70, vs 90 at K=100
    and 500 at K=120), PCR = 57/105 ≈ 0.543 — both confirmed by
    independent manual calculation before writing this test."""
    return [
        {"strike": 100, "call_oi": 5, "put_oi": 50},
        {"strike": 110, "call_oi": 40, "put_oi": 5},
        {"strike": 120, "call_oi": 60, "put_oi": 2},
    ]


def test_calculate_pcr_matches_hand_calculation(sample_strikes):
    pcr = calculate_pcr(sample_strikes)
    assert pcr == pytest.approx(57 / 105)


def test_calculate_pcr_zero_call_oi_raises():
    strikes = [{"strike": 100, "call_oi": 0, "put_oi": 50}]
    with pytest.raises(ValueError, match="Call OI is zero"):
        calculate_pcr(strikes)


def test_calculate_max_pain_matches_hand_calculation(sample_strikes):
    result = calculate_max_pain(sample_strikes)
    assert result == 110


def test_calculate_max_pain_empty_list_raises():
    with pytest.raises(ValueError, match="empty strike list"):
        calculate_max_pain([])


def test_calculate_max_pain_single_strike_returns_that_strike():
    strikes = [{"strike": 50000, "call_oi": 100, "put_oi": 100}]
    assert calculate_max_pain(strikes) == 50000


def test_interpret_pcr_high_is_bullish_leaning():
    text = interpret_pcr(1.5)
    assert "bullish" in text.lower()


def test_interpret_pcr_low_is_bearish_leaning():
    text = interpret_pcr(0.5)
    assert "bearish" in text.lower()


def test_interpret_pcr_neutral_band():
    text = interpret_pcr(1.0)
    assert "neutral" in text.lower()


def test_interpret_max_pain_spot_above():
    text = interpret_max_pain(max_pain_strike=57300, spot=57450)
    assert "above" in text
    assert "150" in text


def test_interpret_max_pain_spot_below():
    text = interpret_max_pain(max_pain_strike=57500, spot=57450)
    assert "below" in text


def test_generate_dos_trade_card_open_position():
    trade = {
        "option_side": "CE", "strike": 57300, "day_type": "wednesday",
        "entry_premium": 370.07, "current_premium": 350.00,
        "is_open": True, "exit_reason": None,
    }
    card = generate_dos_trade_card(trade)
    assert "57,300 CE" in card
    assert "Wednesday" in card
    assert "370.07" in card
    assert "open" in card.lower()


def test_generate_dos_trade_card_initial_sl_exit():
    trade = {
        "option_side": "PE", "strike": 47100, "day_type": "wednesday",
        "entry_premium": 108.05, "is_open": False,
        "exit_reason": "initial_sl", "pnl": -1620.75,
    }
    card = generate_dos_trade_card(trade)
    assert "initial stop-loss" in card.lower()
    assert "loss" in card.lower()
    assert "1,620.75" in card


def test_generate_dos_trade_card_market_close_profit():
    trade = {
        "option_side": "PE", "strike": 47200, "day_type": "thursday",
        "entry_premium": 1402.65, "is_open": False,
        "exit_reason": "market_close", "pnl": 8653.50,
    }
    card = generate_dos_trade_card(trade)
    assert "market close" in card.lower()
    assert "profit" in card.lower()


def test_generate_dos_trade_card_trailing_sl_exit():
    trade = {
        "option_side": "CE", "strike": 57300, "day_type": "thursday",
        "entry_premium": 300.0, "is_open": False,
        "exit_reason": "trailing_sl", "pnl": -50.0,
    }
    card = generate_dos_trade_card(trade)
    assert "supertrend flipped" in card.lower() or "trailing" in card.lower()
    assert "loss" in card.lower()
