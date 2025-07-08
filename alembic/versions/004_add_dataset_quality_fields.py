"""Add dataset quality and preprocessing fields

Revision ID: 004
Revises: 003
Create Date: 2025-01-07

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to datasets table
    op.add_column('datasets', sa.Column('format', sa.Enum('JSON', 'JSONL', 'CSV', 'TSV', 'PARQUET', 'ALPACA', 'SHAREGPT', name='datasetformat'), nullable=True))
    op.add_column('datasets', sa.Column('samples_count', sa.Integer(), nullable=True))
    op.add_column('datasets', sa.Column('preprocessing_config', sa.JSON(), nullable=True))
    op.add_column('datasets', sa.Column('quality_metrics', sa.JSON(), nullable=True))
    
    # Update existing size column comment (it now represents bytes, not samples)
    op.alter_column('datasets', 'size',
                    comment='Size in bytes')


def downgrade() -> None:
    # Remove added columns
    op.drop_column('datasets', 'quality_metrics')
    op.drop_column('datasets', 'preprocessing_config')
    op.drop_column('datasets', 'samples_count')
    op.drop_column('datasets', 'format')
    
    # Drop enum type
    op.execute('DROP TYPE IF EXISTS datasetformat')