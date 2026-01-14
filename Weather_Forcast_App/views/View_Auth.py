from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect

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
