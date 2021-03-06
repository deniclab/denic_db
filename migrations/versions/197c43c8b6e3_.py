"""empty message

Revision ID: 197c43c8b6e3
Revises: 0104cd460789
Create Date: 2018-04-09 10:10:12.290289

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '197c43c8b6e3'
down_revision = '0104cd460789'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('plasmid', sa.Column('backbone', sa.String(length=25), nullable=True))
    op.add_column('plasmid', sa.Column('insert_source', sa.String(length=50), nullable=True))
    op.add_column('temp_plasmid', sa.Column('backbone', sa.String(length=25), nullable=True))
    op.add_column('temp_plasmid', sa.Column('insert_source', sa.String(length=50), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('temp_plasmid', 'insert_source')
    op.drop_column('temp_plasmid', 'backbone')
    op.drop_column('plasmid', 'insert_source')
    op.drop_column('plasmid', 'backbone')
    # ### end Alembic commands ###
