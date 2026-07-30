import json

from django import forms
from pypinyin import lazy_pinyin

from .models import OfficeSupply, StockInApplication, StockOutRecord, StockOutOrder, StockOutItem, ReturnApplication, ItemCategory, Department


def _get_pinyin_initials(text):
    """获取中文文本的拼音首字母（大写）"""
    if not text:
        return ''
    try:
        return ''.join([p[0].upper() for p in lazy_pinyin(str(text)) if p])
    except Exception:
        return ''


class ItemCategoryForm(forms.ModelForm):
    """物品分类表单（树型结构）"""
    class Meta:
        model = ItemCategory
        fields = ['code', 'name', 'parent', 'description', 'sort_order', 'is_active']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '分类编码，如：WJ'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '分类名称，如：文具'}),
            'parent': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': '分类说明'}),
            'sort_order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 排除自身作为上级选项（编辑时）
        instance = kwargs.get('instance')
        if instance:
            # 排除自身及其所有子分类，避免循环引用
            exclude_ids = [instance.id]
            exclude_ids.extend([c.id for c in instance.get_all_children()])
            self.fields['parent'].queryset = ItemCategory.objects.exclude(id__in=exclude_ids)
        else:
            self.fields['parent'].queryset = ItemCategory.objects.all()
        self.fields['parent'].required = False
        self.fields['parent'].empty_label = "无上级（作为根分类）"


class OfficeSupplyForm(forms.ModelForm):
    """办公用品表单"""
    class Meta:
        model = OfficeSupply
        fields = ['name', 'item_category', 'specification', 'unit',
                  'safety_stock', 'location', 'supplier', 'price']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '物品名称'}),
            'item_category': forms.Select(attrs={'class': 'form-select'}),
            'specification': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '规格型号'}),
            'unit': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '个/盒/包等'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'safety_stock': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '存放位置'}),
            'supplier': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '供应商'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': 0}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['item_category'].queryset = ItemCategory.objects.filter(is_active=True).order_by('sort_order', 'code')
        self.fields['item_category'].required = True



