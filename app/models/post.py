from time import time

from app.extensions import db


class Post(db.Model):
    __tablename__ = 'posts'
    __table_args__ = (
        db.Index('ix_posts_user_feed', 'user_id', 'deleted', 'created_at', 'id'),
        db.Index('ix_posts_feed', 'deleted', 'created_at', 'id'),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    image_url = db.Column(db.String(255), nullable=False)
    caption = db.Column(db.Text)
    deleted = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false())
    created_at = db.Column(db.Integer, default=lambda: int(time()))
    updated_at = db.Column(db.Integer, default=lambda: int(time()), onupdate=lambda: int(time()))
    user = db.relationship('User', lazy='joined')

    def __repr__(self):
        return f'<Post {self.id} user={self.user_id}>'

    def to_dict(self, include_user=False, include_likes=False, current_user=None):
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'image_url': self.image_url,
            'caption': self.caption,
            'created_at': self.created_at,
        }
        if include_user:
            data['user'] = self.user.to_dict() if self.user else None
        if include_likes:
            from app.models.like import Like
            data['like_count'] = Like.query.filter_by(post_id=self.id).count()
            data['liked_by_current_user'] = current_user is not None and Like.query.filter_by(
                post_id=self.id, user_id=current_user.id).first() is not None
        return data
