from flask import Blueprint
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models.like import Like
from app.models.post import Post
from app.utils import api_response, token_required


like_bp = Blueprint('like', __name__)


@like_bp.route('/<int:post_id>/like', methods=['POST'])
@token_required
def like_post(current_user, post_id):
    post = db.session.get(Post, post_id)
    if post is None or post.deleted:
        return api_response(message='Post not found', status=404)
    if db.session.get(Like, (current_user.id, post_id)) is not None:
        return api_response(message='Already liked this post', status=409)
    db.session.add(Like(user_id=current_user.id, post_id=post_id))
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return api_response(message='Like could not be created', status=409)
    return api_response(message='Liked post successfully')


@like_bp.route('/<int:post_id>/like', methods=['DELETE'])
@token_required
def unlike_post(current_user, post_id):
    post = db.session.get(Post, post_id)
    if post is None or post.deleted:
        return api_response(message='Post not found', status=404)
    like = db.session.get(Like, (current_user.id, post_id))
    if like is None:
        return api_response(message='Post has not been liked', status=404)
    db.session.delete(like)
    db.session.commit()
    return api_response(message='Unliked post successfully')
