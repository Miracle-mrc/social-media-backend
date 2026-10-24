from werkzeug.exceptions import HTTPException

from app.extensions import db
from app.utils import api_response


def register_error_handlers(app):
    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        return api_response(message=error.description, status=error.code)

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        db.session.rollback()
        app.logger.exception('Unhandled request error')
        return api_response(message='An internal server error occurred', status=500)
