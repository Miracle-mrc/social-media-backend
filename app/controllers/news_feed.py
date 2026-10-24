from flask import Blueprint

from app.extensions import db
from app.models.follow import Follow
from app.models.post import Post
from app.utils import api_response, paginated_data, pagination_args, token_required


news_feed_bp = Blueprint('news_feed', __name__)


@news_feed_bp.route('/newsfeed', methods=['GET'])
@token_required
def view_news_feed(current_user):
    page, per_page = pagination_args()
    followed_ids = db.select(Follow.following_id).where(Follow.follower_id == current_user.id)
    posts = Post.query.filter(
        Post.deleted.is_(False),
        db.or_(Post.user_id == current_user.id, Post.user_id.in_(followed_ids)),
    ).order_by(Post.created_at.desc(), Post.id.desc()).paginate(
        page=page, per_page=per_page, error_out=False, max_per_page=100)
    return api_response(data=paginated_data(posts, lambda post: post.to_dict(include_user=True)))
