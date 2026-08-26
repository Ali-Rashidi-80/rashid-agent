"""Grant messenger tables to rashid_app + HNSW index on kb_chunks.embedding."""

from collections.abc import Sequence

from alembic import op

revision: str = "007_messenger_grants_hnsw"
down_revision: str | None = "006_messenger"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'rashid_app') THEN
            GRANT SELECT, INSERT, UPDATE, DELETE ON
              messenger_integrations, messenger_links, processed_messenger_updates
            TO rashid_app;
          END IF;
        END
        $$;
        """
    )
    # Approximate nearest-neighbor index for RAG retrieve (pgvector HNSW).
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_kb_chunks_embedding_hnsw
        ON kb_chunks
        USING hnsw (embedding vector_cosine_ops);
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_kb_chunks_embedding_hnsw")
    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'rashid_app') THEN
            REVOKE ALL ON
              messenger_integrations, messenger_links, processed_messenger_updates
            FROM rashid_app;
          END IF;
        END
        $$;
        """
    )
