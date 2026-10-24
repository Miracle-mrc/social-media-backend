from secrets import token_hex
import unittest

from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
from app.models.user import User


TEST_PASSWORD = 'testpassword'
TEST_HASH = generate_password_hash(TEST_PASSWORD)


class DatabaseTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app({
            'TESTING': True,
            'SECRET_KEY': token_hex(32),
            'JWT_SECRET_KEY': token_hex(32),
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'GCS_BUCKET_NAME': None,
        })
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def add_user(self, name='alice'):
        user = User(username=name, email=f'{name}@example.com', fullname=name,
                    password_hash=TEST_HASH)
        db.session.add(user)
        db.session.commit()
        return user

    def login(self, user):
        response = self.client.post('/api/auth/login', json={
            'username': user.username, 'password': TEST_PASSWORD,
        })
        self.assertEqual(response.status_code, 200, response.json)
        return response.json['data']

    def headers(self, user):
        return self.token_headers(self.login(user)['access_token'])

    @staticmethod
    def token_headers(token):
        return {'Authorization': f'Bearer {token}'}

    def create_post(self, headers, caption='A test photo'):
        response = self.client.post('/api/post', headers=headers, json={
            'image_url': 'https://example.com/image.jpg', 'caption': caption,
        })
        self.assertEqual(response.status_code, 201, response.json)
        return response.json['data']['id']
