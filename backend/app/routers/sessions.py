import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.session import SessionRepository
from app.db.session import get_db_session

router = APIRouter(prefix="/sessions", tags=["sessions"])


class SessionCreate(BaseModel):
    project_path: str
    title: str | None = None
    mode: str = "agent"


class SessionOut(BaseModel):
    id: str
    project_path: str
    title: str | None
    mode: str
    updated_at: str | None = None

    @classmethod
    def from_orm_session(cls, s) -> "SessionOut":
        updated = s.updated_at.isoformat() if s.updated_at else None
        return cls(
            id=str(s.id),
            project_path=s.project_path,
            title=s.title,
            mode=s.mode,
            updated_at=updated,
        )


class MessageOut(BaseModel):
    id: str
    role: str
    content: str


@router.get("", response_model=list[SessionOut])
async def list_sessions(
    project_path: str | None = None,
    db: AsyncSession = Depends(get_db_session),
):
    repo = SessionRepository(db)
    sessions = await repo.list_sessions(project_path)
    return [SessionOut.from_orm_session(s) for s in sessions]


@router.post("", response_model=SessionOut)
async def create_session(body: SessionCreate, db: AsyncSession = Depends(get_db_session)):
    repo = SessionRepository(db)
    session = await repo.create(body.project_path, body.title, body.mode)
    return SessionOut.from_orm_session(session)


@router.get("/{session_id}", response_model=SessionOut)
async def get_session(session_id: str, db: AsyncSession = Depends(get_db_session)):
    repo = SessionRepository(db)
    try:
        sid = uuid.UUID(session_id)
    except ValueError as exc:
        raise HTTPException(400, "invalid session id") from exc
    session = await repo.get(sid)
    if session is None:
        raise HTTPException(404, "session not found")
    return SessionOut.from_orm_session(session)


@router.get("/{session_id}/messages", response_model=list[MessageOut])
async def get_messages(session_id: str, db: AsyncSession = Depends(get_db_session)):
    repo = SessionRepository(db)
    try:
        sid = uuid.UUID(session_id)
    except ValueError as exc:
        raise HTTPException(400, "invalid session id") from exc
    messages = await repo.list_messages(sid)
    return [MessageOut(id=str(m.id), role=m.role, content=m.content) for m in messages]
