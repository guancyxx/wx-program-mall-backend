# Mall Server - 开发环境设置指南

## 概述

Mall Server 是一个基于 Django 的电商系统，具有完整的会员管理功能。本指南将帮助您设置开发环境。

## 系统要求

- Python 3.11+
- Docker & Docker Compose
- MySQL 8.0+ (通过 Docker 提供)
- Redis (通过 Docker 提供)

## 快速开始

### 1. 克隆项目并进入目录

```bash
cd applications/Fresher/mall-server
```

### 2. 创建虚拟环境 (推荐)

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

复制 `.env.development` 文件并根据需要修改配置：

```bash
cp .env.development .env
```

### 5. 启动开发环境

#### 方式一：使用启动脚本 (推荐)

**Windows:**
```cmd
scripts\start_dev.bat
```

**Linux/Mac:**
```bash
chmod +x scripts/start_dev.sh
./scripts/start_dev.sh
```

#### 方式二：手动启动

1. 启动 Docker 服务：
```bash
docker-compose -f docker-compose.dev.yml up -d mysql-mall redis-mall
```

2. 设置数据库：
```bash
python scripts/setup_dev_db.py
```

3. 运行迁移：
```bash
python manage.py migrate --settings=mall_server.settings.development
```

4. 创建超级用户 (可选)：
```bash
python manage.py createsuperuser --settings=mall_server.settings.development
```

5. 启动开发服务器：
```bash
python manage.py runserver 0.0.0.0:8001 --settings=mall_server.settings.development
```

## 访问应用

- **主应用**: http://localhost:8001
- **管理后台**: http://localhost:8001/admin/
- **API 文档**: http://localhost:8001/api/docs/
- **MySQL**: localhost:3307 (用户: root, 密码: dev_password)
- **Redis**: localhost:6380 (密码: redis_dev_password)

## 默认管理员账号

- **手机号**: 13800000000
- **密码**: admin123456

## 项目结构

```
mall-server/
├── apps/                          # Django 应用目录
│   ├── users/                     # 用户管理
│   ├── membership/                # 会员系统
│   ├── products/                  # 商品管理
│   ├── orders/                    # 订单管理
│   ├── payments/                  # 支付系统
│   ├── points/                    # 积分系统
│   └── common/                    # 公共组件
├── mall_server/                   # Django 项目配置
│   ├── settings/                  # 分环境配置
│   │   ├── base.py               # 基础配置
│   │   ├── development.py        # 开发环境配置
│   │   └── production.py         # 生产环境配置
│   ├── urls.py                   # URL 配置
│   └── wsgi.py                   # WSGI 配置
├── scripts/                       # 脚本目录
│   ├── setup_dev_db.py          # 数据库初始化脚本
│   ├── start_dev.sh              # Linux/Mac 启动脚本
│   └── start_dev.bat             # Windows 启动脚本
├── utils/                         # 工具函数
├── requirements.txt               # Python 依赖
├── docker-compose.dev.yml        # 开发环境 Docker 配置
└── .env.development              # 开发环境变量
```

## 开发工作流

### 1. 创建新的 Django 应用

```bash
python manage.py startapp new_app apps/
```

### 2. 数据库迁移

```bash
# 创建迁移文件
python manage.py makemigrations --settings=mall_server.settings.development

# 应用迁移
python manage.py migrate --settings=mall_server.settings.development
```

### 3. 运行测试

```bash
# 运行所有测试
python manage.py test --settings=mall_server.settings.development

# 运行特定应用的测试
python manage.py test apps.users --settings=mall_server.settings.development

# 运行覆盖率测试
coverage run --source='.' manage.py test --settings=mall_server.settings.development
coverage report
```

### 4. 代码质量检查

```bash
# 安装开发依赖
pip install flake8 black isort

# 代码格式化
black .
isort .

# 代码检查
flake8 .
```

## API 开发

### 1. API 端点

所有 API 端点都以 `/api/` 开头：

- `/api/users/` - 用户管理
- `/api/membership/` - 会员系统
- `/api/products/` - 商品管理
- `/api/orders/` - 订单管理
- `/api/payments/` - 支付系统
- `/api/points/` - 积分系统

### 2. 认证

系统使用 JWT 认证，需要在请求头中包含：

```
Authorization: Bearer <token>
```

### 3. API 文档

访问 http://localhost:8001/api/docs/ 查看完整的 API 文档。

## 数据库管理

### 1. 连接数据库

```bash
# 使用 MySQL 客户端
mysql -h localhost -P 3307 -u root -p
# 密码: dev_password

# 使用 Django shell
python manage.py shell --settings=mall_server.settings.development
```

### 2. 数据库备份和恢复

```bash
# 备份
mysqldump -h localhost -P 3307 -u root -p mall_server_dev > backup.sql

# 恢复
mysql -h localhost -P 3307 -u root -p mall_server_dev < backup.sql
```

## 故障排除

### 1. 数据库连接问题

- 确保 Docker 服务正在运行
- 检查端口 3307 是否被占用
- 验证 `.env.development` 中的数据库配置

### 2. Redis 连接问题

- 确保 Redis 容器正在运行
- 检查端口 6380 是否被占用
- 验证 Redis 密码配置

### 3. 依赖安装问题

```bash
# 清理并重新安装依赖
pip cache purge
pip install --no-cache-dir -r requirements.txt
```

### 4. 权限问题 (Linux/Mac)

```bash
# 给脚本执行权限
chmod +x scripts/start_dev.sh
chmod +x scripts/setup_dev_db.py
```

## 贡献指南

1. 创建功能分支
2. 编写测试
3. 确保代码质量检查通过
4. 提交 Pull Request

## 支持

如有问题，请查看：

1. 项目文档
2. Django 官方文档
3. 创建 Issue

---

**注意**: 这是开发环境配置，不适用于生产环境。生产环境请参考 `README_PROD.md`。