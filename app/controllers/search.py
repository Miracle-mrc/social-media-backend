from flask import Blueprint, request

from app.models.user import User
from app.utils import api_response, paginated_data, pagination_args, token_required
from app.validation import text_field


search_bp = Blueprint('search', __name__)


@search_bp.route('/search', methods=['GET'])
@token_required
def search_users(current_user):
    username = text_field(request.args.get('username', ''), 'username', 50, 1)
    page, per_page = pagination_args()
    # Treat %, _ and the escape character as literal search input.
    pattern = username.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
    users = User.query.filter(User.username.ilike(f'%{pattern}%', escape='\\')).order_by(
        User.username.asc(), User.id.asc()).paginate(
            page=page, per_page=per_page, error_out=False, max_per_page=100)
    return api_response(data=paginated_data(users, lambda user: user.to_dict()))
