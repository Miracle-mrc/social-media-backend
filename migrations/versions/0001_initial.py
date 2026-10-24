"""Baseline schema from the original application.

Revision ID: 0001_initial
Revises:
"""
from alembic import op
import sqlalchemy as sa


revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(50), nullable=False),
        sa.Column('email', sa.String(100), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('fullname', sa.String(100)),
        sa.Column('bio', sa.Text()),
        sa.Column('profile_picture', sa.String(255)),
        sa.Column('created_at', sa.Integer()),
        sa.Column('updated_at', sa.Integer()),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_users')),
        sa.UniqueConstraint('username', name=op.f('uq_users_username')),
        sa.UniqueConstraint('email', name=op.f('uq_users_email')),
    )
    op.create_table(
        'posts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('image_url', sa.String(255), nullable=False),
        sa.Column('caption', sa.Text()),
        sa.Column('created_at', sa.Integer()),
        sa.Column('updated_at', sa.Integer()),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_posts')),
    )
    op.create_table(
        'follows',
        sa.Column('follower_id', sa.Integer(), nullable=False),
        sa.Column('following_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.Integer()),
        sa.PrimaryKeyConstraint('follower_id', 'following_id', name=op.f('pk_follows')),
    )
    op.create_table(
        'likes',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('post_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('user_id', 'post_id', name=op.f('pk_likes')),
    )


def downgrade():
    op.drop_table('likes')
    op.drop_table('follows')
    op.drop_table('posts')
    op.drop_table('users')
