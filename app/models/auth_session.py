from time import time

from app.extensions import db


class AuthSession(db.Model):
    """One login session shared by its access and refresh tokens."""

    __tablename__ = 'auth_sessions'

    id = db.Column(db.String(32), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(
        'users.id', ondelete='CASCADE'), nullable=False, index=True)
    revoked = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false())
    expires_at = db.Column(db.Integer, nullable=False, index=True)
    created_at = db.Column(db.Integer, nullable=False, default=lambda: int(time()))
