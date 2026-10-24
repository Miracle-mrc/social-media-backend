from datetime import timedelta
from unittest.mock import patch

from flask_jwt_extended import create_access_token, decode_token
from werkzeug.security import check_password_hash

from app import create_app
from app.extensions import db
from app.models.user import User
from tests.support import DatabaseTestCase, TEST_PASSWORD


class AuthApiTestCase(DatabaseTestCase):
    def test_registration_login_and_private_profile(self):
        response = self.client.post('/api/auth/register', json={
            'username': 'newuser', 'password': TEST_PASSWORD,
            'fullname': 'New User', 'email': 'NEW@example.com',
        })
        self.assertEqual(response.status_code, 201)
        user = User.query.filter_by(username='newuser').one()
        self.assertNotEqual(user.password_hash, TEST_PASSWORD)
        self.assertTrue(check_password_hash(user.password_hash, TEST_PASSWORD))
        headers = self.headers(user)
        response = self.client.get('/api/user/profile', headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['data']['email'], 'new@example.com')
        self.assertNotIn('password_hash', response.json['data'])

    def test_registration_validates_payloads(self):
        valid = {'username': 'newuser', 'password': TEST_PASSWORD, 'email': 'new@example.com'}
        invalid = [
            {}, [], None, {'email': 'new@example.com'},
            {**valid, 'password': 'short'},
            {**valid, 'password': 12345678},
            {**valid, 'username': 'a' * 51},
            {**valid, 'email': 'invalid'},
            {**valid, 'fullname': None},
        ]
        for payload in invalid:
            with self.subTest(payload=payload):
                response = self.client.post('/api/auth/register', json=payload)
                self.assertIn(response.status_code, (400, 415))
                self.assertFalse(response.json['success'])
        self.assertEqual(User.query.count(), 0)

    def test_duplicate_username_or_email_returns_conflict(self):
        self.add_user()
        for username, email in (('alice', 'different@example.com'), ('bob', 'alice@example.com')):
            response = self.client.post('/api/auth/register', json={
                'username': username, 'email': email, 'password': TEST_PASSWORD,
            })
            self.assertEqual(response.status_code, 409)
        self.assertEqual(User.query.count(), 1)

    def test_login_rejects_invalid_credentials_and_missing_fields(self):
        self.add_user()
        response = self.client.post('/api/auth/login', json={
            'username': 'alice', 'password': 'incorrect',
        })
        self.assertEqual(response.status_code, 401)
        for data in ({}, {'username': 'alice'}, {'username': 1, 'password': []}):
            self.assertEqual(self.client.post('/api/auth/login', json=data).status_code, 400)

    def test_refresh_and_logout_revoke_the_whole_session(self):
        tokens = self.login(self.add_user())
        refresh_headers = self.token_headers(tokens['refresh_token'])
        refreshed = self.client.post('/api/auth/refresh', headers=refresh_headers)
        self.assertEqual(refreshed.status_code, 200)
        access_headers = self.token_headers(tokens['access_token'])
        self.assertEqual(self.client.post('/api/auth/refresh',
                         headers=access_headers).status_code, 401)
        self.assertEqual(self.client.post('/api/auth/logout',
                         headers=access_headers).status_code, 200)
        for token in (tokens['access_token'], refreshed.json['data']['access_token']):
            self.assertEqual(self.client.get(
                '/api/user/profile', headers=self.token_headers(token)).status_code, 401)
        self.assertEqual(self.client.post('/api/auth/refresh',
                         headers=refresh_headers).status_code, 401)

    def test_logout_accepts_refresh_token(self):
        tokens = self.login(self.add_user())
        response = self.client.post(
            '/api/auth/logout', headers=self.token_headers(tokens['refresh_token']))
        self.assertEqual(response.status_code, 200)
        access_headers = self.token_headers(tokens['access_token'])
        self.assertEqual(self.client.get(
            '/api/user/profile', headers=access_headers).status_code, 401)

    def test_logout_does_not_revoke_another_login(self):
        user = self.add_user()
        first, second = self.login(user), self.login(user)
        self.client.post('/api/auth/logout', headers=self.token_headers(first['access_token']))
        second_headers = self.token_headers(second['access_token'])
        self.assertEqual(self.client.get(
            '/api/user/profile', headers=second_headers).status_code, 200)

    def test_missing_malformed_expired_or_sessionless_tokens(self):
        user = self.add_user()
        tokens = self.login(user)
        claims = {'sid': decode_token(tokens['access_token'])['sid']}
        expired = create_access_token(identity=str(user.id), additional_claims=claims,
                                      expires_delta=timedelta(seconds=-1))
        sessionless = create_access_token(identity=str(user.id))
        for headers in ({}, self.token_headers('invalid'), self.token_headers(expired),
                        self.token_headers(sessionless),
                        self.token_headers(tokens['refresh_token'])):
            with self.subTest(headers=headers):
                response = self.client.get('/api/user/profile', headers=headers)
                self.assertEqual(response.status_code, 401)
                self.assertFalse(response.json['success'])

    def test_application_errors_are_500_without_internal_details(self):
        headers = self.headers(self.add_user())
        with patch.object(User, 'to_dict', side_effect=RuntimeError('private connection details')):
            with self.assertLogs(self.app.logger, level='ERROR'):
                response = self.client.get('/api/user/profile', headers=headers)
        self.assertEqual(response.status_code, 500)
        self.assertNotIn('private connection details', response.get_data(as_text=True))
        self.assertEqual(self.client.get('/api/user/profile', headers=headers).status_code, 200)

    def test_factory_rejects_missing_or_short_secrets(self):
        for key, value in (('SECRET_KEY', 'short'), ('SECRET_KEY', None),
                           ('JWT_SECRET_KEY', 'short')):
            with self.subTest(key=key, value=value):
                with self.assertRaises(RuntimeError):
                    create_app({'SECRET_KEY': 'a' * 64, 'JWT_SECRET_KEY': 'b' * 64, key: value})

    def test_factory_registers_routes_consistently(self):
        other = create_app(dict(self.app.config))
        self.assertEqual(
            sorted(str(rule) for rule in self.app.url_map.iter_rules()),
            sorted(str(rule) for rule in other.url_map.iter_rules()),
        )
        self.assertNotIn('gcs_client', other.extensions)
