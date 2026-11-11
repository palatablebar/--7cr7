"""initial lake metadata schema

The DDL is intentionally delegated to Base.metadata so the SQLAlchemy models
remain the single source of truth for the demo stack (see README §local dev).
"""
from alembic import op

revision = "20261110_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    from app.config.database import Base
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    from app.config.database import Base
    import app.models  # noqa: F401

    Base.metadata.drop_all(bind=op.get_bind())
