import warnings

from flask import Blueprint, current_app, request
from PIL import Image, UnidentifiedImageError
from werkzeug.exceptions import BadRequest

from app.utils import allowed_file, api_response, token_required, upload_file_to_gcs


upload_bp = Blueprint('upload', __name__)


def verified_image_format(file):
    if not file.filename or not allowed_file(file.filename):
        raise BadRequest('File must have a PNG, JPG, JPEG or GIF extension')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(file.stream) as image:
                image_format = image.format
                if image_format not in ('PNG', 'JPEG', 'GIF'):
                    raise BadRequest('Unsupported image format')
                extension = file.filename.rsplit('.', 1)[1].lower()
                expected_format = {'png': 'PNG', 'jpg': 'JPEG',
                                   'jpeg': 'JPEG', 'gif': 'GIF'}[extension]
                if image_format != expected_format:
                    raise BadRequest('Image content does not match its file extension')
                if image.width * image.height > current_app.config['MAX_IMAGE_PIXELS']:
                    raise BadRequest('Image dimensions are too large')
                image.verify()
            file.stream.seek(0)
            with Image.open(file.stream) as image:
                image.load()
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise BadRequest('Image dimensions are too large') from None
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError):
        raise BadRequest('File does not contain a valid image') from None
    finally:
        file.stream.seek(0)
    return image_format


# Preserve the existing URL while offering the shorter resource URL.
@upload_bp.route('', methods=['POST'])
@upload_bp.route('/upload', methods=['POST'])
@token_required
def upload_file(current_user):
    if 'file' not in request.files:
        raise BadRequest('A file field is required')
    file = request.files['file']
    image_format = verified_image_format(file)
    public_url = upload_file_to_gcs(file, f'uploads/{current_user.id}', image_format)
    return api_response(message='Upload successful', data={'public_url': public_url}, status=201)
