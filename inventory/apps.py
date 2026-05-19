from django.apps import AppConfig


class InventoryConfig(AppConfig):
    name = 'inventory'

    def ready(self):
        # 自动初始化内置角色（首次启动或数据库重建时）
        from inventory.permissions import init_builtin_roles
        try:
            init_builtin_roles()
        except Exception:
            pass  # 数据库尚未迁移时静默跳过
