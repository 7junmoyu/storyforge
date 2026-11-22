"""link scope on character worlds and novel-specific world notes"""

import sqlalchemy as sa
from alembic import op

revision = "0006_world_character_basics"
down_revision = "0005_character_periods"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("character_worlds", sa.Column("scope", sa.String(32), nullable=False, server_default="global"))
    op.add_column("character_worlds", sa.Column("source", sa.String(80), nullable=False, server_default="手动"))
    op.add_column("character_worlds", sa.Column("novel_id", sa.Uuid(as_uuid=True), sa.ForeignKey("novels.id", ondelete="SET NULL")))
    op.add_column("character_worlds", sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_table(
        "novel_world_settings",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("novel_id", sa.Uuid(as_uuid=True), sa.ForeignKey("novels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("world_id", sa.Uuid(as_uuid=True), sa.ForeignKey("worlds.id", ondelete="CASCADE"), nullable=False),
        sa.Column("supplement", sa.Text(), nullable=False, server_default=""),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("novel_id", "world_id"),
    )
    op.create_index("ix_novel_world_settings_novel_id", "novel_world_settings", ["novel_id"])
    op.create_index("ix_novel_world_settings_world_id", "novel_world_settings", ["world_id"])


def downgrade() -> None:
    op.drop_table("novel_world_settings")
    op.drop_column("character_worlds", "created_at")
    op.drop_column("character_worlds", "novel_id")
    op.drop_column("character_worlds", "source")
    op.drop_column("character_worlds", "scope")
