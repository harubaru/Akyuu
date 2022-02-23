"""create user and story tables

Revision ID: 6336b3efaac0
Revises: 
Create Date: 2022-02-22 08:11:50.733620

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6336b3efaac0'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'users',
        # id is a unsigned 64-bit integer
        sa.Column('id', sa.BigInteger, primary_key=True),
        sa.Column('gensettings', sa.String, unique=False),
        sa.Column('storyids', sa.String, unique=False),
        sa.Column('quota', sa.Integer, unique=False)
    )
    op.create_table(
        'stories',
        sa.Column('uuid', sa.String, primary_key=True),
        sa.Column('owner_id', sa.BigInteger, index=True),
        sa.Column('content_metadata', sa.String, unique=False),
        sa.Column('content', sa.String, unique=False)
    )
    pass

def downgrade():
    op.drop_table('stories')
    op.drop_table('users')
    pass
