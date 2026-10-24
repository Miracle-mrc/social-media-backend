from flask import Blueprint

from app.extensions import db
from app.models.post import Post
from app.models.user import User
from app.utils import api_response, paginated_data, pagination_args, token_required
from app.validation import image_url, json_object, text_field


post_bp = Blueprint('post', __name__)


@post_bp.route('', methods=['POST'])
@token_required
def create_post(current_user):
    data = json_object()
    post = Post(
        image_url=image_url(data.get('image_url')),
        caption=text_field(data.get('caption', ''), 'caption', 2200),
        user_id=current_user.id,
    )
    db.session.add(post)
    db.session.commit()
    return api_response(message='Post created successfully', data=post.to_dict(), status=201)


@post_bp.route('/<int:post_id>', methods=['GET'])
@token_required
def get_post(current_user, post_id):
    post = db.session.get(Post, post_id)
    if post is None or post.deleted:
        return api_response(message='Post not found', status=404)
    return api_response(data=post.to_dict(
        include_user=True, include_likes=True, current_user=current_user))


@post_bp.route('/<int:post_id>', methods=['DELETE'])
@token_required
def delete_post(current_user, post_id):
    post = db.session.get(Post, post_id)
    if post is None or post.deleted:
        return api_response(message='Post not found', status=404)
    if post.user_id != current_user.id:
        return api_response(message='Not authorized to delete this post', status=403)
    post.deleted = True
    db.session.commit()
    return api_response(message='Post deleted successfully')


# Kept as a separate blueprint so user routes do not depend on import order.
user_posts_bp = Blueprint('user_posts', __name__)


@user_posts_bp.route('/<int:user_id>/posts', methods=['GET'])
@token_required
def get_user_posts(current_user, user_id):
    page, per_page = pagination_args()
    if db.session.get(User, user_id) is None:
        return api_response(message='User not found', status=404)
    posts = Post.query.filter_by(user_id=user_id, deleted=False).order_by(
        Post.created_at.desc(), Post.id.desc()).paginate(
            page=page, per_page=per_page, error_out=False, max_per_page=100)
    return api_response(data=paginated_data(posts, lambda post: post.to_dict()))
