"""forensic canvas initial schema

Revision ID: 20260909_01
Revises: None
Create Date: 2026-09-09
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260909_01"
down_revision: str | None = None
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    op.create_table(
        "evidence_items",
        sa.Column("evidence_id", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("canonical_bytes", sa.LargeBinary(), nullable=False),
        sa.PrimaryKeyConstraint("evidence_id"),
    )

    op.create_table(
        "graph_nodes",
        sa.Column("node_id", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("canonical_bytes", sa.LargeBinary(), nullable=False),
        sa.PrimaryKeyConstraint("node_id"),
    )

    op.create_table(
        "graph_edges",
        sa.Column("edge_id", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("target", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("canonical_bytes", sa.LargeBinary(), nullable=False),
        sa.ForeignKeyConstraint(["source"], ["graph_nodes.node_id"]),
        sa.ForeignKeyConstraint(["target"], ["graph_nodes.node_id"]),
        sa.PrimaryKeyConstraint("edge_id"),
    )
    op.create_index("graph_edges_source_idx", "graph_edges", ["source"])
    op.create_index("graph_edges_target_idx", "graph_edges", ["target"])

    op.create_table(
        "cases",
        sa.Column("case_id", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("canonical_bytes", sa.LargeBinary(), nullable=False),
        sa.PrimaryKeyConstraint("case_id"),
    )

    op.create_table(
        "case_snapshots",
        sa.Column("case_id", sa.Text(), nullable=False),
        sa.Column("snapshot_hash", sa.String(length=64), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("canonical_bytes", sa.LargeBinary(), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["cases.case_id"]),
        sa.PrimaryKeyConstraint("case_id", "snapshot_hash"),
    )

    op.create_table(
        "case_evidence",
        sa.Column("case_id", sa.Text(), nullable=False),
        sa.Column("edge_id", sa.Text(), nullable=False),
        sa.Column("evidence_id", sa.Text(), nullable=False),
        sa.Column("is_pinned", sa.Boolean(), nullable=False),
        sa.Column("typology_tag", sa.Text(), nullable=True),
        sa.Column("analyst_id", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("length(trim(analyst_id)) > 0", name="case_evidence_analyst_id_check"),
        sa.CheckConstraint(
            "typology_tag IS NULL OR typology_tag IN ('SEED_HUB', 'SMURFING', 'SHELL_CORP', 'LAYERING', 'CASHOUT', 'CRYPTO_OTC', 'BENIGN')",
            name="case_evidence_typology_tag_check",
        ),
        sa.ForeignKeyConstraint(["case_id"], ["cases.case_id"]),
        sa.ForeignKeyConstraint(["edge_id"], ["graph_edges.edge_id"]),
        sa.ForeignKeyConstraint(["evidence_id"], ["evidence_items.evidence_id"]),
        sa.PrimaryKeyConstraint("case_id", "edge_id"),
    )

    op.create_table(
        "case_feedback",
        sa.Column("event_id", sa.Text(), nullable=False),
        sa.Column("case_id", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("canonical_bytes", sa.LargeBinary(), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["cases.case_id"]),
        sa.PrimaryKeyConstraint("event_id"),
    )


def downgrade() -> None:
    op.drop_table("case_feedback")
    op.drop_table("case_evidence")
    op.drop_table("case_snapshots")
    op.drop_table("cases")
    op.drop_index("graph_edges_target_idx", table_name="graph_edges")
    op.drop_index("graph_edges_source_idx", table_name="graph_edges")
    op.drop_table("graph_edges")
    op.drop_table("graph_nodes")
    op.drop_table("evidence_items")
