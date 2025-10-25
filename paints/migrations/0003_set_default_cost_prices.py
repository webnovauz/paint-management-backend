# Generated manually on 2025-10-24

from django.db import migrations
from decimal import Decimal


def set_default_cost_prices(apps, schema_editor):
    """Устанавливаем cost_price = selling_price * 0.7 для всех существующих красок"""
    Paint = apps.get_model('paints', 'Paint')
    
    for paint in Paint.objects.all():
        # Устанавливаем себестоимость как 70% от цены продажи
        paint.cost_price = paint.selling_price * Decimal('0.7')
        paint.save()


def reverse_set_default_cost_prices(apps, schema_editor):
    """Обратная операция - ничего не делаем"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('paints', '0002_auto_20251024_1209'),
    ]

    operations = [
        migrations.RunPython(
            set_default_cost_prices, 
            reverse_set_default_cost_prices
        ),
    ]