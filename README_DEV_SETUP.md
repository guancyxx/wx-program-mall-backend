# Development Environment Setup

This guide will help you set up the Django mall server for local development.

## Prerequisites

- Python 3.8+ 
- MySQL/MariaDB 8.0+
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

### 3. Database Cache Setup

The application now uses Django's database cache backend instead of Redis. The cache table will be created automatically during the setup process.

#### Cache Table Creation

The database cache table is created automatically when you run the setup script, but you can also create it manually:

```bash
# Create the cache table
python manage.py createcachetable mall_server_cache
```

### 4. Environment Configuration

```bash
# Copy environment template
cp .env.development.example .env.development

# Edit the configuration file
# Update database credentials and other settings
```

### 5. Automated Database Setup

```bash
# Run the automated setup script
python scripts/setup_dev_db.py
```

This script will:
- Create the development database
- Run all migrations
- Create the database cache table
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

# Create database cache table
python manage.py createcachetable mall_server_cache --settings=mall_server.settings.development

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

**Note:** Redis is no longer used in this application. If you see Redis-related errors, they may be from old configuration files or cached settings.

1. **Clear old configuration:**
   - Remove any Redis environment variables from `.env.development`
   - Restart the Django server

2. **Verify cache backend:**
   ```bash
   # Test cache functionality
   python manage.py shell
   >>> from django.core.cache import cache
   >>> cache.set('test_key', 'test_value', 30)
   >>> cache.get('test_key')
   'test_value'
   ```

### Cache Performance Issues

The application now uses database cache instead of Redis:

1. **Monitor cache table size:**
   ```sql
   SELECT COUNT(*) FROM mall_server_cache;
   ```

2. **Clear cache if needed:**
   ```bash
   python manage.py shell
   >>> from django.core.cache import cache
   >>> cache.clear()
   ```

3. **Optimize cache table:**
   ```sql
   OPTIMIZE TABLE mall_server_cache;
   ```

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
   # Start MySQL/MariaDB
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

## Docker Development Environment

For containerized development, you can use Docker Compose:

### Prerequisites

- Docker
- Docker Compose

### Setup

```bash
# Start the development environment
docker-compose -f docker-compose.dev.yml up -d

# The services will be available at:
# - Django app: http://localhost:8001
# - MySQL: localhost:3307
```

### Services

The Docker environment includes:

- **mysql-mall**: MySQL 8.0 database server
- **mall-server**: Django application server

**Note:** Redis service has been removed from the Docker configuration as it's no longer needed.

### Docker Commands

```bash
# Start services
docker-compose -f docker-compose.dev.yml up -d

# View logs
docker-compose -f docker-compose.dev.yml logs -f

# Stop services
docker-compose -f docker-compose.dev.yml down

# Rebuild and start
docker-compose -f docker-compose.dev.yml up --build -d

# Access Django container shell
docker-compose -f docker-compose.dev.yml exec mall-server bash

# Run Django commands in container
docker-compose -f docker-compose.dev.yml exec mall-server python manage.py migrate
docker-compose -f docker-compose.dev.yml exec mall-server python manage.py createcachetable mall_server_cache
```

## Production Deployment

For production deployment, use:
- `mall_server.settings.production`
- Proper database credentials
- SSL certificates
- Environment-specific configurations

See deployment documentation for details.