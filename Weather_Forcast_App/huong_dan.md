## Bước tiếp theo là cấu hình docker cho transaction mongodb để chạy. Các bước như sau. 

### Cấu hình docker transaction
- Hướng dẫn setting docker để chạy (Setting transaction mongodb)

#### ✅ 1) Kiểm tra Docker trước (dọn tài nguyên nếu bị chiếm port / trùng container)

- Xem container đang chạy: `docker ps`
- Xem tất cả container: `docker ps -a`
- Xoá container (nếu cần): `docker rm -f <container_id_or_name>`
- Xem images: `docker images`
- Xoá images (nếu cần): `docker rmi <image_id>`
- Xem network: `docker network ls`
- Xoá network (nếu cần): `docker network rm <network_name>`

#### ✅ 2) Tạo network riêng cho Mongo Replica Set

```bash
docker network create mongoNet
```

#### ✅ 3) Pull MongoDB image (nếu chưa có)

```bash
docker pull mongo:latest
```

#### ✅ 4) Tạo 3 container chạy chung Replica Set (mongoRepSet)

```bash
docker run -d --name r4 --net mongoNet -p 27108:27017 mongo:latest mongod --replSet mongoRepSet --bind_ip_all --port 27017
docker run -d --name r5 --net mongoNet -p 27109:27017 mongo:latest mongod --replSet mongoRepSet --bind_ip_all --port 27017
docker run -d --name r6 --net mongoNet -p 27110:27017 mongo:latest mongod --replSet mongoRepSet --bind_ip_all --port 27017
```

- Lí do tạo ra 3 container (3 node) là vì replica set thường là 3 nốt để node primary mà hỏng thì cũng còn 2 node secondary vẫn sẽ chạy được, không làm hỏng chương trình.

#### ✅ 5) Initiate Replica Set (chạy trong r0)

- Setting r0 sẽ là primary còn lại là secondary

```bash
docker exec -it r0 mongosh --eval '
rs.initiate({
  _id: "mongoRepSet",
  members: [
    { _id: 0, host: "r4:27017" },
    { _id: 1, host: "r5:27017" },
    { _id: 2, host: "r6:27017" }
  ]
})
'
```

#### ✅ 6) Kiểm tra trạng thái Replica Set

```bash
docker exec -it r4 mongosh --eval 'rs.status().members.map(m=>({name:m.name,stateStr:m.stateStr}))'
```

#### ✅ 7) Vào shell của node primary (r0)

```bash
docker exec -it r0 mongosh
```

- Check trạng thái:

```bash
rs.status()
```

#### ✅ 8) Ghi database

```bash
use Login
db.Login.insert({name: "test"})
db.Login.find()
```

## Sau lệnh này thì "exit" ra

## Kết nối MongoDB Compass (Lưu ý về PRIMARY)

- Replica set có nhiều node; PRIMARY có thể thay đổi khi có election. Không cố gắng luôn kết nối cố định vào `27108`.
- Chạy script kiểm tra PRIMARY trước khi kết nối hoặc dùng app:

```powershell
.\check_mongodb_primary.ps1
```

- Sau khi script trả về PRIMARY và port tương ứng, dán URI dạng sau vào MongoDB Compass:

```
mongodb://localhost:<PRIMARY_PORT>/Login?directConnection=true
```

Thay `<PRIMARY_PORT>` bằng port script in ra (27108 / 27109 / 27110). Nếu cần, dùng `start.ps1` để tự động cập nhật `.env` và khởi động server.

## SAU KHI KẾT NỐI XONG SẼ TỚI BƯỚC CẤU HÌNH CHO .env (file này bảo mật anh em đừng public ra nha)
- Đầu tiên truy cập trang webweb: https://mailtrap.io/sending/analytics đăng nhập vào xong xui ròi vào link Youtube này: https://youtu.be/k5aPGb3px-U?si=oDSzkATldr-ADibr xem nó hướng dân cách lấy mấy key để bỏ vào .env cho quá trình gửi otp qua mail 


### Hoặc có thể thực hiện với các bước như sau:
- Vào SandboxesSandboxes --->  bấm vào My SandboxSandbox -> Copy các key sau đây và bỏ vào .env
- File .env đùng sẽ gồm các key
SECRET_KEY = "django-insecure-4$t0@wnk+#qu19m66%a90(d10z69tr$-ei@u_pf_%#m5it@=t+"
MONGO_URI=mongodb://localhost:27108/Login?directConnection=true
DB_HOST = mongodb+srv://voanhnhat1612:<Nhat@16122006>@cluster0.9xeejj9.mongodb.net/
DB_NAME = Login

DB_USER = Ti-coder
DB_PASSWORD = Nhat@16122006
DB_PORT = 27017
DB_ADMIN_EMAIL = voanhnhat1612@gmail.com
DB_AUTH_SOURCE = admin


