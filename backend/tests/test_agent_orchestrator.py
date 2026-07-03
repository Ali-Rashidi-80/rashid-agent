"""Agent orchestrator unit tests."""

import tempfile
from pathlib import Path

from app.domain.edit_verify import verify_edits_on_disk


def test_verify_edits_ok_python():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        target = base / "ok.py"
        target.write_text("x = 1\n", encoding="utf-8")
        issues = verify_edits_on_disk(
            base,
            [
                {
                    "path": "ok.py",
                    "edits": [
                        {
                            "start_number_line": 1,
                            "end_number_line": 1,
                            "code": "x = 1",
                            "new_code": "x = 2",
                        }
                    ],
                }
            ],
        )
        assert issues == []


def test_verify_edits_syntax_error():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        target = base / "bad.py"
        target.write_text("x = 1\n", encoding="utf-8")
        issues = verify_edits_on_disk(
            base,
            [
                {
                    "path": "bad.py",
                    "edits": [
                        {
                            "start_number_line": 1,
                            "end_number_line": 1,
                            "code": "x = 1",
                            "new_code": "def oops(",
                        }
                    ],
                }
            ],
        )
        assert issues
        assert "bad.py" in issues[0]
