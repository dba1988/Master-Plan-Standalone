"""add_building_tables

Revision ID: f8cdd7a90887
Revises: c5e51b2e23f0
Create Date: 2026-02-12

Adds tables for building/tower views feature:
- buildings: Tower/building metadata
- building_views: View angles (elevation, rotation, floor plan)
- building_stacks: Vertical unit groupings
- building_units: Individual apartments
- view_overlay_mappings: Overlay geometry per view
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'f8cdd7a90887'
down_revision: Union[str, None] = 'c5e51b2e23f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # === BUILDINGS TABLE ===
    op.create_table(
        'buildings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('ref', sa.String(50), nullable=False),
        sa.Column('name', postgresql.JSONB, nullable=False),
        sa.Column('floors_count', sa.Integer, nullable=False),
        sa.Column('floors_start', sa.Integer, server_default='1'),
        sa.Column('skip_floors', postgresql.ARRAY(sa.Integer), server_default='{}'),
        sa.Column('metadata', postgresql.JSONB, server_default='{}'),
        sa.Column('sort_order', sa.Integer, server_default='0'),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime, server_default=sa.text('NOW()')),
        sa.UniqueConstraint('project_id', 'ref', name='uq_building_ref'),
    )
    op.create_index('ix_buildings_project', 'buildings', ['project_id'])

    # === BUILDING VIEWS TABLE ===
    op.create_table(
        'building_views',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('building_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('buildings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('view_type', sa.String(20), nullable=False),
        sa.Column('ref', sa.String(50), nullable=False),
        sa.Column('label', postgresql.JSONB, nullable=True),
        sa.Column('angle', sa.Integer, nullable=True),
        sa.Column('floor_number', sa.Integer, nullable=True),
        sa.Column('view_box', sa.String(100), nullable=True),
        sa.Column('asset_path', sa.String(500), nullable=True),
        sa.Column('tiles_generated', sa.Boolean, server_default='false'),
        sa.Column('sort_order', sa.Integer, server_default='0'),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('NOW()')),
        sa.UniqueConstraint('building_id', 'ref', name='uq_building_view_ref'),
        sa.CheckConstraint(
            "(view_type = 'elevation' AND angle IS NULL AND floor_number IS NULL) OR "
            "(view_type = 'rotation' AND angle IS NOT NULL AND floor_number IS NULL) OR "
            "(view_type = 'floor_plan' AND floor_number IS NOT NULL)",
            name='ck_building_view_type_fields'
        ),
    )
    op.create_index('ix_building_views_building', 'building_views', ['building_id'])
    op.create_index('ix_building_views_type', 'building_views', ['view_type'])

    # === BUILDING STACKS TABLE ===
    op.create_table(
        'building_stacks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('building_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('buildings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('ref', sa.String(50), nullable=False),
        sa.Column('label', postgresql.JSONB, nullable=True),
        sa.Column('floor_start', sa.Integer, nullable=False),
        sa.Column('floor_end', sa.Integer, nullable=False),
        sa.Column('unit_type', sa.String(50), nullable=True),
        sa.Column('facing', sa.String(50), nullable=True),
        sa.Column('metadata', postgresql.JSONB, server_default='{}'),
        sa.Column('sort_order', sa.Integer, server_default='0'),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('NOW()')),
        sa.UniqueConstraint('building_id', 'ref', name='uq_building_stack_ref'),
    )
    op.create_index('ix_building_stacks_building', 'building_stacks', ['building_id'])

    # === BUILDING UNITS TABLE ===
    op.create_table(
        'building_units',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('building_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('buildings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('stack_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('building_stacks.id', ondelete='SET NULL'), nullable=True),
        sa.Column('ref', sa.String(50), nullable=False),
        sa.Column('floor_number', sa.Integer, nullable=False),
        sa.Column('unit_number', sa.String(20), nullable=False),
        sa.Column('unit_type', sa.String(50), nullable=True),
        sa.Column('area_sqm', sa.Numeric(10, 2), nullable=True),
        sa.Column('area_sqft', sa.Numeric(10, 2), nullable=True),
        sa.Column('status', sa.String(20), server_default='available'),
        sa.Column('price', sa.Numeric(15, 2), nullable=True),
        sa.Column('props', postgresql.JSONB, server_default='{}'),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime, server_default=sa.text('NOW()')),
        sa.UniqueConstraint('building_id', 'ref', name='uq_building_unit_ref'),
    )
    op.create_index('ix_building_units_building', 'building_units', ['building_id'])
    op.create_index('ix_building_units_floor', 'building_units', ['building_id', 'floor_number'])
    op.create_index('ix_building_units_stack', 'building_units', ['stack_id'])
    op.create_index('ix_building_units_status', 'building_units', ['status'])

    # === VIEW OVERLAY MAPPINGS TABLE ===
    op.create_table(
        'view_overlay_mappings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('view_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('building_views.id', ondelete='CASCADE'), nullable=False),
        sa.Column('target_type', sa.String(20), nullable=False),
        sa.Column('stack_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('building_stacks.id', ondelete='CASCADE'), nullable=True),
        sa.Column('unit_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('building_units.id', ondelete='CASCADE'), nullable=True),
        sa.Column('geometry', postgresql.JSONB, nullable=False),
        sa.Column('label_position', postgresql.JSONB, nullable=True),
        sa.Column('sort_order', sa.Integer, server_default='0'),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('NOW()')),
        sa.UniqueConstraint('view_id', 'target_type', 'stack_id', name='uq_view_stack_mapping'),
        sa.UniqueConstraint('view_id', 'target_type', 'unit_id', name='uq_view_unit_mapping'),
    )
    op.create_index('ix_overlay_mappings_view', 'view_overlay_mappings', ['view_id'])
    op.create_index('ix_overlay_mappings_target', 'view_overlay_mappings', ['target_type'])


def downgrade() -> None:
    op.drop_table('view_overlay_mappings')
    op.drop_table('building_units')
    op.drop_table('building_stacks')
    op.drop_table('building_views')
    op.drop_table('buildings')
