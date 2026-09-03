"""Add MITRE, blast radius, and compliance fields to risk_findings

Revision ID: d5e8f1a2b3c4
Revises: c4f359d476fa
Create Date: 2026-07-17 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers
revision = 'd5e8f1a2b3c4'
down_revision = 'c4f359d476fa'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('risk_findings', sa.Column('mitre_technique', sa.String(20), nullable=True))
    op.add_column('risk_findings', sa.Column('mitre_tactic', sa.String(50), nullable=True))
    op.add_column('risk_findings', sa.Column('blast_radius_score', sa.Integer(), nullable=True))
    op.add_column('risk_findings', sa.Column('compliance_refs', JSONB(), nullable=True))
    op.create_index('ix_risk_findings_mitre_technique', 'risk_findings', ['mitre_technique'])


def downgrade() -> None:
    op.drop_index('ix_risk_findings_mitre_technique', table_name='risk_findings')
    op.drop_column('risk_findings', 'compliance_refs')
    op.drop_column('risk_findings', 'blast_radius_score')
    op.drop_column('risk_findings', 'mitre_tactic')
    op.drop_column('risk_findings', 'mitre_technique')
