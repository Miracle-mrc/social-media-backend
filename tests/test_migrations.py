from pathlib import Path
from secrets import token_hex
import unittest

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from flask_migrate import downgrade, stamp, upgrade
import sqlalchemy as sa

from app import create_app
from app.extensions import db


class MigrationTestCase(unittest.TestCase):
    def setUp(self):
        test_root = Path(__file__).resolve().parents[1] / 'instance' / 'tests'
        test_root.mkdir(parents=True, exist_ok=True)
        self.directory = test_root / token_hex(8)
        self.directory.mkdir()
        self.database_path = self.directory / 'migration.db'
        self.config = {
            'TESTING': True,
            'SECRET_KEY': token_hex(32),
            'JWT_SECRET_KEY': token_hex(32),
            'SQLALCHEMY_DATABASE_URI': f'sqlite:///{self.database_path.as_posix()}',
        }
        self.app = create_app(self.config)
        self.context = self.app.app_context()
        self.context.push()

    def tearDown(self):
        db.session.remove()
        db.engine.dispose()
        self.context.pop()
        for suffix in ('', '-journal', '-wal', '-shm'):
            Path(str(self.database_path) + suffix).unlink(missing_ok=True)
        self.directory.rmdir()

    def test_fresh_database_matches_model_metadata(self):
        upgrade()
        with db.engine.connect() as connection:
            migration_context = MigrationContext.configure(
                connection, opts={'compare_type': True, 'compare_server_default': True})
            self.assertEqual(compare_metadata(migration_context, db.metadata), [])
        downgrade(revision='base')
        upgrade()
        self.assertIn('auth_sessions', sa.inspect(db.engine).get_table_names())

    def test_existing_schema_upgrade_preserves_rows_and_adds_foreign_keys(self):
        upgrade(revision='0001_initial')
        with db.engine.begin() as connection:
            connection.execute(sa.text(
                "INSERT INTO users (id, username, email, password_hash) "
                "VALUES (1, 'alice', 'alice@example.com', 'hash'), "
                "(2, 'bob', 'bob@example.com', 'hash')"))
            connection.execute(sa.text(
                "INSERT INTO posts (id, user_id, image_url) "
                "VALUES (1, 1, 'https://example.com/a.png')"))
            connection.execute(
                sa.text('INSERT INTO follows (follower_id, following_id) VALUES (1, 2)'))
            connection.execute(
                sa.text('INSERT INTO likes (user_id, post_id, created_at) VALUES (2, 1, 1)'))
            # Model a legacy database whose tables predate Alembic.
            connection.execute(sa.text('DELETE FROM alembic_version'))
        stamp(revision='0001_initial')
        upgrade()
        with db.engine.connect() as connection:
            self.assertEqual(connection.execute(
                sa.text('SELECT deleted FROM posts WHERE id=1')).scalar_one(), 0)
            self.assertEqual(connection.execute(
                sa.text('SELECT COUNT(*) FROM likes')).scalar_one(), 1)
            self.assertEqual(connection.execute(sa.text('PRAGMA foreign_key_check')).all(), [])
        with self.assertRaises(sa.exc.IntegrityError):
            with db.engine.begin() as connection:
                connection.execute(
                    sa.text('INSERT INTO likes (user_id, post_id, created_at) VALUES (99, 1, 1)'))
        downgrade(revision='0001_initial')
        upgrade()
        with db.engine.connect() as connection:
            self.assertEqual(connection.execute(
                sa.text('SELECT COUNT(*) FROM posts')).scalar_one(), 1)

    def test_orphan_rows_are_reported_before_schema_changes(self):
        upgrade(revision='0001_initial')
        with db.engine.begin() as connection:
            connection.execute(sa.text(
                "INSERT INTO posts (id, user_id, image_url) "
                "VALUES (1, 99, 'https://example.com/a.png')"))
        with self.assertRaises(SystemExit) as failure:
            upgrade()
        self.assertEqual(failure.exception.code, 1)
        self.assertNotIn('deleted', {c['name'] for c in sa.inspect(db.engine).get_columns('posts')})

    def test_revocation_survives_application_restart(self):
        from app.models.user import User
        from tests.support import TEST_HASH, TEST_PASSWORD
        upgrade()
        user = User(username='alice', email='alice@example.com', password_hash=TEST_HASH)
        db.session.add(user)
        db.session.commit()
        client = self.app.test_client()
        tokens = client.post('/api/auth/login', json={
            'username': 'alice', 'password': TEST_PASSWORD,
        }).json['data']
        headers = {'Authorization': f"Bearer {tokens['access_token']}"}
        self.assertEqual(client.post('/api/auth/logout', headers=headers).status_code, 200)
        restarted = create_app(self.config)
        try:
            response = restarted.test_client().get('/api/user/profile', headers=headers)
            self.assertEqual(response.status_code, 401)
        finally:
            with restarted.app_context():
                db.session.remove()
                db.engine.dispose()
