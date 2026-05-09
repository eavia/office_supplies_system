from django.db import models, transaction, IntegrityError
from django.contrib.auth.models import User
from django.utils import timezone
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
    """入库申请表（支持多物品）"""
    application_no = models.CharField('申请单号', max_length=50, unique=True)
    applicant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='stockin_applications', verbose_name='申请人')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='申请部门')
    reason = models.TextField('申请原因', blank=True)
    status = models.CharField('审批状态', max_length=20, default='待审批',
                              choices=[('待审批', '待审批'), ('已批准', '已批准'), ('已拒绝', '已拒绝')])
    approver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='stockin_approvals', verbose_name='审批人')
    approval_time = models.DateTimeField('审批时间', null=True, blank=True)
    approval_comment = models.TextField('审批意见', blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '入库申请'
        verbose_name_plural = '入库申请管理'
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
    """入库申请明细"""
    application = models.ForeignKey(StockInApplication, on_delete=models.CASCADE, related_name='items', verbose_name='入库申请')
    supply = models.ForeignKey(OfficeSupply, on_delete=models.CASCADE, verbose_name='物品')
    quantity = models.IntegerField('申请数量')
    unit_price = models.DecimalField('单价', max_digits=10, decimal_places=2, default=0)

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
    created_at = models.DateTimeField('出库时间', auto_now_add=True)

    class Meta:
        verbose_name = '出库单'
        verbose_name_plural = '出库单管理'
        ordering = ['-created_at']

    def __str__(self):
        return self.record_no

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

    class Meta:
        verbose_name = '出库明细'
        verbose_name_plural = '出库明细'

    def __str__(self):
        return f'{self.order.record_no} - {self.supply.name} x {self.quantity}'


# Keep old model name as alias for backward compat in queries / list views
StockOutRecord = StockOutOrder


class ComputerType(models.Model):
    """计算机类型表"""
    type_code = models.CharField('类型编码', max_length=20, unique=True)
    type_name = models.CharField('类型名称', max_length=100)
    category = models.CharField('设备类别', max_length=20, 
                                choices=[('主机', '主机'), ('显示器', '显示器'), ('笔记本', '笔记本'), ('其他', '其他')])
    brand = models.CharField('品牌', max_length=50, blank=True)
    model = models.CharField('型号', max_length=100, blank=True)
    specs = models.TextField('配置参数', blank=True)
    warranty_months = models.IntegerField('保修期(月)', default=36)
    description = models.TextField('描述', blank=True)
    
    class Meta:
        verbose_name = '计算机类型'
        verbose_name_plural = '计算机类型管理'
        ordering = ['type_code']
    
    def __str__(self):
        return f"{self.type_code} - {self.type_name}"


class ITDevice(models.Model):
    """IT设备表"""
    device_no = models.CharField('设备编号', max_length=50, unique=True)
    device_type = models.ForeignKey(ComputerType, on_delete=models.CASCADE, verbose_name='设备类型')
    asset_no = models.CharField('资产编号', max_length=50, blank=True)
    serial_no = models.CharField('序列号', max_length=100, blank=True)
    purchase_date = models.DateField('采购日期', null=True, blank=True)
    price = models.DecimalField('采购价格', max_digits=12, decimal_places=2, default=0)
    location = models.CharField('存放位置', max_length=100, blank=True)
    user = models.CharField('使用人', max_length=100, blank=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='使用部门')
    status = models.CharField('使用状态', max_length=20, default='库存',
                              choices=[('库存', '库存'), ('使用中', '使用中'), ('维修中', '维修中'), ('报废', '报废')])
    remarks = models.TextField('备注', blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        verbose_name = 'IT设备'
        verbose_name_plural = 'IT设备管理'
        ordering = ['device_no']
    
    def __str__(self):
        return f"{self.device_no} - {self.device_type.type_name}"


class ReturnApplication(models.Model):
    """办公用品归还申请表"""
    return_no = models.CharField('归还单号', max_length=50, unique=True)
    supply = models.ForeignKey(OfficeSupply, on_delete=models.CASCADE, verbose_name='物品')
    quantity = models.IntegerField('归还数量')
    returner = models.CharField('归还人', max_length=100)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='部门')
    return_date = models.DateField('归还日期')
    reason = models.TextField('归还原因', blank=True)
    operator = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='操作员')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    
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
