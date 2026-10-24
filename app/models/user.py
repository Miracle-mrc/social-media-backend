from time import time

from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    fullname = db.Column(db.String(100))
    bio = db.Column(db.Text)
    profile_picture = db.Column(db.String(255), default='default.jpg')
    created_at = db.Column(db.Integer, default=lambda: int(time()))
    updated_at = db.Column(db.Integer, default=lambda: int(time()), onupdate=lambda: int(time()))

    def __repr__(self):
        return f'<User {self.id} {self.username}>'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self, viewer=None, include_private=False):
        data = {
            'id': self.id,
            'username': self.username,
            'fullname': self.fullname,
            'bio': self.bio,
            'profile_picture': self.profile_picture,
            'created_at': self.created_at,
        }
        if include_private:
            data['email'] = self.email
        if viewer is not None:
            from app.models.follow import Follow
            data['follower_count'] = Follow.query.filter_by(following_id=self.id).count()
            data['following_count'] = Follow.query.filter_by(follower_id=self.id).count()
            data['is_following'] = Follow.query.filter_by(
                follower_id=viewer.id, following_id=self.id).first() is not None
        return data
