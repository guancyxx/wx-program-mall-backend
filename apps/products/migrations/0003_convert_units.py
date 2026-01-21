from django.db import migrations, models
from decimal import Decimal


def convert_product_units(apps, schema_editor):
    """Convert product prices from yuan to cents, specification from kg to grams"""
    Product = apps.get_model('products', 'Product')

    for product in Product.objects.all():
        # Convert price from yuan to cents
        if isinstance(product.price, Decimal):
            product.price = int(product.price * 100)

        # Convert dis_price from yuan to cents
        if product.dis_price and isinstance(product.dis_price, Decimal):
            product.dis_price = int(product.dis_price * 100)

        # Convert specification from kg to grams
        if isinstance(product.specification, Decimal):
            product.specification = int(product.specification * 1000)

        product.save()


def convert_order_units(apps, schema_editor):
    """Convert order amounts from yuan to cents"""
    Order = apps.get_model('orders', 'Order')
    OrderItem = apps.get_model('orders', 'OrderItem')

    for order in Order.objects.all():
        # Convert amount from yuan to cents
        if isinstance(order.amount, Decimal):
            order.amount = int(order.amount * 100)
        order.save()

    for item in OrderItem.objects.all():
        # Convert price and amount from yuan to cents
        if isinstance(item.price, Decimal):
            item.price = int(item.price * 100)
        if isinstance(item.amount, Decimal):
            item.amount = int(item.amount * 100)
        item.save()


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0002_productimage_producttag_and_more'),
        ('orders', '0003_auto_20260104_2047'),
    ]

    operations = [
        # First, alter the field types
        migrations.AlterField(
            model_name='product',
            name='price',
            field=models.IntegerField(help_text='Product price in cents'),
        ),
        migrations.AlterField(
            model_name='product',
            name='dis_price',
            field=models.IntegerField(null=True, blank=True, help_text='Discount price in cents (disPrice in Node.js)'),
        ),
        migrations.AlterField(
            model_name='product',
            name='specification',
            field=models.IntegerField(default=1000, help_text='Product specification in grams (规格，单位：克)'),
        ),
        migrations.AlterField(
            model_name='order',
            name='amount',
            field=models.IntegerField(help_text='Total order amount in cents'),
        ),
        migrations.AlterField(
            model_name='orderitem',
            name='price',
            field=models.IntegerField(help_text='Unit price in cents'),
        ),
        migrations.AlterField(
            model_name='orderitem',
            name='amount',
            field=models.IntegerField(help_text='Line total in cents (quantity * price)'),
        ),

        # Then, run data conversion
        migrations.RunPython(convert_product_units, migrations.RunPython.noop),
        migrations.RunPython(convert_order_units, migrations.RunPython.noop),
    ]
