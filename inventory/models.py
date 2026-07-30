from django.db import models, transaction, IntegrityError
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
import uuid
import re


class SupplyCategory(models.Model):
    """办公用品类别表"""
    code = models.CharField('类别编码', max_length=20, unique=True)
    name = models.CharField('类别名称', max_length=50, unique=True)
    description = models.TextField('类别说明', blank=True)
    sort_order = models.IntegerField('排序', default=0)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    
    class Meta:
        verbose_name = '办公用品类别'
        verbose_name_plural = '办公用品类别管理'
        ordering = ['sort_order', 'code']
    
    def __str__(self):
        return f"{self.code} - {self.name}"


class ItemCategory(models.Model):
    """物品分类表（树型结构）"""
    code = models.CharField('分类编码', max_length=20, unique=True)
    name = models.CharField('分类名称', max_length=50)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, 
                               verbose_name='上级分类', related_name='children')
    description = models.TextField('分类说明', blank=True)
    sort_order = models.IntegerField('排序', default=0)
    is_active = models.BooleanField('是否启用', default=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        verbose_name = '物品分类'
        verbose_name_plural = '物品分类管理'
        ordering = ['sort_order', 'code']
    
    def __str__(self):
        if self.parent:
            return f"{self.parent.name} / {self.name}"
        return self.name
    
    def get_full_path(self):
        """获取完整路径"""
        path = [self.name]
        current = self.parent
        while current:
            path.insert(0, current.name)
            current = current.parent
        return ' > '.join(path)
    
    def get_level(self):
        """获取层级深度"""
        level = 0
        current = self.parent
        while current:
            level += 1
            current = current.parent
        return level
    
    def has_children(self):
        """是否有子分类"""
        return self.children.exists()
    
    def get_all_children(self):
        """获取所有子分类（递归）"""
        result = []
        for child in self.children.all():
            result.append(child)
            result.extend(child.get_all_children())
        return result


class OfficeSupply(models.Model):
    """办公用品库存表"""
    code = models.CharField('物品编码', max_length=50, unique=True)
    name = models.CharField('物品名称', max_length=100)
    item_category = models.ForeignKey(ItemCategory, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='物品分类', related_name='supplies')
    specification = models.CharField('规格型号', max_length=100, blank=True)
    unit = models.CharField('计量单位', max_length=20, default='个')
    quantity = models.IntegerField('库存数量', default=0)
    locked_quantity = models.IntegerField('锁定库存', default=0, help_text='待审批出库单已占用的数量')
    safety_stock = models.IntegerField('安全库存', default=10)
    location = models.CharField('存放位置', max_length=100, blank=True)
    supplier = models.CharField('供应商', max_length=100, blank=True)
    price = models.DecimalField('单价', max_digits=10, decimal_places=2, default=0)
    status = models.CharField('状态', max_length=20, default='正常', 
                              choices=[('正常', '正常'), ('低库存', '低库存'), ('停用', '停用')])
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        verbose_name = '办公用品'
        verbose_name_plural = '办公用品库存'
        ordering = ['code']
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    @property
    def available_quantity(self):
        """可用库存 = 实际库存 - 锁定库存"""
        return max(0, self.quantity - self.locked_quantity)
    
    def _next_numeric_serial(self):
        """获取全局不重复数字流水号"""
        max_num = 0
        pattern = re.compile(r'.*-(\d+)$')
        for code in OfficeSupply.objects.values_list('code', flat=True):
            if not code:
                continue
            match = pattern.match(code)
            if match:
                max_num = max(max_num, int(match.group(1)))
        return max_num + 1

    def _generate_code(self):
        """按规则生成编码：根分类编码-子分类编码-不重复数字"""
        if not self.item_category:
            raise ValueError('物品分类不能为空，无法生成物品编码')

        # 收集从根到当前分类的编码链
        codes = []
        current = self.item_category
        while current:
            codes.insert(0, current.code)
            current = current.parent

        prefix = '-'.join(codes)
        serial = self._next_numeric_serial()
        return f"{prefix}-{serial:06d}"

    def save(self, *args, **kwargs):
        # 自动更新库存状态
        if self.quantity <= self.safety_stock:
            self.status = '低库存'
        else:
            self.status = '正常'

        # 已存在记录：强制保持编码不可修改
        if self.pk:
            old_code = OfficeSupply.objects.filter(pk=self.pk).values_list('code', flat=True).first()
            if old_code:
                self.code = old_code
            return super().save(*args, **kwargs)

        # 新增记录：强制自动生成编码（忽略外部传入 code）
        for _ in range(5):
            self.code = self._generate_code()
            try:
                with transaction.atomic():
                    return super().save(*args, **kwargs)
            except IntegrityError:
                # 并发下编码冲突时重试
                continue

        raise IntegrityError('自动生成物品编码失败，请重试')


class Department(models.Model):
    """部门管理表（树型结构）"""
    code = models.CharField('部门编码', max_length=50, unique=True)
    name = models.CharField('部门名称', max_length=50)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True,
                               verbose_name='上级部门', related_name='children')
    description = models.TextField('部门说明', blank=True)
    sort_order = models.IntegerField('排序', default=0)
    is_active = models.BooleanField('是否启用', default=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '部门'
        verbose_name_plural = '部门管理'
        ordering = ['sort_order', 'code']

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} / {self.name}"
        return self.name

    def get_full_path(self):
        """获取完整路径"""
        path = [self.name]
        current = self.parent
        while current:
            path.insert(0, current.name)
            current = current.parent
        return ' > '.join(path)

    def get_level(self):
        """获取层级深度"""
        level = 0
        current = self.parent
        while current:
            level += 1
            current = current.parent
        return level

    def has_children(self):
        """是否有子部门"""
        return self.children.exists()

    def get_all_children(self):
        """获取所有子部门（递归）"""
        result = []
        for child in self.children.all():
            result.append(child)
            result.extend(child.get_all_children())
        return result

    def _next_serial(self):
        """获取部门流水号"""
        max_num = 0
        pattern = re.compile(r'BU-(\d+)$')
        for code in Department.objects.values_list('code', flat=True):
            if not code:
                continue
            match = pattern.match(code)
            if match:
                max_num = max(max_num, int(match.group(1)))
        return max_num + 1

    def _generate_code(self):
        """生成部门编码：BU-不重复数字"""
        serial = self._next_serial()
        return f"BU-{serial:03d}"

    def save(self, *args, **kwargs):
        # 已存在记录：保持编码不变
        if self.pk:
            old_code = Department.objects.filter(pk=self.pk).values_list('code', flat=True).first()
            if old_code:
                self.code = old_code
            return super().save(*args, **kwargs)

        # 新增记录：自动生成编码
        for _ in range(5):
            self.code = self._generate_code()
            try:
                with transaction.atomic():
                    return super().save(*args, **kwargs)
            except IntegrityError:
                continue

        raise IntegrityError('自动生成部门编码失败，请重试')


