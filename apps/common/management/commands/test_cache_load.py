"""
Load testing for cache performance under concurrent access
"""

import time
import threading
import statistics
import random
import string
from django.core.management.base import BaseCommand
from django.core.cache import cache
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed


class Command(BaseCommand):
    help = 'Test cache performance under load with concurrent users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--concurrent-users',
            type=int,
            default=10,
            help='Number of concurrent users (default: 10)'
        )
        parser.add_argument(
            '--operations-per-user',
            type=int,
            default=50,
            help='Number of operations per user (default: 50)'
        )
        parser.add_argument(
            '--test-duration',
            type=int,
            default=30,
            help='Test duration in seconds (default: 30)'
        )

    def handle(self, *args, **options):
        self.concurrent_users = options['concurrent_users']
        self.operations_per_user = options['operations_per_user']
        self.test_duration = options['test_duration']
        
        self.stdout.write(
            self.style.SUCCESS(f'Starting cache load test...')
        )
        self.stdout.write(f'Concurrent users: {self.concurrent_users}')
        self.stdout.write(f'Operations per user: {self.operations_per_user}')
        self.stdout.write(f'Test duration: {self.test_duration}s')
        
        # Run load tests
        results = self.run_load_test()
        
        # Display results
        self.display_results(results)

    def generate_test_data(self):
        """Generate realistic test data for mall server"""
        return {
            'user_profile': {
                'user_id': random.randint(1, 10000),
                'username': ''.join(random.choices(string.ascii_letters, k=15)),
                'email': f'user{random.randint(1, 1000)}@example.com',
                'membership_tier': random.choice(['bronze', 'silver', 'gold', 'platinum']),
                'points_balance': random.randint(0, 50000),
                'preferences': {
                    'notifications': random.choice([True, False]),
                    'newsletter': random.choice([True, False]),
                    'language': random.choice(['zh-CN', 'en-US']),
                }
            },
            'product_data': {
                'product_id': random.randint(1, 5000),
                'name': ''.join(random.choices(string.ascii_letters + ' ', k=30)),
                'price': round(random.uniform(10.0, 1000.0), 2),
                'category': random.choice(['electronics', 'clothing', 'books', 'home']),
                'in_stock': random.randint(0, 100),
                'description': ''.join(random.choices(string.ascii_letters + ' ', k=200)),
                'attributes': {
                    f'attr_{i}': f'value_{i}'
                    for i in range(random.randint(3, 8))
                }
            },
            'order_summary': {
                'order_id': f'order_{random.randint(100000, 999999)}',
                'user_id': random.randint(1, 10000),
                'total_amount': round(random.uniform(50.0, 2000.0), 2),
                'status': random.choice(['pending', 'processing', 'shipped', 'delivered']),
                'items': [
                    {
                        'product_id': random.randint(1, 5000),
                        'quantity': random.randint(1, 5),
                        'price': round(random.uniform(10.0, 500.0), 2)
                    }
                    for _ in range(random.randint(1, 5))
                ]
            }
        }

    def simulate_user_session(self, user_id):
        """Simulate a user session with typical cache operations"""
        session_results = {
            'operations': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'total_time': 0,
            'errors': 0,
        }
        
        start_time = time.time()
        
        try:
            for i in range(self.operations_per_user):
                # Stop if test duration exceeded
                if time.time() - start_time > self.test_duration:
                    break
                
                operation_start = time.perf_counter()
                
                # Simulate typical user operations
                operation_type = random.choice([
                    'get_user_profile', 'set_user_profile',
                    'get_product_data', 'set_product_data',
                    'get_order_summary', 'set_order_summary',
                    'delete_cache_entry'
                ])
                
                if operation_type.startswith('get_'):
                    # GET operations (70% of traffic)
                    data_type = operation_type.replace('get_', '')
                    key = f'{data_type}_{user_id}_{random.randint(1, 100)}'
                    
                    result = cache.get(key)
                    if result is not None:
                        session_results['cache_hits'] += 1
                    else:
                        session_results['cache_misses'] += 1
                
                elif operation_type.startswith('set_'):
                    # SET operations (25% of traffic)
                    data_type = operation_type.replace('set_', '')
                    key = f'{data_type}_{user_id}_{random.randint(1, 100)}'
                    
                    test_data = self.generate_test_data()
                    data = test_data[data_type]
                    
                    timeout = random.choice([60, 300, 600, 1800])  # Various timeouts
                    cache.set(key, data, timeout=timeout)
                
                elif operation_type == 'delete_cache_entry':
                    # DELETE operations (5% of traffic)
                    data_type = random.choice(['user_profile', 'product_data', 'order_summary'])
                    key = f'{data_type}_{user_id}_{random.randint(1, 100)}'
                    
                    cache.delete(key)
                
                operation_time = time.perf_counter() - operation_start
                session_results['total_time'] += operation_time
                session_results['operations'] += 1
                
                # Small delay to simulate realistic usage
                time.sleep(random.uniform(0.01, 0.05))
        
        except Exception as e:
            session_results['errors'] += 1
        
        return session_results

    def run_load_test(self):
        """Run concurrent load test"""
        self.stdout.write('\nStarting concurrent load test...')
        
        start_time = time.time()
        all_results = []
        
        # Use ThreadPoolExecutor for concurrent execution
        with ThreadPoolExecutor(max_workers=self.concurrent_users) as executor:
            # Submit tasks for each user
            future_to_user = {
                executor.submit(self.simulate_user_session, user_id): user_id
                for user_id in range(self.concurrent_users)
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_user):
                user_id = future_to_user[future]
                try:
                    result = future.result()
                    result['user_id'] = user_id
                    all_results.append(result)
                    
                    self.stdout.write(f'User {user_id} completed: {result["operations"]} ops')
                    
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'User {user_id} failed: {e}')
                    )
        
        total_time = time.time() - start_time
        
        # Aggregate results
        aggregated = {
            'total_time': total_time,
            'total_operations': sum(r['operations'] for r in all_results),
            'total_cache_hits': sum(r['cache_hits'] for r in all_results),
            'total_cache_misses': sum(r['cache_misses'] for r in all_results),
            'total_errors': sum(r['errors'] for r in all_results),
            'avg_operation_time': statistics.mean([
                r['total_time'] / r['operations'] if r['operations'] > 0 else 0
                for r in all_results
            ]),
            'operations_per_second': sum(r['operations'] for r in all_results) / total_time,
            'cache_hit_rate': (
                sum(r['cache_hits'] for r in all_results) /
                (sum(r['cache_hits'] for r in all_results) + sum(r['cache_misses'] for r in all_results))
            ) * 100 if (sum(r['cache_hits'] for r in all_results) + sum(r['cache_misses'] for r in all_results)) > 0 else 0,
            'user_results': all_results,
        }
        
        return aggregated

    def display_results(self, results):
        """Display load test results"""
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('CACHE LOAD TEST RESULTS'))
        self.stdout.write('='*60)
        
        self.stdout.write(f"\nTest Configuration:")
        self.stdout.write(f"  Concurrent users: {self.concurrent_users}")
        self.stdout.write(f"  Target ops per user: {self.operations_per_user}")
        self.stdout.write(f"  Test duration: {self.test_duration}s")
        
        self.stdout.write(f"\nOverall Performance:")
        self.stdout.write(f"  Total operations: {results['total_operations']}")
        self.stdout.write(f"  Operations per second: {results['operations_per_second']:.2f}")
        self.stdout.write(f"  Average operation time: {results['avg_operation_time']*1000:.2f}ms")
        self.stdout.write(f"  Total test time: {results['total_time']:.2f}s")
        
        self.stdout.write(f"\nCache Performance:")
        self.stdout.write(f"  Cache hits: {results['total_cache_hits']}")
        self.stdout.write(f"  Cache misses: {results['total_cache_misses']}")
        self.stdout.write(f"  Cache hit rate: {results['cache_hit_rate']:.1f}%")
        
        self.stdout.write(f"\nError Rate:")
        self.stdout.write(f"  Total errors: {results['total_errors']}")
        self.stdout.write(f"  Error rate: {(results['total_errors']/results['total_operations']*100) if results['total_operations'] > 0 else 0:.2f}%")
        
        # Performance assessment
        self.stdout.write(f"\nPerformance Assessment:")
        
        if results['avg_operation_time'] < 0.05:  # < 50ms
            self.stdout.write(self.style.SUCCESS("✓ Excellent performance (<50ms avg)"))
        elif results['avg_operation_time'] < 0.1:  # < 100ms
            self.stdout.write(self.style.SUCCESS("✓ Good performance (<100ms avg)"))
        elif results['avg_operation_time'] < 0.2:  # < 200ms
            self.stdout.write(self.style.WARNING("⚠ Acceptable performance (<200ms avg)"))
        else:
            self.stdout.write(self.style.ERROR("✗ Poor performance (>200ms avg)"))
        
        if results['cache_hit_rate'] > 80:
            self.stdout.write(self.style.SUCCESS(f"✓ Excellent cache hit rate ({results['cache_hit_rate']:.1f}%)"))
        elif results['cache_hit_rate'] > 60:
            self.stdout.write(self.style.SUCCESS(f"✓ Good cache hit rate ({results['cache_hit_rate']:.1f}%)"))
        elif results['cache_hit_rate'] > 40:
            self.stdout.write(self.style.WARNING(f"⚠ Moderate cache hit rate ({results['cache_hit_rate']:.1f}%)"))
        else:
            self.stdout.write(self.style.ERROR(f"✗ Poor cache hit rate ({results['cache_hit_rate']:.1f}%)"))
        
        if results['operations_per_second'] > 100:
            self.stdout.write(self.style.SUCCESS(f"✓ High throughput ({results['operations_per_second']:.1f} ops/sec)"))
        elif results['operations_per_second'] > 50:
            self.stdout.write(self.style.SUCCESS(f"✓ Good throughput ({results['operations_per_second']:.1f} ops/sec)"))
        else:
            self.stdout.write(self.style.WARNING(f"⚠ Moderate throughput ({results['operations_per_second']:.1f} ops/sec)"))
        
        # Recommendations
        self.stdout.write(f"\nRecommendations:")
        
        if results['avg_operation_time'] > 0.1:
            self.stdout.write("- Consider optimizing database indexes")
            self.stdout.write("- Review cache configuration (MAX_ENTRIES, timeouts)")
        
        if results['cache_hit_rate'] < 70:
            self.stdout.write("- Increase cache timeouts for stable data")
            self.stdout.write("- Review cache key patterns for consistency")
            self.stdout.write("- Consider increasing MAX_ENTRIES")
        
        if results['operations_per_second'] < 50:
            self.stdout.write("- Monitor database connection pool settings")
            self.stdout.write("- Consider cache warming strategies")
            self.stdout.write("- Review application-level optimizations")