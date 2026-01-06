"""
Management command to test and demonstrate password security performance optimizations.

This command provides comprehensive testing of all performance optimization components:
- Performance monitoring and metrics
- Caching for password validation rules
- Optimized hash operations for concurrent access
- Connection pooling for database operations

Requirements addressed: 7.1, 7.2, 7.3, 7.4
"""

import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from apps.common.password_utils import (
    SecurePasswordHasher, PasswordValidator, SecurityMonitor,
    get_password_security_performance_stats, hash_password_optimized,
    verify_password_optimized
)
from apps.common.performance import (
    get_performance_monitor, get_password_validation_cache,
    get_concurrent_hash_processor, get_db_connection_manager
)


class Command(BaseCommand):
    help = 'Test and demonstrate password security performance optimizations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-type',
            type=str,
            choices=['all', 'caching', 'concurrent', 'monitoring', 'database'],
            default='all',
            help='Type of performance test to run'
        )
        parser.add_argument(
            '--iterations',
            type=int,
            default=100,
            help='Number of iterations for performance tests'
        )
        parser.add_argument(
            '--threads',
            type=int,
            default=4,
            help='Number of concurrent threads for concurrent tests'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose output'
        )

    def handle(self, *args, **options):
        """Execute performance tests based on options."""
        self.verbosity = options.get('verbosity', 1)
        self.verbose = options.get('verbose', False)
        
        test_type = options['test_type']
        iterations = options['iterations']
        threads = options['threads']
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Starting password security performance tests: {test_type}'
            )
        )
        
        try:
            if test_type == 'all':
                self.run_all_tests(iterations, threads)
            elif test_type == 'caching':
                self.test_caching_performance(iterations)
            elif test_type == 'concurrent':
                self.test_concurrent_performance(iterations, threads)
            elif test_type == 'monitoring':
                self.test_monitoring_performance(iterations)
            elif test_type == 'database':
                self.test_database_performance(iterations)
                
            # Display final performance summary
            self.display_performance_summary()
            
        except Exception as e:
            raise CommandError(f'Performance test failed: {str(e)}')

    def run_all_tests(self, iterations: int, threads: int):
        """Run all performance tests."""
        self.stdout.write('Running comprehensive performance test suite...\n')
        
        self.test_caching_performance(iterations // 4)
        self.test_concurrent_performance(iterations // 4, threads)
        self.test_monitoring_performance(iterations // 4)
        self.test_database_performance(iterations // 4)

    def test_caching_performance(self, iterations: int):
        """Test caching performance optimizations."""
        self.stdout.write(self.style.HTTP_INFO('Testing caching performance...'))
        
        cache = get_password_validation_cache()
        validator = PasswordValidator()
        
        # Test validation rules caching
        start_time = time.time()
        for i in range(iterations):
            rules = cache.get_validation_rules()
            if self.verbose and i % 10 == 0:
                self.stdout.write(f'  Cached validation rules access {i+1}/{iterations}')
        
        cache_time = time.time() - start_time
        
        # Test common passwords caching
        start_time = time.time()
        for i in range(iterations):
            common_passwords = cache.get_common_passwords()
            if self.verbose and i % 10 == 0:
                self.stdout.write(f'  Cached common passwords access {i+1}/{iterations}')
        
        common_passwords_time = time.time() - start_time
        
        # Test password validation with caching
        test_passwords = [
            'TestPassword123!',
            'WeakPass',
            'AnotherStrongPassword456@',
            'password123',
            'ComplexPassword789#'
        ]
        
        start_time = time.time()
        for i in range(iterations):
            password = test_passwords[i % len(test_passwords)]
            result = validator.validate(password)
            if self.verbose and i % 20 == 0:
                self.stdout.write(f'  Password validation {i+1}/{iterations}: {result.strength_level}')
        
        validation_time = time.time() - start_time
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Caching Performance Results:\n'
                f'  Validation rules cache: {cache_time:.3f}s for {iterations} operations '
                f'({iterations/cache_time:.1f} ops/sec)\n'
                f'  Common passwords cache: {common_passwords_time:.3f}s for {iterations} operations '
                f'({iterations/common_passwords_time:.1f} ops/sec)\n'
                f'  Password validation: {validation_time:.3f}s for {iterations} operations '
                f'({iterations/validation_time:.1f} ops/sec)\n'
            )
        )

    def test_concurrent_performance(self, iterations: int, threads: int):
        """Test concurrent hash operations performance."""
        self.stdout.write(self.style.HTTP_INFO('Testing concurrent performance...'))
        
        processor = get_concurrent_hash_processor()
        hasher = SecurePasswordHasher()
        
        test_passwords = [
            'ConcurrentTest123!',
            'ThreadSafe456@',
            'ParallelHash789#',
            'MultiThread000$',
            'ConcurrentAccess111%'
        ]
        
        def hash_operation(password_index):
            """Single hash operation for concurrent testing."""
            password = test_passwords[password_index % len(test_passwords)]
            
            # Test hash encoding
            encoded = hasher.encode(password)
            
            # Test hash verification
            result = hasher.verify(password, encoded)
            
            return result
        
        # Test concurrent hash operations
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = [
                executor.submit(hash_operation, i) 
                for i in range(iterations)
            ]
            
            successful_operations = 0
            for i, future in enumerate(as_completed(futures)):
                try:
                    result = future.result()
                    if result:
                        successful_operations += 1
                    
                    if self.verbose and i % 20 == 0:
                        self.stdout.write(f'  Concurrent operation {i+1}/{iterations} completed')
                        
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f'  Concurrent operation failed: {str(e)}')
                    )
        
        concurrent_time = time.time() - start_time
        
        # Get processor statistics
        stats = processor.get_statistics()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Concurrent Performance Results:\n'
                f'  Total operations: {iterations}\n'
                f'  Successful operations: {successful_operations}\n'
                f'  Success rate: {successful_operations/iterations:.1%}\n'
                f'  Total time: {concurrent_time:.3f}s\n'
                f'  Throughput: {iterations/concurrent_time:.1f} ops/sec\n'
                f'  Average processing time: {stats.get("avg_processing_time_ms", 0):.2f}ms\n'
                f'  Peak concurrent operations: {stats.get("peak_concurrent_operations", 0)}\n'
            )
        )

    def test_monitoring_performance(self, iterations: int):
        """Test performance monitoring overhead."""
        self.stdout.write(self.style.HTTP_INFO('Testing monitoring performance...'))
        
        monitor = get_performance_monitor()
        security_monitor = SecurityMonitor()
        
        # Test performance monitoring overhead
        start_time = time.time()
        
        for i in range(iterations):
            # Start operation tracking
            operation_id = monitor.start_operation(
                'test_operation',
                {'iteration': i, 'test_type': 'monitoring_performance'}
            )
            
            # Simulate some work
            time.sleep(0.001)  # 1ms of work
            
            # Finish operation tracking
            monitor.finish_operation(operation_id, success=True)
            
            # Log security event
            security_monitor.log_authentication_attempt(
                user=f'test_user_{i % 10}',
                success=i % 3 != 0,  # 2/3 success rate
                details={
                    'ip_address': f'192.168.1.{i % 255}',
                    'user_agent': 'TestAgent/1.0',
                    'iteration': i
                }
            )
            
            if self.verbose and i % 25 == 0:
                self.stdout.write(f'  Monitoring operation {i+1}/{iterations}')
        
        monitoring_time = time.time() - start_time
        
        # Get monitoring statistics
        operation_stats = monitor.get_operation_stats()
        active_operations = monitor.get_active_operations()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Monitoring Performance Results:\n'
                f'  Total time: {monitoring_time:.3f}s for {iterations} operations\n'
                f'  Monitoring overhead: {(monitoring_time - iterations * 0.001):.3f}s\n'
                f'  Operations per second: {iterations/monitoring_time:.1f}\n'
                f'  Active operations tracked: {len(active_operations)}\n'
                f'  Operation types monitored: {len(operation_stats)}\n'
            )
        )

    def test_database_performance(self, iterations: int):
        """Test database connection performance optimizations."""
        self.stdout.write(self.style.HTTP_INFO('Testing database performance...'))
        
        db_manager = get_db_connection_manager()
        
        def database_operation():
            """Simple database operation for testing."""
            def query_func():
                from django.db import connection
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    return cursor.fetchone()
            
            return db_manager.execute_with_connection_management('default', query_func)
        
        # Test database operations with connection management
        start_time = time.time()
        
        successful_queries = 0
        for i in range(iterations):
            try:
                result = database_operation()
                if result:
                    successful_queries += 1
                
                if self.verbose and i % 25 == 0:
                    self.stdout.write(f'  Database operation {i+1}/{iterations}')
                    
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'  Database operation {i+1} failed: {str(e)}')
                )
        
        database_time = time.time() - start_time
        
        # Get connection statistics
        connection_stats = db_manager.get_connection_statistics()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Database Performance Results:\n'
                f'  Total operations: {iterations}\n'
                f'  Successful operations: {successful_queries}\n'
                f'  Success rate: {successful_queries/iterations:.1%}\n'
                f'  Total time: {database_time:.3f}s\n'
                f'  Queries per second: {iterations/database_time:.1f}\n'
                f'  Average query time: {connection_stats.get("default", {}).get("avg_query_time_ms", 0):.2f}ms\n'
            )
        )

    def display_performance_summary(self):
        """Display comprehensive performance summary."""
        self.stdout.write(self.style.HTTP_INFO('\nGenerating performance summary...'))
        
        try:
            stats = get_password_security_performance_stats()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n=== Password Security Performance Summary ===\n'
                    f'Timestamp: {stats.get("timestamp", "unknown")}\n'
                )
            )
            
            # Performance monitor stats
            if 'performance_monitor' in stats:
                pm_stats = stats['performance_monitor']
                self.stdout.write('Performance Monitor:')
                
                operation_stats = pm_stats.get('operation_stats', {})
                for operation, op_stats in operation_stats.items():
                    self.stdout.write(
                        f'  {operation}: {op_stats.get("count", 0)} ops, '
                        f'avg {op_stats.get("avg_duration", 0)*1000:.2f}ms'
                    )
                
                active_ops = pm_stats.get('active_operations', [])
                if active_ops:
                    self.stdout.write(f'  Active operations: {len(active_ops)}')
            
            # Hash processor stats
            if 'hash_processor' in stats:
                hp_stats = stats['hash_processor']
                self.stdout.write(
                    f'\nHash Processor:\n'
                    f'  Total operations: {hp_stats.get("total_operations", 0)}\n'
                    f'  Success rate: {hp_stats.get("success_rate", 0):.1%}\n'
                    f'  Average processing time: {hp_stats.get("avg_processing_time_ms", 0):.2f}ms'
                )
            
            # Database connection stats
            if 'database_connections' in stats:
                db_stats = stats['database_connections']
                self.stdout.write('\nDatabase Connections:')
                for alias, conn_stats in db_stats.items():
                    self.stdout.write(
                        f'  {alias}: {conn_stats.get("queries_executed", 0)} queries, '
                        f'avg {conn_stats.get("avg_query_time_ms", 0):.2f}ms'
                    )
            
            # Cache status
            if 'cache_status' in stats:
                cache_stats = stats['cache_status']
                self.stdout.write(
                    f'\nCache Status:\n'
                    f'  Validation cache active: {cache_stats.get("validation_cache_active", False)}\n'
                    f'  Django cache backend: {cache_stats.get("django_cache_backend", "unknown")}'
                )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Failed to generate performance summary: {str(e)}')
            )
        
        self.stdout.write(
            self.style.SUCCESS('\n=== Performance Testing Complete ===')
        )