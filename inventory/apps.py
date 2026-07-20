from django.apps import AppConfig
from django.db.models.signals import post_migrate


class InventoryConfig(AppConfig):
    name = 'inventory'

    def ready(self):
        # Run role setup after migrations instead of querying during app loading.
        post_migrate.connect(self.initialize_builtin_roles, sender=self)

    @staticmethod
    def initialize_builtin_roles(**kwargs):
        from inventory.permissions import init_builtin_roles
        init_builtin_roles()
