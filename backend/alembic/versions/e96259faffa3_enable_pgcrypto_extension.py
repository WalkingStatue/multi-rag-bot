"""Enable pgcrypto extension

Revision ID: e96259faffa3
Revises: 9ca6c6c94175
Create Date: 2025-08-16 15:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e96259faffa3'
down_revision = '9ca6c6c94175'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto";')


def downgrade():
    op.execute('DROP EXTENSION "pgcrypto";')
