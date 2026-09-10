from pathlib import Path
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
