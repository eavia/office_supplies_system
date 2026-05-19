from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def role_required(*allowed_roles):
    """角色权限装饰器，检查当前用户是否属于允许的角色"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')

            # 超级用户放行
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            # 检查角色
            profile = getattr(request.user, 'profile', None)
            if profile and profile.role in allowed_roles:
                return view_func(request, *args, **kwargs)

            messages.error(request, '您没有权限执行此操作')
            return redirect('home')
        return wrapper
    return decorator
