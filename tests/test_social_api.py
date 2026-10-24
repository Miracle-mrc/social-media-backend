from app.extensions import db
from app.models.follow import Follow
from app.models.like import Like
from app.models.post import Post
from tests.support import DatabaseTestCase


class SocialApiTestCase(DatabaseTestCase):
    def setUp(self):
        super().setUp()
        self.alice = self.add_user()
        self.bob = self.add_user('bob')
        self.alice_headers = self.headers(self.alice)
        self.bob_headers = self.headers(self.bob)

    def test_public_profiles_and_search_do_not_expose_email(self):
        response = self.client.get(f'/api/user/{self.bob.id}/profile', headers=self.alice_headers)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('email', response.json['data'])
        response = self.client.get('/api/user/search?username=bo', headers=self.alice_headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual([u['username'] for u in response.json['data']['items']], ['bob'])
        self.assertNotIn('email', response.json['data']['items'][0])

    def test_profile_update_validates_fields_and_prevents_conflicts(self):
        response = self.client.put('/api/user/profile', headers=self.alice_headers,
                                   json={'fullname': 'Alice Smith', 'bio': 'Hello'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['data']['fullname'], 'Alice Smith')
        for data, status in (({'email': self.bob.email}, 409), ({'email': 'bad'}, 400),
                             ({'username': None}, 400), ({'id': 99}, 400),
                             ({'bio': 'a' * 2001}, 400)):
            response = self.client.put('/api/user/profile', headers=self.alice_headers, json=data)
            self.assertEqual(response.status_code, status)
        self.assertEqual(db.session.get(type(self.alice), self.alice.id).username, 'alice')

    def test_create_view_list_and_soft_delete_post(self):
        post_id = self.create_post(self.alice_headers)
        response = self.client.get(f'/api/post/{post_id}', headers=self.bob_headers)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('email', response.json['data']['user'])
        self.assertEqual(response.json['data']['like_count'], 0)
        self.assertEqual(self.client.delete(
            f'/api/post/{post_id}', headers=self.bob_headers).status_code, 403)
        self.assertEqual(self.client.delete(
            f'/api/post/{post_id}', headers=self.alice_headers).status_code, 200)
        self.assertTrue(db.session.get(Post, post_id).deleted)
        self.assertEqual(self.client.get(
            f'/api/post/{post_id}', headers=self.alice_headers).status_code, 404)
        listed = self.client.get(f'/api/user/{self.alice.id}/posts', headers=self.alice_headers)
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json['data']['items'], [])
        self.assertEqual(self.client.post(
            f'/api/post/{post_id}/like', headers=self.bob_headers).status_code, 404)

    def test_post_validation(self):
        for data in ({}, {'image_url': ''}, {'image_url': 'javascript:alert(1)'},
                     {'image_url': 3}, {'image_url': 'https://example.com/a', 'caption': []}):
            self.assertEqual(self.client.post(
                '/api/post', headers=self.alice_headers, json=data).status_code, 400)
        self.assertEqual(Post.query.count(), 0)

    def test_post_pagination_is_stable_and_bounded(self):
        first = self.create_post(self.alice_headers, 'first')
        second = self.create_post(self.alice_headers, 'second')
        response = self.client.get(
            f'/api/user/{self.alice.id}/posts?per_page=1', headers=self.alice_headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['data']['items'][0]['id'], second)
        self.assertEqual(response.json['data']['pagination']['pages'], 2)
        response = self.client.get(
            f'/api/user/{self.alice.id}/posts?per_page=1&page=2', headers=self.alice_headers)
        self.assertEqual(response.json['data']['items'][0]['id'], first)
        for query in ('per_page=101', 'page=0', 'page=bad', 'per_page=-1'):
            response = self.client.get(
                f'/api/user/{self.alice.id}/posts?{query}', headers=self.alice_headers)
            self.assertEqual(response.status_code, 400)

    def test_follow_feed_and_unfollow(self):
        own_post = self.create_post(self.alice_headers)
        bob_post = self.create_post(self.bob_headers)
        url = f'/api/user/{self.bob.id}/follow'
        response = self.client.get('/api/post/newsfeed', headers=self.alice_headers)
        self.assertEqual([p['id'] for p in response.json['data']['items']], [own_post])
        self.assertEqual(self.client.post(url, headers=self.alice_headers).status_code, 200)
        self.assertEqual(self.client.post(url, headers=self.alice_headers).status_code, 409)
        response = self.client.get('/api/post/newsfeed', headers=self.alice_headers)
        self.assertEqual({p['id'] for p in response.json['data']['items']}, {own_post, bob_post})
        profile = self.client.get(f'/api/user/{self.bob.id}/profile', headers=self.alice_headers)
        self.assertTrue(profile.json['data']['is_following'])
        self.assertEqual(profile.json['data']['follower_count'], 1)
        self.client.delete(f'/api/post/{bob_post}', headers=self.bob_headers)
        response = self.client.get('/api/post/newsfeed', headers=self.alice_headers)
        self.assertEqual([p['id'] for p in response.json['data']['items']], [own_post])
        self.assertEqual(self.client.delete(url, headers=self.alice_headers).status_code, 200)
        self.assertEqual(Follow.query.count(), 0)

    def test_follow_self_and_missing_user_are_rejected(self):
        self.assertEqual(self.client.post(
            f'/api/user/{self.alice.id}/follow', headers=self.alice_headers).status_code, 400)
        self.assertEqual(self.client.post('/api/user/999/follow',
                         headers=self.alice_headers).status_code, 404)

    def test_like_unlike_and_duplicate_like(self):
        post_id = self.create_post(self.alice_headers)
        url = f'/api/post/{post_id}/like'
        self.assertEqual(self.client.post(url, headers=self.bob_headers).status_code, 200)
        self.assertEqual(self.client.post(url, headers=self.bob_headers).status_code, 409)
        response = self.client.get(f'/api/post/{post_id}', headers=self.bob_headers)
        self.assertEqual(response.json['data']['like_count'], 1)
        self.assertTrue(response.json['data']['liked_by_current_user'])
        self.assertEqual(self.client.delete(url, headers=self.bob_headers).status_code, 200)
        self.assertEqual(Like.query.count(), 0)
        self.assertEqual(self.client.delete(url, headers=self.bob_headers).status_code, 404)

    def test_search_is_literal_and_empty_results_are_success(self):
        self.add_user('bob_extra')
        for query, expected in (('bob_', ['bob_extra']), ('%25', []), ('nobody', [])):
            response = self.client.get(
                f'/api/user/search?username={query}', headers=self.alice_headers)
            self.assertEqual(response.status_code, 200)
            self.assertEqual([u['username'] for u in response.json['data']['items']], expected)
        self.assertEqual(self.client.get(
            '/api/user/search', headers=self.alice_headers).status_code, 400)

    def test_missing_resources_return_json_404(self):
        for url in ('/api/post/999', '/api/user/999/profile', '/api/user/999/posts', '/not-an-api'):
            response = self.client.get(url, headers=self.alice_headers)
            self.assertEqual(response.status_code, 404)
            self.assertFalse(response.json['success'])
