"""chapter can belong to one world"""

import sqlalchemy as sa
from alembic import op

revision = "0010_chapter_world"
down_revision = "0009_cover_images"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("chapters", sa.Column("world_id", sa.Uuid(), nullable=True))
    op.create_foreign_key("fk_chapters_world_id", "chapters", "worlds", ["world_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    op.drop_constraint("fk_chapters_world_id", "chapters", type_="foreignkey")
    op.drop_column("chapters", "world_id")
