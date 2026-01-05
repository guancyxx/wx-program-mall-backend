from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('orders', '0002_initial'),
    ]

    operations = [
        # First, remove existing fields that conflict
        migrations.RemoveField(
            model_name='order',
            name='created_at',
        ),
        migrations.RemoveField(
            model_name='order',
            name='order_number',
        ),
        migrations.RemoveField(
            model_name='order',
            name='total_amount',
        ),
        migrations.RemoveField(
            model_name='order',
            name='updated_at',
        ),
        migrations.RemoveField(
            model_name='order',
            name='user',
        ),
        
        # Create new models
        migrations.CreateModel(
            name='OrderDiscount',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('discount_type', models.CharField(choices=[('tier_discount', 'Membership Tier Discount'), ('points_redemption', 'Points Redemption'), ('free_shipping', 'Free Shipping'), ('promotion', 'Promotional Discount')], max_length=20)),
                ('discount_amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('description', models.CharField(help_text='Discount description', max_length=200)),
                ('discount_details', models.JSONField(default=dict, help_text='Additional discount information')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'order_discounts',
            },
        ),
        migrations.CreateModel(
            name='OrderItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rrid', models.CharField(help_text='Return order ID', max_length=50, unique=True)),
                ('gid', models.CharField(help_text='Product/Goods ID', max_length=50)),
                ('quantity', models.IntegerField(help_text='Quantity ordered')),
                ('price', models.DecimalField(decimal_places=2, help_text='Unit price', max_digits=10)),
                ('amount', models.DecimalField(decimal_places=2, help_text='Line total (quantity * price)', max_digits=10)),
                ('is_return', models.BooleanField(default=False, help_text='Whether item has been returned')),
                ('product_info', models.JSONField(default=dict, help_text='Product details snapshot')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'order_items',
            },
        ),
        migrations.CreateModel(
            name='ReturnOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rrid', models.CharField(help_text='Return order ID', max_length=50, unique=True)),
                ('gid', models.CharField(help_text='Product/Goods ID', max_length=50)),
                ('roid', models.CharField(help_text='Original order ID', max_length=50)),
                ('amount', models.DecimalField(decimal_places=2, help_text='Return amount', max_digits=10)),
                ('refund_amount', models.DecimalField(decimal_places=2, help_text='Refundable amount', max_digits=10)),
                ('status', models.IntegerField(default=-1, help_text='Return status: -1=pending, 1=completed')),
                ('create_time', models.DateTimeField(default=django.utils.timezone.now)),
                ('openid', models.CharField(help_text='WeChat OpenID for refunds', max_length=100)),
            ],
            options={
                'db_table': 'return_orders',
            },
        ),
        
        # Update Order model
        migrations.AlterModelOptions(
            name='order',
            options={'ordering': ['-create_time']},
        ),
        
        # Add new fields to Order with proper defaults
        migrations.AddField(
            model_name='order',
            name='roid',
            field=models.CharField(help_text='Order ID from Node.js', max_length=50, unique=True, default='temp_roid'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='order',
            name='uid',
            field=models.ForeignKey(db_column='uid', help_text='User ID', on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, default=1),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='order',
            name='lid',
            field=models.IntegerField(blank=True, help_text='Live/Store ID for pickup orders', null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='create_time',
            field=models.DateTimeField(default=django.utils.timezone.now, help_text='Order creation time'),
        ),
        migrations.AddField(
            model_name='order',
            name='pay_time',
            field=models.DateTimeField(blank=True, help_text='Payment completion time', null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='send_time',
            field=models.DateTimeField(blank=True, help_text='Shipping time', null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='amount',
            field=models.DecimalField(decimal_places=2, help_text='Total order amount', max_digits=10, default=0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='order',
            name='refund_info',
            field=models.JSONField(default=dict, help_text='Refund information: reason, applyTime'),
        ),
        migrations.AddField(
            model_name='order',
            name='openid',
            field=models.CharField(help_text='WeChat OpenID for refunds', max_length=100, default=''),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='order',
            name='type',
            field=models.IntegerField(choices=[(1, 'Store Pickup'), (2, 'Delivery')], default=2, help_text='Order type: 1=pickup, 2=delivery'),
        ),
        migrations.AddField(
            model_name='order',
            name='logistics',
            field=models.JSONField(default=dict, help_text='Logistics info: company, number, code'),
        ),
        migrations.AddField(
            model_name='order',
            name='remark',
            field=models.TextField(blank=True, default='', help_text='Order remarks'),
        ),
        migrations.AddField(
            model_name='order',
            name='address',
            field=models.JSONField(default=dict, help_text='Delivery address information'),
        ),
        migrations.AddField(
            model_name='order',
            name='lock_timeout',
            field=models.DateTimeField(blank=True, help_text='Payment timeout', null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='cancel_text',
            field=models.CharField(blank=True, default='', help_text='Cancellation reason', max_length=200),
        ),
        migrations.AddField(
            model_name='order',
            name='qrcode',
            field=models.URLField(blank=True, default='', help_text='QR code for order verification'),
        ),
        migrations.AddField(
            model_name='order',
            name='verify_time',
            field=models.DateTimeField(blank=True, help_text='Verification time', null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='verify_status',
            field=models.IntegerField(default=0, help_text='Verification status: 0=not verified, 1=verified'),
        ),
        
        # Update status field
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.IntegerField(choices=[(-1, 'Pending Payment'), (1, 'Paid'), (2, 'Shipped'), (3, 'Delivered'), (4, 'Refunded'), (5, 'Cancelled'), (6, 'Partial Refund'), (7, 'Verified')], default=-1, help_text='Order status'),
        ),
        
        # Add foreign key relationships
        migrations.AddField(
            model_name='returnorder',
            name='uid',
            field=models.ForeignKey(db_column='uid', on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='orderitem',
            name='order',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='orders.order'),
        ),
        migrations.AddField(
            model_name='orderdiscount',
            name='order',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='discounts', to='orders.order'),
        ),
        
        # Add indexes
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['uid'], name='orders_uid_ee5d7e_idx'),
        ),
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['status'], name='orders_status_762191_idx'),
        ),
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['roid'], name='orders_roid_75bbb7_idx'),
        ),
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['lid'], name='orders_lid_01cb23_idx'),
        ),
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['create_time'], name='orders_create__b2faac_idx'),
        ),
        migrations.AddIndex(
            model_name='returnorder',
            index=models.Index(fields=['uid'], name='return_orde_uid_680755_idx'),
        ),
        migrations.AddIndex(
            model_name='returnorder',
            index=models.Index(fields=['gid'], name='return_orde_gid_5fa6a8_idx'),
        ),
        migrations.AddIndex(
            model_name='returnorder',
            index=models.Index(fields=['status'], name='return_orde_status_c2c3bb_idx'),
        ),
        migrations.AddIndex(
            model_name='returnorder',
            index=models.Index(fields=['roid'], name='return_orde_roid_3301cf_idx'),
        ),
        migrations.AddIndex(
            model_name='returnorder',
            index=models.Index(fields=['rrid'], name='return_orde_rrid_552647_idx'),
        ),
        migrations.AddIndex(
            model_name='orderitem',
            index=models.Index(fields=['order'], name='order_items_order_i_26ad88_idx'),
        ),
        migrations.AddIndex(
            model_name='orderitem',
            index=models.Index(fields=['gid'], name='order_items_gid_eeaca6_idx'),
        ),
        migrations.AddIndex(
            model_name='orderitem',
            index=models.Index(fields=['rrid'], name='order_items_rrid_961dcf_idx'),
        ),
        migrations.AddIndex(
            model_name='orderdiscount',
            index=models.Index(fields=['order'], name='order_disco_order_i_033612_idx'),
        ),
        migrations.AddIndex(
            model_name='orderdiscount',
            index=models.Index(fields=['discount_type'], name='order_disco_discoun_01bdeb_idx'),
        ),
    ]
