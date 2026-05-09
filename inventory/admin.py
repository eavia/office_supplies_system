from django.contrib import admin
from .models import OfficeSupply, StockInApplication, StockOutRecord, StockOutItem, ITDevice, ComputerType, ReturnApplication, ItemCategory


@admin.register(ItemCategory)
class ItemCategoryAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'parent', 'sort_order', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('code', 'name')
    ordering = ('sort_order', 'code')


@admin.register(OfficeSupply)
class OfficeSupplyAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'item_category', 'specification', 'unit', 'quantity', 'safety_stock', 'status', 'location')
    list_filter = ('item_category', 'status')
    search_fields = ('code', 'name')
    readonly_fields = ('code',)


@admin.register(StockInApplication)
class StockInApplicationAdmin(admin.ModelAdmin):
    list_display = ('application_no', 'applicant', 'department', 'status', 'created_at')
    list_filter = ('status', 'department')
    search_fields = ('application_no', 'supply__name')


@admin.register(StockOutRecord)
class StockOutRecordAdmin(admin.ModelAdmin):
    list_display = ('record_no', 'recipient', 'department', 'out_type', 'created_at')
    list_filter = ('out_type', 'department')
    search_fields = ('record_no', 'recipient')


@admin.register(StockOutItem)
class StockOutItemAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'order', 'supply', 'quantity')
    search_fields = ('order__record_no', 'supply__name')


@admin.register(ITDevice)
class ITDeviceAdmin(admin.ModelAdmin):
    list_display = ('device_no', 'device_type', 'asset_no', 'serial_no', 'user', 'department', 'status')
    list_filter = ('status', 'device_type__category')
    search_fields = ('device_no', 'asset_no', 'serial_no')


@admin.register(ComputerType)
class ComputerTypeAdmin(admin.ModelAdmin):
    list_display = ('type_code', 'type_name', 'category', 'brand', 'model', 'warranty_months')
    list_filter = ('category',)
    search_fields = ('type_code', 'type_name')


@admin.register(ReturnApplication)
class ReturnApplicationAdmin(admin.ModelAdmin):
    list_display = ('return_no', 'supply', 'quantity', 'returner', 'department', 'return_date')
    list_filter = ('department',)
    search_fields = ('return_no', 'supply__name')
