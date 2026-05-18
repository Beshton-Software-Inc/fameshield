"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-05-18 10:00:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create organizations table
    op.create_table(
        'organizations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('type', sa.Enum('federation', 'school', 'agency', 'club', 'individual', name='organizationtype'), nullable=False),
        sa.Column('tier', sa.Enum('starter', 'professional', 'enterprise', name='organizationtier'), nullable=False),
        sa.Column('settings', postgresql.JSON, nullable=True),
        sa.Column('billing_info', postgresql.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_organizations_name', 'organizations', ['name'])

    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('role', sa.Enum('admin', 'coach', 'agent', 'mental_health_staff', 'legal', 'viewer', name='userrole'), nullable=False),
        sa.Column('permissions', postgresql.ARRAY(sa.String), nullable=True),
        sa.Column('first_name', sa.String(100), nullable=False),
        sa.Column('last_name', sa.String(100), nullable=False),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('athlete_access', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column('notification_preferences', postgresql.JSON, nullable=True),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_users_email', 'users', ['email'])
    op.create_index('ix_users_organization', 'users', ['organization_id'])

    # Create athletes table
    op.create_table(
        'athletes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('first_name', sa.String(100), nullable=False),
        sa.Column('last_name', sa.String(100), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('date_of_birth', sa.Date, nullable=False),
        sa.Column('sport', sa.String(100), nullable=False),
        sa.Column('bio', sa.String(1000), nullable=True),
        sa.Column('profile_image_url', sa.String(500), nullable=True),
        sa.Column('risk_level', sa.Enum('low', 'medium', 'high', 'critical', name='risklevel'), nullable=False),
        sa.Column('monitoring_enabled', sa.Boolean, nullable=False, default=True),
        sa.Column('settings', postgresql.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_monitored_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_athletes_email', 'athletes', ['email'])
    op.create_index('ix_athletes_organization', 'athletes', ['organization_id'])
    op.create_index('ix_athletes_risk_level', 'athletes', ['risk_level'])

    # Create social_accounts table
    op.create_table(
        'social_accounts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('athlete_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('athletes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('platform', sa.Enum('twitter', 'instagram', 'tiktok', 'youtube', 'facebook', name='platform'), nullable=False),
        sa.Column('platform_user_id', sa.String(255), nullable=False),
        sa.Column('username', sa.String(255), nullable=False),
        sa.Column('display_name', sa.String(255), nullable=False),
        sa.Column('profile_url', sa.String(500), nullable=False),
        sa.Column('follower_count', sa.Integer, nullable=False, default=0),
        sa.Column('verified', sa.Boolean, nullable=False, default=False),
        sa.Column('access_token', sa.String(500), nullable=True),
        sa.Column('refresh_token', sa.String(500), nullable=True),
        sa.Column('token_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('monitoring_status', sa.Enum('active', 'paused', 'error', name='monitoringstatus'), nullable=False),
        sa.Column('last_monitored_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_social_accounts_athlete', 'social_accounts', ['athlete_id'])
    op.create_index('ix_social_accounts_platform_user', 'social_accounts', ['platform', 'platform_user_id'])
    op.create_index('ix_social_accounts_status', 'social_accounts', ['monitoring_status'])


def downgrade() -> None:
    op.drop_table('social_accounts')
    op.drop_table('athletes')
    op.drop_table('users')
    op.drop_table('organizations')

    op.execute('DROP TYPE IF EXISTS monitoringstatus')
    op.execute('DROP TYPE IF EXISTS platform')
    op.execute('DROP TYPE IF EXISTS risklevel')
    op.execute('DROP TYPE IF EXISTS userrole')
    op.execute('DROP TYPE IF EXISTS organizationtier')
    op.execute('DROP TYPE IF EXISTS organizationtype')
