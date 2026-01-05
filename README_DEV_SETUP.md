# Development Environment Setup

This guide will help you set up the Django mall server for local development.

## Prerequisites

- Python 3.8+ 
- MySQL/MariaDB 8.0+
- Redis 6.0+
- Git

## Quick Setup

### 1. Clone and Setup Project

```bash
# Clone the repository (if not already done)
git clone <repository-url>
cd mall-server

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Database Setup

#### Install MySQL/MariaDB

**Windows:**
- Download and install MySQL from https://dev.mysql.com/downloads/mysql/
- Or install MariaDB from https://mariadb.org/download/

**macOS:**
```bash
brew install mysql
# or
brew install mariadb
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install mysql-server
# or
sudo apt install mariadb-server
```

#### Start Database Service

**Windows:** Start MySQL service from Services panel or MySQL Workbench

**macOS:**
```bash
brew services start mysql
# or
brew services start mariadb
```

**Ubuntu/Debian:**
```bash
sudo systemctl start mysql
# or
sudo systemctl start mariadb
```

### 3. Redis Setup

#### Install Redis

**Windows:**
- Download Redis from https://github.com/microsoftarchive/redis/releases
- Or use WSL with Linux instructions

**macOS:**
```bash
brew install redis
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install redis-server
```

#### Start Redis Service

**Windows:** Run redis-server.exe

**macOS:**
```bash
brew services start redis
```

**Ubuntu/Debian:**
```bash
sudo systemctl start redis-server
```

### 4. Environment Configuration

```bash
# Copy environment template
cp .env.development.example .env.development

# Edit the configuration file
# Update database credentials, Redis settings, etc.
```

### 5. Automated Database Setup

```bash
# Run the automated setup script
python scripts/setup_dev_db.py
```

This script will:
- Create the development database
- Run all migrations
- Set up initial membership tiers and points rules
- Create an admin superuser (admin/admin123)

### 6. Seed Sample Data (Optional)

```bash
# Add sample data for development
python scripts/seed_dev_data.py
```

This will create:
- Sample users with different membership tiers
- Product categories
- Sample products
- Initial points for users

### 7. Start Development Server

```bash
# Start the Django development server
python manage.py runserver

# The server will be available at http://localhost:8000
# Admin panel: http://localhost:8000/admin/
```

## Manual Setup (Alternative)

If you prefer manual setup or the automated script fails:

### 1. Create Database

```sql
-- Connect to MySQL/MariaDB as root
mysql -u root -p

-- Create database
CREATE DATABASE mall_server_dev CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Create user (optional)
CREATE USER 'mall_user'@'localhost' IDENTIFIED BY 'dev_password';
GRANT ALL PRIVILEGES ON mall_server_dev.* TO 'mall_user'@'localhost';
FLUSH PRIVILEGES;
```

### 2. Run Migrations

```bash
# Apply database migrations
python manage.py migrate --settings=mall_server.settings.development

# Set up initial data
python manage.py setup_test_data --settings=mall_server.settings.development

# Create superuser
python manage.py createsuperuser --settings=mall_server.settings.development
```

## Environment Variables

Key environment variables in `.env.development`:

```env
# Database
MYSQL_DATABASE=mall_server_dev
MYSQL_USER=root
MYSQL_PASSWORD=dev_password
MYSQL_HOST=localhost
MYSQL_PORT=3306

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=redis_password

# Django
DEBUG=True
SECRET_KEY=your-secret-key
ALLOWED_HOSTS=localhost,127.0.0.1

# WeChat (for testing)
WECHAT_APPID=your_wechat_appid
WECHAT_APPSECRET=your_wechat_appsecret
```

## Testing

```bash
# Run all tests
python manage.py test --settings=mall_server.settings.test

# Run specific test
python manage.py test tests.test_database_setup --settings=mall_server.settings.test

# Run with coverage
coverage run --source='.' manage.py test --settings=mall_server.settings.test
coverage report
```

## API Documentation

Once the server is running, you can access:

- **Admin Panel:** http://localhost:8000/admin/
- **API Root:** http://localhost:8000/api/
- **User APIs:** http://localhost:8000/api/users/
- **Product APIs:** http://localhost:8000/api/products/
- **Membership APIs:** http://localhost:8000/api/membership/

## Sample Users

After running the seed script, you can use these test accounts:

| Username | Password | Tier | Spending |
|----------|----------|------|----------|
| admin | admin123 | - | Admin user |
| bronze_user | password123 | Bronze | $500 |
| silver_user | password123 | Silver | $2,500 |
| gold_user | password123 | Gold | $10,000 |
| platinum_user | password123 | Platinum | $50,000 |

## Troubleshooting

### Database Connection Issues

1. **Check MySQL/MariaDB is running:**
   ```bash
   # Check service status
   sudo systemctl status mysql
   # or
   sudo systemctl status mariadb
   ```

2. **Verify credentials:**
   - Check `.env.development` file
   - Test connection: `mysql -u root -p`

3. **Check database exists:**
   ```sql
   SHOW DATABASES;
   ```

### Redis Connection Issues

1. **Check Redis is running:**
   ```bash
   redis-cli ping
   # Should return: PONG
   ```

2. **Check Redis configuration:**
   - Verify host, port, and password in `.env.development`

### Migration Issues

1. **Reset migrations (if needed):**
   ```bash
   # Delete migration files (keep __init__.py)
   find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
   find . -path "*/migrations/*.pyc" -delete
   
   # Recreate migrations
   python manage.py makemigrations
   python manage.py migrate
   ```

### Permission Issues

1. **Database permissions:**
   ```sql
   GRANT ALL PRIVILEGES ON mall_server_dev.* TO 'your_user'@'localhost';
   FLUSH PRIVILEGES;
   ```

## Development Workflow

1. **Start services:**
   ```bash
   # Start MySQL/MariaDB and Redis
   # Then start Django server
   python manage.py runserver
   ```

2. **Make changes:**
   - Edit models, views, etc.
   - Create migrations if models changed:
     ```bash
     python manage.py makemigrations
     python manage.py migrate
     ```

3. **Test changes:**
   ```bash
   python manage.py test
   ```

4. **Reset development data:**
   ```bash
   # Re-run seeding script
   python scripts/seed_dev_data.py
   ```

## Production Deployment

For production deployment, use:
- `mall_server.settings.production`
- Proper database credentials
- SSL certificates
- Environment-specific configurations

See deployment documentation for details.