DB_AUTH_MECHANISM = SCRAM_SHA-1
MAX_FAILED_ATTEMPS = 5
LOCKOUT_SECOND = 600
RESET_TOKEN_SALT = manager-reset-salt
RESET_TOKEN_EXPIRY_SECONDS = 3600
SECRET_KEY = O4qvkC2lzeVn70eOD7qajoMHbZhsV3MPYL2WI8bDhG19pFp1g17_VPQw54bJ0kIzSX9uP49-4mZGXrplf_I6Rg
PASSWORD_PEPPER = yPTp0tlNjhhCmktx_FInwo0bLcu2aquaT3BLVMJaQqw
JWT_SECRET=MHGtW9YsZcP1O04ScNbiOTVMPS-DCS_NKeenFBzaWXzR2Fk7_3xxnT2vubAMIuXNVybtBsCYifEYHxVW6fRnEQ
JWT_ALGORITHM=HS256
JWT_ACCESS_TTL=900 
JWT_REFRESH_TTL=604800


USER_NAME_ADMIN = VoAnhNhat
ADMIN_PASSWORD = Nhat@16122006
ADMIN_EMAIL=voanhnhat@zoo.com


ACCESS_TOKEN_EXPIRE_HOURS = 3
REFRESH_TOKEN_EXPIRE_DAYS = 1
JWT_ISSUER=weather_api
JWT_AUDIENCE=weather_web

EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST='sandbox.smtp.mailtrap.io'
EMAIL_PORT=587
EMAIL_HOST_USER='7cea9fdc3a8f18'
EMAIL_HOST_PASSWORD='c8d8e13c72a1b4'
EMAIL_USE_TLS=True

PASSWORD_RESET_OTP_EXPIRE_SECONDS=600
PASSWORD_RESET_OTP_MAX_ATTEMPTS=5



- (TỰ THAY KEY CỦA MÌNH VÀO CÁC DÒNG CUỐI NHA TỪ DÒNG 131 -> 135)
- (VÀ MUỐN TÀI KHOẢN ADMIN TÊN MÌNH THÌ THAY TỪ DÒNG 101 -> 105)


## Sau khi ổn hêt thì tiến hành các bước sau:
- Vào venV
- Cd vào PROJECT_WEATHER_FORECAST/Weather_Forcast_tin
- Chạy lệnh "python manage.py insert_first_data" để insert thông tin ban đầu xuống database
- Sau lênh này có thể chạy "python manage.py runserver" và truy cập để thực thi

## MỘT SỐ VẤN ĐỀ CẦN LƯU Ý:
- Nếu qua ngày hôm sau muốn sử dụng tiếp thì đầu tiên phải khởi động docker trước bằng lệnh: "docker start r4 r5 r6"
- Sau đó truy cập vào mongodbCompass và kết nối
- Ở thư mục scripts. Các file bấm Ctrl + F và gõ chữ output và .db để tìm ra máy đường dãn tuyệt đối và thay vào để không lỗi. 
- Không public file này , nhất là file .env. File trên t đang để full key để dễ  hình dung á, dừng public là chết luôn.

## VẤN ĐỀ CẦN SỬA LÀ:
- Chức năng quên mật khẩu: hiện tại lúc bấm nó chưa gửi email được á, tứn coi youtube cách nào đó ròi làm thử. Có thể sử dụng cái khác cũng dược không nhất thiết là mailtrap như nhật đang dùng. 
- Cài với fix nhiêu đó. Hông đưuọc thì nhật fix tiếp cho. Hay không hiểu gì thì nhắn tin. 


## MÔ TẢ VỀ CÁC FILE CODE LOGIN:
- Đầu tiên là file PROJECT_WEATHER_FORECAST/Weather_Forcast_App/Models/Login.py nó chứa các attribute cho quá trình đăng nhập
- Tiếp theo là PROJECT_WEATHER_FORECAST/Weather_Forcast_App/Seriallizer/Login dùng để khởi tạo attribute cho dữ liệu lúc người dùng create hay update
- Tiếp theo là file PROJECT_WEATHER_FORECAST/Weather_Forcast_App/scripts/Login_services.py là file dùng để xử lí logic cho quá đăng nhập. Liên quan tới nó là các file PROJECT_WEATHER_FORECAST/Weather_Forcast_App/middleware/Auth.py dùng để phân quyền . File PROJECT_WEATHER_FORECAST/Weather_Forcast_App/middleware/Authentication.py cho đăng nhập. Và file /media/voanhnhat/SDD_OUTSIDE5/PROJECT_WEATHER_FORECAST/Weather_Forcast_App/middleware/Jwt_handler.py dùng để xử lí JWT token.

- Tiếp theo Weather_Forcast_App/Repositories/Login_repositories.py dùng để tương tác với database
- Các file còn lai chắc là ae hiểu.