from django import template
from inventory.permissions import has_permission as _has_permission

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """字典取值过滤器，用于模板中 dict|get_item:key
    
    若字典为 None 或键不存在，返回空字典 {}（便于链式嵌套取值）
    """
    if dictionary is None:
        return {}
    # 防御：确保是 dict 类型，避免 Django Manager/QuerySet 的 .get() 被误调用
    if not isinstance(dictionary, dict):
        return {}
    val = dictionary.get(key)
    return val if val is not None else {}


@register.simple_tag
def has_permission(role_key, module, action):
    """检查角色是否拥有某权限

    用法：{% has_permission user.profile.role 'stockout' 'approve' %}
    """
    return _has_permission(role_key, module, action)


@register.filter
def dept_head(department):
    """获取部门的当前部门长

    用法：{{ department|dept_head }}
    返回：User 对象或 None
    """
    if not department:
        return None
    from django.contrib.auth.models import User
    return User.objects.filter(
        groups__name='部门长',
        profile__department=department,
        is_active=True,
    ).select_related('profile').first()
