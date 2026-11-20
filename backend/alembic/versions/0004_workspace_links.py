"""world links on outline, foreshadow sources, text marks, character worlds"""

import sqlalchemy as sa
from alembic import op

revision = "0004_workspace_links"
down_revision = "0003_characters_volumes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("outline_nodes", sa.Column("world_id", sa.Uuid(as_uuid=True), sa.ForeignKey("worlds.id", ondelete="SET NULL")))
    op.add_column("foreshadows", sa.Column("source_quote", sa.Text(), nullable=False, server_default=""))
    op.add_column("foreshadows", sa.Column("source_start", sa.Integer()))
    op.add_column("foreshadows", sa.Column("source_end", sa.Integer()))
    op.create_table(
        "character_worlds",
        sa.Column("character_id", sa.Uuid(as_uuid=True), sa.ForeignKey("characters.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("world_id", sa.Uuid(as_uuid=True), sa.ForeignKey("worlds.id", ondelete="RESTRICT"), primary_key=True),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
    )
    op.create_table(
        "text_marks",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("novel_id", sa.Uuid(as_uuid=True), sa.ForeignKey("novels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chapter_id", sa.Uuid(as_uuid=True), sa.ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False),
        sa.Column("quote", sa.Text(), nullable=False),
        sa.Column("start", sa.Integer(), nullable=False),
        sa.Column("end", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_text_marks_chapter_id", "text_marks", ["chapter_id"])
    op.create_index("ix_text_marks_novel_id", "text_marks", ["novel_id"])


def downgrade() -> None:
    op.drop_table("text_marks")
    op.drop_table("character_worlds")
    op.drop_column("foreshadows", "source_end")
    op.drop_column("foreshadows", "source_start")
    op.drop_column("foreshadows", "source_quote")
    op.drop_column("outline_nodes", "world_id")
