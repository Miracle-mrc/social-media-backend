import re
from urllib.parse import urlsplit

from flask import request
from werkzeug.exceptions import BadRequest


def json_object():
    data = request.get_json()
    if not isinstance(data, dict):
        raise BadRequest('Request body must be a JSON object')
    return data


def text_field(value, name, maximum, minimum=0, strip=True):
    if not isinstance(value, str):
        raise BadRequest(f'{name} must be a string')
    value = value.strip() if strip else value
    if not minimum <= len(value) <= maximum:
        raise BadRequest(f'{name} must contain {minimum} to {maximum} characters')
    return value


def user_fields(data, registering=False):
    fields = {}
    required = ('username', 'email', 'password') if registering else ()
    for name in required:
        if name not in data:
            raise BadRequest(f'{name} is required')
    if 'username' in data:
        username = text_field(data['username'], 'username', 50, 3)
        if not re.fullmatch(r'[A-Za-z0-9_.-]+', username):
            raise BadRequest(
                'username may only contain letters, digits, dots, underscores and hyphens')
        fields['username'] = username
    if 'email' in data:
        email = text_field(data['email'], 'email', 100, 3).lower()
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email):
            raise BadRequest('email is invalid')
        fields['email'] = email
    if registering:
        fields['password'] = text_field(data['password'], 'password', 128, 8, strip=False)
    if 'fullname' in data:
        fields['fullname'] = text_field(data['fullname'], 'fullname', 100)
    elif registering and 'full_name' in data:
        fields['fullname'] = text_field(data['full_name'], 'fullname', 100)
    if 'bio' in data:
        fields['bio'] = text_field(data['bio'], 'bio', 2000)
    return fields


def image_url(value):
    value = text_field(value, 'image_url', 255, 1)
    try:
        parsed = urlsplit(value)
        valid = (parsed.scheme in ('http', 'https') and parsed.hostname
                 and not parsed.username and not parsed.password)
    except ValueError:
        valid = False
    if not valid or any(char.isspace() for char in value):
        raise BadRequest('image_url must be an HTTP or HTTPS URL')
    return value
