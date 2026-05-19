from django.urls import path
from . import views

urlpatterns = [
    # 首页
    path('', views.home, name='home'),
    
    # 办公用品库存管理
    path('supplies/', views.supply_list, name='supply_list'),
    path('supplies/create/', views.supply_create, name='supply_create'),
    path('supplies/name-search/', views.supply_name_search, name='supply_name_search'),
    path('supplies/<int:pk>/update/', views.supply_update, name='supply_update'),
    path('supplies/<int:pk>/delete/', views.supply_delete, name='supply_delete'),
    path('supplies/<int:pk>/detail/', views.supply_detail, name='supply_detail'),
    path('supplies/<int:pk>/add-stock/', views.supply_add_stock, name='supply_add_stock'),
    path('supplies/export/', views.supply_export_excel, name='supply_export'),
    path('supplies/import/', views.supply_import_excel, name='supply_import'),
    path('supplies/template/', views.supply_template_download, name='supply_template'),
    
    # 入库单管理
    path('stockin/applications/', views.stockin_application_list, name='stockin_application_list'),
    path('stockin/applications/create/', views.stockin_application_create, name='stockin_application_create'),
    path('stockin/applications/<int:pk>/update/', views.stockin_application_update, name='stockin_application_update'),
    path('stockin/applications/<int:pk>/delete/', views.stockin_application_delete, name='stockin_application_delete'),
    path('stockin/applications/<int:pk>/detail/', views.stockin_application_detail, name='stockin_application_detail'),
    
    # 审批管理
    path('approvals/', views.approval_list, name='approval_list'),
    path('approvals/<int:pk>/process/', views.approval_process, name='approval_process'),
    path('approvals/stockout/<int:pk>/process/', views.approval_process_stockout, name='approval_process_stockout'),
    
    # 出库管理
    path('stockout/', views.stockout_list, name='stockout_list'),
    path('stockout/create/', views.stockout_create, name='stockout_create'),
    path('stockout/<int:pk>/detail/', views.stockout_detail, name='stockout_detail'),
    path('stockout/<int:pk>/edit/', views.stockout_edit, name='stockout_edit'),
    path('stockout/<int:pk>/delete/', views.stockout_delete, name='stockout_delete'),
    
    # 归还申请
    path('returns/', views.return_application_list, name='return_list'),
    path('returns/create/', views.return_application_create, name='return_create'),
    path('returns/<int:pk>/approve/', views.return_approval, name='return_approval'),
    
    # IT设备管理
    path('devices/', views.device_list, name='device_list'),
    path('devices/create/', views.device_create, name='device_create'),
    path('devices/<int:pk>/update/', views.device_update, name='device_update'),
    path('devices/<int:pk>/delete/', views.device_delete, name='device_delete'),
    path('devices/export/', views.device_export_excel, name='device_export'),
    path('devices/import/', views.device_import_excel, name='device_import'),
    path('devices/template/', views.device_template_download, name='device_template'),
    
    # 计算机类型管理
    path('computer-types/', views.computer_type_list, name='computer_type_list'),
    path('computer-types/create/', views.computer_type_create, name='computer_type_create'),
    path('computer-types/<int:pk>/update/', views.computer_type_update, name='computer_type_update'),
    path('computer-types/<int:pk>/delete/', views.computer_type_delete, name='computer_type_delete'),
    
    # 统计报表
    path('statistics/stockin/', views.stockin_statistics, name='stockin_statistics'),
    path('statistics/stockout/', views.stockout_statistics, name='stockout_statistics'),
    
    # 物品分类管理（树型结构）
    path('item-categories/', views.item_category_list, name='item_category_list'),
    path('item-categories/create/', views.item_category_create, name='item_category_create'),
    path('item-categories/<int:pk>/update/', views.item_category_update, name='item_category_update'),
    path('item-categories/<int:pk>/delete/', views.item_category_delete, name='item_category_delete'),

    # 部门管理（树型结构）
    path('departments/', views.department_list, name='department_list'),
    path('departments/create/', views.department_create, name='department_create'),
    path('departments/<int:pk>/update/', views.department_update, name='department_update'),
    path('departments/<int:pk>/delete/', views.department_delete, name='department_delete'),

    # 用户管理
    path('users/', views.user_list, name='user_list'),
    path('users/create/', views.user_create, name='user_create'),
    path('users/<int:pk>/edit/', views.user_edit, name='user_edit'),
    path('users/<int:pk>/disable/', views.user_disable, name='user_disable'),
    path('users/<int:pk>/password/', views.user_password_reset, name='user_password_reset'),
    path('users/<int:pk>/role/', views.user_role_assign, name='user_role_assign'),
    path('users/pending/', views.user_pending_list, name='user_pending_list'),
    path('users/<int:pk>/approve/', views.user_approve, name='user_approve'),
    path('users/permissions/', views.permission_management, name='permission_management'),
    path('users/roles/', views.role_list, name='role_list'),
    path('users/roles/create/', views.role_create, name='role_create'),
    path('users/roles/<int:pk>/edit/', views.role_edit, name='role_edit'),
    path('users/roles/<int:pk>/delete/', views.role_delete, name='role_delete'),

    # 个人中心
    path('profile/', views.profile_view, name='profile'),
    path('profile/password/', views.profile_password, name='profile_password'),

    # 注册
    path('register/', views.register_view, name='register'),

    # API
    path('api/dept-head-check/', views.api_dept_head_check, name='api_dept_head_check'),
    path('api/permissions/save/', views.api_save_permissions, name='api_save_permissions'),
    path('api/permissions/<str:role_key>/', views.api_role_permissions, name='api_role_permissions'),
]
