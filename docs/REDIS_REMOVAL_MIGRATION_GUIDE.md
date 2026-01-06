# Redis Removal Migration Guide

## Overview

This guide provides step-by-step instructions for migrating from Redis-based caching to database-based caching in the Django mall-server project. The migration removes Redis dependencies to simplify the infrastructure and reduce deployment complexity.

## Migration Summary

### What's Being Removed
- Redis cache backend
- Celery task queue configuration (unused)
- Redis-related Python packages
- Redis Docker service
- Redis environment variables

### What's Being Added
- Database cache backend using MySQL
- Cache table (`mall_server_cache`)
- Updated environment configurations
- Simplified Docker Compose setup

## Pre-Migration Checklist

Before starting the migration, ensure you have:

- [ ] Backup of current database
- [ ] Backup of current environment files
- [ ] Access to update Docker containers
- [ ] Understanding of current cache usage (if any)
- [ ] Coordination with team members

## Step-by-Step Migration Process

### Step 1: Update Git Repository

```bash
# Pull the latest changes with Redis removal
git pull origin main

# Check the current branch
git status
```

### Step 2: Update Python Dependencies

```bash
# Activate your virtual environment
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate     # Windows

# Update dependencies (Redis packages removed)
pip install -r requirements.txt

# Verify Redis packages are removed
pip list | grep -i redis
pip list | grep -i celery
# These should return no results
```

### Step 3: Update Environment Configuration

#### 3.1 Update Development Environment File

```bash
# Backup current environment file
cp .env.development .env.development.backup

# Remove Redis-related variables from .env.development
# Remove these lines if they exist:
# REDIS_URL=redis://127.0.0.1:6379/1
# REDIS_HOST=localhost
# REDIS_PORT=6379
# REDIS_PASSWORD=redis_password
# CELERY_BROKER_URL=redis://127.0.0.1:6379/0
# CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/0
```

#### 3.2 Verify Environment Variables

Your `.env.development` should now contain only:

```env
# Database Configuration
MYSQL_DATABASE=mall_server_dev
MYSQL_USER=root
MYSQL_PASSWORD=dev_password
MYSQL_HOST=localhost
MYSQL_PORT=3306

# Django Configuration
DEBUG=True
SECRET_KEY=your-secret-key
ALLOWED_HOSTS=localhost,127.0.0.1

# WeChat Configuration (if used)
WECHAT_APPID=your_wechat_appid
WECHAT_APPSECRET=your_wechat_appsecret

# JWT Configuration
JWT_SECRET_KEY=tokenTp
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

### Step 4: Database Cache Setup

#### 4.1 Create Cache Table

```bash
# Create the database cache table
python manage.py createcachetable mall_server_cache

# Verify table creation
python manage.py dbshell
```

In the database shell:
```sql
DESCRIBE mall_server_cache;
-- Should show: cache_key, value, expires columns
EXIT;
```

#### 4.2 Test Cache Functionality

```bash
# Test cache operations
python manage.py shell
```

In the Django shell:
```python
from django.core.cache import cache

# Test cache set/get
cache.set('migration_test', 'success', 60)
result = cache.get('migration_test')
print(f"Cache test result: {result}")  # Should print: Cache test result: success

# Test cache clear
cache.clear()
print("Cache cleared successfully")

exit()
```

### Step 5: Update Docker Environment

#### 5.1 Stop Current Docker Services

```bash
# Stop all services
docker-compose -f docker-compose.dev.yml down

# Remove Redis containers and volumes (if they exist)
docker container rm mall-server-redis-dev 2>/dev/null || true
docker volume rm mall-server_redis_mall_data 2>/dev/null || true
```

#### 5.2 Start Updated Docker Services

```bash
# Start services with updated configuration
docker-compose -f docker-compose.dev.yml up -d

# Verify services are running
docker-compose -f docker-compose.dev.yml ps

