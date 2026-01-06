"""
Simulated cache performance benchmark for demonstration purposes
This can run without database connection to show benchmarking methodology
"""

import time
import statistics
import json
import random
import string
from django.core.management.base import BaseCommand
from datetime import datetime


class MockCacheBackend:
    """Mock cache backend that simulates database cache performance"""
    
    def __init__(self):
        self.storage = {}
        self.query_count = 0
    
    def set(self, key, value, timeout=None):
        """Simulate database cache SET operation"""
        # Simulate database query latency
        time.sleep(random.uniform(0.008, 0.020))  # 8-20ms
        self.query_count += 1
        self.storage[key] = {
            'value': value,
            'expires': time.time() + (timeout or 300)
        }
    
    def get(self, key):
        """Simulate database cache GET operation"""
        # Simulate database query latency
        time.sleep(random.uniform(0.005, 0.015))  # 5-15ms
        self.query_count += 1
        
        if key in self.storage:
            entry = self.storage[key]
            if entry['expires'] > time.time():
                return entry['value']
            else:
                del self.storage[key]
        return None
    
    def delete(self, key):
        """Simulate database cache DELETE operation"""
        # Simulate database query latency
        time.sleep(random.uniform(0.003, 0.010))  # 3-10ms
        self.query_count += 1
        
        if key in self.storage:
            del self.storage[key]


class MockRedisBackend:
    """Mock Redis backend for comparison"""
    
    def __init__(self):
        self.storage = {}
    
    def set(self, key, value, timeout=None):
        """Simulate Redis SET operation"""
        time.sleep(random.uniform(0.001, 0.003))  # 1-3ms
        self.storage[key] = {
            'value': value,
            'expires': time.time() + (timeout or 300)
        }
    
    def get(self, key):
        """Simulate Redis GET operation"""
        time.sleep(random.uniform(0.0005, 0.002))  # 0.5-2ms
        
        if key in self.storage:
            entry = self.storage[key]
            if entry['expires'] > time.time():
                return entry['value']
            else:
                del self.storage[key]
        return None
    
    def delete(self, key):
        """Simulate Redis DELETE operation"""
        time.sleep(random.uniform(0.0005, 0.002))  # 0.5-2ms
        
        if key in self.storage:
            del self.storage[key]


