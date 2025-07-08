"""add training jobs

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
    # Create training status enum
    op.execute("CREATE TYPE trainingstatus AS ENUM ('pending', 'queued', 'running', 'completed', 'failed', 'cancelled')")
    
    # Create training_jobs table
    op.create_table('training_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('status', sa.Enum('pending', 'queued', 'running', 'completed', 'failed', 'cancelled', name='trainingstatus'), nullable=True),
        sa.Column('progress', sa.Float(), nullable=True),
        sa.Column('base_model', sa.String(), nullable=False),
        sa.Column('training_method', sa.String(), nullable=False),
        sa.Column('hyperparameters', sa.JSON(), nullable=True),
        sa.Column('gpu_type', sa.String(), nullable=True),
        sa.Column('gpu_count', sa.Integer(), nullable=True),
        sa.Column('current_epoch', sa.Integer(), nullable=True),
        sa.Column('total_epochs', sa.Integer(), nullable=True),
        sa.Column('current_step', sa.Integer(), nullable=True),
        sa.Column('total_steps', sa.Integer(), nullable=True),
        sa.Column('loss', sa.Float(), nullable=True),
        sa.Column('learning_rate', sa.Float(), nullable=True),
        sa.Column('metrics', sa.JSON(), nullable=True),
        sa.Column('logs', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.String(), nullable=True),
        sa.Column('task_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('model_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('dataset_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['dataset_id'], ['datasets.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['model_id'], ['models.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('task_id')
    )


def downgrade() -> None:
    op.drop_table('training_jobs')
    op.execute('DROP TYPE trainingstatus')