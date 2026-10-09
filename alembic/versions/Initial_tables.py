"""Create initial Stage 1 tables

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2026_09_29_0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create images table
    op.create_table(
        'images',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('path', sa.String(length=500), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='PENDING'),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('low_confidence', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_images_id', 'images', ['id'], unique=False)
    op.create_index('ix_images_status', 'images', ['status'], unique=False)

    # 2. Create tags table
    op.create_table(
        'tags',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('image_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(['image_id'], ['images.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_tags_id', 'tags', ['id'], unique=False)
    op.create_index('ix_tags_name', 'tags', ['name'], unique=False)

    # 3. Create posts table
    op.create_table(
        'posts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_posts_id', 'posts', ['id'], unique=False)

    # 4. Create embeddings table
    op.create_table(
        'embeddings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('image_id', sa.Integer(), nullable=True),
        sa.Column('post_id', sa.Integer(), nullable=True),
        sa.Column('vector', sa.JSON(), nullable=False),
        sa.Column('model_name', sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(['image_id'], ['images.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['post_id'], ['posts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_embeddings_id', 'embeddings', ['id'], unique=False)

    # 5. Create suggestions table
    op.create_table(
        'suggestions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('post_id', sa.Integer(), nullable=False),
        sa.Column('image_id', sa.Integer(), nullable=False),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='PENDING'),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['image_id'], ['images.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['post_id'], ['posts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_suggestions_id', 'suggestions', ['id'], unique=False)
    op.create_index('ix_suggestions_post_id_status', 'suggestions', ['post_id', 'status'], unique=False)

    # 6. Create reviews table
    op.create_table(
        'reviews',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('suggestion_id', sa.Integer(), nullable=False),
        sa.Column('approved', sa.Boolean(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['suggestion_id'], ['suggestions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_reviews_id', 'reviews', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_reviews_id', table_name='reviews')
    op.drop_table('reviews')

    op.drop_index('ix_suggestions_post_id_status', table_name='suggestions')
    op.drop_index('ix_suggestions_id', table_name='suggestions')
    op.drop_table('suggestions')

    op.drop_index('ix_embeddings_id', table_name='embeddings')
    op.drop_table('embeddings')

    op.drop_index('ix_posts_id', table_name='posts')
    op.drop_table('posts')

    op.drop_index('ix_tags_name', table_name='tags')
    op.drop_index('ix_tags_id', table_name='tags')
    op.drop_table('tags')

    op.drop_index('ix_images_status', table_name='images')
    op.drop_index('ix_images_id', table_name='images')
    op.drop_table('images')
