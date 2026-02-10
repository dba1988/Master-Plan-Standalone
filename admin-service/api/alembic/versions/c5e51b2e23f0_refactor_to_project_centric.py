"""refactor_to_project_centric

Revision ID: c5e51b2e23f0
Revises: c97521d7a70c
Create Date: 2026-02-11

This migration refactors the schema so that:
- Assets belong to Projects (not Versions)
- Overlays belong to Projects (not Versions)
- ProjectConfig belongs to Projects (not Versions)

Versions become just release tags (like git tags).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c5e51b2e23f0'
down_revision: Union[str, None] = 'c97521d7a70c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # === ASSETS TABLE ===
    # 1. Add project_id column (nullable initially)
    op.add_column('assets', sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=True))

    # 2. Populate project_id from version's project_id
    op.execute("""
        UPDATE assets
        SET project_id = pv.project_id
        FROM project_versions pv
        WHERE assets.version_id = pv.id
    """)

    # 3. Make project_id not nullable
    op.alter_column('assets', 'project_id', nullable=False)

    # 4. Add foreign key constraint
    op.create_foreign_key(
        'fk_assets_project_id',
        'assets', 'projects',
        ['project_id'], ['id'],
        ondelete='CASCADE'
    )

    # 5. Drop old indexes
    op.drop_index('ix_assets_version_type', table_name='assets')
    op.drop_index('ix_assets_version_level', table_name='assets')

    # 6. Drop old foreign key and column
    op.drop_constraint('assets_version_id_fkey', 'assets', type_='foreignkey')
    op.drop_column('assets', 'version_id')

    # 7. Create new indexes
    op.create_index('ix_assets_project_type', 'assets', ['project_id', 'asset_type'])
    op.create_index('ix_assets_project_level', 'assets', ['project_id', 'level'])


    # === OVERLAYS TABLE ===
    # 1. Add project_id column (nullable initially)
    op.add_column('overlays', sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=True))

    # 2. Populate project_id from version's project_id
    op.execute("""
        UPDATE overlays
        SET project_id = pv.project_id
        FROM project_versions pv
        WHERE overlays.version_id = pv.id
    """)

    # 3. Make project_id not nullable
    op.alter_column('overlays', 'project_id', nullable=False)

    # 4. Add foreign key constraint
    op.create_foreign_key(
        'fk_overlays_project_id',
        'overlays', 'projects',
        ['project_id'], ['id'],
        ondelete='CASCADE'
    )

    # 5. Drop old unique constraint and indexes
    op.drop_constraint('uq_overlay_ref', 'overlays', type_='unique')
    op.drop_index('ix_overlays_version', table_name='overlays')

    # 6. Drop old foreign key and column
    op.drop_constraint('overlays_version_id_fkey', 'overlays', type_='foreignkey')
    op.drop_column('overlays', 'version_id')

    # 7. Create new unique constraint and indexes
    op.create_unique_constraint('uq_overlay_ref', 'overlays', ['project_id', 'overlay_type', 'ref'])
    op.create_index('ix_overlays_project', 'overlays', ['project_id'])


    # === PROJECT_CONFIGS TABLE ===
    # 1. Add project_id column (nullable initially)
    op.add_column('project_configs', sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=True))

    # 2. Populate project_id from version's project_id
    op.execute("""
        UPDATE project_configs
        SET project_id = pv.project_id
        FROM project_versions pv
        WHERE project_configs.version_id = pv.id
    """)

    # 3. Delete duplicate configs (keep the most recent one per project)
    op.execute("""
        DELETE FROM project_configs
        WHERE id NOT IN (
            SELECT DISTINCT ON (project_id) id
            FROM project_configs
            WHERE project_id IS NOT NULL
            ORDER BY project_id, updated_at DESC
        )
    """)

    # 4. Make project_id not nullable
    op.alter_column('project_configs', 'project_id', nullable=False)

    # 5. Add foreign key constraint
    op.create_foreign_key(
        'fk_project_configs_project_id',
        'project_configs', 'projects',
        ['project_id'], ['id'],
        ondelete='CASCADE'
    )

    # 6. Drop old foreign key and column
    op.drop_constraint('project_configs_version_id_fkey', 'project_configs', type_='foreignkey')
    op.drop_column('project_configs', 'version_id')

    # 7. Add unique constraint on project_id (one config per project)
    op.create_unique_constraint('uq_project_configs_project', 'project_configs', ['project_id'])


def downgrade() -> None:
    # === PROJECT_CONFIGS TABLE ===
    op.drop_constraint('uq_project_configs_project', 'project_configs', type_='unique')
    op.add_column('project_configs', sa.Column('version_id', postgresql.UUID(as_uuid=True), nullable=True))
    # Note: Data migration back would require knowing which version to use
    op.drop_constraint('fk_project_configs_project_id', 'project_configs', type_='foreignkey')
    op.drop_column('project_configs', 'project_id')
    op.create_foreign_key(
        'project_configs_version_id_fkey',
        'project_configs', 'project_versions',
        ['version_id'], ['id'],
        ondelete='CASCADE'
    )

    # === OVERLAYS TABLE ===
    op.drop_index('ix_overlays_project', table_name='overlays')
    op.drop_constraint('uq_overlay_ref', 'overlays', type_='unique')
    op.add_column('overlays', sa.Column('version_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.drop_constraint('fk_overlays_project_id', 'overlays', type_='foreignkey')
    op.drop_column('overlays', 'project_id')
    op.create_foreign_key(
        'overlays_version_id_fkey',
        'overlays', 'project_versions',
        ['version_id'], ['id'],
        ondelete='CASCADE'
    )
    op.create_unique_constraint('uq_overlay_ref', 'overlays', ['version_id', 'overlay_type', 'ref'])
    op.create_index('ix_overlays_version', 'overlays', ['version_id'])

    # === ASSETS TABLE ===
    op.drop_index('ix_assets_project_level', table_name='assets')
    op.drop_index('ix_assets_project_type', table_name='assets')
    op.add_column('assets', sa.Column('version_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.drop_constraint('fk_assets_project_id', 'assets', type_='foreignkey')
    op.drop_column('assets', 'project_id')
    op.create_foreign_key(
        'assets_version_id_fkey',
        'assets', 'project_versions',
        ['version_id'], ['id'],
        ondelete='CASCADE'
    )
    op.create_index('ix_assets_version_type', 'assets', ['version_id', 'asset_type'])
    op.create_index('ix_assets_version_level', 'assets', ['version_id', 'level'])
