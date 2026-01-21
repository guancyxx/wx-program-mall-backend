#!/usr/bin/env python
"""
Script to convert existing data from yuan/kg to cents/grams
"""
import os
import sys
import django
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mall_server.settings')
sys.path.insert(0, '.')
django.setup()

from apps.products.models import Product
from apps.orders.models import Order, OrderItem

def convert_data():
    print('Converting product prices from yuan to cents...')
    products = Product.objects.all()
    for product in products:
        if isinstance(product.price, Decimal):
            product.price = int(product.price * 100)
        if product.dis_price and isinstance(product.dis_price, Decimal):
            product.dis_price = int(product.dis_price * 100)
        if isinstance(product.specification, Decimal):
            product.specification = int(product.specification * 1000)
        product.save()

    print('Converting order amounts from yuan to cents...')
    orders = Order.objects.all()
    for order in orders:
        if isinstance(order.amount, Decimal):
            order.amount = int(order.amount * 100)
        order.save()

    print('Converting order item prices and amounts from yuan to cents...')
    order_items = OrderItem.objects.all()
    for item in order_items:
        if isinstance(item.price, Decimal):
            item.price = int(item.price * 100)
        if isinstance(item.amount, Decimal):
            item.amount = int(item.amount * 100)
        item.save()

    print('Data conversion completed!')

if __name__ == '__main__':
    convert_data()
