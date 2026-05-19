"""
可配置化权限系统 - 权限查询工具

设计原则：
1. 向后兼容：不破坏现有 get_user_role / get_visible_queryset 的调用方式
2. 配置优先：优先读取数据库中的 RolePermission 配置，无配置时回退到硬编码默认
3. 内存缓存：权限配置缓存于进程内存，变更时主动刷新
"""

from django.core.cache import cache
from inventory.models import SystemRole, RolePermission


def _get_role_group_map():
    """动态获取角色-用户组映射"""
    from inventory.models import get_role_group_map
    return get_role_group_map()

CACHE_KEY_PREFIX = 'role_perm:'
CACHE_VERSION_KEY = 'role_perm_version'
CACHE_TTL = 300  # 5 分钟（生产环境可调整）


# ========== 内置角色的默认权限（回退用） ==========
# module -> {action -> scope}
BUILTIN_PERMISSIONS = {
    'admin': {
        'basic_data':    {'view': 'all', 'create': 'all', 'update': 'all', 'delete': 'all', 'export': 'all', 'import': 'all'},
        'supply':        {'view': 'all', 'create': 'all', 'update': 'all', 'delete': 'all', 'export': 'all', 'import': 'all'},
        'stockin':       {'view': 'all', 'create': 'all', 'update': 'all', 'delete': 'all', 'approve': 'all', 'export': 'all'},
        'stockout':      {'view': 'all', 'create': 'all', 'update': 'all', 'delete': 'all', 'approve': 'all', 'export': 'all'},
        'approval':      {'view': 'all', 'approve': 'all'},
        'return':        {'view': 'all', 'create': 'all', 'update': 'all', 'delete': 'all', 'approve': 'all'},
        'it_device':     {'view': 'all', 'create': 'all', 'update': 'all', 'delete': 'all', 'export': 'all', 'import': 'all'},
        'statistics':    {'view': 'all', 'export': 'all'},
        'user_management': {'view': 'all', 'create': 'all', 'update': 'all', 'delete': 'all'},
    },
    'warehouse': {
        'basic_data':    {'view': 'all'},
        'supply':        {'view': 'all', 'create': 'all', 'update': 'all', 'delete': 'all'},
        'stockin':       {'view': 'all', 'create': 'all', 'approve': 'all'},
        'stockout':      {'view': 'all', 'create': 'all', 'approve': 'all'},
        'approval':      {'view': 'all', 'approve': 'all'},
        'return':        {'view': 'all', 'create': 'all', 'approve': 'all'},
        'it_device':     {'view': 'all', 'create': 'all', 'update': 'all', 'delete': 'all'},
        'statistics':    {'view': 'all'},
        'user_management': {'view': 'none'},
    },
    'dept_head': {
        'basic_data':    {'view': 'all'},
        'supply':        {'view': 'all'},
        'stockin':       {'view': 'dept', 'create': 'all'},
        'stockout':      {'view': 'dept', 'create': 'all', 'approve': 'dept'},
        'approval':      {'view': 'dept', 'approve': 'dept'},
        'return':        {'view': 'dept', 'create': 'all'},
        'it_device':     {'view': 'dept'},
        'statistics':    {'view': 'dept'},
        'user_management': {'view': 'none'},
    },
    'staff': {
        'basic_data':    {'view': 'all'},
        'supply':        {'view': 'all'},
        'stockin':       {'view': 'own', 'create': 'all'},
        'stockout':      {'view': 'own', 'create': 'all'},
        'approval':      {'view': 'own'},
        'return':        {'view': 'own', 'create': 'all'},
        'it_device':     {'view': 'dept'},
        'statistics':    {'view': 'dept'},
        'user_management': {'view': 'none'},
    },
}


# ========== 模型 -> 模块映射 ==========
MODEL_MODULE_MAP = {
    'StockInApplication': 'stockin',
    'StockOutOrder':      'stockout',
    'StockOutRecord':     'stockout',
    'ITDevice':           'it_device',
    'OfficeSupply':       'supply',
    'ReturnApplication':  'return',
}


def _get_cache_version():
    """获取当前缓存版本号"""
    version = cache.get(CACHE_VERSION_KEY)
    if version is None:
        version = 1
        cache.set(CACHE_VERSION_KEY, version, None)
    return version


def _make_cache_key(role_key):
    """构造缓存 key"""
    return f"{CACHE_KEY_PREFIX}{_get_cache_version()}:{role_key}"


