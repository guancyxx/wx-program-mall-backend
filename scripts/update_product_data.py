#!/usr/bin/env python
"""
Update existing product data:
1. Generate random sold and views counts for products
2. Remove "建议定价区间" section from description field

用法（在 mall-server 目录下执行）::

    python scripts/update_product_data.py
"""

from __future__ import annotations

import os
import re
import sys
import random
from decimal import Decimal
from pathlib import Path

import django

# ---------------------------------------------------------------------------
# Django 环境初始化
# ---------------------------------------------------------------------------

# 项目根目录：.../mall-server
THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mall_server.settings")
os.environ.setdefault('ENVIRONMENT', 'development')
django.setup()

from apps.products.models import Product  # noqa: E402


def _remove_section(text: str, heading: str) -> str:
    """
    从文本中移除指定二级标题（如 '## 建议定价区间'）及其下面的内容，
    直到下一个同级标题或文末。
    """
    if not text:
        return text
    
    lines = text.splitlines()
    result_lines: list[str] = []
    skip_section = False
    for line in lines:
        if line.strip().startswith("## "):
            if skip_section:
                skip_section = False
            if line.strip().startswith(heading):
                skip_section = True
                continue
        if not skip_section:
            result_lines.append(line)
    return "\n".join(result_lines).strip()


def update_products():
    """更新所有产品的数据"""
    print("🚩 开始更新产品数据...")
    
    products = Product.objects.all()
    total = products.count()
    
    if total == 0:
        print("⚠ 未找到任何产品，结束。")
        return
    
    updated_sold = 0
    updated_views = 0
    updated_description = 0
    updated_price = 0
    updated_specification = 0
    
    for product in products:
        updated = False
        
        # 1. 更新规格：如果未设置，默认为1.0公斤
        if not hasattr(product, 'specification') or product.specification is None or product.specification == 0:
            product.specification = Decimal('1.0')
            updated_specification += 1
            updated = True
        
        # 2. 更新价格：当前price作为优惠价存入dis_price，原价（price * 1.2）存入price
        if product.dis_price is None or product.dis_price == 0:
            # 将当前price作为优惠价
            discount_price = product.price
            # 计算原价（提升20%）
            original_price = product.price * Decimal('1.2')
            product.price = original_price
            product.dis_price = discount_price
            updated_price += 1
            updated = True
        
        # 3. 更新sold和views（如果为0）
        if product.sold == 0:
            product.sold = random.randint(10, 500)
            updated_sold += 1
            updated = True
        
        if product.views == 0:
            product.views = random.randint(50, 2000)
            updated_views += 1
            updated = True
        
        # 4. 更新description，去掉建议定价区间
        if product.description:
            new_description = _remove_section(product.description, "## 建议定价区间")
            if new_description != product.description:
                product.description = new_description
                updated_description += 1
                updated = True
        
        if updated:
            product.save()
            print(f"✓ 更新产品：{product.name} (规格={product.specification}kg, 原价={product.price}, 优惠价={product.dis_price}, sold={product.sold}, views={product.views})")
    
    print("🎉 更新完成：")
    print(f"  总产品数：{total}")
    print(f"  更新规格：{updated_specification} 条")
    print(f"  更新价格：{updated_price} 条")
    print(f"  更新sold：{updated_sold} 条")
    print(f"  更新views：{updated_views} 条")
    print(f"  更新description：{updated_description} 条")


def main() -> None:
    try:
        update_products()
    except Exception as exc:  # pragma: no cover - 简单脚本错误输出
        print(f"✗ 更新过程中出错：{exc}")
        raise


if __name__ == "__main__":
    main()