class Command(BaseCommand):
    help = 'Simulate cache performance benchmark (works without database)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--iterations',
            type=int,
            default=500,
            help='Number of iterations for each test (default: 500)'
        )
        parser.add_argument(
            '--data-size',
            type=str,
            default='medium',
            choices=['small', 'medium', 'large'],
            help='Size of test data (default: medium)'
        )
        parser.add_argument(
            '--output-file',
            type=str,
            help='Output file for benchmark results (JSON format)'
        )

    def handle(self, *args, **options):
        self.iterations = options['iterations']
        self.data_size = options['data_size']
        self.output_file = options['output_file']
        
        self.stdout.write(
            self.style.SUCCESS(f'Starting simulated cache performance benchmark...')
        )
        self.stdout.write(f'Iterations: {self.iterations}')
        self.stdout.write(f'Data size: {self.data_size}')
        
        # Generate test data
        test_data = self.generate_test_data()
        
        # Initialize cache backends
        db_cache = MockCacheBackend()
        redis_cache = MockRedisBackend()
        
        # Run benchmarks
        results = {
            'timestamp': datetime.now().isoformat(),
            'config': {
                'iterations': self.iterations,
                'data_size': self.data_size,
                'simulation': True,
            },
            'database_cache': self.benchmark_cache_backend(db_cache, test_data, 'Database'),
            'redis_cache': self.benchmark_cache_backend(redis_cache, test_data, 'Redis'),
        }
        
        # Display results
        self.display_results(results)
        
        # Save to file if requested
        if self.output_file:
            self.save_results(results)

    def generate_test_data(self):
        """Generate test data of different sizes"""
        data_sizes = {
            'small': 100,    # ~100 bytes
            'medium': 1000,  # ~1KB
            'large': 10000,  # ~10KB
        }
        
        size = data_sizes[self.data_size]
        
        # Generate different types of test data
        test_data = {
            'string_data': ''.join(random.choices(string.ascii_letters + string.digits, k=size)),
            'dict_data': {
                f'key_{i}': f'value_{i}_' + ''.join(random.choices(string.ascii_letters, k=20))
                for i in range(size // 50)
            },
            'list_data': [
                f'item_{i}_' + ''.join(random.choices(string.ascii_letters, k=10))
                for i in range(size // 20)
            ],
            'user_profile': {
                'user_id': random.randint(1, 10000),
                'username': ''.join(random.choices(string.ascii_letters, k=20)),
                'profile': {
                    'name': ''.join(random.choices(string.ascii_letters, k=30)),
                    'email': f'user{random.randint(1, 1000)}@example.com',
                    'membership_tier': random.choice(['bronze', 'silver', 'gold', 'platinum']),
                    'points': random.randint(0, 10000),
                    'preferences': {
                        f'pref_{i}': random.choice([True, False, None])
                        for i in range(10)
                    }
                },
                'order_history': [
                    {
                        'order_id': f'order_{i}',
                        'total': random.uniform(10.0, 500.0),
                        'status': random.choice(['pending', 'completed', 'cancelled'])
                    }
                    for i in range(size // 200)
                ]
            }
        }
        
        return test_data

    def benchmark_cache_backend(self, cache_backend, test_data, backend_name):
        """Benchmark a cache backend"""
        self.stdout.write(f'\nBenchmarking {backend_name} cache...')
        
        results = {}
        
        for data_type, data in test_data.items():
            self.stdout.write(f'Testing {data_type}...')
            
            # Test cache SET operations
            set_times = []
            for i in range(self.iterations):
                key = f'benchmark_{data_type}_{i}'
                
                start_time = time.perf_counter()
                cache_backend.set(key, data, timeout=300)
                end_time = time.perf_counter()
                
                set_times.append((end_time - start_time) * 1000)  # Convert to milliseconds
            
            # Test cache GET operations
            get_times = []
            cache_hits = 0
            for i in range(self.iterations):
                key = f'benchmark_{data_type}_{i}'
                
                start_time = time.perf_counter()
                result = cache_backend.get(key)
                end_time = time.perf_counter()
                
                get_times.append((end_time - start_time) * 1000)  # Convert to milliseconds
                if result is not None:
                    cache_hits += 1
            
            # Test cache DELETE operations
            delete_times = []
            for i in range(self.iterations):
                key = f'benchmark_{data_type}_{i}'
                
                start_time = time.perf_counter()
                cache_backend.delete(key)
                end_time = time.perf_counter()
                
                delete_times.append((end_time - start_time) * 1000)  # Convert to milliseconds
            
            # Calculate statistics
            results[data_type] = {
                'set_operations': {
                    'mean': statistics.mean(set_times),
                    'median': statistics.median(set_times),
                    'min': min(set_times),
                    'max': max(set_times),
                    'std_dev': statistics.stdev(set_times) if len(set_times) > 1 else 0,
                    'p95': self.percentile(set_times, 95),
                },
                'get_operations': {
                    'mean': statistics.mean(get_times),
                    'median': statistics.median(get_times),
                    'min': min(get_times),
                    'max': max(get_times),
                    'std_dev': statistics.stdev(get_times) if len(get_times) > 1 else 0,
                    'p95': self.percentile(get_times, 95),
                    'cache_hit_rate': (cache_hits / self.iterations) * 100,
                },
                'delete_operations': {
                    'mean': statistics.mean(delete_times),
                    'median': statistics.median(delete_times),
                    'min': min(delete_times),
                    'max': max(delete_times),
                    'std_dev': statistics.stdev(delete_times) if len(delete_times) > 1 else 0,
                    'p95': self.percentile(delete_times, 95),
                },
                'data_size_bytes': len(str(data).encode('utf-8')),
            }
        
        # Add query count for database cache
        if hasattr(cache_backend, 'query_count'):
            results['database_queries'] = cache_backend.query_count
        
        return results

    def percentile(self, data, percentile):
        """Calculate percentile of data"""
        sorted_data = sorted(data)
        index = int((percentile / 100) * len(sorted_data))
        return sorted_data[min(index, len(sorted_data) - 1)]

    def display_results(self, results):
        """Display benchmark results in a formatted way"""
        self.stdout.write('\n' + '='*80)
        self.stdout.write(self.style.SUCCESS('CACHE PERFORMANCE BENCHMARK RESULTS (SIMULATED)'))
        self.stdout.write('='*80)
        
        db_results = results['database_cache']
        redis_results = results['redis_cache']
        
        # Summary table
        self.stdout.write('\nPERFORMANCE COMPARISON:')
        self.stdout.write('-' * 80)
        self.stdout.write(f"{'Data Type':<15} {'Operation':<8} {'DB Cache':<12} {'Redis':<12} {'Ratio':<8}")
        self.stdout.write('-' * 80)
        
        for data_type in db_results:
            if data_type == 'database_queries':
                continue
                
            # SET operations
            db_set = db_results[data_type]['set_operations']['mean']
            redis_set = redis_results[data_type]['set_operations']['mean']
            set_ratio = db_set / redis_set if redis_set > 0 else 0
            
            self.stdout.write(f"{data_type:<15} {'SET':<8} {db_set:<12.2f} {redis_set:<12.2f} {set_ratio:<8.1f}x")
            
            # GET operations
            db_get = db_results[data_type]['get_operations']['mean']
            redis_get = redis_results[data_type]['get_operations']['mean']
            get_ratio = db_get / redis_get if redis_get > 0 else 0
            
            self.stdout.write(f"{'':<15} {'GET':<8} {db_get:<12.2f} {redis_get:<12.2f} {get_ratio:<8.1f}x")
            
            # DELETE operations
            db_del = db_results[data_type]['delete_operations']['mean']
            redis_del = redis_results[data_type]['delete_operations']['mean']
            del_ratio = db_del / redis_del if redis_del > 0 else 0
            
            self.stdout.write(f"{'':<15} {'DELETE':<8} {db_del:<12.2f} {redis_del:<12.2f} {del_ratio:<8.1f}x")
            self.stdout.write('-' * 80)
        
        # Database impact
        if 'database_queries' in db_results:
            self.stdout.write(f"\nDATABASE IMPACT:")
            self.stdout.write(f"Total database queries: {db_results['database_queries']}")
            self.stdout.write(f"Queries per operation: {db_results['database_queries'] / (self.iterations * 3 * len([k for k in db_results.keys() if k != 'database_queries'])):.1f}")
        
        # Performance summary
        self.stdout.write('\nPERFORMANCE SUMMARY:')
        self.stdout.write('-' * 40)
        
        # Calculate overall averages
        all_db_sets = [db_results[dt]['set_operations']['mean'] for dt in db_results if dt != 'database_queries']
        all_redis_sets = [redis_results[dt]['set_operations']['mean'] for dt in redis_results if dt != 'database_queries']
        
        avg_db_set = statistics.mean(all_db_sets)
        avg_redis_set = statistics.mean(all_redis_sets)
        
        self.stdout.write(f"Average SET latency - DB: {avg_db_set:.2f}ms, Redis: {avg_redis_set:.2f}ms")
        self.stdout.write(f"Database cache is {avg_db_set/avg_redis_set:.1f}x slower than Redis")
        self.stdout.write(f"Acceptable for non-real-time applications")

    def save_results(self, results):
        """Save results to JSON file"""
        try:
            with open(self.output_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            
            self.stdout.write(
                self.style.SUCCESS(f'\nResults saved to: {self.output_file}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Failed to save results: {e}')
            )