from pydantic import BaseModel


class ErrorBody(BaseModel):
    code: str
    message: str
    message_fa: str = ""
    details: dict | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody
