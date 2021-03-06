"""empty message

Revision ID: f36dc55495f9
Revises: fab9bd53103a
Create Date: 2020-04-28 17:00:31.047278

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import Sequence, CreateSequence

Session = sessionmaker()

# revision identifiers, used by Alembic.
revision = 'f36dc55495f9'
down_revision = '646e59f05e1a'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    # op.drop_column('Patient', 'is_found')
    # op.drop_column('Patient', 'is_infected')
    
    op.add_column('Patient', sa.Column('is_dead', sa.BOOLEAN(), autoincrement=False, nullable=False, server_default='false'))
    op.add_column('Patient', sa.Column('in_hospital', sa.BOOLEAN(), autoincrement=False, nullable=False, server_default='false'))
    op.add_column('Patient', sa.Column('is_home', sa.BOOLEAN(), autoincrement=False, nullable=False, server_default='false'))
    op.add_column('Patient', sa.Column('is_healthy', sa.BOOLEAN(), autoincrement=False, nullable=False, server_default='false'))
    op.add_column('PatientState', sa.Column('attrs', sa.JSON(), nullable=True))
    op.add_column('PatientState', sa.Column('id', sa.Integer(), nullable=True))

    op.drop_constraint('PatientState_pkey', 'PatientState', type_='primary')
    bind = op.get_bind()
    session = Session(bind=bind)
    session.execute('UPDATE "PatientState" ou SET id=(SELECT count(*) FROM "PatientState" WHERE ou.created_at > created_at)+1;')
    count = int(session.execute('select count(*) from "PatientState";').fetchone()[0])
    op.execute(CreateSequence(Sequence('patient_state_id_seq')))
    op.alter_column("PatientState", "id", nullable=False, server_default=sa.text("nextval('patient_state_id_seq'::regclass)+%d" % count))

    op.alter_column('PatientState', 'detection_date',
               existing_type=postgresql.TIMESTAMP(),
               nullable=True)
    op.create_primary_key("PatientState_pkey", "PatientState", ["id"])
    op.drop_constraint('PatientState_patient_id_fkey', 'PatientState', type_='foreignkey')
    op.drop_constraint('PatientState_state_id_fkey', 'PatientState', type_='foreignkey')
    op.add_column('State', sa.Column('value', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('State', 'value')
    op.create_foreign_key('PatientState_state_id_fkey', 'PatientState', 'State', ['state_id'], ['id'])
    op.create_foreign_key('PatientState_patient_id_fkey', 'PatientState', 'Patient', ['patient_id'], ['id'])
    op.drop_index(op.f('ix_PatientState_id'), table_name='PatientState')
    op.alter_column('PatientState', 'detection_date',
               existing_type=postgresql.TIMESTAMP(),
               nullable=False)
    op.drop_column('PatientState', 'id')
    op.drop_column('PatientState', 'attrs')
    op.drop_column('Patient', 'is_dead')
    op.drop_column('Patient', 'in_hospital')
    op.drop_column('Patient', 'is_home')
    op.drop_column('Patient', 'is_healthy')

    # op.add_column('Patient', sa.Column('is_infected', sa.BOOLEAN(), autoincrement=False, nullable=True))
    # op.add_column('Patient', sa.Column('is_found', sa.BOOLEAN(), autoincrement=False, nullable=True))
    # ### end Alembic commands ###
