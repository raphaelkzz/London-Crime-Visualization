from pathlib import Path
import json
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / 'dashboard' / 'app.py'


def test_borough_and_unavailable_lsoa_category():
    app = AppTest.from_file(str(APP), default_timeout=60).run()
    assert not app.exception
    assert any('31/32' in warning.value for warning in app.warning)
    app.selectbox(key='borough').select('Camden').run()
    assert not app.exception
    assert app.metric[3].value == 'Chưa có'
    app.selectbox(key='group').select('SEXUAL OFFENCES').run()
    assert not app.exception
    assert any('Không có dữ liệu LSOA' in info.value for info in app.info)


def test_unavailable_filter_combination_is_reported_not_fabricated():
    app = AppTest.from_file(str(APP), default_timeout=60).run()
    app.selectbox(key='borough').select('Enfield').run()
    app.selectbox(key='group').select('NFIB FRAUD').run()
    assert not app.exception
    assert any('Không có bản ghi' in info.value for info in app.info)


def test_reference_lines_follow_filters_and_drop_lines_are_enabled():
    app = AppTest.from_file(str(APP), default_timeout=60).run()
    facts = pd.read_parquet(APP.parents[1] / 'data/processed/crime_borough.parquet')
    dim = pd.read_parquet(APP.parents[1] / 'data/processed/dim_borough.parquet')

    def trend_spec():
        specs = [json.loads(e.proto.spec) for e in app.get('plotly_chart')]
        return next(s for s in specs if s['layout'].get('title', {}).get('text', '').startswith('Xu hướng'))

    start, end = app.select_slider[0].value
    rows = facts[facts.month.between(pd.Timestamp(start), pd.Timestamp(end))]
    spec = trend_spec()
    assert spec['layout']['shapes'][0]['y0'] == pytest.approx(rows.groupby('month').crime_count.sum().mean())
    for axis in ['xaxis', 'yaxis']:
        assert spec['layout'][axis]['showspikes']
        assert spec['layout'][axis]['spikemode'] == 'toaxis'
        assert spec['layout'][axis]['spikesnap'] == 'data'
    specs = [json.loads(e.proto.spec) for e in app.get('plotly_chart')]
    ranking = next(s for s in specs if s['data'][0]['type'] == 'bar')
    assert ranking['layout']['shapes'][0]['x0'] == pytest.approx(rows.groupby('borough_name').crime_count.sum().mean())

    app.selectbox(key='borough').select('Enfield').run()
    app.selectbox(key='group').select('THEFT').run()
    app.radio[0].set_value('Vụ / 1.000 dân').run()
    assert not app.exception
    subset = rows[(rows.borough_name == 'Enfield') & (rows.crime_group == 'THEFT')]
    population = dim.loc[dim.borough_name == 'Enfield', 'population_2021'].iloc[0]
    expected = subset.groupby('month').crime_count.sum().mean() / population * 1000
    assert trend_spec()['layout']['shapes'][0]['y0'] == pytest.approx(expected)
    app.selectbox(key='borough').select('Tất cả').run()
    app.selectbox(key='group').select('NFIB FRAUD').run()
    assert not app.exception
    specs = [json.loads(e.proto.spec) for e in app.get('plotly_chart')]
    ranking = next(s for s in specs if s['data'][0]['type'] == 'bar')
    count = rows[rows.crime_group == 'NFIB FRAUD'].borough_name.nunique()
    assert count < 32
    assert ranking['layout']['annotations'][0]['text'].startswith(f'TB {count} borough:')
