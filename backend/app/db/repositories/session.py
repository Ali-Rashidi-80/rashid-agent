import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Message, Session


class SessionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, project_path: str, title: str | None = None, mode: str = "agent") -> Session:
        session = Session(
            id=uuid.uuid4(),
            project_path=project_path,
            title=title,
            mode=mode,
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def list_sessions(self, project_path: str | None = None) -> list[Session]:
        q = select(Session).order_by(Session.updated_at.desc())
        if project_path:
            q = q.where(Session.project_path == project_path)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def get(self, session_id: uuid.UUID) -> Session | None:
        return await self.db.get(Session, session_id)

    async def add_message(self, session_id: uuid.UUID, role: str, content: str) -> Message:
        msg = Message(
            id=uuid.uuid4(),
            session_id=session_id,
            role=role,
            content=content,
        )
        self.db.add(msg)
        await self.db.execute(
            update(Session)
            .where(Session.id == session_id)
            .values(updated_at=datetime.now(UTC))
        )
        await self.db.commit()
        await self.db.refresh(msg)
        return msg

    async def list_messages(self, session_id: uuid.UUID) -> list[Message]:
        result = await self.db.execute(
            select(Message).where(Message.session_id == session_id).order_by(Message.created_at)
        )
        return list(result.scalars().all())
