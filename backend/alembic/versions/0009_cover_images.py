"""cover images for worlds and characters"""

import sqlalchemy as sa
from alembic import op

revision = "0009_cover_images"
down_revision = "0008_novel_groups"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("worlds", sa.Column("cover_url", sa.String(500), nullable=False, server_default=""))
    op.add_column("characters", sa.Column("cover_url", sa.String(500), nullable=False, server_default=""))


def downgrade() -> None:
    op.drop_column("characters", "cover_url")
    op.drop_column("worlds", "cover_url")
