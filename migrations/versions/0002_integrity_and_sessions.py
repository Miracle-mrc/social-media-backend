"""Add soft deletion, referential integrity and persistent login sessions.

Revision ID: 0002_integrity
Revises: 0001_initial
"""
from alembic import op
import sqlalchemy as sa


revision = '0002_integrity'
down_revision = '0001_initial'
branch_labels = None
depends_on = None


def check_existing_data():
    checks = {
        'posts': (
            'SELECT COUNT(*) FROM posts p LEFT JOIN users u ON p.user_id = u.id '
            'WHERE u.id IS NULL'
        ),
        'follows': (
            'SELECT COUNT(*) FROM follows f '
            'LEFT JOIN users a ON f.follower_id = a.id '
            'LEFT JOIN users b ON f.following_id = b.id '
            'WHERE a.id IS NULL OR b.id IS NULL'
        ),
        'likes': (
            'SELECT COUNT(*) FROM likes l '
            'LEFT JOIN users u ON l.user_id = u.id '
            'LEFT JOIN posts p ON l.post_id = p.id '
            'WHERE u.id IS NULL OR p.id IS NULL'
        ),
    }
    for table, query in checks.items():
        count = op.get_bind().execute(sa.text(query)).scalar_one()
        if count:
            raise RuntimeError(
                f'{table} contains {count} orphan rows. Repair them before retrying the migration.'
            )


def upgrade():
    # Check before any DDL, including on MySQL where DDL may auto-commit.
    check_existing_data()
    with op.batch_alter_table('posts') as batch:
        batch.add_column(sa.Column('deleted', sa.Boolean(),
                         server_default=sa.false(), nullable=False))
        batch.create_foreign_key('fk_posts_user_id_users', 'users', [
                                 'user_id'], ['id'], ondelete='CASCADE')
        batch.create_index('ix_posts_user_feed', ['user_id', 'deleted', 'created_at', 'id'])
        batch.create_index('ix_posts_feed', ['deleted', 'created_at', 'id'])
    with op.batch_alter_table('follows') as batch:
        batch.create_foreign_key('fk_follows_follower_id_users', 'users', [
                                 'follower_id'], ['id'], ondelete='CASCADE')
        batch.create_foreign_key('fk_follows_following_id_users', 'users', [
                                 'following_id'], ['id'], ondelete='CASCADE')
        batch.create_index('ix_follows_following_id', ['following_id'])
    with op.batch_alter_table('likes') as batch:
        batch.create_foreign_key('fk_likes_user_id_users', 'users', [
                                 'user_id'], ['id'], ondelete='CASCADE')
        batch.create_foreign_key('fk_likes_post_id_posts', 'posts', [
                                 'post_id'], ['id'], ondelete='CASCADE')
        batch.create_index('ix_likes_post_id', ['post_id'])
    op.create_table(
        'auth_sessions',
        sa.Column('id', sa.String(32), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('revoked', sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column('expires_at', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ['user_id'], ['users.id'],
            name=op.f('fk_auth_sessions_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_auth_sessions')),
    )
    op.create_index('ix_auth_sessions_user_id', 'auth_sessions', ['user_id'])
    op.create_index('ix_auth_sessions_expires_at', 'auth_sessions', ['expires_at'])


def downgrade():
    op.drop_table('auth_sessions')
    with op.batch_alter_table('likes') as batch:
        batch.drop_index('ix_likes_post_id')
        batch.drop_constraint('fk_likes_user_id_users', type_='foreignkey')
        batch.drop_constraint('fk_likes_post_id_posts', type_='foreignkey')
    with op.batch_alter_table('follows') as batch:
        batch.drop_index('ix_follows_following_id')
        batch.drop_constraint('fk_follows_follower_id_users', type_='foreignkey')
        batch.drop_constraint('fk_follows_following_id_users', type_='foreignkey')
    with op.batch_alter_table('posts') as batch:
        batch.drop_index('ix_posts_user_feed')
        batch.drop_index('ix_posts_feed')
        batch.drop_constraint('fk_posts_user_id_users', type_='foreignkey')
        batch.drop_column('deleted')
