"""Custom SQLAlchemy types (pgvector without the PyPI package)."""

from __future__ import annotations

from sqlalchemy.types import UserDefinedType


class Vector(UserDefinedType):
    """Postgres ``vector(n)`` from the pgvector extension."""

    cache_ok = True

    def __init__(self, dim: int | None = None) -> None:
        self.dim = dim

    def get_col_spec(self, **_kw: object) -> str:
        if self.dim is not None:
            return f"vector({self.dim})"
        return "vector"

    def bind_processor(self, _dialect: object):
        def process(value: object) -> str | None:
            if value is None:
                return None
            if isinstance(value, str):
                return value
            if not isinstance(value, list | tuple):
                raise TypeError("vector value must be a sequence of floats")
            return "[" + ",".join(str(float(x)) for x in value) + "]"

        return process

    def result_processor(self, _dialect: object, _coltype: object):
        def process(value: object) -> list[float] | None:
            if value is None:
                return None
            if isinstance(value, list):
                return [float(x) for x in value]
            text = str(value).strip()
            if text.startswith("[") and text.endswith("]"):
                inner = text[1:-1].strip()
                if not inner:
                    return []
                return [float(x) for x in inner.split(",")]
            return None

        return process
