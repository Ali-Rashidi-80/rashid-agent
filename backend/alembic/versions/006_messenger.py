"""Messenger integrations, links, processed updates (Phase D1)."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "006_messenger"
down_revision: str | None = "005_org_bots_grants"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "messenger_integrations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "org_bot_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("org_bots.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("platform", sa.String(32), nullable=False),
        sa.Column("bot_token_encrypted", sa.Text(), nullable=False),
        sa.Column("webhook_secret", sa.String(128), nullable=False),
        sa.Column("external_username", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("platform", "external_username", name="uq_messenger_platform_username"),
    )
    op.create_index("idx_messenger_integrations_tenant", "messenger_integrations", ["tenant_id"])

    op.create_table(
        "messenger_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "integration_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("messenger_integrations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chat_id", sa.String(64), nullable=False),
        sa.Column("authorized_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("integration_id", "chat_id", name="uq_messenger_link_chat"),
    )
    op.create_index("idx_messenger_links_integration", "messenger_links", ["integration_id"])

    op.create_table(
        "processed_messenger_updates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "integration_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("messenger_integrations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("update_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("integration_id", "update_id", name="uq_processed_messenger_update"),
    )


def downgrade() -> None:
    op.drop_table("processed_messenger_updates")
    op.drop_index("idx_messenger_links_integration", table_name="messenger_links")
    op.drop_table("messenger_links")
    op.drop_index("idx_messenger_integrations_tenant", table_name="messenger_integrations")
    op.drop_table("messenger_integrations")