class StockInApplication(models.Model):
    """入库单表（支持多物品）"""
    application_no = models.CharField('申请单号', max_length=50, unique=True)
    applicant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='stockin_applications', verbose_name='申请人')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='申请部门')
    reason = models.TextField('申请原因', blank=True)
    stockin_date = models.DateField('入库日期', null=False, blank=False, default=timezone.now)  # 必填字段，默认为当前日期
    status = models.CharField('审批状态', max_length=20, default='待审批',
                              choices=[('待审批', '待审批'), ('已批准', '已批准'), ('已拒绝', '已拒绝')])
    approver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='stockin_approvals', verbose_name='审批人')
    approval_time = models.DateTimeField('审批时间', null=True, blank=True)
    approval_comment = models.TextField('审批意见', blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '入库单'
        verbose_name_plural = '入库单管理'
        ordering = ['-created_at']

    def __str__(self):
        return self.application_no

    def save(self, *args, **kwargs):
        if not self.created_at:
            self.created_at = timezone.now()
        if not self.application_no:
            self.application_no = f"RK{self.created_at.strftime('%Y%m%d')}{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)

    def get_items_summary(self):
        """获取物品摘要，用于列表显示"""
        items = list(self.items.select_related('supply').all())
        if not items:
            return '-'
        if len(items) == 1:
            return f"{items[0].supply.name} × {items[0].quantity}"
        return f"{items[0].supply.name} 等 {len(items)} 项"

    def get_total_amount(self):
        """合计金额 = 所有明细小计之和"""
        total = 0
        for item in self.items.all():
            total += item.subtotal
        return total


class StockInItem(models.Model):
    """入库单明细"""
    application = models.ForeignKey(StockInApplication, on_delete=models.CASCADE, related_name='items', verbose_name='入库单')
    supply = models.ForeignKey(OfficeSupply, on_delete=models.CASCADE, verbose_name='物品')
    quantity = models.IntegerField('申请数量')
    unit_price = models.DecimalField('单价', max_digits=10, decimal_places=2, default=0)
    # 快照字段：记录入库时物品的属性，防止后续物品属性变更导致历史记录失真
    specification = models.CharField('规格快照', max_length=100, blank=True)
    unit = models.CharField('单位快照', max_length=20, default='个')
    location = models.CharField('存放位置快照', max_length=100, blank=True)
    supplier = models.CharField('供应商快照', max_length=100, blank=True)
    doc_no = models.CharField('发票或对方单据编号', max_length=100, blank=True)

    class Meta:
        verbose_name = '入库明细'
        verbose_name_plural = '入库明细'

    def __str__(self):
        return f'{self.application.application_no} - {self.supply.name} × {self.quantity}'

    @property
    def subtotal(self):
        """小计 = 单价 × 数量"""
        return self.unit_price * self.quantity


class StockOutOrder(models.Model):
    """出库单"""
    record_no = models.CharField('出库单号', max_length=50, unique=True)
    recipient = models.CharField('领用人', max_length=100)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='领用部门')
    purpose = models.TextField('用途说明', blank=True)
    operator = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='操作员')
    out_type = models.CharField('出库类型', max_length=20, default='领用',
                                choices=[('领用', '领用'), ('归还', '归还'), ('报废', '报废'), ('调拨', '调拨')])
    status = models.CharField('审批状态', max_length=20, default='待审批',
                              choices=[('待审批', '待审批'), ('待仓管审批', '待仓管审批'), ('已批准', '已批准'), ('已拒绝', '已拒绝')])
    dept_approver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='stockout_dept_approvals', verbose_name='部门长审批人')
    dept_approval_time = models.DateTimeField('部门长审批时间', null=True, blank=True)
    dept_approval_comment = models.TextField('部门长审批意见', blank=True)
    approver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='stockout_approvals', verbose_name='仓管审批人')
    approval_time = models.DateTimeField('仓管审批时间', null=True, blank=True)
    approval_comment = models.TextField('仓管审批意见', blank=True)
    created_at = models.DateTimeField('出库时间', auto_now_add=True)

    class Meta:
        verbose_name = '出库单'
        verbose_name_plural = '出库单管理'
        ordering = ['-created_at']

    def __str__(self):
        return self.record_no

    def get_items_summary(self):
        """获取物品摘要，用于列表显示"""
        items = list(self.items.select_related('supply').all())
        if not items:
            return '-'
        if len(items) == 1:
            return f"{items[0].supply.name} × {items[0].quantity}"
        return f"{items[0].supply.name} 等 {len(items)} 项"

    def save(self, *args, **kwargs):
        if not self.created_at:
            self.created_at = timezone.now()
        if not self.record_no:
            self.record_no = f"CK{self.created_at.strftime('%Y%m%d')}{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)


