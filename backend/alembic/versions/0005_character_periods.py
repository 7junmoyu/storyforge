"""character periods and novel-specific character versions"""

import sqlalchemy as sa
from alembic import op

revision = "0005_character_periods"
down_revision = "0004_workspace_links"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "character_periods",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("character_id", sa.Uuid(as_uuid=True), sa.ForeignKey("characters.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("time_range", sa.String(200), nullable=False, server_default=""),
        sa.Column("attributes", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("position", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_character_periods_character_id", "character_periods", ["character_id"])
    op.create_table(
        "character_versions",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("novel_id", sa.Uuid(as_uuid=True), sa.ForeignKey("novels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("character_id", sa.Uuid(as_uuid=True), sa.ForeignKey("characters.id", ondelete="CASCADE"), nullable=False),
        sa.Column("period_id", sa.Uuid(as_uuid=True), sa.ForeignKey("character_periods.id", ondelete="SET NULL")),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("attributes", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("novel_id", "character_id"),
    )
    op.create_index("ix_character_versions_novel_id", "character_versions", ["novel_id"])
    op.create_index("ix_character_versions_character_id", "character_versions", ["character_id"])


def downgrade() -> None:
    op.drop_table("character_versions")
    op.drop_table("character_periods")
