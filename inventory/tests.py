from django.test import TestCase, Client
from django.apps import apps
from django.contrib.auth.models import User
from inventory.models import (
    Department, ItemCategory, OfficeSupply, ReturnApplication,
    StockInApplication, StockOutItem, StockOutOrder, StockOutRecord,
)


class SystemTestCase(TestCase):
    """系统功能测试"""
    
    def setUp(self):
        """测试前准备"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        self.client.login(username='testuser', password='testpass123')
        
        # 创建测试数据
        self.item_category = ItemCategory.objects.create(
            code='WJ',
            name='文具',
            description='办公文具类',
            is_active=True,
        )
        self.department = Department.objects.create(
            code='CS',
            name='测试部门',
            is_active=True,
        )
        self.user.profile.department = self.department
        self.user.profile.save(update_fields=['department'])

        self.supply = OfficeSupply.objects.create(
            code='BGY001',
            name='A4打印纸',
            item_category=self.item_category,
            specification='70g/500张',
            unit='包',
            quantity=100,
            safety_stock=20,
            price=25.00
        )
        

    
    # ========== 首页测试 ==========
    def test_home_page(self):
        """测试首页"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '系统首页')
        print("✓ 首页访问正常")
    
    # ========== 办公用品库存测试 ==========
    def test_supply_list(self):
        """测试库存列表"""
        response = self.client.get('/supplies/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'A4打印纸')
        print("✓ 库存列表页正常")
    
    def test_supply_create(self):
        """测试库存创建（编码自动生成）"""
        response = self.client.post('/supplies/create/', {
            'name': '中性笔',
            'item_category': self.item_category.id,
            'specification': '0.5mm黑色',
            'unit': '支',
            'quantity': 200,
            'safety_stock': 50,
            'price': 2.50,
            'status': '正常'
        })
        self.assertEqual(response.status_code, 302)
        created = OfficeSupply.objects.filter(name='中性笔').first()
        self.assertIsNotNone(created)
        self.assertTrue(created.code.startswith(f'{self.item_category.code}-'))
        print("✓ 库存创建功能正常（编码自动生成）")
    
    def test_supply_export(self):
        """测试库存导出"""
        response = self.client.get('/supplies/export/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 
                         'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        print("✓ 库存导出功能正常")
    
    # ========== 入库单测试 ==========
    def test_stockin_application_list(self):
        """测试入库单列表"""
        response = self.client.get('/stockin/applications/')
        self.assertEqual(response.status_code, 200)
        print("✓ 入库单列表页正常")
    
    def test_stockin_application_create(self):
        """测试入库单创建（多物品）"""
        import json
        response = self.client.post('/stockin/applications/create/', {
            'department': str(self.department.id),
            'reason': '补充库存',
            'stockin_date': '2026-07-30',
            'items_json': json.dumps([{'supply_id': self.supply.id, 'quantity': 50}])
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(StockInApplication.objects.filter(items__supply=self.supply, items__quantity=50).exists())
        print("✓ 入库单创建功能正常")
    
    # ========== 审批测试 ==========
    def test_approval_list(self):
        """测试审批列表"""
        response = self.client.get('/approvals/')
        self.assertEqual(response.status_code, 200)
        print("✓ 审批列表页正常")
    
    # ========== 出库测试 ==========
    def test_stockout_list(self):
        """测试出库列表"""
        response = self.client.get('/stockout/')
        self.assertEqual(response.status_code, 200)
        print("✓ 出库列表页正常")
    
    def test_stockout_create(self):
        """测试出库创建（多物品）"""
        import json
        response = self.client.post('/stockout/create/', {
            'recipient': '张三',
            'department': str(self.department.id),
            'purpose': '办公使用',
            'out_type': '领用',
            'items_json': json.dumps([{'supply_id': self.supply.id, 'quantity': 10}])
        })
        self.assertEqual(response.status_code, 302)
        # 出库申请提交后仅锁定库存，待审批通过才扣减实际库存。
        self.supply.refresh_from_db()
        self.assertEqual(self.supply.quantity, 100)
        self.assertEqual(self.supply.locked_quantity, 10)
        print("✓ 出库创建功能正常，库存已锁定等待审批")
    
    # ========== 归还申请测试 ==========
    def test_return_list(self):
        """测试归还列表"""
        response = self.client.get('/returns/')
        self.assertEqual(response.status_code, 200)
        print("✓ 归还列表页正常")
    

    # ========== 统计报表测试 ==========
    def test_stockin_statistics(self):
        """测试入库统计"""
        response = self.client.get('/statistics/stockin/')
        self.assertEqual(response.status_code, 200)
        print("✓ 入库统计页正常")
    
    def test_stockout_statistics(self):
        """测试出库统计"""
        response = self.client.get('/statistics/stockout/')
        self.assertEqual(response.status_code, 200)
        print("✓ 出库统计页正常")
    
    # ========== 模板下载测试 ==========
    def test_supply_template_download(self):
        """测试办公用品模板下载"""
        response = self.client.get('/supplies/template/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 
                         'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        print("✓ 办公用品导入模板下载正常")
    
class ProcessManagementTestCase(TestCase):
    """管理员流程扭转必须保证状态和库存同步。"""

    def setUp(self):
        self.admin = User.objects.create_superuser('admin', 'admin@example.com', 'testpass123')
        self.client.force_login(self.admin)
        self.department = Department.objects.create(code='GL', name='管理部', is_active=True)
        self.category = ItemCategory.objects.create(code='BG', name='办公用品', is_active=True)
        self.supply = OfficeSupply.objects.create(
            name='测试物品', item_category=self.category, quantity=20,
            safety_stock=15,
        )

    def _stockout_order(self, status='待审批'):
        order = StockOutOrder.objects.create(
            recipient='测试人员', department=self.department, operator=self.admin,
            status=status,
        )
        StockOutItem.objects.create(order=order, supply=self.supply, quantity=10)
        if status in ('待审批', '待仓管审批'):
            self.supply.locked_quantity = 10
            self.supply.save()
        elif status == '已批准':
            self.supply.quantity = 10
            self.supply.save()
        return order

    def test_rejects_forged_process_parameters(self):
        order = self._stockout_order()
        response = self.client.post('/process-management/action/', {
            'order_type': 'invalid', 'action': '已批准', 'selected': [order.pk],
        })
        self.assertRedirects(response, '/process-management/')
        order.refresh_from_db()
        self.supply.refresh_from_db()
        self.assertEqual(order.status, '待审批')
        self.assertEqual(self.supply.quantity, 20)
        self.assertEqual(self.supply.locked_quantity, 10)

        response = self.client.post('/process-management/action/', {
            'order_type': 'stockout', 'action': '伪造状态', 'selected': [order.pk],
        })
        self.assertRedirects(response, '/process-management/')
        order.refresh_from_db()
        self.assertEqual(order.status, '待审批')

    def test_process_approval_updates_inventory_and_stock_status(self):
        order = self._stockout_order()
        response = self.client.post('/process-management/action/', {
            'order_type': 'stockout', 'action': '已批准', 'selected': [order.pk],
        })
        self.assertRedirects(response, '/process-management/?type=stockout')
        order.refresh_from_db()
        self.supply.refresh_from_db()
        self.assertEqual(order.status, '已批准')
        self.assertEqual(self.supply.quantity, 10)
        self.assertEqual(self.supply.locked_quantity, 0)
        self.assertEqual(self.supply.status, '低库存')

    def test_approved_stockout_with_returns_cannot_be_deleted_or_reversed(self):
        order = self._stockout_order(status='已批准')
        ReturnApplication.objects.create(
            stockout_order=order, supply=self.supply, quantity=1,
            returner='测试人员', department=self.department, operator=self.admin,
            return_date='2026-01-01', status='已批准',
        )
        response = self.client.post('/process-management/delete/', {
            'order_type': 'stockout', 'selected': [order.pk],
        })
        self.assertRedirects(response, '/process-management/?type=stockout')
        self.assertTrue(StockOutOrder.objects.filter(pk=order.pk).exists())
        self.assertTrue(ReturnApplication.objects.filter(stockout_order=order).exists())

        response = self.client.post('/process-management/action/', {
            'order_type': 'stockout', 'action': '待审批', 'selected': [order.pk],
        })
        self.assertRedirects(response, '/process-management/?type=stockout')
        order.refresh_from_db()
        self.assertEqual(order.status, '已批准')

    def test_superuser_profile_uses_admin_role(self):
        self.assertEqual(self.admin.profile.role, 'admin')
        self.assertEqual(self.admin.profile.role_display, '管理员')


class ITDeviceModuleRemovalTests(TestCase):
    """IT设备管理模块必须不存在。"""

    def test_it_device_models_are_not_registered(self):
        model_names = {
            model.__name__
            for model in apps.get_app_config('inventory').get_models()
        }
        self.assertNotIn('ITDevice', model_names)
        self.assertNotIn('ComputerType', model_names)

    def test_it_device_routes_return_not_found(self):
        for path in (
            '/devices/',
            '/devices/create/',
            '/devices/export/',
            '/devices/import/',
            '/devices/template/',
            '/computer-types/',
            '/computer-types/create/',
        ):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 404)

    def test_it_device_tables_are_absent(self):
        from django.db import connection

        table_names = set(connection.introspection.table_names())
        self.assertNotIn('inventory_itdevice', table_names)
        self.assertNotIn('inventory_computertype', table_names)

    def test_it_device_permission_module_is_not_available(self):
        from inventory.models import RolePermission

        module_keys = {key for key, _ in RolePermission.MODULE_CHOICES}
        self.assertNotIn('it_device', module_keys)
