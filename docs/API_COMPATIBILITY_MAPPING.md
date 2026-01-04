# API Compatibility Mapping: Node.js to Django

This document maps the existing Node.js/Koa API endpoints to their Django REST Framework equivalents, ensuring frontend compatibility during the migration.

## User Management APIs

### Authentication Endpoints

| Node.js Endpoint | Django Endpoint | Method | Description | Status |
|------------------|-----------------|--------|-------------|---------|
| `/api/users/login` | `/api/users/login/` | POST | WeChat OAuth login | ✅ Implemented |
| `/api/users/passwordLogin` | `/api/users/password-login/` | POST | Password-based login | ✅ Implemented |
| `/api/users/register` | `/api/users/register/` | POST | User registration | ✅ Implemented |

### User Profile Endpoints

| Node.js Endpoint | Django Endpoint | Method | Description | Status |
|------------------|-----------------|--------|-------------|---------|
| `/api/users/getUserInfo` | `/api/users/profile/` | GET | Get user information | ✅ Implemented |
| `/api/users/modifyInfo` | `/api/users/profile/` | PUT | Update user profile | ✅ Implemented |
| `/api/users/uploaderImg` | `/api/users/upload-avatar/` | POST | Upload avatar image | ✅ Implemented |

### Address Management Endpoints

| Node.js Endpoint | Django Endpoint | Method | Description | Status |
|------------------|-----------------|--------|-------------|---------|
| `/api/users/addAddress` | `/api/users/addresses/` | POST | Add/Update address | ✅ Implemented |
| `/api/users/deteleAddress` | `/api/users/addresses/{id}/` | DELETE | Delete address | ✅ Implemented |

## Product Management APIs

### Product Listing Endpoints

| Node.js Endpoint | Django Endpoint | Method | Description | Status |
|------------------|-----------------|--------|-------------|---------|
| `/api/goods/getGoodslist` | `/api/products/` | GET | Get product list (public) | ✅ Implemented |
| `/api/goods/getGoodsDetail` | `/api/products/{gid}/` | GET | Get product details | ✅ Implemented |
| `/api/goods/adminGetGoodslist` | `/api/products/admin/` | GET | Admin product list | ✅ Implemented |

### Product Management Endpoints

| Node.js Endpoint | Django Endpoint | Method | Description | Status |
|------------------|-----------------|--------|-------------|---------|
| `/api/goods/create` | `/api/products/` | POST | Create product (admin) | ✅ Implemented |
| `/api/goods/updateGoods` | `/api/products/{gid}/` | PUT | Update product (admin) | ✅ Implemented |

## Order Management APIs

### Order Processing Endpoints

| Node.js Endpoint | Django Endpoint | Method | Description | Status |
|------------------|-----------------|--------|-------------|---------|
| `/api/order/createOrder` | `/api/orders/` | POST | Create new order | ✅ Implemented |
| `/api/order/getMyOrder` | `/api/orders/` | GET | Get user's orders | ✅ Implemented |
| `/api/order/getOrderDetail` | `/api/orders/{roid}/` | GET | Get order details | ✅ Implemented |
| `/api/order/cancelOrder` | `/api/orders/{roid}/cancel/` | POST | Cancel order | ✅ Implemented |
| `/api/order/againPay` | `/api/orders/{roid}/retry-payment/` | POST | Retry payment | ✅ Implemented |
| `/api/order/refund` | `/api/orders/{roid}/refund/` | POST | Request refund | ✅ Implemented |

### Payment Endpoints

| Node.js Endpoint | Django Endpoint | Method | Description | Status |
|------------------|-----------------|--------|-------------|---------|
| `/api/order/getPayStatus` | `/api/payments/{roid}/status/` | GET | Check payment status | ✅ Implemented |
| `/api/order/callback` | `/api/payments/wechat-callback/` | POST | WeChat payment callback | ✅ Implemented |

## Response Format Compatibility

### Standard Success Response
```json
{
  "code": 200,
  "msg": "Success message",
  "data": {
    // Response data
  }
}
```

### Standard Error Response
```json
{
  "code": 40001,
  "msg": "Error message",
  "data": null
}
```

### Authentication Response
```json
{
  "code": 200,
  "msg": "登陆成功",
  "data": {
    "token": "jwt_token_here",
    "uid": 1001,
    "nickName": "User Name",
    "phone": "13800138000",
    "avatar": "avatar_url",
    "roles": 1,
    "address": []
  }
}
```

## Field Mapping

### User Model Field Mapping

| Node.js Field | Django Field | Type | Notes |
|---------------|--------------|------|-------|
| `uid` | `id` | Integer | Primary key |
| `nickName` | `username` | String | Display name |
| `openId` | `wechat_openid` | String | WeChat OpenID |
| `session_key` | `wechat_session_key` | String | WeChat session key |
| `createTime` | `date_joined` | DateTime | Account creation |
| `lastLoginTime` | `last_login` | DateTime | Last login time |
| `address` | `addresses` | Array/Relation | Address list |

### Product Model Field Mapping

