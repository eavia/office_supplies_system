from django.db import migrations, models
import django.db.models.deletion


def forward_fill_item_category(apps, schema_editor):
    SupplyCategory = apps.get_model('inventory', 'SupplyCategory')
    ItemCategory = apps.get_model('inventory', 'ItemCategory')
    OfficeSupply = apps.get_model('inventory', 'OfficeSupply')

    id_map = {}

    for sc in SupplyCategory.objects.all().order_by('id'):
        item = ItemCategory.objects.filter(code=sc.code).first()
        if not item:
            item = ItemCategory.objects.filter(name=sc.name, parent__isnull=True).first()
        if not item:
            item = ItemCategory.objects.create(
                code=sc.code,
                name=sc.name,
                parent=None,
                description=sc.description,
                sort_order=sc.sort_order,
                is_active=True,
            )
        id_map[sc.id] = item.id

    for supply in OfficeSupply.objects.exclude(category_id__isnull=True).iterator():
        target_id = id_map.get(supply.category_id)
        if target_id:
            supply.item_category_id = target_id
            supply.save(update_fields=['item_category'])


def backward_clear_item_category(apps, schema_editor):
    OfficeSupply = apps.get_model('inventory', 'OfficeSupply')
    OfficeSupply.objects.update(item_category_id=None)


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0003_itemcategory'),
    ]

    operations = [
        migrations.AddField(
            model_name='officesupply',
            name='item_category',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='supplies', to='inventory.itemcategory', verbose_name='物品分类'),
        ),
        migrations.RunPython(forward_fill_item_category, backward_clear_item_category),
    ]
