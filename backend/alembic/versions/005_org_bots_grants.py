"""Grant org_bot tables to rashid_app role."""

from collections.abc import Sequence

from alembic import op

revision: str = "005_org_bots_grants"
down_revision: str | None = "004_org_bots"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'rashid_app') THEN
            GRANT SELECT, INSERT, UPDATE, DELETE ON
              org_bots, org_bot_credentials, org_bot_sessions, org_bot_audit
            TO rashid_app;
          END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'rashid_app') THEN
            REVOKE ALL ON
              org_bots, org_bot_credentials, org_bot_sessions, org_bot_audit
            FROM rashid_app;
          END IF;
        END
        $$;
        """
    )
