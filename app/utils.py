from functools import wraps
from uuid import uuid4

from flask import current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from werkzeug.exceptions import BadRequest, ServiceUnavailable

from app.extensions import db
from app.models.user import User


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
IMAGE_FORMATS = {
    'PNG': ('png', 'image/png'),
    'JPEG': ('jpg', 'image/jpeg'),
    'GIF': ('gif', 'image/gif'),
}


def allowed_file(filename):
    if not isinstance(filename, str) or '.' not in filename:
        return False
    stem, extension = filename.rsplit('.', 1)
    return bool(stem) and extension.lower() in ALLOWED_EXTENSIONS


def upload_file_to_gcs(file_obj, destination_folder, image_format):
    bucket_name = current_app.config.get('GCS_BUCKET_NAME')
    if not bucket_name:
        raise ServiceUnavailable('Image storage is not configured')
    client = current_app.extensions.get('gcs_client')
    if client is None:
        from google.cloud import storage
        client = storage.Client()
        current_app.extensions['gcs_client'] = client
    extension, content_type = IMAGE_FORMATS[image_format]
    # Object names and MIME types are generated from verified image content.
    filename = f'{destination_folder}/{uuid4().hex}.{extension}'
    blob = client.bucket(bucket_name).blob(filename)
    blob.upload_from_file(file_obj.stream, rewind=True, content_type=content_type, timeout=60)
    return blob.public_url


def api_response(data=None, message=None, status=200):
    response = {'success': 200 <= status < 300, 'status': status}
    if message:
        response['message'] = message
    if data is not None:
        response['data'] = data
    return jsonify(response), status


def token_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        current_user = db.session.get(User, int(get_jwt_identity()))
        if current_user is None:
            return api_response(message='User does not exist', status=401)
        return fn(current_user, *args, **kwargs)
    return wrapper


def pagination_args():
    values = []
    for name, default in (('page', 1), ('per_page', 10)):
        try:
            value = int(request.args.get(name, default))
        except (ValueError, TypeError):
            raise BadRequest(f'{name} must be a positive integer') from None
        if value < 1 or (name == 'per_page' and value > 100):
            raise BadRequest(f'{name} must be between 1 and 100' if name == 'per_page'
                             else 'page must be a positive integer')
        values.append(value)
    return values


def paginated_data(result, serialize):
    return {
        'items': [serialize(item) for item in result.items],
        'pagination': {
            'page': result.page,
            'per_page': result.per_page,
            'total': result.total,
            'pages': result.pages,
        },
    }
