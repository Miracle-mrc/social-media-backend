# Social Media Backend

Backend Flask cho tài khoản, hồ sơ, bài viết có ảnh, follow, like, bảng tin và tìm kiếm.
Dùng Python 3.12, SQLAlchemy, Flask-JWT-Extended và Flask-Migrate.
SQLite dùng cho phát triển; MySQL dùng qua biến môi trường DATABASE_URL.

## Chạy trên Windows (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_hex(32))"
```

Dán khóa vừa sinh vào SECRET_KEY trong .env. Có thể sinh một khóa riêng cho JWT_SECRET_KEY;
nếu để trống, ứng dụng dùng SECRET_KEY. Không đưa khóa thật lên Git.

```powershell
python -m flask --app main db upgrade
python -m flask --app main run --debug --port 5000
```

API chạy ở http://127.0.0.1:5000. SQLite được lưu trong instance/social_media.db.

## Chạy trên Linux/macOS

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
# Điền SECRET_KEY bằng một khóa ngẫu nhiên trước khi tiếp tục.
python -m flask --app main db upgrade
sh devserver.sh
```

devserver.sh chỉ dùng cho phát triển. Production chạy Gunicorn; không bật Flask debug.

## Cấu hình

| Biến môi trường | Ý nghĩa |
| --- | --- |
| SECRET_KEY | Bắt buộc, khóa ngẫu nhiên tối thiểu 32 byte. |
| JWT_SECRET_KEY | Khóa JWT riêng; mặc định dùng SECRET_KEY. |
| DATABASE_URL | Mặc định sqlite:///social_media.db. MySQL: mysql+pymysql://app_user:URL_ENCODED_PASSWORD@host:3306/social_media. |
| GCS_BUCKET_NAME | Bucket dùng để lưu ảnh; chỉ bắt buộc khi upload. |
| GOOGLE_APPLICATION_CREDENTIALS | Đường dẫn credentials khi cần ở máy local; giữ file ngoài dự án. |
| PORT | Cổng cho main.py/Gunicorn, mặc định 5000. |

Không cấu hình Google Cloud vẫn khởi động và chạy các API khác được.
Upload chưa cấu hình bucket trả 503; không tự kết nối Google Cloud lúc import.
Tài khoản database của ứng dụng nên có quyền trên database cần dùng, không dùng root.

**Thông tin đăng nhập và khóa ký đã từng nằm trong mã cũ cần được thay trên hệ thống thật.**
Xóa khỏi mã không vô hiệu hóa các giá trị cũ. Đổi mật khẩu database, khóa JWT và cập nhật
cấu hình triển khai; các token cũ sẽ cần đăng nhập lại. File credentials JSON cần nằm
ngoài thư mục build và được mount/cấp qua môi trường triển khai.

## Database cũ

Migration gồm hai bước: 0001_initial mô tả bốn bảng cũ; 0002_integrity thêm deleted,
foreign key, index và bảng auth_sessions. Database trống chỉ cần chạy db upgrade.

Với database đã có bảng từ phiên bản cũ, sao lưu trước, kiểm tra schema khớp
migrations/versions/0001_initial.py và thử trên bản sao trước khi áp dụng:

```sh
python -m flask --app main db stamp 0001_initial
python -m flask --app main db upgrade
```

Stamp chỉ ghi nhận phiên bản, không kiểm tra hay sửa schema; không dùng trên database
có cấu trúc khác hoặc đã có lịch sử migration. Dừng traffic ghi khi nâng cấp schema.
Migration kiểm tra bản ghi tham chiếu đến user/post không tồn tại và dừng trước khi
đổi schema nếu có dữ liệu đó. Cần sửa quan hệ theo dữ liệu thực tế rồi chạy lại;
migration không tự xóa các bản ghi.

Các bài viết cũ được đặt deleted=false. Xóa bài là xóa mềm; chi tiết bài, danh sách,
bảng tin và like đều bỏ qua bài đã xóa. Downgrade từ 0002 bỏ lịch sử phiên đăng nhập
và trạng thái xóa mềm, nên cần cân nhắc dữ liệu trước khi thực hiện.

## API

Các API được bảo vệ nhận header Authorization: Bearer <access_token>.

