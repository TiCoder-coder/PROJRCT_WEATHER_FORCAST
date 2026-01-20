# 🌦️ Hướng Dẫn Chạy Dự Án Weather Forecast

## 📋 Yêu Cầu Hệ Thống

- Windows 10/11
- Python 3.10+
- Docker Desktop
- MongoDB Compass (tùy chọn)

---

## 🚀 Hướng Dẫn Cài Đặt Lần Đầu

### Bước 1: Cài Đặt Docker Desktop

```powershell
winget install Docker.DockerDesktop --accept-package-agreements --accept-source-agreements
```

Sau khi cài xong, **khởi động lại máy** hoặc mở Docker Desktop và đợi cho đến khi nó chạy hoàn tất.

---

### Bước 2: Tạo MongoDB Replica Set

#### 2.1 Tạo network cho MongoDB

```powershell
docker network create mongoNet
```

#### 2.2 Pull MongoDB image

```powershell
docker pull mongo:latest
```

#### 2.3 Tạo 3 container MongoDB

```powershell
docker run -d --name r4 --net mongoNet -p 27108:27017 mongo:latest mongod --replSet mongoRepSet --bind_ip_all --port 27017
docker run -d --name r5 --net mongoNet -p 27109:27017 mongo:latest mongod --replSet mongoRepSet --bind_ip_all --port 27017
docker run -d --name r6 --net mongoNet -p 27110:27017 mongo:latest mongod --replSet mongoRepSet --bind_ip_all --port 27017
```

#### 2.4 Khởi tạo Replica Set

```powershell
docker exec r4 mongosh --eval "rs.initiate({ _id: 'mongoRepSet', members: [ { _id: 0, host: 'r4:27017' }, { _id: 1, host: 'r5:27017' }, { _id: 2, host: 'r6:27017' } ] })"
```

#### 2.5 Kiểm tra trạng thái

```powershell
docker exec r4 mongosh --eval "rs.status().members.map(m=>({name:m.name,stateStr:m.stateStr}))"
```

**Kết quả mong đợi:**
```
[
  { name: 'r4:27017', stateStr: 'PRIMARY' },
  { name: 'r5:27017', stateStr: 'SECONDARY' },
  { name: 'r6:27017', stateStr: 'SECONDARY' }
]
```

---

### Bước 3: Tạo File .env

Tạo file `.env` trong thư mục gốc dự án với nội dung sau:

```env
SECRET_KEY=django-insecure-4$t0@wnk+#qu19m66%a90(d10z69tr$-ei@u_pf_%#m5it@=t+
MONGO_URI=mongodb://localhost:27108/Login?directConnection=true
DB_HOST=mongodb+srv://voanhnhat1612:<Nhat@16122006>@cluster0.9xeejj9.mongodb.net/
DB_NAME=Login

DB_USER=Ti-coder
DB_PASSWORD=Nhat@16122006
DB_PORT=27017
DB_ADMIN_EMAIL=voanhnhat1612@gmail.com
DB_AUTH_SOURCE=admin

DB_AUTH_MECHANISM=SCRAM_SHA-1
MAX_FAILED_ATTEMPS=5
LOCKOUT_SECOND=600
RESET_TOKEN_SALT=manager-reset-salt
RESET_TOKEN_EXPIRY_SECONDS=3600
SECRET_KEY=O4qvkC2lzeVn70eOD7qajoMHbZhsV3MPYL2WI8bDhG19pFp1g17_VPQw54bJ0kIzSX9uP49-4mZGXrplf_I6Rg
PASSWORD_PEPPER=yPTp0tlNjhhCmktx_FInwo0bLcu2aquaT3BLVMJaQqw
JWT_SECRET=MHGtW9YsZcP1O04ScNbiOTVMPS-DCS_NKeenFBzaWXzR2Fk7_3xxnT2vubAMIuXNVybtBsCYifEYHxVW6fRnEQ
JWT_ALGORITHM=HS256
JWT_ACCESS_TTL=900
JWT_REFRESH_TTL=604800

USER_NAME_ADMIN=VoAnhNhat
ADMIN_PASSWORD=Nhat@16122006
ADMIN_EMAIL=voanhnhat@zoo.com

ACCESS_TOKEN_EXPIRE_HOURS=3
REFRESH_TOKEN_EXPIRE_DAYS=1
JWT_ISSUER=weather_api
JWT_AUDIENCE=weather_web

EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=sandbox.smtp.mailtrap.io
EMAIL_PORT=587
EMAIL_HOST_USER=7cea9fdc3a8f18
EMAIL_HOST_PASSWORD=c8d8e13c72a1b4
EMAIL_USE_TLS=True

PASSWORD_RESET_OTP_EXPIRE_SECONDS=600
PASSWORD_RESET_OTP_MAX_ATTEMPTS=5
```

