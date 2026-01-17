from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.urls import reverse
from datetime import datetime
from Weather_Forcast_App.scripts.Login_services import ManagerService
from Weather_Forcast_App.middleware.Jwt_handler import create_access_token
from bson import ObjectId

SESSION_RESET_EMAIL = "reset_email"
SESSION_RESET_OTP_OK = "reset_otp_ok"
SESSION_RESET_OTP = "reset_otp"

def _make_json_safe(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _make_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_make_json_safe(v) for v in obj]
    return obj

class SessionUser:
    def __init__(self, data: dict):
        self.username = data.get("userName") or data.get("username")
        self.email = data.get("email")
        full_name = data.get("name") or ""
        parts = full_name.split(" ", 1)
        self.first_name = parts[0] if parts else ""
        self.last_name = parts[1] if len(parts) > 1 else ""
        self.date_joined = data.get("createdAt")
        self.last_login = data.get("last_login")

    def get_full_name(self):
        return (self.first_name + " " + self.last_name).strip()


def _require_session_login(request):
    profile = request.session.get("profile")
    token = request.session.get("access_token")
    if not profile or not token:
        return None
    return profile


@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.method == "GET":
        return render(request, "weather/auth/Login.html")

    identifier = request.POST.get("username", "").strip()
    password = request.POST.get("password", "")

    try:
        manager = ManagerService.authenticate(identifier, password)

        token = create_access_token({
            "manager_id": manager["_id"],
            "role": manager.get("role", "guest"),
        })

        request.session["access_token"] = token
        request.session["profile"] = _make_json_safe(manager)

        messages.success(request, "Đăng nhập thành công!")
        return redirect("weather:profile")

    except Exception as e:
        messages.error(request, str(e))
        return redirect("weather:login")


@require_http_methods(["GET", "POST"])
def register_view(request):
    if request.method == "GET":
        return render(request, "weather/auth/Register.html")

    # Lấy dữ liệu từ form (đúng theo Register.html hiện tại)
    first_name = request.POST.get("first_name", "").strip()
    last_name = request.POST.get("last_name", "").strip()
    name = f"{first_name} {last_name}".strip()

    userName = request.POST.get("username", "").strip()
    email = request.POST.get("email", "").strip()
    password = request.POST.get("password", "")
    confirm_password = request.POST.get("confirm_password", "")

    # Validate cơ bản
    if not name:
        messages.error(request, "Vui lòng nhập Họ và Tên.")
        return redirect("weather:register")

    if not userName or not email or not password:
        messages.error(request, "Thiếu thông tin đăng ký (name, username, email, password).")
        return redirect("weather:register")

    if password != confirm_password:
        messages.error(request, "Mật khẩu xác nhận không khớp.")
        return redirect("weather:register")

    try:
        ManagerService.register_public({
            "name": name,
            "userName": userName,
            "email": email,
            "password": password,
            "role": "staff",  # public đăng ký mặc định staff
        })

        messages.success(request, "Tạo tài khoản thành công! Hãy đăng nhập.")
        return redirect("weather:login")

    except Exception as e:
        messages.error(request, str(e))
        return redirect("weather:register")



@require_http_methods(["GET"])
def logout_view(request):
    request.session.flush()
    messages.info(request, "Bạn đã đăng xuất.")
    return redirect("weather:login")


@require_http_methods(["GET"])
def profile_view(request):
    profile = _require_session_login(request)
    if not profile:
        messages.warning(request, "Bạn cần đăng nhập.")
        return redirect("weather:login")

    user_obj = SessionUser(profile)
    return render(request, "weather/auth/Profile.html", {"user": user_obj})


@require_http_methods(["GET", "POST"])
def forgot_password_view(request):
    if request.method == "GET":
        return render(request, "weather/auth/Forgot_password.html")

    identifier = request.POST.get("email", "").strip()  # form đang đặt name="email"
    try:
        token = ManagerService.generate_token(identifier)

        reset_link = request.build_absolute_uri(
            reverse("weather:reset_password", kwargs={"token": token})
        )

        # Dev mode: in ra console để test (sau này thay bằng gửi email)
        print("========== RESET LINK (DEV) ==========")
        print(reset_link)
        print("======================================")

        request.session["last_reset_link"] = reset_link
        messages.success(request, "Nếu tài khoản tồn tại, link reset đã được tạo (dev: xem terminal).")
        return redirect("weather:password_reset_sent")

    except Exception as e:
        messages.error(request, str(e))
        return redirect("weather:forgot_password")


