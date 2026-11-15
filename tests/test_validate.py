"""
test_validate.py · Cada regla de calidad debe DETECTAR el problema que dice detectar.
Se usan datos sintéticos con errores sembrados a propósito (no toca la base).
"""
import pandas as pd

from src import validate as v


def frame(rows):
    df = pd.DataFrame(rows, columns=["source", "reporter", "partner", "hs_code", "period",
                                     "net_weight_kg", "value_usd", "quality_flag"])
    df["period"] = pd.to_datetime(df["period"])
    return df


def china(partner, period, kg, usd=None, hs="020649", flag=None):
    return ["comtrade", "CHN", partner, hs, period, kg, usd if usd is not None else kg * 2, flag]


def mirror(exporter, period, kg, usd=None, hs="020649", flag=None):
    return ["comtrade_mirror", exporter, "CHN", hs, period, kg, usd if usd is not None else kg * 2, flag]


def test_r03_detects_partners_above_world():
    ok = frame([china("W00", "2024-01-01", 3000), china("USA", "2024-01-01", 1000), china("ESP", "2024-01-01", 2000)])
    bad = frame([china("W00", "2024-01-01", 2000), china("USA", "2024-01-01", 1000), china("ESP", "2024-01-01", 2000)])
    assert v.r03_partners_vs_world(ok).passed
    assert not v.r03_partners_vs_world(bad).passed


def test_r04_detects_missing_month():
    ok = frame([china("USA", f"2024-{m:02d}-01", 1000) for m in range(1, 13)])
    bad = frame([china("USA", f"2024-{m:02d}-01", 1000) for m in range(1, 13) if m != 6])
    assert v.r04_monthly_continuity(ok).passed
    r = v.r04_monthly_continuity(bad)
    assert not r.passed and "2024-06" in r.detail


def test_r05_requires_flag_on_implausible_unit_values():
    implausible = china("ESP", "2018-07-01", 33540, usd=33540 * 0.27, hs="020312")
    unflagged = frame([implausible])
    flagged = frame([implausible[:-1] + ["outlier_unit_value"]])
    assert not v.r05_plausible_unit_value(unflagged)[0].passed
    assert v.r05_plausible_unit_value(flagged)[0].passed


def test_r05_ignores_small_shipments():
    tiny = frame([china("GBR", "2019-07-01", 500, usd=500 * 25, hs="020311")])
    assert v.r05_plausible_unit_value(tiny)[0].passed


def test_r06_missing_weight_threshold():
    rows = [china("USA", "2024-01-01", 1000) for _ in range(99)] + [china("ESP", "2024-01-01", None, usd=5)]
    assert v.r06_missing_weight(frame(rows)).passed            # 1% exacto: se acepta
    rows += [china("BRA", "2024-01-01", None, usd=5)]
    assert not v.r06_missing_weight(frame(rows)).passed        # > 1%


def test_r07_detects_big_mirror_gap():
    ok = frame([china("ESP", "2024-01-01", 1000), mirror("ESP", "2024-01-01", 1020)])
    bad = frame([china("ESP", "2024-01-01", 1000), mirror("ESP", "2024-01-01", 1300)])
    assert v.r07_mirror_reconciliation(ok)[0].passed
    assert not v.r07_mirror_reconciliation(bad)[0].passed


def test_r08_detects_spike():
    rows = [china("USA", f"2024-{m:02d}-01", 1000) for m in range(1, 12)] + [china("USA", "2024-12-01", 9000)]
    r = v.r08_spikes(frame(rows))
    assert not r.passed and "2024-12" in r.detail


def test_r09_detects_future_period():
    assert v.r09_no_future(frame([china("USA", "2024-01-01", 1000)])).passed
    assert not v.r09_no_future(frame([china("USA", "2099-01-01", 1000)])).passed


def test_r11_flags_match_missing_weight():
    ok = frame([china("USA", "2024-01-01", None, usd=5, flag="missing_weight")])
    bad = frame([china("USA", "2024-01-01", None, usd=5, flag=None)])
    assert v.r11_flags_consistent(ok).passed
    assert not v.r11_flags_consistent(bad).passed


def test_spanish_number_format():
    assert v.es_num(5244085) == "5.244.085"
    assert v.es_num(1.015, 3) == "1,015"
    assert v.es_num(0) == "0"
