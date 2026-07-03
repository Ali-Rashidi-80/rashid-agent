"""Additional patch edge cases for regression gate."""

import pytest
from app.domain.patch_engine import LineEdit, preview_patch


@pytest.mark.parametrize("i", range(20))
def test_replace_line_i(i):
    n = i + 1
    lines = "".join(f"N{j}\n" for j in range(1, 25))
    edit = LineEdit(start_number_line=n, end_number_line=n, code=f"N{n}\n", new_code=f"R{n}\n")
    result = preview_patch(lines, [edit])
    assert result.ok
    assert f"R{n}" in (result.new_content or "")
