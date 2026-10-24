from flask import Blueprint
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models.follow import Follow
from app.models.user import User
from app.utils import api_response, token_required


follow_bp = Blueprint('follow', __name__)


@follow_bp.route('/<int:user_id>/follow', methods=['POST'])
@token_required
def follow_user(current_user, user_id):
    if current_user.id == user_id:
        return api_response(message='Cannot follow yourself', status=400)
    if db.session.get(User, user_id) is None:
        return api_response(message='User not found', status=404)
    if db.session.get(Follow, (current_user.id, user_id)) is not None:
        return api_response(message='Already following this user', status=409)
    db.session.add(Follow(follower_id=current_user.id, following_id=user_id))
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return api_response(message='Follow relationship could not be created', status=409)
    return api_response(message='Followed user successfully')


@follow_bp.route('/<int:user_id>/follow', methods=['DELETE'])
@token_required
def unfollow_user(current_user, user_id):
    if current_user.id == user_id:
        return api_response(message='Cannot unfollow yourself', status=400)
    if db.session.get(User, user_id) is None:
        return api_response(message='User not found', status=404)
    follow = db.session.get(Follow, (current_user.id, user_id))
    if follow is None:
        return api_response(message='Not following this user', status=404)
    db.session.delete(follow)
    db.session.commit()
    return api_response(message='Unfollowed user successfully')