def clear_permission_cache():
    """清除权限缓存（权限变更后调用）"""
    version = cache.get(CACHE_VERSION_KEY, 1)
    cache.set(CACHE_VERSION_KEY, version + 1, None)


def _load_role_permissions(role_key):
    """从数据库加载某角色的权限配置，无配置时返回内置默认"""
    try:
        role = SystemRole.objects.get(key=role_key, is_active=True)
    except SystemRole.DoesNotExist:
        # 角色不存在或已停用：回退到内置默认
        return BUILTIN_PERMISSIONS.get(role_key, {})

    perms = {}
    qs = RolePermission.objects.filter(role=role, is_enabled=True)
    for p in qs:
        perms.setdefault(p.module, {})[p.action] = p.scope
    
    # 如果数据库中一条配置都没有，回退到内置默认（兼容新角色未配置的情况）
    if not perms:
        perms = BUILTIN_PERMISSIONS.get(role_key, {})
    
    return perms


def get_role_permissions(role_key):
    """获取某角色的全部权限配置（带缓存）
    
    返回格式：
    {
        'stockout': {'view': 'dept', 'create': 'all', 'approve': 'dept'},
        'supply':   {'view': 'all'},
        ...
    }
    """
    cache_key = _make_cache_key(role_key)
    perms = cache.get(cache_key)
    if perms is None:
        perms = _load_role_permissions(role_key)
        cache.set(cache_key, perms, CACHE_TTL)
    return perms


def has_permission(role_key, module, action):
    """检查某角色是否拥有某权限
    
    超级管理员始终返回 True
    """
    if role_key == 'admin':
        return True
    perms = get_role_permissions(role_key)
    mod = perms.get(module, {})
    scope = mod.get(action)
    return scope is not None and scope != 'none'


def get_data_scope(role_key, module, action='view'):
    """获取某角色在某模块某操作下的数据权限范围
    
    返回值：'all' | 'dept' | 'own' | 'none'
    """
    if role_key == 'admin':
        return 'all'
    perms = get_role_permissions(role_key)
    mod = perms.get(module, {})
    return mod.get(action, 'none')


def get_visible_queryset_config(user, model_class, action='view'):
    """配置驱动的 get_visible_queryset 替代方案
    
    用法：在视图中替换原有的 get_visible_queryset(request.user, Model)
    """
    from django.contrib.auth.models import User
    from inventory.utils import get_user_role
    from inventory.models import (
        StockInApplication, StockOutOrder, StockOutRecord,
        ITDevice, OfficeSupply, ReturnApplication,
    )

    role = get_user_role(user)
    if role == 'admin':
        return model_class.objects.all()

    model_name = model_class.__name__
    module = MODEL_MODULE_MAP.get(model_name)
    if not module:
        # 未知模型：默认全部可见
        return model_class.objects.all()

    scope = get_data_scope(role, module, action)

    if scope == 'all':
        return model_class.objects.all()

    if scope == 'dept':
        profile = getattr(user, 'profile', None)
        dept = getattr(profile, 'department', None)
        if dept:
            # 不同模型的部门字段名可能不同
            if model_class in (StockInApplication,):
                return model_class.objects.filter(department=dept)
            elif model_class in (StockOutOrder, StockOutRecord):
                return model_class.objects.filter(department=dept)
            elif model_class == ITDevice:
                return model_class.objects.filter(department=dept)
            elif model_class == ReturnApplication:
                return model_class.objects.filter(department=dept)
            else:
                return model_class.objects.all()
        # 未分配部门时退回到仅自己
        scope = 'own'

    if scope == 'own':
        if model_class in (StockInApplication,):
            return model_class.objects.filter(applicant=user)
        elif model_class in (StockOutOrder, StockOutRecord, ReturnApplication):
            return model_class.objects.filter(operator=user)
        elif model_class == ITDevice:
            profile = getattr(user, 'profile', None)
            dept = getattr(profile, 'department', None)
            if dept:
                return model_class.objects.filter(department=dept)
            return model_class.objects.none()
        else:
            return model_class.objects.all()

    # scope == 'none'
    return model_class.objects.none()


# ========== 权限配置管理工具 ==========

