from uuid import uuid4

from flask import Blueprint
from flask_jwt_extended import (
    create_access_token, create_refresh_token, decode_token,
    get_jwt, get_jwt_identity, jwt_required,
)
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models.auth_session import AuthSession
from app.models.user import User
from app.utils import api_response
from app.validation import json_object, text_field, user_fields


auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
def register():
    fields = user_fields(json_object(), registering=True)
    if User.query.filter_by(username=fields['username']).first():
        return api_response(message='Username already exists', status=409)
    if User.query.filter_by(email=fields['email']).first():
        return api_response(message='Email already exists', status=409)
    password = fields.pop('password')
    user = User(**fields)
    user.set_password(password)
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return api_response(message='Username or email already exists', status=409)
    return api_response(
        message='User registered successfully',
        data={'user_id': user.id, 'username': user.username},
        status=201,
    )


@auth_bp.route('/login', methods=['POST'])
def login():
    data = json_object()
    username = text_field(data.get('username'), 'username', 50, 1)
    password = text_field(data.get('password'), 'password', 128, 1, strip=False)
    user = User.query.filter_by(username=username).first()
    if user is None or not user.check_password(password):
        return api_response(message='Invalid username or password', status=401)

    session_id = uuid4().hex
    claims = {'sid': session_id}
    access_token = create_access_token(identity=str(user.id), additional_claims=claims)
    refresh_token = create_refresh_token(identity=str(user.id), additional_claims=claims)
    db.session.add(AuthSession(
        id=session_id, user_id=user.id, expires_at=decode_token(refresh_token)['exp']))
    db.session.commit()
    return api_response(message='Login successful', data={
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user': user.to_dict(include_private=True),
    })


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    user = db.session.get(User, int(get_jwt_identity()))
    if user is None:
        return api_response(message='User does not exist', status=401)
    access_token = create_access_token(
        identity=str(user.id), additional_claims={'sid': get_jwt()['sid']})
    return api_response(data={'access_token': access_token})


@auth_bp.route('/logout', methods=['POST'])
@jwt_required(verify_type=False)
def logout():
    session = db.session.get(AuthSession, get_jwt()['sid'])
    session.revoked = True
    db.session.commit()
    return api_response(message='Logout successful')