class StockOutItem(models.Model):
    """出库明细"""
    order = models.ForeignKey(StockOutOrder, on_delete=models.CASCADE, related_name='items', verbose_name='出库单')
    supply = models.ForeignKey(OfficeSupply, on_delete=models.CASCADE, verbose_name='物品')
    quantity = models.IntegerField('出库数量')
    # 快照字段：记录出库时物品的属性，防止后续物品属性变更导致历史记录失真
    specification = models.CharField('规格快照', max_length=100, blank=True)
    unit = models.CharField('单位快照', max_length=20, default='个')
    location = models.CharField('存放位置快照', max_length=100, blank=True)
    supplier = models.CharField('供应商快照', max_length=100, blank=True)
    remark = models.CharField('备注', max_length=200, blank=True)

    class Meta:
        verbose_name = '出库明细'
        verbose_name_plural = '出库明细'

    def __str__(self):
        return f'{self.order.record_no} - {self.supply.name} x {self.quantity}'


# Keep old model name as alias for backward compat in queries / list views
StockOutRecord = StockOutOrder


class ReturnApplication(models.Model):
    """办公用品归还申请表"""
    return_no = models.CharField('归还单号', max_length=50, unique=True)
    stockout_order = models.ForeignKey(StockOutOrder, on_delete=models.CASCADE, related_name='returns', verbose_name='关联出库单', null=True, blank=True)
    supply = models.ForeignKey(OfficeSupply, on_delete=models.CASCADE, verbose_name='物品')
    quantity = models.IntegerField('归还数量')
    returner = models.CharField('归还人', max_length=100)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='部门')
    return_date = models.DateField('归还日期')
    reason = models.TextField('归还原因', blank=True)
    operator = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='操作员')
    status = models.CharField('审批状态', max_length=20, default='待审批',
                              choices=[('待审批', '待审批'), ('已批准', '已批准'), ('已拒绝', '已拒绝')])
    approver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='return_approvals', verbose_name='审批人')
    approval_time = models.DateTimeField('审批时间', null=True, blank=True)
    approval_comment = models.TextField('审批意见', blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    # 快照字段：记录归还时物品的属性，防止后续物品属性变更导致历史记录失真
    specification = models.CharField('规格快照', max_length=100, blank=True)
    unit = models.CharField('单位快照', max_length=20, default='个')
    location = models.CharField('存放位置快照', max_length=100, blank=True)
    supplier = models.CharField('供应商快照', max_length=100, blank=True)
    
    class Meta:
        verbose_name = '归还申请'
        verbose_name_plural = '归还申请管理'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.return_no
    
    def save(self, *args, **kwargs):
        if not self.created_at:
            self.created_at = timezone.now()
        if not self.return_no:
            self.return_no = f"GH{self.created_at.strftime('%Y%m%d')}{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)


# ========== 角色常量（默认值，首次启动 SystemRole 表为空时回退使用） ==========
ROLE_CHOICES = [
    ('admin', '管理员'),
    ('warehouse', '仓管员'),
    ('dept_head', '部门长'),
    ('staff', '普通用户'),
]

ROLE_GROUP_MAP = {
    'admin': '管理员',
    'warehouse': '仓管员',
    'dept_head': '部门长',
    'staff': '普通用户',
}


def get_role_choices():
    """动态获取角色选项，优先从 SystemRole 表读取"""
    try:
        return [(r.key, r.name) for r in SystemRole.objects.filter(is_active=True).order_by('sort_order', 'key')]
    except Exception:
        return ROLE_CHOICES


def get_role_group_map():
    """动态获取角色-用户组映射，优先从 SystemRole 表读取"""
    try:
        return {r.key: r.name for r in SystemRole.objects.filter(is_active=True)}
    except Exception:
        return ROLE_GROUP_MAP


def get_role_display_name(role_key):
    """动态获取角色显示名称"""
    try:
        role = SystemRole.objects.filter(key=role_key, is_active=True).first()
        if role:
            return role.name
    except Exception:
        pass
    return dict(ROLE_CHOICES).get(role_key, '普通用户')


class Profile(models.Model):
    """用户扩展信息"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile', verbose_name='用户')
    name = models.CharField('姓名', max_length=50, blank=True)
    phone = models.CharField('手机号', max_length=20, blank=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='所属部门')
    applied_role = models.CharField('申请角色', max_length=20, choices=get_role_choices(), default='staff')
    is_pending = models.BooleanField('待审核', default=False, help_text='注册后待管理员审核')

    class Meta:
        verbose_name = '用户信息'
        verbose_name_plural = '用户信息管理'

    def __str__(self):
        return f"{self.user.username} - {self.name or self.user.username}"

    @property
    def role(self):
        """获取用户当前角色"""
        groups = self.user.groups.values_list('name', flat=True)
        group_map = get_role_group_map()
        for role_key, group_name in group_map.items():
            if group_name in groups:
                return role_key
        return 'staff'

    @property
    def role_display(self):
        """获取角色中文名"""
        return get_role_display_name(self.role)


# ========== 信号：User 创建时自动创建 Profile ==========
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(user=instance)


# ========== 可配置化权限系统 ==========

class SystemRole(models.Model):
    """系统角色定义（支持自定义角色）"""

    key = models.CharField('角色标识', max_length=20, unique=True)
    name = models.CharField('角色名称', max_length=50)
    description = models.TextField('角色说明', blank=True)
    is_builtin = models.BooleanField('是否内置角色', default=False,
                                      help_text='内置角色不可删除，权限变更即时生效')
    is_active = models.BooleanField('是否启用', default=True)
    sort_order = models.IntegerField('排序', default=0)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '系统角色'
        verbose_name_plural = '系统角色管理'
        ordering = ['sort_order', 'key']

    def __str__(self):
        return f"{self.key} - {self.name}"


class RolePermission(models.Model):
    """角色-权限配置表（一行代表一个角色对某个功能点的权限）"""

    MODULE_CHOICES = [
        ('basic_data', '基础数据管理'),
        ('supply', '库存管理'),
        ('stockin', '入库单管理'),
        ('stockout', '出库单管理'),
        ('approval', '审批管理'),
        ('return', '归还管理'),
        ('statistics', '统计报表'),
        ('user_management', '用户管理'),
    ]

    ACTION_CHOICES = [
        ('view', '查看'),
        ('create', '创建'),
        ('update', '编辑'),
        ('delete', '删除'),
        ('approve', '审批'),
        ('export', '导出'),
        ('import', '导入'),
    ]

    SCOPE_CHOICES = [
        ('all', '全部'),
        ('dept', '本部门'),
        ('own', '仅自己'),
        ('none', '无权限'),
    ]

    role = models.ForeignKey(SystemRole, on_delete=models.CASCADE,
                              related_name='permissions', verbose_name='角色')
    module = models.CharField('功能模块', max_length=30, choices=MODULE_CHOICES)
    action = models.CharField('操作类型', max_length=20, choices=ACTION_CHOICES)
    scope = models.CharField('数据范围', max_length=20, choices=SCOPE_CHOICES, default='none')
    is_enabled = models.BooleanField('是否启用', default=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '角色权限配置'
        verbose_name_plural = '角色权限配置'
        unique_together = ['role', 'module', 'action']
        ordering = ['role__sort_order', 'module', 'action']

    def __str__(self):
        return f"{self.role.name} | {self.get_module_display()} | {self.get_action_display()} = {self.get_scope_display()}"
