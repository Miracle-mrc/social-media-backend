from io import BytesIO
from unittest.mock import Mock

from PIL import Image

from tests.support import DatabaseTestCase


def png_file():
    stream = BytesIO()
    Image.new('RGB', (2, 2), color='red').save(stream, format='PNG')
    stream.seek(0)
    return stream


class UploadApiTestCase(DatabaseTestCase):
    def setUp(self):
        super().setUp()
        self.user = self.add_user()
        self.auth_headers = self.headers(self.user)
        self.storage = Mock()
        self.blob = self.storage.bucket.return_value.blob.return_value
        self.blob.public_url = 'https://storage.googleapis.com/test-bucket/image.png'
        self.app.extensions['gcs_client'] = self.storage
        self.app.config['GCS_BUCKET_NAME'] = 'test-bucket'

    def upload(self, stream, filename, url='/api/upload'):
        return self.client.post(url, headers=self.auth_headers, data={
            'file': (stream, filename, 'text/html'),
        }, content_type='multipart/form-data')

    def test_verified_image_uses_generated_filename_and_trusted_mime_type(self):
        response = self.upload(png_file(), '../../unsafe.PNG')
        self.assertEqual(response.status_code, 201, response.json)
        self.assertEqual(response.json['data']['public_url'], self.blob.public_url)
        object_name = self.storage.bucket.return_value.blob.call_args.args[0]
        self.assertRegex(object_name, rf'^uploads/{self.user.id}/[a-f0-9]{{32}}\.png$')
        self.assertEqual(self.blob.upload_from_file.call_args.kwargs['content_type'], 'image/png')

    def test_existing_upload_url_still_works(self):
        self.assertEqual(self.upload(png_file(), 'test.png', '/api/upload/upload').status_code, 201)

    def test_jpeg_and_gif_content_are_accepted(self):
        for image_format, extension, mime in (
                ('JPEG', 'jpg', 'image/jpeg'), ('GIF', 'gif', 'image/gif')):
            with self.subTest(image_format=image_format):
                stream = BytesIO()
                Image.new('RGB', (2, 2)).save(stream, format=image_format)
                stream.seek(0)
                self.assertEqual(self.upload(stream, f'image.{extension}').status_code, 201)
                self.assertEqual(
                    self.blob.upload_from_file.call_args.kwargs['content_type'], mime)

    def test_upload_requires_authentication(self):
        response = self.client.post('/api/upload', data={'file': (png_file(), 'test.png')})
        self.assertEqual(response.status_code, 401)
        self.storage.bucket.assert_not_called()

    def test_invalid_or_missing_file_is_rejected(self):
        response = self.client.post('/api/upload', headers=self.auth_headers, data={})
        self.assertEqual(response.status_code, 400)
        for contents, filename in (
                (b'fake image', 'image.jpg'), (b'fake image', 'image.txt'),
                (png_file().getvalue(), 'image.jpg'), (b'', ''),
                (b'\xff\xd8\xff\xe0truncated', 'image.jpg')):
            with self.subTest(filename=filename):
                self.assertEqual(self.upload(BytesIO(contents), filename).status_code, 400)
        self.storage.bucket.assert_not_called()

    def test_size_limit_returns_413(self):
        self.app.config['MAX_CONTENT_LENGTH'] = 512
        response = self.upload(BytesIO(b'x' * 2048), 'large.png')
        self.assertEqual(response.status_code, 413)
        self.storage.bucket.assert_not_called()

    def test_pixel_limit_rejects_large_dimensions(self):
        self.app.config['MAX_IMAGE_PIXELS'] = 1
        self.assertEqual(self.upload(png_file(), 'large.png').status_code, 400)
        self.storage.bucket.assert_not_called()

    def test_missing_storage_configuration_returns_503(self):
        self.app.config['GCS_BUCKET_NAME'] = None
        self.assertEqual(self.upload(png_file(), 'test.png').status_code, 503)

    def test_storage_failure_is_500_without_internal_details(self):
        self.blob.upload_from_file.side_effect = RuntimeError('private storage credentials')
        with self.assertLogs(self.app.logger, level='ERROR'):
            response = self.upload(png_file(), 'test.png')
        self.assertEqual(response.status_code, 500)
        self.assertNotIn('private storage credentials', response.get_data(as_text=True))
