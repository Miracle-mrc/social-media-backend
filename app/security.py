from time import time

from app.extensions import db, jwt
from app.models.auth_session import AuthSession
from app.utils import api_response


def register_jwt_callbacks():
    @jwt.token_in_blocklist_loader
    def is_revoked(_header, payload):
        session_id = payload.get('sid')
        if not isinstance(session_id, str) or len(session_id) != 32:
            return True
        session = db.session.get(AuthSession, session_id)
        return (
            session is None
            or session.revoked
            or session.expires_at <= int(time())
            or str(session.user_id) != payload.get('sub')
        )

    @jwt.unauthorized_loader
    def missing_token(_reason):
        return api_response(message='Authentication required', status=401)

    @jwt.invalid_token_loader
    def invalid_token(_reason):
        return api_response(message='Invalid token', status=401)

    @jwt.expired_token_loader
    def expired_token(_header, _payload):
        return api_response(message='Token has expired', status=401)

    @jwt.revoked_token_loader
    def revoked_token(_header, _payload):
        return api_response(message='Session has been revoked', status=401)

    @jwt.needs_fresh_token_loader
    def fresh_token_required(_header, _payload):
        return api_response(message='A fresh token is required', status=401)
