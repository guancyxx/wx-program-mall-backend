"""
Management command to benchmark cache performance with database backend
"""

import time
import statistics
import json
from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.db import connection
from django.conf import settings
from django.utils import timezone
from datetime import datetime, timedelta
import random
import string


class Command(BaseCommand):
    help = 'Benchmark cache performance with database backend'

    def add_arguments(self, parser):
        parser.add_argument(
            '--iterations',
            type=int,
            default=1000,
            help='Number of iterations for each test (default: 1000)'
        )
        parser.add_argument(
            '--data-size',
            type=str,
            default='small',
            choices=['small', 'medium', 'large'],
            help='Size of test data (default: small)'
        )
        parser.add_argument(
            '--output-file',
            type=str,
            help='Output file for benchmark results (JSON format)'
        )
        parser.add_argument(
            '--compare-redis',
            action='store_true',
            help='Include Redis comparison if available'
        )

    def handle(self, *args, **options):
        self.iterations = options['iterations']
        self.data_size = options['data_size']
        self.output_file = options['output_file']
        self.compare_redis = options['compare_redis']
        
        self.stdout.write(
            self.style.SUCCESS(f'Starting cache performance benchmark...')
        )
        self.stdout.write(f'Iterations: {self.iterations}')
        self.stdout.write(f'Data size: {self.data_size}')
        
        # Generate test data
        test_data = self.generate_test_data()
        
        # Run benchmarks
        results = {
            'timestamp': datetime.now().isoformat(),
            'config': {
                'iterations': self.iterations,
                'data_size': self.data_size,
                'cache_backend': settings.CACHES['default']['BACKEND'],
                'cache_location': settings.CACHES['default']['LOCATION'],
            },
            'database_cache': self.benchmark_database_cache(test_data),
        }
        
        # Add Redis comparison if requested
        if self.compare_redis:
            results['redis_comparison'] = self.benchmark_redis_comparison(test_data)
        
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
            'complex_data': {
                'user_id': random.randint(1, 10000),
                'username': ''.join(random.choices(string.ascii_letters, k=20)),
                'profile': {
                    'name': ''.join(random.choices(string.ascii_letters, k=30)),
                    'email': f'user{random.randint(1, 1000)}@example.com',
                    'preferences': {
                        f'pref_{i}': random.choice([True, False, None])
                        for i in range(20)
                    }
                },
                'metadata': [
                    {'key': f'meta_{i}', 'value': random.randint(1, 100)}
                    for i in range(size // 100)
                ]
            }
        }
        
        return test_data

    def benchmark_database_cache(self, test_data):
        """Benchmark database cache performance"""
        self.stdout.write('\nBenchmarking database cache...')
        
        results = {}
        
        for data_type, data in test_data.items():
            self.stdout.write(f'Testing {data_type}...')
            
            # Test cache SET operations
            set_times = []
            for i in range(self.iterations):
                key = f'benchmark_{data_type}_{i}'
                
                start_time = time.perf_counter()
                cache.set(key, data, timeout=300)
                end_time = time.perf_counter()
                
                set_times.append((end_time - start_time) * 1000)  # Convert to milliseconds
            
            # Test cache GET operations
            get_times = []
            cache_hits = 0
            for i in range(self.iterations):
                key = f'benchmark_{data_type}_{i}'
                
                start_time = time.perf_counter()
                result = cache.get(key)
                end_time = time.perf_counter()
                
                get_times.append((end_time - start_time) * 1000)  # Convert to milliseconds
                if result is not None:
                    cache_hits += 1
            
            # Test cache DELETE operations
            delete_times = []
            for i in range(self.iterations):
                key = f'benchmark_{data_type}_{i}'
                
                start_time = time.perf_counter()
                cache.delete(key)
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
                },
                'get_operations': {
                    'mean': statistics.mean(get_times),
                    'median': statistics.median(get_times),
                    'min': min(get_times),
                    'max': max(get_times),
                    'std_dev': statistics.stdev(get_times) if len(get_times) > 1 else 0,
                    'cache_hit_rate': (cache_hits / self.iterations) * 100,
                },
                'delete_operations': {
                    'mean': statistics.mean(delete_times),
                    'median': statistics.median(delete_times),
                    'min': min(delete_times),
                    'max': max(delete_times),
                    'std_dev': statistics.stdev(delete_times) if len(delete_times) > 1 else 0,
                },
                'data_size_bytes': len(str(data).encode('utf-8')),
            }
        
        # Test database query impact
        results['database_impact'] = self.measure_database_impact()
        
        return results

    def measure_database_impact(self):
        """Measure the impact on database performance"""
        self.stdout.write('Measuring database query impact...')
        
        # Clear existing queries
        connection.queries_log.clear()
        initial_query_count = len(connection.queries)
        
        # Perform cache operations and measure database queries
        start_time = time.perf_counter()
        
        for i in range(100):  # Smaller sample for database impact
            key = f'db_impact_test_{i}'
            data = {'test': f'data_{i}', 'timestamp': time.time()}
            
            cache.set(key, data, timeout=60)
            cache.get(key)
            cache.delete(key)
        
        end_time = time.perf_counter()
        
        final_query_count = len(connection.queries)
        query_count = final_query_count - initial_query_count
        
        # Analyze query types
        cache_queries = [
            query for query in connection.queries[initial_query_count:]
            if 'mall_server_cache' in query['sql']
        ]
        
        return {
            'total_time_ms': (end_time - start_time) * 1000,
            'total_queries': query_count,
            'cache_queries': len(cache_queries),
            'avg_query_time_ms': statistics.mean([
                float(query['time']) * 1000 for query in cache_queries
            ]) if cache_queries else 0,
            'sample_queries': [query['sql'] for query in cache_queries[:3]],
        }

    def benchmark_redis_comparison(self, test_data):
        """Benchmark Redis for comparison (if available)"""
        try:
            import redis
            
            # Try to connect to Redis
            redis_client = redis.Redis(host='localhost', port=6379, db=1, decode_responses=True)
            redis_client.ping()
            
            self.stdout.write('\nBenchmarking Redis for comparison...')
            
            results = {}
            
            for data_type, data in test_data.items():
                # Convert data to JSON for Redis storage
                json_data = json.dumps(data)
                
                # Test Redis SET operations
                set_times = []
                for i in range(self.iterations):
                    key = f'redis_benchmark_{data_type}_{i}'
                    
                    start_time = time.perf_counter()
                    redis_client.setex(key, 300, json_data)
                    end_time = time.perf_counter()
                    
                    set_times.append((end_time - start_time) * 1000)
                
                # Test Redis GET operations
                get_times = []
                for i in range(self.iterations):
                    key = f'redis_benchmark_{data_type}_{i}'
                    
                    start_time = time.perf_counter()
                    result = redis_client.get(key)
                    end_time = time.perf_counter()
                    
                    get_times.append((end_time - start_time) * 1000)
                
                # Test Redis DELETE operations
                delete_times = []
                for i in range(self.iterations):
                    key = f'redis_benchmark_{data_type}_{i}'
                    
                    start_time = time.perf_counter()
                    redis_client.delete(key)
                    end_time = time.perf_counter()
                    
                    delete_times.append((end_time - start_time) * 1000)
                
                results[data_type] = {
                    'set_operations': {
                        'mean': statistics.mean(set_times),
                        'median': statistics.median(set_times),
                    },
                    'get_operations': {
                        'mean': statistics.mean(get_times),
                        'median': statistics.median(get_times),
                    },
                    'delete_operations': {
                        'mean': statistics.mean(delete_times),
                        'median': statistics.median(delete_times),
                    },
                }
            
            return results
            
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'Redis comparison not available: {e}')
            )
            return None

    def display_results(self, results):
        """Display benchmark results in a formatted way"""
        self.stdout.write('\n' + '='*80)
        self.stdout.write(self.style.SUCCESS('CACHE PERFORMANCE BENCHMARK RESULTS'))
        self.stdout.write('='*80)
        
        db_results = results['database_cache']
        
        # Summary table
        self.stdout.write('\nSUMMARY (Database Cache):')
        self.stdout.write('-' * 60)
        self.stdout.write(f"{'Data Type':<15} {'SET (ms)':<12} {'GET (ms)':<12} {'DEL (ms)':<12}")
        self.stdout.write('-' * 60)
        
        for data_type, metrics in db_results.items():
            if data_type == 'database_impact':
                continue
                
            set_avg = metrics['set_operations']['mean']
            get_avg = metrics['get_operations']['mean']
            del_avg = metrics['delete_operations']['mean']
            
            self.stdout.write(f"{data_type:<15} {set_avg:<12.2f} {get_avg:<12.2f} {del_avg:<12.2f}")
        
        # Database impact
        db_impact = db_results['database_impact']
        self.stdout.write('\nDATABASE IMPACT:')
        self.stdout.write('-' * 40)
        self.stdout.write(f"Total queries: {db_impact['total_queries']}")
        self.stdout.write(f"Cache queries: {db_impact['cache_queries']}")
        self.stdout.write(f"Avg query time: {db_impact['avg_query_time_ms']:.2f}ms")
        
        # Redis comparison if available
        if 'redis_comparison' in results and results['redis_comparison']:
            self.stdout.write('\nREDIS COMPARISON:')
            self.stdout.write('-' * 60)
            self.stdout.write(f"{'Data Type':<15} {'DB SET':<10} {'Redis SET':<12} {'Ratio':<8}")
            self.stdout.write('-' * 60)
            
            redis_results = results['redis_comparison']
            for data_type in db_results:
                if data_type == 'database_impact':
                    continue
                    
                db_set = db_results[data_type]['set_operations']['mean']
                redis_set = redis_results[data_type]['set_operations']['mean']
                ratio = db_set / redis_set if redis_set > 0 else 0
                
                self.stdout.write(f"{data_type:<15} {db_set:<10.2f} {redis_set:<12.2f} {ratio:<8.1f}x")

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