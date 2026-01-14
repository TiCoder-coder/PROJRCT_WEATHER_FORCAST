from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.template.loader import render_to_string
from django.conf import settings

@csrf_protect
@require_http_methods(["GET", "POST"])
def login_view(request):
    """
    View xử lý đăng nhập
    """
    # Nếu user đã đăng nhập, redirect về trang chủ
    if request.user.is_authenticated:
        return redirect('weather:home')
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        remember_me = request.POST.get('remember_me')
        
        if not username or not password:
            messages.error(request, 'Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu.')
            return render(request, 'weather/auth/login.html')
        
        # Xác thực người dùng
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            
            # Xử lý "Remember me"
            if not remember_me:
                request.session.set_expiry(0)  # Session hết hạn khi đóng browser
            else:
                request.session.set_expiry(1209600)  # 2 tuần
            
            messages.success(request, f'Xin chào {user.username}! Đăng nhập thành công.')
            
            # Redirect về trang được yêu cầu hoặc trang chủ
            next_page = request.GET.get('next', 'weather:home')
            return redirect(next_page)
        else:
            messages.error(request, 'Tên đăng nhập hoặc mật khẩu không đúng.')
    
    return render(request, 'weather/auth/login.html')


@csrf_protect
@require_http_methods(["GET", "POST"])
def register_view(request):
    """
    View xử lý đăng ký tài khoản mới
    """
    # Nếu user đã đăng nhập, redirect về trang chủ
    if request.user.is_authenticated:
        return redirect('weather:home')
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        
        # Validation
        if not username or not email or not password or not confirm_password:
            messages.error(request, 'Vui lòng điền đầy đủ thông tin bắt buộc.')
            return render(request, 'weather/auth/register.html')
        
        if len(username) < 3:
            messages.error(request, 'Tên đăng nhập phải có ít nhất 3 ký tự.')
            return render(request, 'weather/auth/register.html')
        
        if len(password) < 6:
            messages.error(request, 'Mật khẩu phải có ít nhất 6 ký tự.')
            return render(request, 'weather/auth/register.html')
        
        if password != confirm_password:
            messages.error(request, 'Mật khẩu xác nhận không khớp.')
            return render(request, 'weather/auth/register.html')
        
        # Kiểm tra username đã tồn tại
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Tên đăng nhập đã tồn tại.')
            return render(request, 'weather/auth/register.html')
        
        # Kiểm tra email đã tồn tại
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email đã được đăng ký.')
            return render(request, 'weather/auth/register.html')
        
        try:
            # Tạo user mới
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
            
            messages.success(request, 'Đăng ký thành công! Vui lòng đăng nhập.')
            return redirect('weather:login')
        
        except Exception as e:
            messages.error(request, f'Có lỗi xảy ra: {str(e)}')
            return render(request, 'weather/auth/register.html')
    
    return render(request, 'weather/auth/register.html')


@require_http_methods(["GET", "POST"])
def logout_view(request):
    """
    View xử lý đăng xuất
    """
    logout(request)
    messages.info(request, 'Bạn đã đăng xuất thành công.')
    return redirect('weather:login')


@login_required(login_url='weather:login')
def profile_view(request):
    """
    View hiển thị thông tin profile người dùng
    """
    return render(request, 'weather/auth/profile.html', {
        'user': request.user
    })


@csrf_protect
@require_http_methods(["GET", "POST"])
def forgot_password_view(request):
    """
    View xử lý quên mật khẩu - gửi email reset
    """
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        
        if not email:
            messages.error(request, 'Vui lòng nhập địa chỉ email.')
            return render(request, 'weather/auth/forgot_password.html')
        
        try:
            user = User.objects.get(email=email)
            
            # Tạo token reset password
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # Tạo link reset (trong môi trường thực tế, dùng domain thật)
            reset_link = request.build_absolute_uri(
                f"/auth/reset-password/{uid}/{token}/"
            )
            
            # Gửi email (trong development mode, chỉ log ra console)
            subject = 'Đặt lại mật khẩu - VN Weather Hub'
            message = f"""
Xin chào {user.username},

Bạn đã yêu cầu đặt lại mật khẩu cho tài khoản VN Weather Hub của mình.

Vui lòng nhấp vào liên kết dưới đây để đặt lại mật khẩu:
{reset_link}

Liên kết này sẽ hết hạn sau 24 giờ.

Nếu bạn không yêu cầu đặt lại mật khẩu, vui lòng bỏ qua email này.

Trân trọng,
VN Weather Hub Team
            """
            
            # Trong development, in ra console
            print(f"\n{'='*60}")
            print(f"PASSWORD RESET EMAIL")
            print(f"{'='*60}")
            print(f"To: {email}")
            print(f"Subject: {subject}")
            print(f"\n{message}")
            print(f"{'='*60}\n")
            
            # Trong production, uncomment dòng dưới để gửi email thật
            # send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email])
            
            messages.success(request, 'Email đặt lại mật khẩu đã được gửi. Vui lòng kiểm tra hộp thư của bạn.')
            return redirect('weather:password_reset_sent')
            
        except User.DoesNotExist:
            # Vì lý do bảo mật, không tiết lộ email có tồn tại hay không
            messages.success(request, 'Nếu email tồn tại trong hệ thống, bạn sẽ nhận được hướng dẫn đặt lại mật khẩu.')
            return redirect('weather:password_reset_sent')
        except Exception as e:
            messages.error(request, f'Có lỗi xảy ra: {str(e)}')
    
    return render(request, 'weather/auth/forgot_password.html')


@require_http_methods(["GET"])
def password_reset_sent_view(request):
    """
    View hiển thị thông báo đã gửi email reset
    """
    return render(request, 'weather/auth/password_reset_sent.html')


@csrf_protect
@require_http_methods(["GET", "POST"])
def reset_password_view(request, uidb64, token):
    """
    View xử lý đặt lại mật khẩu mới
    """
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    
    # Kiểm tra token hợp lệ
    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            password1 = request.POST.get('new_password1', '')
            password2 = request.POST.get('new_password2', '')
            
            if not password1 or not password2:
                messages.error(request, 'Vui lòng nhập đầy đủ mật khẩu.')
                return render(request, 'weather/auth/reset_password.html', {'validlink': True})
            
            if len(password1) < 8:
                messages.error(request, 'Mật khẩu phải có ít nhất 8 ký tự.')
                return render(request, 'weather/auth/reset_password.html', {'validlink': True})
            
            if password1 != password2:
                messages.error(request, 'Mật khẩu xác nhận không khớp.')
                return render(request, 'weather/auth/reset_password.html', {'validlink': True})
            
            # Đặt mật khẩu mới
            user.set_password(password1)
            user.save()
            
            messages.success(request, 'Mật khẩu đã được đặt lại thành công!')
            return redirect('weather:password_reset_complete')
        
        return render(request, 'weather/auth/reset_password.html', {'validlink': True})
    else:
        # Token không hợp lệ hoặc đã hết hạn
        return render(request, 'weather/auth/reset_password.html', {'validlink': False})


@require_http_methods(["GET"])
def password_reset_complete_view(request):
    """
    View hiển thị thông báo hoàn tất đặt lại mật khẩu
    """
    return render(request, 'weather/auth/password_reset_complete.html')