| Node.js Field | Django Field | Type | Notes |
|---------------|--------------|------|-------|
| `gid` | `gid` | String | Product ID (preserved) |
| `disPrice` | `dis_price` | Decimal | Discount price |
| `hasTop` | `has_top` | Integer | Pinned status |
| `hasRecommend` | `has_recommend` | Integer | Recommended status |
| `createTime` | `create_time` | DateTime | Creation time |
| `updateTime` | `update_time` | DateTime | Update time |
| `images` | `images` (relation) | Array/Relation | Product images |
| `tags` | `product_tags` (relation) | Array/Relation | Product tags |

### Order Model Field Mapping

| Node.js Field | Django Field | Type | Notes |
|---------------|--------------|------|-------|
| `roid` | `roid` | String | Order ID (preserved) |
| `payTime` | `pay_time` | DateTime | Payment time |
| `sendTime` | `send_time` | DateTime | Shipping time |
| `refundInfo` | `refund_info` | JSON | Refund information |
| `lockTimeout` | `lock_timeout` | DateTime | Payment timeout |
| `cancelText` | `cancel_text` | String | Cancellation reason |
| `verifyTime` | `verify_time` | DateTime | Verification time |
| `verifyStatus` | `verify_status` | Integer | Verification status |
| `goods` | `items` (relation) | Array/Relation | Order items |

## Backward Compatibility Features

### 1. Response Format Wrapper
All Django API responses are wrapped in the Node.js format using a custom renderer:

```python
class NodeJSCompatibilityRenderer(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        if renderer_context and renderer_context.get('response'):
            response = renderer_context['response']
            if response.status_code >= 400:
                # Error response
                return super().render({
                    'code': response.status_code * 100 + 1,  # Convert to Node.js error codes
                    'msg': data.get('detail', 'Error occurred'),
                    'data': None
                }, accepted_media_type, renderer_context)
            else:
                # Success response
                return super().render({
                    'code': 200,
                    'msg': 'ok',
                    'data': data
                }, accepted_media_type, renderer_context)
        return super().render(data, accepted_media_type, renderer_context)
```

### 2. URL Compatibility Layer
Django URLs are configured to match Node.js patterns:

```python
# urls.py
urlpatterns = [
    # User endpoints
    path('api/users/login/', UserLoginView.as_view(), name='user-login'),
    path('api/users/passwordLogin/', PasswordLoginView.as_view(), name='password-login'),
    path('api/users/register/', UserRegistrationView.as_view(), name='user-register'),
    path('api/users/getUserInfo/', UserProfileView.as_view(), name='user-profile'),
    path('api/users/modifyInfo/', UserProfileView.as_view(), name='user-profile-update'),
    
    # Product endpoints
    path('api/goods/getGoodslist/', ProductListView.as_view(), name='product-list'),
    path('api/goods/getGoodsDetail/', ProductDetailView.as_view(), name='product-detail'),
    
    # Order endpoints
    path('api/order/createOrder/', OrderCreateView.as_view(), name='order-create'),
    path('api/order/getMyOrder/', OrderListView.as_view(), name='order-list'),
]
```

### 3. Authentication Compatibility
JWT tokens maintain the same format and structure:

```python
def generate_token(user):
    payload = {
        'users': {
            'uid': user.id
        }
    }
    return jwt.encode(payload, 'tokenTp', algorithm='HS256')
```

### 4. WeChat Integration Compatibility
WeChat API integration maintains the same flow and response handling as the Node.js implementation.

## Migration Testing Checklist

- [ ] All existing API endpoints return expected response format
- [ ] JWT token authentication works with existing tokens
- [ ] WeChat OAuth flow functions correctly
- [ ] Payment callback handling works with WeChat Pay
- [ ] File upload (avatar) maintains same URL structure
- [ ] Error responses match Node.js error codes
- [ ] Pagination parameters work as expected
- [ ] Search and filtering maintain same behavior
- [ ] Order status transitions match Node.js logic
- [ ] Address management preserves array structure in responses

## Breaking Changes (If Any)

### Minor Changes
1. **Date Format**: Django uses ISO 8601 format by default, but compatibility layer converts to Node.js format
2. **Decimal Precision**: Django Decimal fields may have slightly different precision handling
3. **File URLs**: Avatar and image URLs may have different base paths (handled by compatibility layer)

### Mitigation Strategies
1. **Response Serializers**: Custom serializers ensure exact field name and format matching
2. **URL Rewriting**: Middleware handles any URL path differences
3. **Data Validation**: Input validation matches Node.js validation rules
4. **Error Handling**: Custom exception handlers return Node.js-compatible error responses

## Frontend Integration Notes

### No Changes Required
The frontend application should work without any modifications when connecting to the Django backend, as all endpoints maintain the same:
- URL patterns
- Request/response formats
- Authentication mechanisms
- Error handling
- Data structures

### Testing Recommendations
1. **Automated Testing**: Run existing frontend test suite against Django backend
2. **Manual Testing**: Test critical user flows (login, purchase, payment)
3. **Performance Testing**: Ensure response times are comparable
4. **WeChat Integration**: Test WeChat mini-program integration thoroughly
5. **Payment Flow**: Verify WeChat Pay integration works end-to-end