def init_builtin_roles():
    """初始化内置角色及其默认权限
    
    应在 migrations 或首次部署时调用
    """
    from django.contrib.auth.models import Group

    builtin_roles = [
        {'key': 'admin',     'name': '管理员',   'is_builtin': True, 'sort_order': 0},
        {'key': 'warehouse', 'name': '仓管员',   'is_builtin': True, 'sort_order': 1},
        {'key': 'dept_head', 'name': '部门长',   'is_builtin': True, 'sort_order': 2},
        {'key': 'staff',     'name': '普通用户', 'is_builtin': True, 'sort_order': 3},
    ]

    created_any = False
    for r in builtin_roles:
        role, created = SystemRole.objects.get_or_create(
            key=r['key'],
            defaults={
                'name': r['name'],
                'is_builtin': r['is_builtin'],
                'is_active': True,
                'sort_order': r['sort_order'],
            }
        )
        if not created:
            # 更新名称（防止变更）
            role.name = r['name']
            role.is_builtin = True
            role.save(update_fields=['name', 'is_builtin'])

        # 同步创建 Django Group（与现有体系兼容）
        group_map = _get_role_group_map()
        group_name = group_map.get(r['key'], r['name'])
        Group.objects.get_or_create(name=group_name)

        # 初始化权限配置
        default_perms = BUILTIN_PERMISSIONS.get(r['key'], {})
        for module, actions in default_perms.items():
            for action, scope in actions.items():
                RolePermission.objects.get_or_create(
                    role=role,
                    module=module,
                    action=action,
                    defaults={'scope': scope, 'is_enabled': True}
                )

        created_any = True

    if created_any:
        clear_permission_cache()
    return created_any


def set_role_permission(role_key, module, action, scope, is_enabled=True):
    """设置单个权限配置（管理后台调用）"""
    role = SystemRole.objects.get(key=role_key)
    perm, _ = RolePermission.objects.update_or_create(
        role=role,
        module=module,
        action=action,
        defaults={'scope': scope, 'is_enabled': is_enabled}
    )
    clear_permission_cache()
    return perm


def batch_set_permissions(role_key, permissions_data):
    """批量设置权限
    
    permissions_data 格式：
    {
        'stockout': {'view': 'dept', 'create': 'all'},
        'supply':   {'view': 'all', 'export': 'all'},
    }
    """
    role = SystemRole.objects.get(key=role_key)
    for module, actions in permissions_data.items():
        for action, scope in actions.items():
            is_enabled = scope != 'none'
            RolePermission.objects.update_or_create(
                role=role,
                module=module,
                action=action,
                defaults={'scope': scope, 'is_enabled': is_enabled}
            )
    clear_permission_cache()


def get_all_roles_permissions():
    """获取所有角色的权限配置（用于配置页面展示）"""
    roles = SystemRole.objects.filter(is_active=True).order_by('sort_order', 'key')
    result = []
    for role in roles:
        perms = get_role_permissions(role.key)
        result.append({
            'role': role,
            'permissions': perms,
        })
    return result


def get_permission_matrix():
    """获取权限矩阵（用于前端表格渲染）
    
    返回格式：
    {
        'modules': [
            {'key': 'stockout', 'name': '出库单管理', 'actions': ['view','create',...]},
            ...
        ],
        'roles': [
            {'key': 'admin', 'name': '管理员', 'permissions': {...}},
            ...
        ]
    }
    """
    from inventory.models import RolePermission

    modules_info = []
    # 按模块分组收集所有涉及的操作
    module_actions = {}
    for mod_key, mod_name in RolePermission.MODULE_CHOICES:
        module_actions[mod_key] = {
            'key': mod_key,
            'name': mod_name,
            'actions': [],
        }

    # 收集所有已配置的操作类型
    qs = RolePermission.objects.select_related('role').filter(role__is_active=True)
    for p in qs:
        mod = module_actions.get(p.module)
        if mod and p.action not in mod['actions']:
            mod['actions'].append(p.action)

    # 补充默认操作
    all_actions = [a[0] for a in RolePermission.ACTION_CHOICES]
    for mod in module_actions.values():
        # 按 ACTION_CHOICES 的顺序排列
        ordered = [a for a in all_actions if a in mod['actions']]
        mod['actions'] = ordered
        if ordered:
            modules_info.append(mod)

    roles_info = []
    roles = SystemRole.objects.filter(is_active=True).order_by('sort_order', 'key')
    for role in roles:
        roles_info.append({
            'key': role.key,
            'name': role.name,
            'is_builtin': role.is_builtin,
            'permissions': get_role_permissions(role.key),
        })

    return {
        'modules': modules_info,
        'roles': roles_info,
    }
