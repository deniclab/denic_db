"""empty message

Revision ID: 915d2224ed26
Revises: 
Create Date: 2018-02-09 17:09:33.432660

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '915d2224ed26'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('user',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('username', sa.String(length=64), nullable=True),
    sa.Column('email', sa.String(length=120), nullable=True),
    sa.Column('password_hash', sa.String(length=128), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_email'), 'user', ['email'], unique=True)
    op.create_index(op.f('ix_user_username'), 'user', ['username'], unique=True)
    op.drop_table('oligos')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('oligos',
    sa.Column('oligo_tube', mysql.INTEGER(display_width=10, unsigned=True), nullable=False),
    sa.Column('oligo_name', mysql.VARCHAR(length=150), nullable=True),
    sa.Column('sequence', mysql.VARCHAR(length=2000), nullable=True),
    sa.Column('creator', mysql.VARCHAR(length=25), nullable=True),
    sa.Column('creation_date', sa.DATE(), nullable=True),
    sa.Column('restrixn_site', mysql.VARCHAR(length=20), nullable=True),
    sa.Column('notes', mysql.VARCHAR(length=500), nullable=True),
    sa.PrimaryKeyConstraint('oligo_tube'),
    mysql_default_charset='utf8',
    mysql_engine='InnoDB'
    )
    op.drop_index(op.f('ix_user_username'), table_name='user')
    op.drop_index(op.f('ix_user_email'), table_name='user')
    op.drop_table('user')
    # ### end Alembic commands ###
