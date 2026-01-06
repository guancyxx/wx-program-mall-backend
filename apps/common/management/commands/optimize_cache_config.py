"""
Management command to optimize database cache configuration and indexes
"""

from django.core.management.base import BaseCommand
from django.db import connection
from django.core.cache import cache
from django.conf import settings
import time


class Command(BaseCommand):
    help = 'Optimize database cache configuration and create performance indexes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--create-indexes',
            action='store_true',
            help='Create optimized indexes for cache table'
        )
        parser.add_argument(
            '--test-performance',
            action='store_true',
            help='Test cache performance after optimization'
        )
        parser.add_argument(
            '--analyze-table',
            action='store_true',
            help='Analyze cache table statistics'
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting cache configuration optimization...')
        )
        
        if options['create_indexes']:
            self.create_optimized_indexes()
        
        if options['analyze_table']:
            self.analyze_cache_table()
        
        if options['test_performance']:
            self.test_cache_performance()
        
        self.display_optimization_recommendations()

    def create_optimized_indexes(self):
        """Create optimized indexes for the cache table"""
        self.stdout.write('\nCreating optimized indexes...')
        
        cache_table = settings.CACHES['default']['LOCATION']
        
        with connection.cursor() as cursor:
            # Check if table exists
            cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = DATABASE() 
                AND table_name = %s
            """, [cache_table])
            
            if cursor.fetchone()[0] == 0:
                self.stdout.write(
                    self.style.WARNING(f'Cache table {cache_table} does not exist. Run createcachetable first.')
                )
                return
            
            # Get existing indexes
            cursor.execute(f"SHOW INDEX FROM {cache_table}")
            existing_indexes = {row[2] for row in cursor.fetchall()}
            
            # Create composite index for cache key and expiration
            if 'idx_cache_key_expires' not in existing_indexes:
                try:
                    cursor.execute(f"""
                        CREATE INDEX idx_cache_key_expires 
                        ON {cache_table} (cache_key, expires)
                    """)
                    self.stdout.write(
                        self.style.SUCCESS('✓ Created composite index: idx_cache_key_expires')
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f'Index idx_cache_key_expires may already exist: {e}')
                    )
            
            # Create index for expiration cleanup
            if 'idx_expires_cleanup' not in existing_indexes:
                try:
                    cursor.execute(f"""
                        CREATE INDEX idx_expires_cleanup 
                        ON {cache_table} (expires)
                    """)
                    self.stdout.write(
                        self.style.SUCCESS('✓ Created expiration index: idx_expires_cleanup')
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f'Index idx_expires_cleanup may already exist: {e}')
                    )
            
            # Optimize table for better performance
            try:
                cursor.execute(f"OPTIMIZE TABLE {cache_table}")
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Optimized table: {cache_table}')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'Table optimization failed: {e}')
                )

    def analyze_cache_table(self):
        """Analyze cache table statistics and structure"""
        self.stdout.write('\nAnalyzing cache table...')
        
        cache_table = settings.CACHES['default']['LOCATION']
        
        with connection.cursor() as cursor:
            # Table size and row count
            cursor.execute(f"""
                SELECT 
                    COUNT(*) as row_count,
                    ROUND(AVG(LENGTH(value))) as avg_value_size,
                    ROUND(SUM(LENGTH(value))/1024/1024, 2) as total_size_mb
                FROM {cache_table}
            """)
            
            row = cursor.fetchone()
            if row:
                self.stdout.write(f"Cache entries: {row[0]}")
                self.stdout.write(f"Average value size: {row[1]} bytes")
                self.stdout.write(f"Total cache size: {row[2]} MB")
            
            # Expired entries
            cursor.execute(f"""
                SELECT COUNT(*) as expired_count
                FROM {cache_table}
                WHERE expires < NOW()
            """)
            
            expired_count = cursor.fetchone()[0]
            self.stdout.write(f"Expired entries: {expired_count}")
            
            # Index information
            cursor.execute(f"SHOW INDEX FROM {cache_table}")
            indexes = cursor.fetchall()
            
            self.stdout.write('\nExisting indexes:')
            for index in indexes:
                self.stdout.write(f"  - {index[2]} on column {index[4]}")
            
            # Table status
            cursor.execute(f"""
                SELECT 
                    engine,
                    table_rows,
                    avg_row_length,
                    data_length,
                    index_length
                FROM information_schema.tables 
                WHERE table_schema = DATABASE() 
                AND table_name = %s
            """, [cache_table])
            
            table_info = cursor.fetchone()
            if table_info:
                self.stdout.write(f'\nTable information:')
                self.stdout.write(f"  Engine: {table_info[0]}")
                self.stdout.write(f"  Estimated rows: {table_info[1]}")
                self.stdout.write(f"  Average row length: {table_info[2]} bytes")
                self.stdout.write(f"  Data size: {table_info[3] / 1024 / 1024:.2f} MB")
                self.stdout.write(f"  Index size: {table_info[4] / 1024 / 1024:.2f} MB")

    def test_cache_performance(self):
        """Test cache performance with current configuration"""
        self.stdout.write('\nTesting cache performance...')
        
        test_data = {
            'small': 'x' * 100,
            'medium': 'x' * 1000,
            'large': 'x' * 10000,
        }
        
        results = {}
        
        for size_name, data in test_data.items():
            # Test SET performance
            start_time = time.perf_counter()
            for i in range(100):
                cache.set(f'perf_test_{size_name}_{i}', data, timeout=60)
            set_time = (time.perf_counter() - start_time) * 1000 / 100
            
            # Test GET performance
            start_time = time.perf_counter()
            for i in range(100):
                cache.get(f'perf_test_{size_name}_{i}')
            get_time = (time.perf_counter() - start_time) * 1000 / 100
            
            # Test DELETE performance
            start_time = time.perf_counter()
            for i in range(100):
                cache.delete(f'perf_test_{size_name}_{i}')
            delete_time = (time.perf_counter() - start_time) * 1000 / 100
            
            results[size_name] = {
                'set': set_time,
                'get': get_time,
                'delete': delete_time,
            }
        
        # Display results
        self.stdout.write('\nPerformance test results:')
        self.stdout.write('-' * 50)
        self.stdout.write(f"{'Size':<10} {'SET (ms)':<10} {'GET (ms)':<10} {'DEL (ms)':<10}")
        self.stdout.write('-' * 50)
        
        for size_name, metrics in results.items():
            self.stdout.write(
                f"{size_name:<10} {metrics['set']:<10.2f} "
                f"{metrics['get']:<10.2f} {metrics['delete']:<10.2f}"
            )

    def display_optimization_recommendations(self):
        """Display cache optimization recommendations"""
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('CACHE OPTIMIZATION RECOMMENDATIONS'))
        self.stdout.write('='*60)
        
        current_config = settings.CACHES['default']
        
        self.stdout.write('\nCurrent Configuration:')
        self.stdout.write(f"  Backend: {current_config['BACKEND']}")
        self.stdout.write(f"  Location: {current_config['LOCATION']}")
        self.stdout.write(f"  Timeout: {current_config['TIMEOUT']}s")
        self.stdout.write(f"  Max Entries: {current_config['OPTIONS'].get('MAX_ENTRIES', 'Not set')}")
        self.stdout.write(f"  Cull Frequency: {current_config['OPTIONS'].get('CULL_FREQUENCY', 'Not set')}")
        
        self.stdout.write('\nOptimized Configuration Recommendations:')
        self.stdout.write("""
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'mall_server_cache',
        'TIMEOUT': 300,  # 5 minutes default
        'OPTIONS': {
            'MAX_ENTRIES': 15000,    # Increased for better hit rate
            'CULL_FREQUENCY': 4,     # Remove 1/4 when max reached (gentler)
        },
        'KEY_PREFIX': 'mall_server',
    }
}
        """)
        
        self.stdout.write('\nCache Strategy Recommendations:')
        self.stdout.write('1. User Profile Data: 30 minutes timeout')
        self.stdout.write('2. Product Catalog: 60 minutes timeout')
        self.stdout.write('3. Category Data: 2 hours timeout')
        self.stdout.write('4. Membership Calculations: 15 minutes timeout')
        self.stdout.write('5. Points Balances: 10 minutes timeout')
        
        self.stdout.write('\nDatabase Optimization:')
        self.stdout.write('1. Ensure proper indexing (run with --create-indexes)')
        self.stdout.write('2. Regular table optimization (weekly OPTIMIZE TABLE)')
        self.stdout.write('3. Monitor cache hit rates (target >80%)')
        self.stdout.write('4. Clean expired entries regularly')
        
        self.stdout.write('\nMonitoring Setup:')
        self.stdout.write('1. Track cache hit/miss ratios')
        self.stdout.write('2. Monitor cache operation latency')
        self.stdout.write('3. Watch database query impact')
        self.stdout.write('4. Set alerts for performance degradation')