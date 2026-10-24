from time import time

from app.extensions import db


class Follow(db.Model):
    __tablename__ = 'follows'
    __table_args__ = (db.Index('ix_follows_following_id', 'following_id'),)

    follower_id = db.Column(db.Integer, db.ForeignKey(
        'users.id', ondelete='CASCADE'), primary_key=True)
    following_id = db.Column(db.Integer, db.ForeignKey(
        'users.id', ondelete='CASCADE'), primary_key=True)
    created_at = db.Column(db.Integer, default=lambda: int(time()))

    def __repr__(self):
        return f'<Follow {self.follower_id} -> {self.following_id}>'
