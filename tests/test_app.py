from pathlib import Path

import pytest

st_testing = pytest.importorskip("streamlit.testing.v1")

APP = str(Path(__file__).resolve().parents[1] / "app.py")


def test_app_renders_without_exception():
    at = st_testing.AppTest.from_file(APP, default_timeout=60).run()
    assert not at.exception
    assert len(at.metric) == 4


def test_app_filters_do_not_crash():
    at = st_testing.AppTest.from_file(APP, default_timeout=60).run()
    at.radio[0].set_value("AI-related").run()
    assert not at.exception
    share = at.metric[1].value
    assert share == "100%"
