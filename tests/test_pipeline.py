import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from common import ratio
from preprocess import unpivot
from model import features


def test_missing_and_zero_denominators_are_not_valid_rates():
    result = ratio(pd.Series([10, 10, 10]), pd.Series([100, 0, np.nan]), 1000)
    assert result.iloc[0] == 100
    assert result.iloc[1:].isna().all()


def test_unpivot_preserves_zero_but_rejects_unknown_counts():
    frame = pd.DataFrame({'area': ['A', 'B'], '202401': [0, 2], '202402': [3, 4]})
    long = unpivot(frame, ['area'])
    assert len(long) == 4 and long.crime_count.sum() == 9
    frame.loc[0, '202401'] = np.nan
    with pytest.raises(ValueError):
        unpivot(frame, ['area'])


def test_unpivot_rejects_duplicate_join_keys():
    frame = pd.DataFrame({'area': ['A', 'A'], '202401': [1, 2]})
    with pytest.raises(ValueError):
        unpivot(frame, ['area'])


def test_real_population_and_security_joins():
    monthly = pd.read_parquet(ROOT / 'data/processed/monthly.parquet')
    facts = pd.read_parquet(ROOT / 'data/processed/crime_borough.parquet')
    assert len(monthly) == 32 * 72
    assert not monthly.duplicated(['borough_name', 'month']).any()
    assert monthly.population_2021.gt(0).all()
    assert monthly.crime_count.sum() == facts.crime_count.sum()
    assert monthly[monthly.month < '2021-08-01'].officer_fte.isna().all()
    common = monthly[monthly.month >= '2021-08-01']
    missing = common[common.officer_fte.isna()]
    assert len(missing) == 24
    assert set(missing.borough_name) == {'Camden'}
    assert missing.month.min() == pd.Timestamp('2024-08-01')
    assert common.minutes.notna().all()
    assert monthly.groupby('borough_name').head(11).rolling_12_count.isna().all()
    np.testing.assert_allclose(monthly.rate_per_1000, monthly.crime_count / monthly.population_2021 * 1000)


def test_forecast_is_chronological_and_future_has_no_actual():
    f = pd.read_parquet(ROOT / 'data/processed/forecast.parquet')
    assert f[f.split == 'train'].month.max() < f[f.split == 'test'].month.min()
    assert f[f.split == 'test'].month.max() < f[f.split == 'forecast'].month.min()
    assert f[f.split == 'forecast'].actual.isna().all()
    assert f[f.split == 'forecast'].groupby('borough_name').size().eq(6).all()
    assert f[f.split == 'test'].groupby('borough_name').size().eq(12).all()
    assert f[f.split != 'train'].predicted.ge(0).all()
    assert list(features(pd.to_datetime(['2026-08-01'])).columns) == ['time_index', 'month_sin', 'month_cos', 'connect']
