from inventory.models import (
    StockInApplication, StockOutOrder, ITDevice, OfficeSupply,
    ROLE_GROUP_MAP, Profile
)


def get_user_role(user):
    """获取用户角色"""
    if user.is_superuser:
        return 'admin'
    profile = getattr(user, 'profile', None)
    return profile.role if profile else 'staff'


def get_visible_queryset(user, model):
    """根据用户角色返回可见的 QuerySet"""
    role = get_user_role(user)
    
    if role == 'admin':
        return model.objects.all()
    
    if model == StockInApplication:
        if role == 'warehouse':
            return model.objects.all()
        return model.objects.filter(applicant=user)
    
    if model == StockOutOrder:
        if role == 'warehouse':
            return model.objects.all()
        if role == 'dept_head':
            profile = getattr(user, 'profile', None)
            if profile and profile.department:
                return model.objects.filter(department=profile.department)
            return model.objects.filter(operator=user)
        return model.objects.filter(operator=user)
    
    if model == ITDevice:
        if role == 'warehouse':
            return model.objects.all()
        if role == 'dept_head':
            profile = getattr(user, 'profile', None)
            if profile and profile.department:
                return model.objects.filter(department=profile.department)
            return model.objects.none()
        return model.objects.filter(department=getattr(
            getattr(user, 'profile', None), 'department', None))
    
    if model == OfficeSupply:
        return model.objects.all()
    
    return model.objects.all()


def check_dept_head_exists(department, exclude_user=None):
    """检查部门是否已有部门长，返回 (exists: bool, user: User or None)"""
    from django.contrib.auth.models import User
    dept_head_group = User.objects.filter(
        groups__name='部门长',
        profile__department=department,
        is_active=True,
    )
    if exclude_user:
        dept_head_group = dept_head_group.exclude(pk=exclude_user.pk)
    return dept_head_group.first()


def check_pending_before_role_change(user):
    """角色变更前检查待处理数据，返回 (can_change: bool, pending_items: list)"""
    pending = []
    
    # 通用：自己创建的待处理单据
    pending_stockout = StockOutOrder.objects.filter(
        operator=user, status__in=['待审批', '待仓管审批']
    )
    for order in pending_stockout:
        pending.append(f"出库单 {order.record_no} 状态为「{order.status}」")
    
    pending_stockin = StockInApplication.objects.filter(
        applicant=user, status='待审批'
    )
    for app in pending_stockin:
        pending.append(f"入库单 {app.application_no} 等待审批")
    
    # 部门长专属检查
    role = get_user_role(user)
    if role == 'dept_head':
        profile = getattr(user, 'profile', None)
        if profile and profile.department:
            pending_approval = StockOutOrder.objects.filter(
                department=profile.department, status='待审批'
            )
            for order in pending_approval:
                pending.append(f"出库单 {order.record_no} 等待您（部门长）审批")
    
    # 仓管员专属检查
    if role == 'warehouse':
        pending_wh_stockin = StockInApplication.objects.filter(status='待审批')
        for app in pending_wh_stockin:
            pending.append(f"入库单 {app.application_no} 等待您（仓管）审批")
        pending_wh_stockout = StockOutOrder.objects.filter(status='待仓管审批')
        for order in pending_wh_stockout:
            pending.append(f"出库单 {order.record_no} 等待您（仓管）审批")
    
    return len(pending) == 0, pending
