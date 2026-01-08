#!/usr/bin/env python
"""
Import beef products defined in markdown files under the project-level
`牛肉` directory into the Django `Product` / `ProductImage` tables.

用法（在 mall-server 目录下执行）::

    python scripts/import_beef_products.py

脚本会：
- 自动加载 Django 开发环境配置
- 在 `Category` 中创建/获取名称为「牛肉」的分类
- 扫描项目根目录下的 `牛肉/*.md` 文件
- 从 markdown 中提取：
  - 商品名称（标题行 `# 牛肉 · 匙仁` 等）
  - 商品简介（`## 商品简介` 段落）
  - 详细内容（整份 markdown 文本）
  - 价格区间（从「建议定价区间」中的人民币价格自动取区间平均值）
  - 对应图片（同名 `.jpg` 文件，如果存在，则写入 `ProductImage.image_url`）

注意：
- 价格区间解析失败时，价格会回退为 0。
- `gid` 采用基于文件名的稳定前缀，例如：`beef_01_匙仁_shiren`。
- 图片 URL 默认以 `/static/beef/<文件名>.jpg` 形式写入数据库，
  实际静态资源部署路径可按需要在前端或 Nginx 层做映射。
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable, List, Optional

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

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mall_server.settings.development")
django.setup()

from apps.products.models import Category, Product, ProductImage  # noqa: E402


@dataclass
class BeefProductData:
    """从 markdown 文件中解析出来的商品数据."""

    gid: str
    name: str
    price: Decimal
    dis_price: Optional[Decimal]
    description: str
    content: str
    image_filename: Optional[str]


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_title(text: str) -> str:
    """从 markdown 文本中提取标题行作为商品名."""
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("#"):
            # 去掉开头的 # 号及空格
            title = line.lstrip("#").strip()
            return title or "未命名牛肉商品"
    return "未命名牛肉商品"


def _extract_section(text: str, heading: str) -> str:
    """
    从 markdown 文本中提取指定二级标题（如 '## 商品简介'）下面的内容，
    直到下一个同级标题或文末。
    """
    lines = text.splitlines()
    content_lines: List[str] = []
    in_section = False
    for line in lines:
        if line.strip().startswith("## "):
            if in_section:
                break
            if line.strip().startswith(heading):
                in_section = True
                continue
        elif in_section:
            content_lines.append(line)
    return "\n".join(content_lines).strip()


def _parse_price_from_text(text: str) -> Decimal:
    """
    从「建议定价区间」文本中解析人民币价格，取区间平均值作为商品 price。

    例：
        - 散装零售：¥68–¥88 / 斤
        - 精修称重、精品包装：¥88–¥108 / 斤
    """
    # 提取所有形如 ¥68、¥88.5 的数字
    prices = re.findall(r"¥\s*([\d]+(?:\.\d+)?)", text)
    if not prices:
        return Decimal("0")

    decimals: List[Decimal] = []
    for p in prices:
        try:
            decimals.append(Decimal(p))
        except InvalidOperation:
            continue

    if not decimals:
        return Decimal("0")

    if len(decimals) == 1:
        return decimals[0]

    # 多个价格时，取最小值和最大值的平均
    min_p = min(decimals)
    max_p = max(decimals)
    return (min_p + max_p) / 2


def _build_gid_from_path(md_path: Path) -> str:
    """
    基于文件名构造稳定的 gid，例如：
    '01_匙仁_shiren.md' -> 'beef_01_匙仁_shiren'
    """
    stem = md_path.stem  # 不含扩展名
    # 替换空白为下划线，保持中文不变
    normalized = re.sub(r"\s+", "_", stem)
    return f"beef_{normalized}"


def parse_beef_markdown(md_path: Path) -> BeefProductData:
    """将单个牛肉 markdown 文件解析为 BeefProductData."""
    text = _read_text(md_path)

    title = _extract_title(text)
    description = _extract_section(text, "## 商品简介")
    if not description:
        # 退化为整篇内容前几行
        description = "\n".join(text.splitlines()[0:5]).strip()

    # 价格：查找「建议定价区间」段落
    price_section = _extract_section(text, "## 建议定价区间")
    price = _parse_price_from_text(price_section) if price_section else Decimal("0")

    gid = _build_gid_from_path(md_path)

    # 同名 jpg 作为主图
    image_filename = md_path.with_suffix(".jpg").name
    image_file = md_path.with_suffix(".jpg")
    if not image_file.exists():
        image_filename = None

    return BeefProductData(
        gid=gid,
        name=title,
        price=price,
        dis_price=None,
        description=description,
        content=text,
        image_filename=image_filename,
    )


def discover_beef_markdowns() -> Iterable[Path]:
    """
    查找仓库根目录下 `牛肉` 目录内的所有 markdown 文件。
    """
    beef_dir = REPO_ROOT / "牛肉"
    if not beef_dir.exists():
        raise FileNotFoundError(f"未找到牛肉目录：{beef_dir}")
    return sorted(beef_dir.glob("*.md"))


def import_beef_products() -> None:
    """主导入逻辑：创建牛肉分类，逐个导入商品和图片."""
    print("🚩 开始导入牛肉商品...")
    md_files = list(discover_beef_markdowns())
    if not md_files:
        print("⚠ 未在 `牛肉` 目录下找到任何 markdown 文件，结束。")
        return

    # 分类：牛肉
    category, _ = Category.objects.get_or_create(name="牛肉")

    created_count = 0
    updated_count = 0

    for md_path in md_files:
        data = parse_beef_markdown(md_path)

        # Product 基本信息
        product_defaults = {
            "name": data.name,
            "price": data.price,
            "dis_price": data.dis_price,
            "description": data.description,
            "content": data.content,
            "status": 1,
            "has_top": 0,
            "has_recommend": 0,
            "inventory": 0,
            "sold": 0,
            "views": 0,
            "category": category,
        }

        product, created = Product.objects.update_or_create(
            gid=data.gid,
            defaults=product_defaults,
        )

        if created:
            created_count += 1
            print(f"✓ 创建商品：{product.name} (gid={product.gid}, 价格={product.price})")
        else:
            updated_count += 1
            print(f"✓ 更新商品：{product.name} (gid={product.gid}, 价格={product.price})")

        # 处理主图
        if data.image_filename:
            # 这里仅在数据库中写入 URL，实际文件部署交由前端/运维配置
            image_url = f"/static/beef/{data.image_filename}"

            # 删除已存在的主图，避免重复
            ProductImage.objects.filter(product=product, is_primary=True).delete()

            ProductImage.objects.create(
                product=product,
                image_url=image_url,
                is_primary=True,
                order=0,
            )
            print(f"  ↳ 绑定主图：{image_url}")
        else:
            print("  ↳ 未找到对应 jpg 图片，跳过主图绑定。")

    print("🎉 导入完成：")
    print(f"  新建商品：{created_count} 条")
    print(f"  更新商品：{updated_count} 条")


def main() -> None:
    try:
        import_beef_products()
    except Exception as exc:  # pragma: no cover - 简单脚本错误输出
        print(f"✗ 导入过程中出错：{exc}")
        raise


if __name__ == "__main__":
    main()



