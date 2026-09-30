"""Initial relational schema with 11 tables, constraints, partial indexes, and append-only triggers.

Revision ID: 001_initial_schema
Revises: None
Create Date: 2026-10-01 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. users
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('role', sa.String(length=32), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('phone', sa.String(length=64), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('demo_session_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_demo_session_id', 'users', ['demo_session_id'])

    # 2. medical_profiles
    op.create_table(
        'medical_profiles',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('blood_group', sa.String(length=8), nullable=True),
        sa.Column('allergies', sa.Text(), nullable=True),
        sa.Column('conditions', sa.Text(), nullable=True),
        sa.Column('medications', sa.Text(), nullable=True),
        sa.Column('contacts', postgresql.JSONB(), server_default='[]', nullable=False),
        sa.Column('share_during_emergency', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 3. responder_profiles
    op.create_table(
        'responder_profiles',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('category', sa.String(length=64), nullable=False),
        sa.Column('readiness', sa.String(length=32), server_default='off_duty', nullable=False),
        sa.Column('service_radius_m', sa.Integer(), server_default='3000', nullable=False),
        sa.Column('last_lat', sa.Float(), nullable=True),
        sa.Column('last_lng', sa.Float(), nullable=True),
        sa.Column('last_location_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('pinned_location', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('acceptance_rate', sa.Float(), server_default='1.0', nullable=False),
        sa.Column('responses_24h', sa.Integer(), server_default='0', nullable=False),
        sa.Column('cooldown_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_responder_readiness_loc', 'responder_profiles', ['readiness', 'last_lat', 'last_lng'])

    # 4. responder_skills
    op.create_table(
        'responder_skills',
        sa.Column('responder_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('skill_code', sa.String(length=64), primary_key=True),
        sa.Column('level', sa.Integer(), nullable=False),
        sa.CheckConstraint('level BETWEEN 1 AND 3', name='ck_responder_skills_level'),
    )

    # 5. responder_credentials
    op.create_table(
        'responder_credentials',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('responder_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('credential_type', sa.String(length=64), nullable=False),
        sa.Column('issuer', sa.String(length=255), nullable=False),
        sa.Column('reference_no', sa.String(length=128), nullable=False),
        sa.Column('expires_on', sa.Date(), nullable=False),
        sa.Column('status', sa.String(length=32), server_default='pending', nullable=False),
        sa.Column('reviewed_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('review_note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_responder_credentials_responder_id', 'responder_credentials', ['responder_id'])

    # 6. ambulance_units
    op.create_table(
        'ambulance_units',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('operator_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('callsign', sa.String(length=64), nullable=False),
        sa.Column('unit_type', sa.String(length=32), server_default='basic', nullable=False),
        sa.Column('status', sa.String(length=32), server_default='available', nullable=False),
        sa.Column('lat', sa.Float(), nullable=False),
        sa.Column('lng', sa.Float(), nullable=False),
        sa.Column('base_name', sa.String(length=255), nullable=False),
        sa.Column('demo_session_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.UniqueConstraint('callsign', 'demo_session_id', name='uq_ambulance_callsign_session'),
    )
    op.create_index('ix_ambulance_units_callsign', 'ambulance_units', ['callsign'])
    op.create_index('ix_ambulance_units_demo_session_id', 'ambulance_units', ['demo_session_id'])

    # 7. emergencies
    op.create_table(
        'emergencies',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('patient_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('reported_by_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('idempotency_key', sa.String(length=128), nullable=False),
        sa.Column('status', sa.String(length=32), server_default='CREATED', nullable=False),
        sa.Column('community_track', sa.String(length=32), server_default='NOT_STARTED', nullable=False),
        sa.Column('professional_track', sa.String(length=32), server_default='NOT_STARTED', nullable=False),
        sa.Column('priority', sa.String(length=16), nullable=False),
        sa.Column('emergency_type', sa.String(length=64), nullable=False),
        sa.Column('triage', postgresql.JSONB(), nullable=False),
        sa.Column('dispatch_plan', postgresql.JSONB(), server_default='{}', nullable=False),
        sa.Column('lat', sa.Float(), nullable=False),
        sa.Column('lng', sa.Float(), nullable=False),
        sa.Column('location_accuracy_m', sa.Float(), server_default='10.0', nullable=False),
        sa.Column('location_hint', sa.Text(), nullable=True),
        sa.Column('patient_is_reporter', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('consent_share_medical', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('next_event_seq', sa.Integer(), server_default='1', nullable=False),
        sa.Column('handover_snapshot', postgresql.JSONB(), nullable=True),
        sa.Column('close_reason', sa.String(length=64), nullable=True),
        sa.Column('demo_session_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint('lat BETWEEN -90 AND 90', name='ck_emergencies_lat'),
        sa.CheckConstraint('lng BETWEEN -180 AND 180', name='ck_emergencies_lng'),
    )
    op.create_index('ix_emergencies_status_demo', 'emergencies', ['status', 'demo_session_id'])

    # Partial unique indexes for emergencies (Spec §7.2)
    op.execute("""
        CREATE UNIQUE INDEX uq_emergencies_active_patient 
        ON emergencies(patient_user_id) 
        WHERE status NOT IN ('COMPLETED', 'CANCELLED', 'NO_COVERAGE_CLOSED');
    """)
    op.execute("""
        CREATE UNIQUE INDEX uq_emergencies_reporter_idempotency 
        ON emergencies(reported_by_user_id, idempotency_key);
    """)

    # 8. emergency_events
    op.create_table(
        'emergency_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('emergency_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('emergencies.id', ondelete='CASCADE'), nullable=False),
        sa.Column('seq', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(length=64), nullable=False),
        sa.Column('actor_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('actor_role', sa.String(length=32), nullable=False),
        sa.Column('payload', postgresql.JSONB(), server_default='{}', nullable=False),
        sa.Column('visible_to', postgresql.JSONB(), server_default='[]', nullable=False),
        sa.Column('at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('emergency_id', 'seq', name='uq_events_emergency_seq'),
    )
    op.create_index('ix_events_emergency_seq', 'emergency_events', ['emergency_id', 'seq'])

    # 9. dispatch_offers
    op.create_table(
        'dispatch_offers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('emergency_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('emergencies.id', ondelete='CASCADE'), nullable=False),
        sa.Column('track', sa.String(length=32), nullable=False),
        sa.Column('target_kind', sa.String(length=32), nullable=False),
        sa.Column('responder_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('ambulance_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('ambulance_units.id', ondelete='SET NULL'), nullable=True),
        sa.Column('rank', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=32), server_default='OFFERED', nullable=False),
        sa.Column('offered_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('responded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('arrived_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('decline_reason', sa.String(length=64), nullable=True),
        sa.Column('eta_s', sa.Integer(), nullable=True),
        sa.Column('distance_m', sa.Float(), nullable=True),
        sa.Column('score_snapshot', postgresql.JSONB(), nullable=True),
        sa.Column('sim_start_lat', sa.Float(), nullable=True),
        sa.Column('sim_start_lng', sa.Float(), nullable=True),
        sa.Column('sim_travel_s', sa.Integer(), nullable=True),
        sa.Column('actions_reported', postgresql.JSONB(), server_default='[]', nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.CheckConstraint(
            "((target_kind = 'responder' AND responder_id IS NOT NULL AND ambulance_id IS NULL) OR "
            "(target_kind = 'ambulance' AND ambulance_id IS NOT NULL AND responder_id IS NULL))",
            name='ck_offer_target_kind'
        ),
    )
    op.create_index('ix_offers_status_expiry', 'dispatch_offers', ['status', 'expires_at'])
    op.create_index('ix_offers_emergency_id', 'dispatch_offers', ['emergency_id'])

    # Partial unique indexes for dispatch_offers (Spec §7.2)
    op.execute("""
        CREATE UNIQUE INDEX uq_offers_active_responder 
        ON dispatch_offers(responder_id) 
        WHERE status IN ('OFFERED', 'ACCEPTED', 'ARRIVED');
    """)
    op.execute("""
        CREATE UNIQUE INDEX uq_offers_active_ambulance 
        ON dispatch_offers(ambulance_id) 
        WHERE status IN ('OFFERED', 'ACCEPTED', 'ARRIVED');
    """)
    op.execute("""
        CREATE UNIQUE INDEX uq_offers_active_track 
        ON dispatch_offers(emergency_id, track) 
        WHERE status IN ('OFFERED', 'ACCEPTED', 'ARRIVED');
    """)

    # 10. audit_logs
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('actor_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('actor_role', sa.String(length=32), nullable=False),
        sa.Column('action', sa.String(length=64), nullable=False),
        sa.Column('resource_type', sa.String(length=64), nullable=False),
        sa.Column('resource_id', sa.String(length=128), nullable=False),
        sa.Column('outcome', sa.String(length=16), nullable=False),
        sa.Column('ip_hash', sa.String(length=128), nullable=False),
        sa.Column('meta', postgresql.JSONB(), server_default='{}', nullable=False),
    )
    op.create_index('ix_audit_logs_at', 'audit_logs', ['at'])
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('ix_audit_logs_action_at', 'audit_logs', ['action', 'at'])

    # 11. demo_sessions
    op.create_table(
        'demo_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('clock_offset_s', sa.Integer(), server_default='0', nullable=False),
        sa.Column('scenario', postgresql.JSONB(), server_default='{}', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
    )

    # 12. PL/pgSQL Append-Only Triggers for emergency_events and audit_logs (Spec §7.1, §7.2, DATA-03)
    op.execute("""
        CREATE OR REPLACE FUNCTION prevent_append_only_mutation()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'Table % is append-only: UPDATE and DELETE operations are forbidden.', TG_TABLE_NAME;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE TRIGGER trg_emergency_events_immutable
        BEFORE UPDATE OR DELETE ON emergency_events
        FOR EACH ROW EXECUTE FUNCTION prevent_append_only_mutation();
    """)

    op.execute("""
        CREATE TRIGGER trg_audit_logs_immutable
        BEFORE UPDATE OR DELETE ON audit_logs
        FOR EACH ROW EXECUTE FUNCTION prevent_append_only_mutation();
    """)


def downgrade() -> None:
    # Drop triggers and procedures
    op.execute("DROP TRIGGER IF EXISTS trg_audit_logs_immutable ON audit_logs;")
    op.execute("DROP TRIGGER IF EXISTS trg_emergency_events_immutable ON emergency_events;")
    op.execute("DROP FUNCTION IF EXISTS prevent_append_only_mutation();")

    # Drop partial indexes
    op.execute("DROP INDEX IF EXISTS uq_offers_active_track;")
    op.execute("DROP INDEX IF EXISTS uq_offers_active_ambulance;")
    op.execute("DROP INDEX IF EXISTS uq_offers_active_responder;")
    op.execute("DROP INDEX IF EXISTS uq_emergencies_reporter_idempotency;")
    op.execute("DROP INDEX IF EXISTS uq_emergencies_active_patient;")

    # Drop tables in reverse dependency order
    op.drop_table('demo_sessions')
    op.drop_table('audit_logs')
    op.drop_table('dispatch_offers')
    op.drop_table('emergency_events')
    op.drop_table('emergencies')
    op.drop_table('ambulance_units')
    op.drop_table('responder_credentials')
    op.drop_table('responder_skills')
    op.drop_table('responder_profiles')
    op.drop_table('medical_profiles')
    op.drop_table('users')
