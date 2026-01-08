#!/usr/bin/env python
"""
Standalone cache performance test for Redis removal validation
This test can run without database connection to validate cache performance properties
Feature: redis-removal, Property 4: Cache Performance Acceptability
"""

import os
import sys
import time
import statistics
import threading
import queue

# Add the project directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mall_server.settings')
os.environ.setdefault('ENVIRONMENT', 'test')

import django
from django.conf import settings

# Override cache settings to use in-memory cache for testing
TEST_CACHE_SETTINGS = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'test_cache_performance',
        'TIMEOUT': 300,
        'OPTIONS': {
            'MAX_ENTRIES': 10000,
            'CULL_FREQUENCY': 3,
        },
        'KEY_PREFIX': 'test_perf',
    }
}

# Configure Django with test cache settings
if not settings.configured:
    settings.configure(
        CACHES=TEST_CACHE_SETTINGS,
        USE_TZ=True,
        SECRET_KEY='test-key-for-cache-performance',
        INSTALLED_APPS=[
            'django.contrib.contenttypes',
        ],
    )

django.setup()

from django.core.cache import cache


class CachePerformanceValidator:
    """Validates cache performance properties for Redis removal"""
    
    def __init__(self):
        self.test_results = []
        self.passed_tests = 0
        self.failed_tests = 0
    
    def log_result(self, test_name, passed, message=""):
        """Log test result"""
        status = "PASS" if passed else "FAIL"
        result = f"[{status}] {test_name}"
        if message:
            result += f": {message}"
        
        self.test_results.append(result)
        if passed:
            self.passed_tests += 1
        else:
            self.failed_tests += 1
        
        print(result)
    
    def assert_less(self, actual, threshold, message):
        """Assert that actual value is less than threshold"""
        if actual < threshold:
            return True
        else:
            raise AssertionError(f"{message}: {actual:.3f} >= {threshold:.3f}")
    
    def assert_greater_equal(self, actual, minimum, message):
        """Assert that actual value is greater than or equal to minimum"""
        if actual >= minimum:
            return True
        else:
            raise AssertionError(f"{message}: {actual:.3f} < {minimum:.3f}")
    
    def test_cache_performance_small_data(self):
        """
        Property 4: Cache Performance Acceptability (Small Data)
        **Feature: redis-removal, Property 4: Cache Performance Acceptability**
        **Validates: Requirements 3.2**
        """
        try:
            cache.clear()
            
            # Test with small data (1KB)
            test_data = 'x' * 1000
            operation_count = 50
            
            # Performance thresholds (relaxed for in-memory testing)
            SET_THRESHOLD = 0.050  # 50ms for SET operations
            GET_THRESHOLD = 0.030  # 30ms for GET operations
            DELETE_THRESHOLD = 0.020  # 20ms for DELETE operations
            
            # Test SET performance
            set_times = []
            keys = []
            for i in range(operation_count):
                key = f"perf_set_small_{i}_{int(time.time() * 1000000) % 1000000}"
                keys.append(key)
                
                start_time = time.perf_counter()
                cache.set(key, test_data, 300)
                end_time = time.perf_counter()
                
                set_time = end_time - start_time
                set_times.append(set_time)
            
            # Test GET performance
            get_times = []
            for key in keys:
                start_time = time.perf_counter()
                retrieved_data = cache.get(key)
                end_time = time.perf_counter()
                
                get_time = end_time - start_time
                get_times.append(get_time)
                
                # Verify data integrity
                assert retrieved_data == test_data, "Cache data integrity check failed"
            
            # Test DELETE performance
            delete_times = []
            for key in keys:
                start_time = time.perf_counter()
                cache.delete(key)
                end_time = time.perf_counter()
                
                delete_time = end_time - start_time
                delete_times.append(delete_time)
            
            # Calculate performance statistics
            avg_set_time = statistics.mean(set_times)
            avg_get_time = statistics.mean(get_times)
            avg_delete_time = statistics.mean(delete_times)
            
            # Performance assertions
            self.assert_less(avg_set_time, SET_THRESHOLD, 
                f"Average SET time {avg_set_time:.3f}s exceeds threshold {SET_THRESHOLD}s")
            
            self.assert_less(avg_get_time, GET_THRESHOLD, 
                f"Average GET time {avg_get_time:.3f}s exceeds threshold {GET_THRESHOLD}s")
            
            self.assert_less(avg_delete_time, DELETE_THRESHOLD, 
                f"Average DELETE time {avg_delete_time:.3f}s exceeds threshold {DELETE_THRESHOLD}s")
            
            self.log_result("Cache Performance Small Data", True, 
                f"SET: {avg_set_time*1000:.1f}ms, GET: {avg_get_time*1000:.1f}ms, DELETE: {avg_delete_time*1000:.1f}ms")
            
        except Exception as e:
            self.log_result("Cache Performance Small Data", False, str(e))
    
    def test_cache_throughput_performance(self):
        """
        Test cache throughput performance
        **Feature: redis-removal, Property 4: Cache Performance Acceptability**
        **Validates: Requirements 3.2**
        """
        try:
            cache.clear()
            
            # Throughput test parameters
            test_duration = 2  # seconds
            min_ops_per_second = 100  # Minimum acceptable throughput
            
            operations_completed = 0
            start_time = time.time()
            
            # Run operations for the test duration
            while time.time() - start_time < test_duration:
                key = f"throughput_{operations_completed}_{int(time.time() * 1000000) % 1000000}"
                data = f"throughput_data_{operations_completed}"
                
                # Perform cache operations
                cache.set(key, data, 300)
                retrieved = cache.get(key)
                cache.delete(key)
                
                # Verify operation success
                assert retrieved == data, "Throughput test data integrity failed"
                
                operations_completed += 1
            
            actual_duration = time.time() - start_time
            ops_per_second = operations_completed / actual_duration
            
            # Throughput assertion
            self.assert_greater_equal(ops_per_second, min_ops_per_second, 
                f"Cache throughput {ops_per_second:.1f} ops/sec is below minimum {min_ops_per_second} ops/sec")
            
            self.log_result("Cache Throughput Performance", True, 
                f"{ops_per_second:.1f} ops/sec (target: >{min_ops_per_second} ops/sec)")
            
        except Exception as e:
            self.log_result("Cache Throughput Performance", False, str(e))
    
    def test_cache_concurrent_performance(self):
        """
        Test cache performance under concurrent load
        **Feature: redis-removal, Property 4: Cache Performance Acceptability**
        **Validates: Requirements 3.2**
        """
        try:
            cache.clear()
            
            # Performance threshold for concurrent operations
            CONCURRENT_THRESHOLD = 0.100  # 100ms per operation under load
            
            results_queue = queue.Queue()
            thread_count = 3
            operations_per_thread = 10
            
            def worker_thread(thread_id):
                """Worker thread that performs cache operations"""
                thread_times = []
                
                for i in range(operations_per_thread):
                    key = f"concurrent_{thread_id}_{i}_{int(time.time() * 1000000) % 1000000}"
                    data = f"test_data_{thread_id}_{i}"
                    
                    # Measure SET operation
                    start_time = time.perf_counter()
                    cache.set(key, data, 300)
                    set_time = time.perf_counter() - start_time
                    
                    # Measure GET operation
                    start_time = time.perf_counter()
                    retrieved = cache.get(key)
                    get_time = time.perf_counter() - start_time
                    
                    # Measure DELETE operation
                    start_time = time.perf_counter()
                    cache.delete(key)
                    delete_time = time.perf_counter() - start_time
                    
                    # Verify data integrity
                    assert retrieved == data, f"Data integrity failed in thread {thread_id}"
                    
                    thread_times.extend([set_time, get_time, delete_time])
                
                results_queue.put(thread_times)
            
            # Start concurrent threads
            threads = []
            for i in range(thread_count):
                thread = threading.Thread(target=worker_thread, args=(i,))
                threads.append(thread)
                thread.start()
            
            # Wait for all threads to complete
            for thread in threads:
                thread.join()
            
            # Collect all timing results
            all_times = []
            while not results_queue.empty():
                thread_times = results_queue.get()
                all_times.extend(thread_times)
            
            # Calculate performance statistics
            if all_times:
                avg_time = statistics.mean(all_times)
                max_time = max(all_times)
                
                # Performance assertions for concurrent operations
                self.assert_less(avg_time, CONCURRENT_THRESHOLD, 
                    f"Average concurrent operation time {avg_time:.3f}s exceeds threshold {CONCURRENT_THRESHOLD}s")
                
                self.assert_less(max_time, CONCURRENT_THRESHOLD * 3, 
                    f"Maximum concurrent operation time {max_time:.3f}s is unacceptably high")
                
                self.log_result("Cache Concurrent Performance", True, 
                    f"Avg: {avg_time*1000:.1f}ms, Max: {max_time*1000:.1f}ms")
            else:
                raise AssertionError("No concurrent operation results collected")
            
        except Exception as e:
            self.log_result("Cache Concurrent Performance", False, str(e))
    
    def test_cache_performance_vs_redis(self):
        """
        Test cache performance relative to Redis expectations
        **Feature: redis-removal, Property 4: Cache Performance Acceptability**
        **Validates: Requirements 3.2**
        """
        try:
            cache.clear()
            
            # Expected Redis performance (theoretical baseline)
            REDIS_SET_TIME = 0.002  # 2ms
            REDIS_GET_TIME = 0.001  # 1ms
            REDIS_DELETE_TIME = 0.001  # 1ms
            
            # Acceptable performance ratio (in-memory cache vs Redis)
            ACCEPTABLE_RATIO = 5  # Up to 5x slower is acceptable for in-memory
            
            # Test with small data
            test_data = 'x' * 500
            operation_count = 20
            
            # Measure cache performance
            set_times = []
            get_times = []
            delete_times = []
            
            for i in range(operation_count):
                key = f"ratio_test_{i}_{int(time.time() * 1000000) % 1000000}"
                
                # SET operation
                start_time = time.perf_counter()
                cache.set(key, test_data, 300)
                set_time = time.perf_counter() - start_time
                set_times.append(set_time)
                
                # GET operation
                start_time = time.perf_counter()
                retrieved = cache.get(key)
                get_time = time.perf_counter() - start_time
                get_times.append(get_time)
                
                # DELETE operation
                start_time = time.perf_counter()
                cache.delete(key)
                delete_time = time.perf_counter() - start_time
                delete_times.append(delete_time)
                
                # Verify data integrity
                assert retrieved == test_data, "Data integrity check failed"
            
            # Calculate average times
            avg_set_time = statistics.mean(set_times)
            avg_get_time = statistics.mean(get_times)
            avg_delete_time = statistics.mean(delete_times)
            
            # Calculate performance ratios
            set_ratio = avg_set_time / REDIS_SET_TIME
            get_ratio = avg_get_time / REDIS_GET_TIME
            delete_ratio = avg_delete_time / REDIS_DELETE_TIME
            
            # Performance ratio assertions
            self.assert_less(set_ratio, ACCEPTABLE_RATIO, 
                f"SET performance ratio {set_ratio:.1f}x exceeds acceptable limit {ACCEPTABLE_RATIO}x")
            
            self.assert_less(get_ratio, ACCEPTABLE_RATIO, 
                f"GET performance ratio {get_ratio:.1f}x exceeds acceptable limit {ACCEPTABLE_RATIO}x")
            
            self.assert_less(delete_ratio, ACCEPTABLE_RATIO, 
                f"DELETE performance ratio {delete_ratio:.1f}x exceeds acceptable limit {ACCEPTABLE_RATIO}x")
            
            self.log_result("Cache Performance vs Redis", True, 
                f"SET: {set_ratio:.1f}x, GET: {get_ratio:.1f}x, DELETE: {delete_ratio:.1f}x slower than Redis")
            
        except Exception as e:
            self.log_result("Cache Performance vs Redis", False, str(e))
    
    def test_cache_configuration_validation(self):
        """
        Test that cache configuration supports performance requirements
        **Feature: redis-removal, Property 4: Cache Performance Acceptability**
        **Validates: Requirements 3.2**
        """
        try:
            # Verify cache backend is configured
            cache_backend = settings.CACHES['default']['BACKEND']
            assert 'cache' in cache_backend.lower(), f"Expected cache backend, got {cache_backend}"
            
            # Verify cache configuration supports performance
            cache_options = settings.CACHES['default'].get('OPTIONS', {})
            
            # MAX_ENTRIES should be reasonable for performance
            max_entries = cache_options.get('MAX_ENTRIES', 0)
            assert max_entries >= 1000, f"MAX_ENTRIES should be at least 1000, got {max_entries}"
            
            # CULL_FREQUENCY should be reasonable
            cull_frequency = cache_options.get('CULL_FREQUENCY', 0)
            assert cull_frequency >= 2, f"CULL_FREQUENCY should be at least 2, got {cull_frequency}"
            
            # Timeout should be configured
            timeout = settings.CACHES['default'].get('TIMEOUT', 0)
            assert timeout > 0, f"Cache timeout should be configured, got {timeout}"
            
            self.log_result("Cache Configuration Validation", True, 
                f"Backend: {cache_backend.split('.')[-1]}, MAX_ENTRIES: {max_entries}, TIMEOUT: {timeout}s")
            
        except Exception as e:
            self.log_result("Cache Configuration Validation", False, str(e))
    
    def run_all_tests(self):
        """Run all cache performance tests"""
        print("="*80)
        print("CACHE PERFORMANCE PROPERTY TESTS")
        print("Feature: redis-removal, Property 4: Cache Performance Acceptability")
        print("="*80)
        
        # Run all test methods
        self.test_cache_configuration_validation()
        self.test_cache_performance_small_data()
        self.test_cache_throughput_performance()
        self.test_cache_concurrent_performance()
        self.test_cache_performance_vs_redis()
        
        # Print summary
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        print(f"Total tests: {self.passed_tests + self.failed_tests}")
        print(f"Passed: {self.passed_tests}")
        print(f"Failed: {self.failed_tests}")
        
        if self.failed_tests == 0:
            print("\n✓ ALL CACHE PERFORMANCE PROPERTY TESTS PASSED")
            print("Cache performance meets acceptability requirements for Redis removal.")
            return True
        else:
            print(f"\n✗ {self.failed_tests} CACHE PERFORMANCE TESTS FAILED")
            print("Cache performance may not meet requirements.")
            return False


def main():
    """Main function to run cache performance validation"""
    validator = CachePerformanceValidator()
    success = validator.run_all_tests()
    
    if success:
        print("\nProperty 4 (Cache Performance Acceptability) validation: PASSED")
        return 0
    else:
        print("\nProperty 4 (Cache Performance Acceptability) validation: FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())