"""Add content, classification, and evidence models

Revision ID: 002
Revises: 001
Create Date: 2026-05-18 10:30:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create content_items table
    op.create_table(
        'content_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('athlete_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('athletes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('social_account_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('social_accounts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('platform', sa.String(50), nullable=False),
        sa.Column('content_type', sa.Enum('post', 'comment', 'mention', 'dm', 'story', 'video', 'reply', name='contenttype'), nullable=False),
        sa.Column('platform_content_id', sa.String(255), nullable=False),
        sa.Column('author_platform_id', sa.String(255), nullable=False),
        sa.Column('author_username', sa.String(255), nullable=False),
        sa.Column('author_display_name', sa.String(255), nullable=False),
        sa.Column('author_profile_url', sa.String(500), nullable=False),
        sa.Column('author_follower_count', sa.Integer, nullable=False, default=0),
        sa.Column('content_text', sa.Text, nullable=True),
        sa.Column('content_url', sa.String(500), nullable=False),
        sa.Column('media_urls', postgresql.ARRAY(sa.String), nullable=True),
        sa.Column('parent_content_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('content_items.id', ondelete='SET NULL'), nullable=True),
        sa.Column('engagement_metrics', postgresql.JSON, nullable=True),
        sa.Column('discovered_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_content_athlete_discovered', 'content_items', ['athlete_id', 'discovered_at'])
    op.create_index('ix_content_platform_id', 'content_items', ['platform', 'platform_content_id'], unique=True)
    op.create_index('ix_content_author', 'content_items', ['author_platform_id'])
    op.create_index('ix_content_published', 'content_items', ['published_at'])

    # Create classifications table
    op.create_table(
        'classifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('content_item_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('content_items.id', ondelete='CASCADE'), nullable=False),
        sa.Column('athlete_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('athletes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('classification_version', sa.String(50), nullable=False, default='1.0'),
        sa.Column('primary_category', sa.Enum(
            'normal_criticism', 'harassment', 'hate_speech', 'sexual_harassment',
            'threat_of_violence', 'doxxing', 'impersonation', 'fake_quote',
            'fake_endorsement', 'deepfake', 'coordinated_attack', 'gambling_abuse',
            name='classificationcategory'
        ), nullable=False),
        sa.Column('secondary_categories', postgresql.ARRAY(sa.String), nullable=True),
        sa.Column('severity_level', sa.Integer, nullable=False),
        sa.Column('confidence_score', sa.Float, nullable=False),
        sa.Column('reasoning', sa.Text, nullable=False),
        sa.Column('key_evidence', postgresql.ARRAY(sa.String), nullable=True),
        sa.Column('detected_entities', postgresql.JSON, nullable=True),
        sa.Column('model_used', sa.String(100), nullable=False),
        sa.Column('human_reviewed', sa.Boolean, nullable=False, default=False),
        sa.Column('human_review_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('human_reviewer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('human_override_category', sa.String(100), nullable=True),
        sa.Column('status', sa.Enum('pending', 'confirmed', 'false_positive', 'escalated', name='classificationstatus'), nullable=False),
        sa.Column('recommended_action', sa.String(50), nullable=False, default='monitor'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_classification_content', 'classifications', ['content_item_id'])
    op.create_index('ix_classification_athlete_severity', 'classifications', ['athlete_id', 'severity_level'])
    op.create_index('ix_classification_category', 'classifications', ['primary_category'])
    op.create_index('ix_classification_created', 'classifications', ['created_at'])
    op.create_index('ix_classification_status', 'classifications', ['status'])

    # Create evidence table
    op.create_table(
        'evidence',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('content_item_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('content_items.id', ondelete='CASCADE'), nullable=False),
        sa.Column('classification_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('classifications.id', ondelete='CASCADE'), nullable=True),
        sa.Column('athlete_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('athletes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('evidence_type', sa.Enum('screenshot', 'video', 'raw_html', 'metadata', 'api_response', name='evidencetype'), nullable=False),
        sa.Column('storage_path', sa.String(1000), nullable=False),
        sa.Column('storage_url', sa.String(1000), nullable=True),
        sa.Column('file_size', sa.BigInteger, nullable=True),
        sa.Column('mime_type', sa.String(100), nullable=True),
        sa.Column('checksum', sa.String(64), nullable=False),
        sa.Column('metadata', postgresql.JSON, nullable=True),
        sa.Column('chain_of_custody', postgresql.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_evidence_content', 'evidence', ['content_item_id'])
    op.create_index('ix_evidence_athlete', 'evidence', ['athlete_id'])
    op.create_index('ix_evidence_type', 'evidence', ['evidence_type'])
    op.create_index('ix_evidence_created', 'evidence', ['created_at'])


def downgrade() -> None:
    op.drop_table('evidence')
    op.drop_table('classifications')
    op.drop_table('content_items')

    op.execute('DROP TYPE IF EXISTS evidencetype')
    op.execute('DROP TYPE IF EXISTS classificationstatus')
    op.execute('DROP TYPE IF EXISTS classificationcategory')
    op.execute('DROP TYPE IF EXISTS contenttype')
