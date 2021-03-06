"""empty message

Revision ID: ba270072d922
Revises: e7e960f5cd18
Create Date: 2020-06-20 12:24:45.547584

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ba270072d922'
down_revision = 'e7e960f5cd18'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('AddressLocationType',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('value', sa.String(), nullable=True),
    sa.Column('name', sa.String(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name'),
    sa.UniqueConstraint('value')
    )
    op.add_column('Address', sa.Column('location_type_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'Address', 'AddressLocationType', ['location_type_id'], ['id'])
    # op.drop_constraint('Download_status_key', 'Download', type_='unique')
    # op.drop_column('Download', 'status')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    # op.add_column('Download', sa.Column('status', sa.VARCHAR(), autoincrement=False, nullable=True))
    # op.create_unique_constraint('Download_status_key', 'Download', ['status'])
    op.drop_constraint(None, 'Address', type_='foreignkey')
    op.drop_column('Address', 'location_type_id')
    op.drop_table('AddressLocationType')
    # ### end Alembic commands ###
