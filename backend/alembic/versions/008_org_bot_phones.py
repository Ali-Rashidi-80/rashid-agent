"""Org bot phone allowlist for SMS OTP."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "008_org_bot_phones"
down_revision: str | None = "007_messenger_grants_hnsw"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "org_bot_phone_allowlist",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "bot_id",
            UUID(as_uuid=True),
            sa.ForeignKey("org_bots.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("phone", sa.String(16), nullable=False),
        sa.Column("label", sa.String(128), nullable=False, server_default=""),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("bot_id", "phone", name="uq_org_bot_phone_allowlist"),
    )
    op.create_index("idx_org_bot_phones_bot", "org_bot_phone_allowlist", ["bot_id"])
    op.create_index("idx_org_bot_phones_tenant", "org_bot_phone_allowlist", ["tenant_id"])
    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'rashid_app') THEN
            GRANT SELECT, INSERT, UPDATE, DELETE ON org_bot_phone_allowlist TO rashid_app;
          END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    op.drop_index("idx_org_bot_phones_tenant", table_name="org_bot_phone_allowlist")
    op.drop_index("idx_org_bot_phones_bot", table_name="org_bot_phone_allowlist")
    op.drop_table("org_bot_phone_allowlist")
