# Models 拆分需求检查报告

## ❌ 发现的问题

根据 `.cursor/django/02-models.md` 规范要求：
> **原则**：每个模型必须独立成文件，通过 `models/__init__.py` 集中导出。

以下模块的 `models.py` 文件包含多个模型，需要拆分：

### 1. products/models.py (5个模型)
- `Category` - 产品分类
- `Product` - 产品
- `ProductImage` - 产品图片
- `ProductTag` - 产品标签
- `Banner` - 轮播图

**建议拆分结构**：
```
products/models/
├── __init__.py
├── category.py
├── product.py
├── product_image.py
├── product_tag.py
└── banner.py
```

### 2. users/models.py (2个模型)
- `User` - 用户
- `Address` - 地址

**建议拆分结构**：
```
users/models/
├── __init__.py
├── user.py
└── address.py
```

### 3. points/models.py (4个模型)
- `PointsAccount` - 积分账户
- `PointsRule` - 积分规则
- `PointsTransaction` - 积分交易
- `PointsExpiration` - 积分过期记录

**建议拆分结构**：
```
points/models/
├── __init__.py
├── account.py
├── rule.py
├── transaction.py
└── expiration.py
```

### 4. payments/models.py (5个模型)
- `PaymentMethod` - 支付方式
- `PaymentTransaction` - 支付交易
- `RefundRequest` - 退款请求
- `WeChatPayment` - 微信支付记录
- `PaymentCallback` - 支付回调记录

**建议拆分结构**：
```
payments/models/
├── __init__.py
├── payment_method.py
├── payment_transaction.py
├── refund_request.py
├── wechat_payment.py
└── payment_callback.py
```

### 5. orders/models.py (4个模型)
- `Order` - 订单
- `OrderItem` - 订单项
- `ReturnOrder` - 退货订单
- `OrderDiscount` - 订单折扣

**建议拆分结构**：
```
orders/models/
├── __init__.py
├── order.py
├── order_item.py
├── return_order.py
└── order_discount.py
```

## ✅ 已符合规范的模块

- **common/models/** - 已拆分 ✅
- **membership/models/** - 已拆分 ✅

## 📋 拆分计划

需要拆分的模块：
1. products (5个模型)
2. users (2个模型)
3. points (4个模型)
4. payments (5个模型)
5. orders (4个模型)

**总计：20个模型需要拆分**

## ⚠️ 注意事项

拆分后需要：
1. 创建 `models/` 目录结构
2. 创建 `models/__init__.py` 导出所有模型
3. 更新所有引用这些模型的导入语句
4. 删除旧的 `models.py` 文件
5. 确保所有外键引用使用字符串引用（如 `'ModelName'`）以避免循环导入

