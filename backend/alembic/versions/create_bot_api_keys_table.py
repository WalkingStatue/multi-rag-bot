"""Add bot_api_keys table

Revision ID: add_bot_api_keys
Revises: 
Create Date: 2024-08-22 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision = 'add_bot_api_keys'
down_revision = None  # Replace with your latest migration ID
branch_labels = None
depends_on = None


def upgrade():
    # Create bot_api_keys table
    op.create_table(
        'bot_api_keys',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('bot_id', UUID(as_uuid=True), sa.ForeignKey('bots.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('key_hash', sa.String(128), nullable=False, unique=True),
        sa.Column('key_prefix', sa.String(12), nullable=False),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        
        # Create indexes
        sa.Index('ix_bot_api_keys_bot_id', 'bot_id'),
        sa.Index('ix_bot_api_keys_key_hash', 'key_hash'),
        sa.Index('ix_bot_api_keys_created_by', 'created_by'),
    )


def downgrade():
    # Drop bot_api_keys table
    op.drop_table('bot_api_keys')
