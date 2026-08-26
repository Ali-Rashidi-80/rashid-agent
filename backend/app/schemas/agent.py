from typing import Literal

from pydantic import BaseModel, Field


class LineEdit(BaseModel):
    type: Literal["edit"] = "edit"
    start_number_line: int = Field(ge=1)
    end_number_line: int = Field(ge=1)
    code: str = ""
    new_code: str = ""
    Total_lines: int | None = None


class FileEdit(BaseModel):
    path: str
    edits: list[LineEdit] = Field(default_factory=list)
    info: str = ""
    log: str = ""


class AgentResponse(BaseModel):
    message: str = ""
    pip: str = ""
    edits: list[FileEdit] = Field(default_factory=list)
    log: str = ""


class GenerateRequest(BaseModel):
    prompt: str
    mode: Literal["ask", "plan", "agent"] = "agent"
    session_id: str | None = None
    project_path: str | None = None
    model: str | None = None
    provider: str | None = None
    knowledge_base_id: str | None = None
    rag_only: bool = False
    tenant_id: str | None = None


class StreamEvent(BaseModel):
    type: str
    data: dict = Field(default_factory=dict)
