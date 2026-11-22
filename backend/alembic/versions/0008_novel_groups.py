"""user-made groups for novels"""

import sqlalchemy as sa
from alembic import op

revision = "0008_novel_groups"
down_revision = "0007_catalog_assets_templates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "novel_groups",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.add_column("novels", sa.Column("group_id", sa.Uuid(as_uuid=True), sa.ForeignKey("novel_groups.id", ondelete="SET NULL")))
    op.add_column("novels", sa.Column("grouped_at", sa.DateTime(timezone=True)))
    op.create_index("ix_novels_group_id", "novels", ["group_id"])


def downgrade() -> None:
    op.drop_index("ix_novels_group_id", table_name="novels")
    op.drop_column("novels", "grouped_at")
    op.drop_column("novels", "group_id")
    op.drop_table("novel_groups")
