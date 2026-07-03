"""Schema validation tests."""

from app.schemas.agent import AgentResponse, FileEdit, GenerateRequest, LineEdit
from app.schemas.errors import ErrorResponse


def test_agent_response_defaults():
    r = AgentResponse()
    assert r.message == ""
    assert r.edits == []


def test_line_edit():
    e = LineEdit(start_number_line=1, end_number_line=1, code="a", new_code="b")
    assert e.type == "edit"


def test_file_edit():
    f = FileEdit(path="x.py", edits=[])
    assert f.path == "x.py"


def test_generate_request():
    g = GenerateRequest(prompt="hi", mode="ask")
    assert g.mode == "ask"


def test_error_response():
    from app.schemas.errors import ErrorBody

    e = ErrorResponse(error=ErrorBody(code="x", message="y"))
    assert e.error.code == "x"
