"""Knowledge bases + pgvector + tenant RLS (Phase B1)."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003_knowledge_base"
down_revision: str | None = "002_tenants"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EMBEDDING_DIM = 1536


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # App role must not be superuser / BYPASSRLS so FORCE RLS is enforced.
    op.execute(
        """
        DO $$
        BEGIN
          IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'rashid_app') THEN
            CREATE ROLE rashid_app LOGIN PASSWORD 'rashid'
              NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;
          END IF;
        END
        $$;
        """
    )
    op.execute("GRANT CONNECT ON DATABASE rashid TO rashid_app")
    op.execute("GRANT USAGE ON SCHEMA public TO rashid_app")
    op.execute("GRANT rashid_app TO CURRENT_USER")

    op.create_table(
        "knowledge_bases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_knowledge_bases_tenant", "knowledge_bases", ["tenant_id"])

    op.create_table(
        "kb_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "kb_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column(
            "mime", sa.String(128), nullable=False, server_default="application/octet-stream"
        ),
        sa.Column("size", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("storage_path", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_kb_documents_kb", "kb_documents", ["kb_id"])
    op.create_index("idx_kb_documents_tenant", "kb_documents", ["tenant_id"])

    op.execute(
        f"""
        CREATE TABLE kb_chunks (
            id UUID PRIMARY KEY,
            doc_id UUID NOT NULL REFERENCES kb_documents(id) ON DELETE CASCADE,
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            chunk_index INTEGER NOT NULL DEFAULT 0,
            content TEXT NOT NULL,
            embedding vector({EMBEDDING_DIM}),
            metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb,
            created_at TIMESTAMPTZ DEFAULT now()
        )
        """
    )
    op.create_index("idx_kb_chunks_doc", "kb_chunks", ["doc_id"])
    op.create_index("idx_kb_chunks_tenant", "kb_chunks", ["tenant_id"])

    for table in ("knowledge_bases", "kb_documents", "kb_chunks"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY {table}_tenant_isolation ON {table}
            FOR ALL
            TO rashid_app
            USING (
                tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
            )
            WITH CHECK (
                tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
            )
            """
        )
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO rashid_app")

    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON tenants TO rashid_app")
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON tenant_admins, tenant_admin_sessions TO rashid_app"
    )


def downgrade() -> None:
    for table in ("kb_chunks", "kb_documents", "knowledge_bases"):
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    op.drop_index("idx_kb_chunks_tenant", table_name="kb_chunks")
    op.drop_index("idx_kb_chunks_doc", table_name="kb_chunks")
    op.execute("DROP TABLE IF EXISTS kb_chunks")
    op.drop_index("idx_kb_documents_tenant", table_name="kb_documents")
    op.drop_index("idx_kb_documents_kb", table_name="kb_documents")
    op.drop_table("kb_documents")
    op.drop_index("idx_knowledge_bases_tenant", table_name="knowledge_bases")
    op.drop_table("knowledge_bases")
    # Keep rashid_app role (may be referenced by DATABASE_URL); drop grants only.