> ⚠️ **LƯU Ý**: Thay đổi các giá trị `USER_NAME_ADMIN`, `ADMIN_PASSWORD`, `ADMIN_EMAIL` và các key EMAIL theo thông tin của bạn.

---

### Bước 4: Cài Đặt Dependencies

```powershell
# Kích hoạt virtual environment
.\venv\Scripts\Activate.ps1

# Cài đặt packages
pip install -r requirements.txt
pip install pymongo django python-dotenv PyJWT dnspython
```

---

### Bước 5: Khởi Tạo Database

```powershell
python manage.py insert_first_data
```

**Kết quả mong đợi:**
```
Admin 'VoAnhNhat' created successfully in MongoDB!
```

---

### Bước 6: Chạy Server

```powershell
python manage.py runserver
```

Truy cập: **http://127.0.0.1:8000**

---

## 🔄 Hướng Dẫn Chạy Lại (Các Ngày Sau)

### Bước 1: Khởi động Docker containers

```powershell
docker start r4 r5 r6
```

### Bước 2: Kiểm tra trạng thái (tùy chọn)

```powershell
docker exec r4 mongosh --eval "rs.status().members.map(m=>({name:m.name,stateStr:m.stateStr}))"
```

### Bước 3: Chạy server

```powershell
cd D:\PROJRCT_WEATHER_FORCAST
.\venv\Scripts\Activate.ps1
python manage.py runserver
```

---

## 🔗 Kết Nối MongoDB Compass

Sử dụng URI sau để kết nối:

```
mongodb://localhost:27108/Login?directConnection=true
```

> **Lưu ý**: Port 27108 là PRIMARY. Nếu PRIMARY thay đổi, kiểm tra lại bằng lệnh `rs.status()` và sử dụng port tương ứng (27108/27109/27110).

---

## 📊 Thông Tin Database

| Collection | Mô tả |
|------------|-------|
| `logins` | Thông tin đăng nhập người dùng |
| `revoked_tokens` | Quản lý token bị thu hồi |
| `password_reset_otps` | Quản lý OTP reset mật khẩu |

---

## 🛠️ Các Lệnh Docker Hữu Ích

| Lệnh | Mô tả |
|------|-------|
| `docker ps` | Xem container đang chạy |
| `docker ps -a` | Xem tất cả container |
| `docker start r4 r5 r6` | Khởi động các container |
| `docker stop r4 r5 r6` | Dừng các container |
| `docker rm -f r4 r5 r6` | Xóa các container |
| `docker network ls` | Xem danh sách network |

---

## ⚠️ Lưu Ý Quan Trọng

1. **KHÔNG public file `.env`** - Chứa thông tin nhạy cảm
2. **Luôn khởi động Docker trước** khi chạy server
3. **Kiểm tra PRIMARY** trước khi kết nối MongoDB Compass
4. **Backup database** định kỳ

---

## 🐛 Xử Lý Lỗi Thường Gặp

### Lỗi: Docker command not found

```powershell
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
```

### Lỗi: Port already in use

```powershell
docker rm -f r4 r5 r6
# Sau đó chạy lại các lệnh tạo container
```

### Lỗi: Module not found

```powershell
pip install pymongo django python-dotenv PyJWT dnspython
```

---

## 📞 Liên Hệ

Nếu có vấn đề, liên hệ: **voanhnhat1612@gmail.com**
