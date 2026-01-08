#!/usr/bin/env python
"""
Update beef product content with HTML files from 牛肉 directory.

用法（在 mall-server 目录下执行）::

    python scripts/update_beef_html_content.py

脚本会：
- 扫描项目根目录下的 `牛肉/*.html` 文件
- 通过产品名称匹配数据库中的产品
- 更新产品的 content 字段为 HTML 内容
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import django

# ---------------------------------------------------------------------------
# Django 环境初始化
# ---------------------------------------------------------------------------

# 项目根目录：.../mall-server
THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parent

# 仓库根目录：上级目录（包含 mall-server、web、牛肉 等）
REPO_ROOT = PROJECT_ROOT.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mall_server.settings")
os.environ.setdefault('ENVIRONMENT', 'development')
django.setup()

from apps.products.models import Product, Category  # noqa: E402


def _read_html(path: Path) -> str:
    """读取HTML文件内容"""
    return path.read_text(encoding="utf-8")


def _extract_product_name_from_html(html_content: str) -> str:
    """从HTML中提取产品名称（从title或h1标签）"""
    # 尝试从title标签提取
    title_match = re.search(r'<title>(.*?)</title>', html_content, re.IGNORECASE | re.DOTALL)
    if title_match:
        title = title_match.group(1).strip()
        # 去掉"牛肉 · "前缀
        if "·" in title:
            return title.split("·")[-1].strip()
        return title
    
    # 尝试从h1标签提取
    h1_match = re.search(r'<h1>(.*?)</h1>', html_content, re.IGNORECASE | re.DOTALL)
    if h1_match:
        h1_text = h1_match.group(1).strip()
        # 去掉"牛肉 · "前缀
        if "·" in h1_text:
            return h1_text.split("·")[-1].strip()
        return h1_text
    
    return ""


def _extract_product_name_from_filename(html_path: Path) -> str:
    """从文件名提取产品名称"""
    # 例如: 01_匙仁_shiren.html -> 匙仁
    stem = html_path.stem
    # 去掉编号和英文后缀
    parts = stem.split('_')
    if len(parts) >= 2:
        return parts[1]  # 返回中文部分
    return stem


def discover_beef_htmls() -> list[Path]:
    """查找仓库根目录下 `牛肉` 目录内的所有 HTML 文件"""
    beef_dir = REPO_ROOT / "牛肉"
    if not beef_dir.exists():
        raise FileNotFoundError(f"未找到牛肉目录：{beef_dir}")
    return sorted(beef_dir.glob("*.html"))


def update_beef_products_with_html() -> None:
    """更新牛肉产品的HTML内容"""
    print("开始更新牛肉商品HTML内容...")
    
    html_files = discover_beef_htmls()
    if not html_files:
        print("未在 `牛肉` 目录下找到任何 HTML 文件，结束。")
        return
    
    # 获取牛肉分类
    try:
        category = Category.objects.get(name="牛肉")
    except Category.DoesNotExist:
        print("未找到'牛肉'分类，请先运行导入脚本创建分类")
        return
    
    updated_count = 0
    not_found_count = 0
    
    for html_path in html_files:
        html_content = _read_html(html_path)
        
        # 从HTML中提取产品名称
        product_name_from_html = _extract_product_name_from_html(html_content)
        # 从文件名提取产品名称作为备选
        product_name_from_file = _extract_product_name_from_filename(html_path)
        
        # 构建可能的匹配名称
        possible_names = []
        if product_name_from_html:
            possible_names.append(product_name_from_html)
            # 添加"牛肉 · "前缀的完整名称
            possible_names.append(f"牛肉 · {product_name_from_html}")
        if product_name_from_file:
            possible_names.append(product_name_from_file)
            possible_names.append(f"牛肉 · {product_name_from_file}")
        
        # 查找匹配的产品
        product = None
        for name in possible_names:
            try:
                product = Product.objects.get(name=name, category=category)
                break
            except Product.DoesNotExist:
                continue
            except Product.MultipleObjectsReturned:
                # 如果有多个同名产品，取第一个
                product = Product.objects.filter(name=name, category=category).first()
                break
        
        if not product:
            print(f"未找到匹配的产品: {html_path.name} (尝试的名称: {possible_names})")
            not_found_count += 1
            continue
        
        # 更新content字段
        product.content = html_content
        product.save(update_fields=['content'])
        updated_count += 1
        print(f"更新产品：{product.name} (ID: {product.id})")
    
    print("更新完成：")
    print(f"  成功更新：{updated_count} 条")
    if not_found_count > 0:
        print(f"  未找到匹配：{not_found_count} 条")


def main() -> None:
    try:
        update_beef_products_with_html()
    except Exception as exc:  # pragma: no cover - 简单脚本错误输出
        print(f"更新过程中出错：{exc}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()