# Check logs for any errors
docker-compose -f docker-compose.dev.yml logs mall-server
```

#### 5.3 Setup Cache Table in Docker

```bash
# Create cache table in Docker environment
docker-compose -f docker-compose.dev.yml exec mall-server python manage.py createcachetable mall_server_cache

# Test Docker environment
docker-compose -f docker-compose.dev.yml exec mall-server python manage.py shell -c "
from django.core.cache import cache
cache.set('docker_test', 'working', 60)
print('Docker cache test:', cache.get('docker_test'))
"
```

### Step 6: Application Testing

#### 6.1 Start Development Server

```bash
# Start Django development server
python manage.py runserver

# Or using Docker
docker-compose -f docker-compose.dev.yml up
```

#### 6.2 Verify Application Functionality

1. **Admin Panel**: http://localhost:8000/admin/
   - Login with admin credentials
   - Verify all sections load correctly

2. **API Endpoints**: Test key API endpoints
   ```bash
   # Test user API
   curl http://localhost:8000/api/users/
   
   # Test products API
   curl http://localhost:8000/api/products/
   ```

3. **Cache Operations**: Monitor cache table
   ```sql
   -- Check cache entries
   SELECT cache_key, expires FROM mall_server_cache LIMIT 10;
   ```

### Step 7: Performance Validation

#### 7.1 Monitor Cache Performance

```bash
# Run cache performance test
python manage.py shell -c "
import time
from django.core.cache import cache

# Test cache write performance
start = time.time()
for i in range(100):
    cache.set(f'perf_test_{i}', f'value_{i}', 300)
write_time = time.time() - start
print(f'Cache write time for 100 operations: {write_time:.3f}s')

# Test cache read performance
start = time.time()
for i in range(100):
    cache.get(f'perf_test_{i}')
read_time = time.time() - start
print(f'Cache read time for 100 operations: {read_time:.3f}s')

# Cleanup
cache.clear()
"
```

#### 7.2 Database Performance Impact

```sql
-- Monitor cache table size
SELECT 
    COUNT(*) as cache_entries,
    AVG(LENGTH(value)) as avg_value_size,
    MAX(expires) as latest_expiry
FROM mall_server_cache;

-- Check for performance issues
SHOW PROCESSLIST;
```

## Rollback Procedure

If you need to rollback to Redis-based caching:

### Step 1: Restore Redis Configuration

```bash
# Restore environment backup
cp .env.development.backup .env.development

# Install Redis packages
pip install django-redis==5.4.0 redis==5.0.1 celery==5.3.4
```

### Step 2: Update Django Settings

Edit `mall_server/settings/base.py`:

```python
# Restore Redis cache configuration
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://127.0.0.1:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'mall_server',
        'TIMEOUT': 300,
    }
}
```

### Step 3: Restore Redis Service

Add Redis service back to `docker-compose.dev.yml`:

```yaml
redis-mall:
  image: redis:7-alpine
  container_name: mall-server-redis-dev
  restart: unless-stopped
  command: redis-server --requirepass redis_dev_password
  ports:
    - "6380:6379"
  volumes:
    - redis_mall_data:/data
  networks:
    - mall-network
```

### Step 4: Start Redis and Test

```bash
# Start Redis service
docker-compose -f docker-compose.dev.yml up -d redis-mall

