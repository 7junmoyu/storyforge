"""world records, character attributes, templates, and uploaded files"""

import sqlalchemy as sa
from alembic import op

revision = "0007_catalog_assets_templates"
down_revision = "0006_world_character_basics"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("characters", sa.Column("attributes", sa.Text(), nullable=False, server_default="{}"))
    op.create_table(
        "world_records",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("world_id", sa.Uuid(as_uuid=True), sa.ForeignKey("worlds.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("time_label", sa.String(200), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_world_records_world_id", "world_records", ["world_id"])
    op.create_table(
        "attribute_templates",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("target", sa.String(32), nullable=False, server_default="character"),
        sa.Column("fields", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "media_assets",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("owner_kind", sa.String(32), nullable=False, server_default=""),
        sa.Column("owner_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("stored_name", sa.String(255), nullable=False),
        sa.Column("mime", sa.String(120), nullable=False, server_default=""),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_media_assets_owner_id", "media_assets", ["owner_id"])


def downgrade() -> None:
    op.drop_table("media_assets")
    op.drop_table("attribute_templates")
    op.drop_table("world_records")
    op.drop_column("characters", "attributes")
