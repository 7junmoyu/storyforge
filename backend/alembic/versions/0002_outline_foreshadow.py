"""outline nodes and foreshadows"""

import sqlalchemy as sa
from alembic import op

revision = "0002_outline_foreshadow"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "outline_nodes",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("novel_id", sa.Uuid(as_uuid=True), sa.ForeignKey("novels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("parent_id", sa.Uuid(as_uuid=True), sa.ForeignKey("outline_nodes.id", ondelete="CASCADE")),
        sa.Column("chapter_id", sa.Uuid(as_uuid=True), sa.ForeignKey("chapters.id", ondelete="SET NULL")),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_outline_nodes_novel_id", "outline_nodes", ["novel_id"])
    op.create_index("ix_outline_nodes_parent_id", "outline_nodes", ["parent_id"])
    op.create_table(
        "foreshadows",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("novel_id", sa.Uuid(as_uuid=True), sa.ForeignKey("novels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("outline_node_id", sa.Uuid(as_uuid=True), sa.ForeignKey("outline_nodes.id", ondelete="SET NULL")),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("kind", sa.String(80), nullable=False),
        sa.Column("importance", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("plant_chapter_id", sa.Uuid(as_uuid=True), sa.ForeignKey("chapters.id", ondelete="SET NULL")),
        sa.Column("expected_chapter_id", sa.Uuid(as_uuid=True), sa.ForeignKey("chapters.id", ondelete="SET NULL")),
        sa.Column("actual_chapter_id", sa.Uuid(as_uuid=True), sa.ForeignKey("chapters.id", ondelete="SET NULL")),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_foreshadows_novel_id", "foreshadows", ["novel_id"])


def downgrade() -> None:
    op.drop_table("foreshadows")
    op.drop_table("outline_nodes")