| Method | URL | Chức năng |
| --- | --- | --- |
| POST | /api/auth/register | Đăng ký: username, email, password; fullname tùy chọn. |
| POST | /api/auth/login | Đăng nhập: username, password. |
| POST | /api/auth/refresh | Dùng refresh_token trong header để lấy access_token mới. |
| POST | /api/auth/logout | Thu hồi phiên hiện tại bằng access_token hoặc refresh_token. |
| GET, PUT | /api/user/profile | Xem/sửa hồ sơ cá nhân. |
| GET | /api/user/<user_id>/profile | Hồ sơ công khai. |
| GET | /api/user/<user_id>/posts | Bài viết của người dùng. |
| POST, DELETE | /api/user/<user_id>/follow | Follow/unfollow. |
| GET | /api/user/search?username=... | Tìm kiếm username. |
| POST | /api/post | Tạo bài: image_url (HTTP/HTTPS), caption tùy chọn. |
| GET, DELETE | /api/post/<post_id> | Xem/xóa bài. Chỉ chủ bài được xóa. |
| POST, DELETE | /api/post/<post_id>/like | Like/unlike. |
| GET | /api/post/newsfeed | Bài của bản thân và người đang theo dõi. |
| POST | /api/upload | Upload ảnh bằng multipart/form-data, trường file. |

Upload yêu cầu đăng nhập; URL /api/upload/upload vẫn được hỗ trợ để tương thích.
Các blueprint follow/like dùng URL tài nguyên user/post như bảng trên.

Username dài 3–50 ký tự, gồm chữ Latin, số, dấu chấm, gạch dưới và gạch nối.
Mật khẩu đăng ký dài 8–128 ký tự; email tối đa 100 ký tự.
fullname tối đa 100, bio tối đa 2000 và caption tối đa 2200 ký tự.
Danh sách hỗ trợ page từ 1 và per_page từ 1 đến 100, mặc định 10.
Tìm kiếm không có kết quả trả 200 với items rỗng; ký tự % và _ được tìm theo nghĩa đen.

Access token có hạn 15 phút, refresh token 7 ngày. Cả hai gắn với phiên lưu trong database.
Logout thu hồi cả token gốc lẫn access token đã được làm mới của phiên đó; phiên đăng nhập
trên thiết bị khác vẫn hoạt động. Phiên đã thu hồi không tự có hiệu lực lại sau khi restart.
Ứng dụng trả 401 cho lỗi xác thực, 400 cho dữ liệu sai, 403 khi không có quyền, 404 khi không
tìm thấy, 409 khi trùng dữ liệu, 413 khi upload quá dung lượng, và 500 cho lỗi nội bộ.
Lỗi nội bộ được ghi log; phản hồi không chứa exception hay thông tin kết nối.
Email chỉ xuất hiện ở đăng nhập và hồ sơ cá nhân, không xuất hiện ở hồ sơ công khai/tìm kiếm.

## Upload ảnh

Ảnh tối đa 8 MiB cho toàn bộ request và 20 triệu pixel. Chấp nhận PNG, JPEG, GIF;
kiểm tra định dạng/nội dung ảnh bằng Pillow và đối chiếu với đuôi file.
Tên object dùng UUID, MIME type lấy từ định dạng đã xác minh.
Ảnh được lưu ở uploads/<user_id>/ trong bucket; không còn route phục vụ ảnh từ đĩa local.

Cấu hình Application Default Credentials và GCS_BUCKET_NAME trước khi dùng upload.
Tài khoản dịch vụ cần quyền tạo object trong bucket. API trả public_url cho ảnh công khai;
bucket phải cho phép đọc các object này. Mã không tự thay đổi IAM/ACL của bucket.
Không dùng cơ chế public_url cho dữ liệu cần giữ riêng tư.
Tests dùng storage giả và không tải ảnh lên Google Cloud.

## Kiểm thử

```sh
python -m unittest discover -s tests -t . -v
```

Tests dùng SQLite riêng, không đọc DATABASE_URL thật và không cần Google credentials.
Bao phủ đăng ký/đăng nhập/refresh/logout, phân quyền, dữ liệu công khai, bài viết,
follow/like/feed/search, upload hợp lệ/sai/quá giới hạn và phản hồi lỗi.
Migration được kiểm tra trên database trống, schema cũ có dữ liệu và dữ liệu bị đứt quan hệ.
Database dạng file phục vụ tests được tạo và dọn trong instance/tests.

## Docker

```sh
docker build -t social-media-backend .
# Chạy migration một lần bằng cùng database/cấu hình sẽ dùng cho ứng dụng.
docker run --rm --env-file .env social-media-backend python -m flask --app main db upgrade
docker run --rm --env-file .env -p 5000:5000 social-media-backend
```

Container chạy bằng user không phải root. Dùng database MySQL bên ngoài container cho
triển khai có dữ liệu bền vững; hai lệnh trên phải cùng DATABASE_URL. Với SQLite, cần mount
cùng volume /app/instance cho cả migration và server. .env, runtime local và credentials
không được đưa vào image. Chỉ truyền khóa/database/GCS qua cấu hình khi chạy.
