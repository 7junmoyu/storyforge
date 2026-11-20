"""characters, novel fields, and volumes"""

import sqlalchemy as sa
from alembic import op

revision = "0003_characters_volumes"
down_revision = "0002_outline_foreshadow"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("novels", sa.Column("tags", sa.Text(), nullable=False, server_default=""))
    op.add_column("novels", sa.Column("cover_url", sa.String(500), nullable=False, server_default=""))
    op.add_column("novels", sa.Column("archived", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_table(
        "characters",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "novel_characters",
        sa.Column("novel_id", sa.Uuid(as_uuid=True), sa.ForeignKey("novels.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("character_id", sa.Uuid(as_uuid=True), sa.ForeignKey("characters.id", ondelete="RESTRICT"), primary_key=True),
    )
    op.create_table(
        "volumes",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("novel_id", sa.Uuid(as_uuid=True), sa.ForeignKey("novels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_volumes_novel_id", "volumes", ["novel_id"])
    op.add_column("chapters", sa.Column("volume_id", sa.Uuid(as_uuid=True), sa.ForeignKey("volumes.id", ondelete="SET NULL")))
    op.create_table(
        "outline_characters",
        sa.Column("outline_node_id", sa.Uuid(as_uuid=True), sa.ForeignKey("outline_nodes.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("character_id", sa.Uuid(as_uuid=True), sa.ForeignKey("characters.id", ondelete="RESTRICT"), primary_key=True),
    )
    op.create_table(
        "foreshadow_characters",
        sa.Column("foreshadow_id", sa.Uuid(as_uuid=True), sa.ForeignKey("foreshadows.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("character_id", sa.Uuid(as_uuid=True), sa.ForeignKey("characters.id", ondelete="RESTRICT"), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table("foreshadow_characters")
    op.drop_table("outline_characters")
    op.drop_column("chapters", "volume_id")
    op.drop_table("volumes")
    op.drop_table("novel_characters")
    op.drop_table("characters")
    op.drop_column("novels", "archived")
    op.drop_column("novels", "cover_url")
    op.drop_column("novels", "tags")
