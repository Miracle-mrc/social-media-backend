import os
from datetime import timedelta

from flask import Flask

from app.extensions import db, jwt, migrate


def create_app(config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY'),
        JWT_SECRET_KEY=os.environ.get('JWT_SECRET_KEY'),
        SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URL', 'sqlite:///social_media.db'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        JWT_ACCESS_TOKEN_EXPIRES=timedelta(minutes=15),
        JWT_REFRESH_TOKEN_EXPIRES=timedelta(days=7),
        JWT_TOKEN_LOCATION=['headers'],
        MAX_CONTENT_LENGTH=8 * 1024 * 1024,
        MAX_IMAGE_PIXELS=20_000_000,
        GCS_BUCKET_NAME=os.environ.get('GCS_BUCKET_NAME'),
    )
    if config:
        app.config.update(config)
    if not app.config['JWT_SECRET_KEY']:
        app.config['JWT_SECRET_KEY'] = app.config['SECRET_KEY']
    for key in ('SECRET_KEY', 'JWT_SECRET_KEY'):
        value = app.config[key]
        if not isinstance(value, str) or len(value.encode('utf-8')) < 32:
            raise RuntimeError(f'{key} must be set to a random secret of at least 32 bytes')

    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)

    # Load every model before migrations inspect the metadata.
    from app import models  # noqa: F401
    from app.errors import register_error_handlers
    from app.security import register_jwt_callbacks
    from app.controllers.auth import auth_bp
    from app.controllers.user import user_bp
    from app.controllers.post import post_bp, user_posts_bp
    from app.controllers.upload import upload_bp
    from app.controllers.follow import follow_bp
    from app.controllers.like import like_bp
    from app.controllers.news_feed import news_feed_bp
    from app.controllers.search import search_bp

    register_error_handlers(app)
    register_jwt_callbacks()
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(user_bp, url_prefix='/api/user')
    app.register_blueprint(user_posts_bp, url_prefix='/api/user')
    app.register_blueprint(post_bp, url_prefix='/api/post')
    app.register_blueprint(upload_bp, url_prefix='/api/upload')
    # These groups share resource URLs, with no dependence on import order.
    app.register_blueprint(follow_bp, url_prefix='/api/user')
    app.register_blueprint(like_bp, url_prefix='/api/post')
    app.register_blueprint(news_feed_bp, url_prefix='/api/post')
    app.register_blueprint(search_bp, url_prefix='/api/user')
    return app
