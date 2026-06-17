"""Add evaluation_reports table

Revision ID: a1b2c3d4e5f6
Revises: 3c0bad4d4d5c
Create Date: 2026-06-17 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '3c0bad4d4d5c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("evaluation_reports"):
        op.create_table(
            "evaluation_reports",
            sa.Column("id", sa.CHAR(length=32), nullable=False),
            sa.Column("user_id", sa.CHAR(length=32), nullable=False),
            sa.Column("message_id", sa.CHAR(length=32), nullable=True),
            sa.Column("mode", sa.String(length=64), nullable=True),
            sa.Column("report_json", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DATETIME(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["message_id"], ["chat_messages.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )

    existing_indexes = {
        idx["name"]
        for idx in inspector.get_indexes("evaluation_reports")
    } if inspector.has_table("evaluation_reports") else set()

    if "ix_evaluation_reports_id" not in existing_indexes:
        op.create_index("ix_evaluation_reports_id", "evaluation_reports", ["id"], unique=False)
    if "ix_evaluation_reports_user_id" not in existing_indexes:
        op.create_index("ix_evaluation_reports_user_id", "evaluation_reports", ["user_id"], unique=False)
    if "ix_evaluation_reports_message_id" not in existing_indexes:
        op.create_index("ix_evaluation_reports_message_id", "evaluation_reports", ["message_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_evaluation_reports_message_id", table_name="evaluation_reports")
    op.drop_index("ix_evaluation_reports_user_id", table_name="evaluation_reports")
    op.drop_index("ix_evaluation_reports_id", table_name="evaluation_reports")
    op.drop_table("evaluation_reports")
