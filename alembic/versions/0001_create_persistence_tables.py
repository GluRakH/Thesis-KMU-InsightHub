"""create persistence tables

Revision ID: 0001_create_persistence_tables
Revises:
Create Date: 2026-02-15 00:00:00

"""

from alembic import op
import sqlalchemy as sa


revision = "0001_create_persistence_tables"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "use_cases",
        sa.Column("use_case_id", sa.String(length=64), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("use_case_type", sa.Enum("BUSINESS_IMPACT", "PROCESS_AUTOMATION", "COMBINED", name="usecasetype"), nullable=False),
        sa.Column("model_version", sa.String(length=32), nullable=False, server_default="1.0.0"),
        sa.Column("prompt_version", sa.String(length=32), nullable=False, server_default="1.0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "answer_sets",
        sa.Column("answer_set_id", sa.String(length=64), primary_key=True),
        sa.Column("use_case_id", sa.String(length=64), sa.ForeignKey("use_cases.use_case_id"), nullable=False),
        sa.Column("status", sa.Enum("DRAFT", "SUBMITTED", "LOCKED", name="answersetstatus"), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("model_version", sa.String(length=32), nullable=False, server_default="1.0.0"),
        sa.Column("prompt_version", sa.String(length=32), nullable=False, server_default="1.0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "answers",
        sa.Column("answer_id", sa.String(length=64), primary_key=True),
        sa.Column("answer_set_id", sa.String(length=64), sa.ForeignKey("answer_sets.answer_set_id"), nullable=False),
        sa.Column("question_id", sa.String(length=64), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("model_version", sa.String(length=32), nullable=False, server_default="1.0.0"),
        sa.Column("prompt_version", sa.String(length=32), nullable=False, server_default="1.0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "assessments_bi",
        sa.Column("bi_assessment_id", sa.String(length=64), primary_key=True),
        sa.Column("answer_set_id", sa.String(length=64), sa.ForeignKey("answer_sets.answer_set_id"), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("model_version", sa.String(length=32), nullable=False, server_default="1.0.0"),
        sa.Column("prompt_version", sa.String(length=32), nullable=False, server_default="1.0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "assessments_pa",
        sa.Column("pa_assessment_id", sa.String(length=64), primary_key=True),
        sa.Column("answer_set_id", sa.String(length=64), sa.ForeignKey("answer_sets.answer_set_id"), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("model_version", sa.String(length=32), nullable=False, server_default="1.0.0"),
        sa.Column("prompt_version", sa.String(length=32), nullable=False, server_default="1.0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "synthesis",
        sa.Column("synthesis_id", sa.String(length=64), primary_key=True),
        sa.Column("bi_assessment_id", sa.String(length=64), sa.ForeignKey("assessments_bi.bi_assessment_id"), nullable=False),
        sa.Column("pa_assessment_id", sa.String(length=64), sa.ForeignKey("assessments_pa.pa_assessment_id"), nullable=False),
        sa.Column("recommendation", sa.Text(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("model_version", sa.String(length=32), nullable=False, server_default="1.0.0"),
        sa.Column("prompt_version", sa.String(length=32), nullable=False, server_default="1.0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "measure_catalogs",
        sa.Column("catalog_id", sa.String(length=64), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("status", sa.Enum("DRAFT", "PUBLISHED", "ARCHIVED", name="catalogstatus"), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("model_version", sa.String(length=32), nullable=False, server_default="1.0.0"),
        sa.Column("prompt_version", sa.String(length=32), nullable=False, server_default="1.0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "measures",
        sa.Column("measure_id", sa.String(length=64), primary_key=True),
        sa.Column("catalog_id", sa.String(length=64), sa.ForeignKey("measure_catalogs.catalog_id"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.Enum("ORGANIZATIONAL", "TECHNICAL", "GOVERNANCE", "DATA", name="measurecategory"), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("model_version", sa.String(length=32), nullable=False, server_default="1.0.0"),
        sa.Column("prompt_version", sa.String(length=32), nullable=False, server_default="1.0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "user_selections",
        sa.Column("user_selection_id", sa.String(length=64), primary_key=True),
        sa.Column("synthesis_id", sa.String(length=64), sa.ForeignKey("synthesis.synthesis_id"), nullable=False),
        sa.Column("selected_measure_ids", sa.JSON(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("model_version", sa.String(length=32), nullable=False, server_default="1.0.0"),
        sa.Column("prompt_version", sa.String(length=32), nullable=False, server_default="1.0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("user_selections")
    op.drop_table("measures")
    op.drop_table("measure_catalogs")
    op.drop_table("synthesis")
    op.drop_table("assessments_pa")
    op.drop_table("assessments_bi")
    op.drop_table("answers")
    op.drop_table("answer_sets")
    op.drop_table("use_cases")