@require_http_methods(["GET"])
def password_reset_sent_view(request):
    # Bạn có thể show link dev trong template nếu muốn
    return render(request, "weather/auth/Password_reset_sent.html")


@require_http_methods(["GET", "POST"])
def reset_password_view(request, token: str):
    # Kiểm tra token hợp lệ để set validlink cho template
    try:
        ManagerService.verify_reset_token(token)
        validlink = True
    except Exception as e:
        validlink = False
        messages.error(request, str(e))

    if request.method == "GET":
        return render(request, "weather/auth/Reset_password.html", {"validlink": validlink})

    if not validlink:
        return render(request, "weather/auth/Reset_password.html", {"validlink": False})

    new_password = request.POST.get("new_password1", "")
    confirm_password = request.POST.get("new_password2", "")

    if new_password != confirm_password:
        messages.error(request, "Mật khẩu xác nhận không khớp.")
        return render(request, "weather/auth/Reset_password.html", {"validlink": True})

    try:
        ManagerService.reset_password_with_token(token, new_password)
        messages.success(request, "Đặt lại mật khẩu thành công!")
        return redirect("weather:password_reset_complete")

    except Exception as e:
        messages.error(request, str(e))
        return render(request, "weather/auth/Reset_password.html", {"validlink": True})


@require_http_methods(["GET"])
def password_reset_complete_view(request):
    return render(request, "weather/auth/Password_reset_complete.html")
@require_http_methods(["GET", "POST"])
def forgot_password_otp_view(request):
    if request.method == "GET":
        return render(request, "weather/auth/Forgot_password.html")

    email = request.POST.get("email", "").strip().lower()
    if not email:
        messages.error(request, "Vui lòng nhập email.")
        return redirect("weather:forgot_password_otp")

    try:
        # luôn hiển thị thông báo chung chung (security)
        ManagerService.send_reset_otp(email)

        request.session[SESSION_RESET_EMAIL] = email
        messages.success(request, "Nếu email tồn tại, OTP đã được gửi. Vui lòng kiểm tra hộp thư (Mailtrap Inbox).")
        return redirect("weather:verify_otp")

    except Exception as e:
        messages.error(request, f"Gửi OTP thất bại: {e}")
        return redirect("weather:forgot_password_otp")



@require_http_methods(["GET", "POST"])
def verify_otp_view(request):
    email = request.session.get(SESSION_RESET_EMAIL)
    if not email:
        messages.warning(request, "Vui lòng nhập email để nhận OTP trước.")
        return redirect("weather:forgot_password_otp")

    if request.method == "GET":
        return render(request, "weather/auth/Verify_otp.html", {"email": email})

    otp = request.POST.get("otp", "").strip()
    if not otp:
        messages.error(request, "Vui lòng nhập OTP.")
        return redirect("weather:verify_otp")

    try:
        ManagerService.verify_reset_otp(email, otp)

        request.session[SESSION_RESET_OTP_OK] = True
        request.session[SESSION_RESET_OTP] = otp  # giữ tạm để bước reset dùng
        messages.success(request, "OTP hợp lệ. Bạn có thể đặt mật khẩu mới.")
        return redirect("weather:reset_password_otp")

    except Exception as e:
        messages.error(request, str(e))
        return redirect("weather:verify_otp")


@require_http_methods(["GET", "POST"])
def reset_password_otp_view(request):
    email = request.session.get(SESSION_RESET_EMAIL)
    otp_ok = request.session.get(SESSION_RESET_OTP_OK)
    otp = request.session.get(SESSION_RESET_OTP)

    if not email or not otp_ok or not otp:
        messages.warning(request, "Phiên đặt lại mật khẩu không hợp lệ. Vui lòng làm lại.")
        return redirect("weather:forgot_password_otp")

    if request.method == "GET":
        return render(request, "weather/auth/Reset_password_otp.html")

    new_password = request.POST.get("new_password", "")
    confirm_password = request.POST.get("confirm_password", "")

    if new_password != confirm_password:
        messages.error(request, "Mật khẩu xác nhận không khớp.")
        return redirect("weather:reset_password_otp")

    try:
        ManagerService.reset_password_with_otp(email, otp, new_password)

        # clear session
        request.session.pop(SESSION_RESET_EMAIL, None)
        request.session.pop(SESSION_RESET_OTP_OK, None)
        request.session.pop(SESSION_RESET_OTP, None)

        messages.success(request, "Đổi mật khẩu thành công! Hãy đăng nhập lại.")
        return redirect("weather:login")

    except Exception as e:
        messages.error(request, str(e))
        return redirect("weather:reset_password_otp")