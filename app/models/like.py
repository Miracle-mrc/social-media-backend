from time import time

from app.extensions import db


class Like(db.Model):
    __tablename__ = 'likes'
    __table_args__ = (db.Index('ix_likes_post_id', 'post_id'),)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id', ondelete='CASCADE'), primary_key=True)
    created_at = db.Column(db.Integer, default=lambda: int(time()), nullable=False)

    def __repr__(self):
        return f'<Like user={self.user_id} post={self.post_id}>'
