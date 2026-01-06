"""
Optimized cache configuration for database cache backend
This configuration provides optimal performance settings for the mall server
"""

# Optimized Cache Configuration
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'mall_server_cache',
        'TIMEOUT': 300,  # 5 minutes default timeout
        'OPTIONS': {
            # Increased max entries for better hit rate
            'MAX_ENTRIES': 15000,
            
            # Gentler culling - remove 1/4 when max reached instead of 1/3
            'CULL_FREQUENCY': 4,
            
            # Additional optimization options
            'VERSION': 1,
        },
        'KEY_PREFIX': 'mall_server',
        'VERSION': 1,
    },
    
    # Separate cache for sessions (shorter timeout)
    'sessions': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'mall_server_sessions_cache',
        'TIMEOUT': 1800,  # 30 minutes for sessions
        'OPTIONS': {
            'MAX_ENTRIES': 5000,
            'CULL_FREQUENCY': 3,
        },
        'KEY_PREFIX': 'mall_sessions',
    },
    
    # Long-term cache for static data
    'static_data': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'mall_server_static_cache',
        'TIMEOUT': 7200,  # 2 hours for static data
        'OPTIONS': {
            'MAX_ENTRIES': 3000,
            'CULL_FREQUENCY': 5,
        },
        'KEY_PREFIX': 'mall_static',
    }
}

# Cache timeout configurations for different data types
CACHE_TIMEOUTS = {
    # User-related data
    'user_profile': 1800,      # 30 minutes
    'user_membership': 1800,   # 30 minutes
    'user_points': 600,        # 10 minutes
    'user_orders': 900,        # 15 minutes
    
    # Product-related data
    'product_detail': 3600,    # 1 hour
    'product_list': 1800,      # 30 minutes
    'product_categories': 7200, # 2 hours
    'product_featured': 1800,   # 30 minutes
    
    # Order-related data
    'order_summary': 600,      # 10 minutes
    'order_history': 1800,     # 30 minutes
    
    # System data
    'membership_tiers': 7200,  # 2 hours
    'payment_methods': 3600,   # 1 hour
    'system_config': 7200,     # 2 hours
}

# Cache key patterns for consistent naming
CACHE_KEY_PATTERNS = {
    'user_profile': 'user:{user_id}:profile',
    'user_membership': 'user:{user_id}:membership',
    'user_points': 'user:{user_id}:points',
    'user_orders': 'user:{user_id}:orders:{page}',
    
    'product_detail': 'product:{product_id}:detail',
    'product_list': 'product:category:{category_id}:page:{page}',
    'product_categories': 'product:categories:tree',
    'product_featured': 'product:featured:list',
    
    'order_summary': 'order:{order_id}:summary',
    'order_history': 'order:user:{user_id}:history',
    
    'membership_tiers': 'membership:tiers:all',
    'payment_methods': 'payment:methods:active',
}

# Performance monitoring settings
CACHE_PERFORMANCE_MONITORING = {
    'ENABLE_MONITORING': True,
    'LOG_SLOW_OPERATIONS': True,
    'SLOW_OPERATION_THRESHOLD': 0.1,  # 100ms
    'MONITOR_HIT_RATE': True,
    'HIT_RATE_ALERT_THRESHOLD': 0.7,  # Alert if hit rate < 70%
}

# Database cache table creation SQL with optimizations
CACHE_TABLE_SQL = {
    'mall_server_cache': """
        CREATE TABLE IF NOT EXISTS mall_server_cache (
            cache_key VARCHAR(255) NOT NULL PRIMARY KEY,
            value LONGTEXT NOT NULL,
            expires DATETIME(6) NOT NULL,
            INDEX idx_expires (expires),
            INDEX idx_key_expires (cache_key, expires)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """,
    
    'mall_server_sessions_cache': """
        CREATE TABLE IF NOT EXISTS mall_server_sessions_cache (
            cache_key VARCHAR(255) NOT NULL PRIMARY KEY,
            value LONGTEXT NOT NULL,
            expires DATETIME(6) NOT NULL,
            INDEX idx_expires (expires)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """,
    
    'mall_server_static_cache': """
        CREATE TABLE IF NOT EXISTS mall_server_static_cache (
            cache_key VARCHAR(255) NOT NULL PRIMARY KEY,
            value LONGTEXT NOT NULL,
            expires DATETIME(6) NOT NULL,
            INDEX idx_expires (expires)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """
}

# Cache optimization recommendations
CACHE_OPTIMIZATION_NOTES = """
Cache Optimization Configuration Notes:

1. Multiple Cache Backends:
   - default: General application cache (5 min timeout)
   - sessions: User session data (30 min timeout)
   - static_data: Rarely changing data (2 hour timeout)

2. Timeout Strategy:
   - User data: 10-30 minutes (frequently changing)
   - Product data: 30-60 minutes (moderate changes)
   - System data: 2+ hours (rarely changing)

3. Performance Optimizations:
   - Increased MAX_ENTRIES for better hit rates
   - Gentler CULL_FREQUENCY to reduce cache churn
   - Optimized database indexes for cache tables
   - Separate caches for different data types

4. Monitoring:
   - Enable performance monitoring
   - Track cache hit rates (target >80%)
   - Alert on slow operations (>100ms)
   - Monitor database impact

5. Database Optimizations:
   - InnoDB engine for better concurrency
   - Composite indexes for efficient lookups
   - UTF8MB4 charset for full Unicode support
   - Regular table optimization (weekly)

Usage Example:
    from django.core.cache import caches
    from django.conf import settings
    
    # Use specific cache backend
    static_cache = caches['static_data']
    
    # Use configured timeouts
    timeout = settings.CACHE_TIMEOUTS['user_profile']
    
    # Use consistent key patterns
    key = settings.CACHE_KEY_PATTERNS['user_profile'].format(user_id=123)
"""