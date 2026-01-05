"""
Performance optimization utilities and monitoring
"""

import time
import logging
from functools import wraps
from django.core.cache import cache
from django.db import connection
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import json

logger = logging.getLogger(__name__)
performance_logger = logging.getLogger('performance')


class QueryOptimizer:
    """Database query optimization utilities"""
    
    @staticmethod
    def get_query_stats():
        """Get database query statistics"""
        queries = connection.queries
        total_time = sum(float(query['time']) for query in queries)
        
        return {
            'query_count': len(queries),
            'total_time': total_time,
            'queries': queries[-10:] if len(queries) > 10 else queries
        }
    
    @staticmethod
    def log_slow_queries(threshold=0.1):
        """Log queries that exceed the time threshold"""
        queries = connection.queries
        slow_queries = [
            query for query in queries 
            if float(query['time']) > threshold
        ]
        
        for query in slow_queries:
            performance_logger.warning(
                f"Slow query detected: {query['time']}s - {query['sql'][:200]}..."
            )
        
        return slow_queries


class CacheManager:
    """Centralized cache management with performance monitoring"""
    
    # Cache key prefixes
    USER_PREFIX = 'user:'
    PRODUCT_PREFIX = 'product:'
    ORDER_PREFIX = 'order:'
    MEMBERSHIP_PREFIX = 'membership:'
    POINTS_PREFIX = 'points:'
    
    # Default cache timeouts (in seconds)
    DEFAULT_TIMEOUT = 300  # 5 minutes
    SHORT_TIMEOUT = 60     # 1 minute
    LONG_TIMEOUT = 3600    # 1 hour
    
    @classmethod
    def get_user_cache_key(cls, user_id, suffix=''):
        """Generate cache key for user data"""
        return f"{cls.USER_PREFIX}{user_id}:{suffix}" if suffix else f"{cls.USER_PREFIX}{user_id}"
    
    @classmethod
    def get_product_cache_key(cls, product_id, suffix=''):
        """Generate cache key for product data"""
        return f"{cls.PRODUCT_PREFIX}{product_id}:{suffix}" if suffix else f"{cls.PRODUCT_PREFIX}{product_id}"
    
    @classmethod
    def cached_get_or_set(cls, key, callable_func, timeout=None):
        """Get from cache or set if not exists, with performance monitoring"""
        start_time = time.time()
        
        # Try to get from cache
        result = cache.get(key)
        
        if result is not None:
            # Cache hit
            cache_time = time.time() - start_time
            performance_logger.debug(f"Cache HIT for {key} in {cache_time:.4f}s")
            return result
        
        # Cache miss - compute value
        result = callable_func()
        
        # Set in cache
        timeout = timeout or cls.DEFAULT_TIMEOUT
        cache.set(key, result, timeout)
        
        total_time = time.time() - start_time
        performance_logger.debug(f"Cache MISS for {key} - computed in {total_time:.4f}s")
        
        return result


class PerformanceMonitor:
    """Performance monitoring and metrics collection"""
    
    @staticmethod
    def monitor_view_performance(view_func):
        """Decorator to monitor view performance"""
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            start_time = time.time()
            initial_queries = len(connection.queries)
            
            try:
                response = view_func(request, *args, **kwargs)
                execution_time = time.time() - start_time
                query_count = len(connection.queries) - initial_queries
                
                performance_logger.info(
                    f"View: {view_func.__name__} | "
                    f"Time: {execution_time:.4f}s | "
                    f"Queries: {query_count}"
                )
                
                if execution_time > 1.0:
                    performance_logger.warning(
                        f"SLOW VIEW: {view_func.__name__} took {execution_time:.4f}s"
                    )
                
                return response
                
            except Exception as e:
                execution_time = time.time() - start_time
                performance_logger.error(
                    f"View ERROR: {view_func.__name__} | Time: {execution_time:.4f}s"
                )
                raise
        
        return wrapper


class PerformanceMiddleware:
    """Middleware for performance monitoring"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        start_time = time.time()
        initial_queries = len(connection.queries)
        
        response = self.get_response(request)
        
        execution_time = time.time() - start_time
        query_count = len(connection.queries) - initial_queries
        
        if settings.DEBUG:
            response['X-Execution-Time'] = f"{execution_time:.4f}s"
            response['X-Query-Count'] = str(query_count)
        
        if request.path.startswith('/api/'):
            performance_logger.info(
                f"API: {request.method} {request.path} | "
                f"Time: {execution_time:.4f}s | "
                f"Queries: {query_count}"
            )
        
        return response


# Utility functions
def cache_user_data(user_id, data, timeout=None):
    """Cache user data with automatic key generation"""
    key = CacheManager.get_user_cache_key(user_id)
    timeout = timeout or CacheManager.DEFAULT_TIMEOUT
    cache.set(key, data, timeout)


def get_cached_user_data(user_id):
    """Get cached user data"""
    key = CacheManager.get_user_cache_key(user_id)
    return cache.get(key)


# Performance monitoring decorators
monitor_view = PerformanceMonitor.monitor_view_performance