"""
backend/tests/test_bhavcopy.py

Tests the Bhavcopy parsing/filtering logic using a synthetic zip built to
match NSE's real UDiFF schema — no live network calls in these tests
(that's verified separately, manually, since it needs the real internet).
"""

import io
import zipfile
from datetime import date

import pandas as pd
import pytest

from services.bhavcopy import (
    parse_bhavcopy_zip,
    BhavcopyFetchError,
    RELEVANT_COLUMNS,
)


def _make_synthetic_bhavcopy_zip(rows: list[dict]) -> bytes:
    """Build a zip byte-string mimicking NSE's real UDiFF Bhavcopy structure."""
    df = pd.DataFrame(rows)
    csv_bytes = df.to_csv(index=False).encode()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("BhavCopy_NSE_FO_0_0_0_20240207_F_0000.csv", csv_bytes)
    return buf.getvalue()


def _base_row(**overrides):
    row = {
        "TradDt": "2024-02-07", "BizDt": "2024-02-07", "Sgmt": "FO", "Src": "NSE",
        "FinInstrmTp": "IDO", "FinInstrmId": 1, "ISIN": "", "TckrSymb": "BANKNIFTY",
        "SctySrs": "", "XpryDt": "2024-02-07", "FininstrmActlXpryDt": "2024-02-07",
        "StrkPric": 48000, "OptnTp": "CE", "FinInstrmNm": "BANKNIFTY",
        "OpnPric": 300.0, "HghPric": 310.0, "LwPric": 290.0, "ClsPric": 300.0,
        "LastPric": 300.0, "PrvsClsgPric": 300.0, "UndrlygPric": 48100, "SttlmPric": 300.0,
        "OpnIntrst": 1000, "ChngInOpnIntrst": 100, "TtlTradgVol": 500, "TtlTrfVal": 0,
        "TtlNbOfTxsExctd": 0, "SsnId": "", "NewBrdLotQty": 0, "Rmks": "",
    }
    row.update(overrides)
    return row


def test_parse_bhavcopy_zip_returns_correct_columns():
    zip_bytes = _make_synthetic_bhavcopy_zip([_base_row()])
    df = parse_bhavcopy_zip(zip_bytes)
    assert list(df.columns) == RELEVANT_COLUMNS


def test_parse_bhavcopy_zip_rejects_bad_zip():
    with pytest.raises(BhavcopyFetchError):
        parse_bhavcopy_zip(b"not a real zip file")


def test_parse_bhavcopy_zip_rejects_missing_columns():
    """If NSE changes the schema again, this should fail loudly with a
    clear message, not silently return a DataFrame missing columns
    the rest of the code assumes exist."""
    rows = [{"SomeOtherColumn": "value"}]
    df = pd.DataFrame(rows)
    csv_bytes = df.to_csv(index=False).encode()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("test.csv", csv_bytes)

    with pytest.raises(BhavcopyFetchError, match="Expected columns missing"):
        parse_bhavcopy_zip(buf.getvalue())


def test_filters_exclude_futures_and_other_symbols():
    """OptnTp == 'XX' marks futures rows (not options) — these and any
    non-BANKNIFTY symbol should never leak into the filtered result."""
    rows = [
        _base_row(OptnTp="CE", StrkPric=48000),
        _base_row(OptnTp="PE", StrkPric=48000),
        _base_row(OptnTp="XX", StrkPric=0),  # futures row
        _base_row(TckrSymb="NIFTY", OptnTp="CE"),  # different symbol
    ]
    zip_bytes = _make_synthetic_bhavcopy_zip(rows)
    df = parse_bhavcopy_zip(zip_bytes)

    filtered = df[df["TckrSymb"] == "BANKNIFTY"]
    filtered = filtered[filtered["OptnTp"].isin(["CE", "PE"])]

    assert len(filtered) == 2
    assert "XX" not in filtered["OptnTp"].values
    assert (filtered["TckrSymb"] == "BANKNIFTY").all()


def test_empty_result_when_no_banknifty_rows():
    """A file with no BANKNIFTY rows at all should filter down to empty,
    not error at the parse stage (the empty-check belongs in
    get_banknifty_options, which does the network fetch — tested
    separately/manually since it needs live internet)."""
    rows = [_base_row(TckrSymb="NIFTY")]
    zip_bytes = _make_synthetic_bhavcopy_zip(rows)
    df = parse_bhavcopy_zip(zip_bytes)
    filtered = df[df["TckrSymb"] == "BANKNIFTY"]
    assert len(filtered) == 0