# Test Redis connection
redis-cli -h localhost -p 6380 -a redis_dev_password ping
```

## Performance Implications

### Database Cache vs Redis Cache

| Aspect | Database Cache | Redis Cache |
|--------|----------------|-------------|
| **Latency** | 5-15ms | 1-3ms |
| **Throughput** | Database-dependent | Very high |
| **Persistence** | Persistent | Configurable |
| **Memory Usage** | Database storage | Dedicated RAM |
| **Complexity** | Lower | Higher |
| **Dependencies** | None (uses existing DB) | Redis service |

### Expected Performance Changes

1. **Slightly Higher Latency**: Cache operations may be 3-10ms slower
2. **Database Load**: Minimal increase in database queries
3. **Memory Usage**: Reduced overall memory footprint (no Redis)
4. **Startup Time**: Faster (one less service to start)

### Optimization Recommendations

1. **Database Indexing**: Ensure cache table has proper indexes
2. **Cache Timeout**: Use appropriate cache expiration times
3. **Selective Caching**: Cache only high-value operations
4. **Monitor Performance**: Track cache hit rates and response times

## Troubleshooting

### Common Issues and Solutions

#### Issue: Cache table creation fails

**Error**: `django.db.utils.ProgrammingError: (1146, "Table 'mall_server_cache' doesn't exist")`

**Solution**:
```bash
# Ensure database is accessible
python manage.py migrate
python manage.py createcachetable mall_server_cache
```

#### Issue: Permission denied on cache table

**Error**: `django.db.utils.OperationalError: (1142, "CREATE command denied")`

**Solution**:
```sql
-- Grant permissions to database user
GRANT ALL PRIVILEGES ON mall_server_dev.* TO 'mall_user'@'localhost';
FLUSH PRIVILEGES;
```

#### Issue: Old Redis connections still attempted

**Error**: `redis.exceptions.ConnectionError: Error 111 connecting to localhost:6379`

**Solution**:
```bash
# Clear Django cache and restart
rm -rf __pycache__/
python manage.py runserver --settings=mall_server.settings.development
```

#### Issue: Cache performance degradation

**Symptoms**: Slow response times, high database load

**Solution**:
```sql
-- Optimize cache table
OPTIMIZE TABLE mall_server_cache;

-- Add indexes if needed
CREATE INDEX idx_cache_expires ON mall_server_cache(expires);
```

#### Issue: Docker services won't start

**Error**: `ERROR: Service 'redis-mall' failed to build`

**Solution**:
```bash
# Remove old containers and rebuild
docker-compose -f docker-compose.dev.yml down --volumes
docker-compose -f docker-compose.dev.yml up --build -d
```

### Getting Help

If you encounter issues during migration:

1. **Check Logs**: Review Django and Docker logs for error messages
2. **Verify Configuration**: Ensure all Redis references are removed
3. **Test Incrementally**: Test each step before proceeding
4. **Use Rollback**: If needed, use the rollback procedure above
5. **Contact Team**: Reach out to team members for assistance

## Post-Migration Checklist

After completing the migration, verify:

- [ ] Application starts without Redis connection attempts
- [ ] All API endpoints work correctly
- [ ] Admin panel functions normally
- [ ] Cache operations work (set/get/delete)
- [ ] Docker environment runs without Redis service
- [ ] No Redis-related error messages in logs
- [ ] Performance is acceptable for your use case
- [ ] Team members are informed of the changes

## Security Improvements

The Redis removal provides several security benefits:

1. **Reduced Attack Surface**: One less network service exposed
2. **Fewer Dependencies**: Reduced third-party package vulnerabilities
3. **Simplified Configuration**: Less configuration to secure
4. **Consolidated Storage**: All data in one database system

## Maintenance Notes

### Cache Management

```bash
# Monitor cache table size
python manage.py shell -c "
from django.db import connection
cursor = connection.cursor()
cursor.execute('SELECT COUNT(*), SUM(LENGTH(value)) FROM mall_server_cache')
count, size = cursor.fetchone()
print(f'Cache entries: {count}, Total size: {size} bytes')
"

# Clear expired entries (Django handles this automatically)
python manage.py shell -c "
from django.core.cache import cache
cache._cache.clear_expired()
print('Expired cache entries cleared')
"
```

### Regular Maintenance

1. **Monitor cache table growth**
2. **Optimize database periodically**
3. **Review cache hit rates**
4. **Update cache timeouts as needed**

This completes the Redis removal migration guide. The application should now run successfully without Redis dependencies while maintaining all existing functionality.