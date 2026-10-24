from flask import Blueprint
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models.user import User
from app.utils import api_response, token_required
from app.validation import json_object, user_fields


user_bp = Blueprint('user', __name__)


@user_bp.route('/profile', methods=['GET'])
@token_required
def get_profile(current_user):
    return api_response(data=current_user.to_dict(viewer=current_user, include_private=True))


@user_bp.route('/profile', methods=['PUT'])
@token_required
def edit_profile(current_user):
    fields = user_fields(json_object())
    if not fields:
        return api_response(message='No supported fields to update', status=400)
    for name in ('username', 'email'):
        if name in fields and fields[name] != getattr(current_user, name):
            if User.query.filter_by(**{name: fields[name]}).first():
                return api_response(message=f'{name} already exists', status=409)
    for name, value in fields.items():
        setattr(current_user, name, value)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return api_response(message='Username or email already exists', status=409)
    return api_response(message='Profile updated successfully',
                        data=current_user.to_dict(viewer=current_user, include_private=True))


@user_bp.route('/<int:user_id>/profile', methods=['GET'])
@token_required
def view_other_profile(current_user, user_id):
    user = db.session.get(User, user_id)
    if user is None:
        return api_response(message='User not found', status=404)
    return api_response(data=user.to_dict(viewer=current_user))