class StockInApplicationForm(forms.ModelForm):
    """入库单表单（多物品，只选已有）"""
    class Meta:
        model = StockInApplication
        fields = ['department', 'reason', 'stockin_date']
        widgets = {
            'department': forms.Select(attrs={'class': 'form-select'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': '申请原因'}),
            'stockin_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        active_departments = list(Department.objects.filter(is_active=True).order_by('sort_order', 'code'))
        self.fields['department'].queryset = Department.objects.filter(pk__in=[d.pk for d in active_departments]).order_by('sort_order', 'code')
        self.fields['department'].label_from_instance = lambda obj: f"{obj.code} {obj.name}"
        self.fields['department'].required = True
        self.fields['stockin_date'].required = False
        self.fields['stockin_date'].input_formats = ['%Y-%m-%d']
        self.dept_pinyin_json = json.dumps({
            str(d.id): _get_pinyin_initials(d.name)
            for d in active_departments
        })

    def clean_department(self):
        department = self.cleaned_data.get('department')
        if not department:
            return department
        if not department.is_active:
            raise forms.ValidationError('该部门已停用，请选择有效部门')
        return department


class StockInApprovalForm(forms.ModelForm):
    """入库审批表单"""
    class Meta:
        model = StockInApplication
        fields = ['status', 'approval_comment']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'approval_comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class StockOutForm(forms.ModelForm):
    """出库单表单（不含物品明细）"""
    class Meta:
        model = StockOutOrder
        fields = ['recipient', 'department', 'purpose', 'out_type']
        widgets = {
            'recipient': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '领用人姓名'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'purpose': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': '用途说明'}),
            'out_type': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        active_departments = list(Department.objects.filter(is_active=True).order_by('sort_order', 'code'))
        self.fields['department'].queryset = Department.objects.filter(pk__in=[d.pk for d in active_departments]).order_by('sort_order', 'code')
        self.fields['department'].label_from_instance = lambda obj: f"{obj.code} {obj.name}"
        self.fields['department'].required = True
        self.dept_pinyin_json = json.dumps({
            str(d.id): _get_pinyin_initials(d.name)
            for d in active_departments
        })
        self.dept_active_json = json.dumps({
            str(d.id): bool(d.is_active)
            for d in active_departments
        })

        # 非管理员/仓管员：锁定部门为用户所属部门
        if self.user:
            from .utils import get_user_role
            role = get_user_role(self.user)
            if role not in ('admin', 'warehouse'):
                profile = getattr(self.user, 'profile', None)
                user_dept = getattr(profile, 'department', None)
                # 无论用户是否有部门，统一隐藏字段并锁定
                self.fields['department'].widget = forms.HiddenInput()
                if user_dept:
                    self.fields['department'].initial = user_dept.pk
                    self.fields['department'].queryset = Department.objects.filter(pk=user_dept.pk)
                else:
                    self.fields['department'].queryset = Department.objects.none()

    def clean_department(self):
        department = self.cleaned_data.get('department')
        if not department:
            return department
        if not department.is_active:
            raise forms.ValidationError('该部门已停用，请选择有效部门')
        # 非管理员/仓管员：强制校验部门必须等于用户所属部门
        if self.user:
            from .utils import get_user_role
            role = get_user_role(self.user)
            if role not in ('admin', 'warehouse'):
                profile = getattr(self.user, 'profile', None)
                user_dept = getattr(profile, 'department', None)
                if user_dept and department.pk != user_dept.pk:
                    raise forms.ValidationError('部门必须与您的所属部门一致')
        return department


class ReturnApplicationForm(forms.ModelForm):
    """归还申请表单"""
    class Meta:
        model = ReturnApplication
        fields = ['supply', 'quantity', 'returner', 'department', 'return_date', 'reason']
        widgets = {
            'supply': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'returner': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '归还人姓名'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'return_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': '归还原因'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        active_departments = list(Department.objects.filter(is_active=True).order_by('sort_order', 'code'))
        active_supplies = list(
            OfficeSupply.objects.select_related('item_category')
            .exclude(status__icontains='停用')
            .exclude(item_category__is_active=False)
            .order_by('code')
        )
        self.fields['supply'].queryset = OfficeSupply.objects.filter(pk__in=[s.pk for s in active_supplies]).order_by('code')
        self.fields['department'].queryset = Department.objects.filter(pk__in=[d.pk for d in active_departments]).order_by('sort_order', 'code')
        self.fields['department'].label_from_instance = lambda obj: f"{obj.code} {obj.name}"
        self.fields['department'].required = True
        self.dept_pinyin_json = json.dumps({
            str(d.id): _get_pinyin_initials(d.name)
            for d in active_departments
        })

    def clean_supply(self):
        supply = self.cleaned_data.get('supply')
        if not supply:
            return supply
        is_supply_disabled = ('停用' in (supply.status or '')) or (
            supply.item_category is not None and not supply.item_category.is_active
        )
        if is_supply_disabled:
            raise forms.ValidationError('该物品已停用，请选择有效物品')
        return supply

    def clean_department(self):
        department = self.cleaned_data.get('department')
        if not department:
            return department
        if not department.is_active:
            raise forms.ValidationError('该部门已停用，请选择有效部门')
        return department


class DepartmentForm(forms.ModelForm):
    """部门表单（树型结构）"""
    class Meta:
        model = Department
        fields = ['name', 'parent', 'description', 'sort_order', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '部门名称，如：技术部'}),
            'parent': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': '部门说明'}),
            'sort_order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = kwargs.get('instance')
        if instance:
            exclude_ids = [instance.id]
            exclude_ids.extend([d.id for d in instance.get_all_children()])
            self.fields['parent'].queryset = Department.objects.exclude(id__in=exclude_ids)
        else:
            self.fields['parent'].queryset = Department.objects.all()
        self.fields['parent'].required = False
        self.fields['parent'].empty_label = "无上级（作为根部门）"


class ExcelImportForm(forms.Form):
    """Excel导入表单"""
    excel_file = forms.FileField(
        label='选择Excel文件',
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.xlsx,.xls'})
    )
    update_existing = forms.BooleanField(
        label='更新已存在记录（按编码匹配）',
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )


class RegisterForm(forms.Form):
    """用户注册表单"""
    username = forms.CharField(
        label='用户名',
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '登录用户名'})
    )
    password = forms.CharField(
        label='密码',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '密码'})
    )
    password_confirm = forms.CharField(
        label='确认密码',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '再次输入密码'})
    )
    name = forms.CharField(
        label='姓名',
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '真实姓名'})
    )
    phone = forms.CharField(
        label='手机号',
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '手机号（可选）'})
    )
    department = forms.ModelChoiceField(
        label='所属部门',
        queryset=None,
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label='请选择部门'
    )
    applied_role = forms.ChoiceField(
        label='申请角色',
        choices=[
            ('staff', '普通用户'),
            ('warehouse', '仓管员'),
            ('dept_head', '部门长'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['department'].queryset = Department.objects.filter(is_active=True).order_by('sort_order', 'code')

    def clean_username(self):
        username = self.cleaned_data['username']
        from django.contrib.auth.models import User
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('该用户名已被注册')
        return username

    def clean(self):
        cleaned = super().clean()
        pw = cleaned.get('password')
        pw2 = cleaned.get('password_confirm')
        if pw and pw2 and pw != pw2:
            self.add_error('password_confirm', '两次密码不一致')
        return cleaned


class UserEditForm(forms.Form):
    """管理员编辑用户表单"""
    name = forms.CharField(label='姓名', max_length=50, widget=forms.TextInput(attrs={'class': 'form-control'}))
    phone = forms.CharField(label='手机号', max_length=20, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    department = forms.ModelChoiceField(
        label='所属部门',
        queryset=None,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label='请选择部门'
    )
    role = forms.ChoiceField(
        label='角色',
        choices=[
            ('admin', '管理员'),
            ('warehouse', '仓管员'),
            ('dept_head', '部门长'),
            ('staff', '普通用户'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    is_active = forms.BooleanField(label='启用', required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['department'].queryset = Department.objects.filter(is_active=True).order_by('sort_order', 'code')


class PasswordResetForm(forms.Form):
    """密码重置表单"""
    new_password = forms.CharField(
        label='新密码',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '输入新密码'})
    )
    confirm_password = forms.CharField(
        label='确认新密码',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '再次输入新密码'})
    )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('new_password') != cleaned.get('confirm_password'):
            self.add_error('confirm_password', '两次密码不一致')
        return cleaned


class ProfileForm(forms.Form):
    """个人信息编辑表单"""
    name = forms.CharField(label='姓名', max_length=50, widget=forms.TextInput(attrs={'class': 'form-control'}))
    phone = forms.CharField(label='手机号', max_length=20, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
