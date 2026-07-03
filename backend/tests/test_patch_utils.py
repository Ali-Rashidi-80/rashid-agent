import pytest
from app.domain.patch_engine import fuzzy_ratio, normalize_text


@pytest.mark.parametrize(
    "a,b,min_ratio",
    [
        ("hello", "hello", 1.0),
        ("hello\n", "hello", 1.0),
        ("abc", "xyz", 0.0),
    ],
)
def test_fuzzy_ratio(a, b, min_ratio):
    assert fuzzy_ratio(a, b) >= min_ratio


@pytest.mark.parametrize("text", ["a\n", "a\r\n", "  x  \n"])
def test_normalize(text):
    assert isinstance(normalize_text(text), str)
