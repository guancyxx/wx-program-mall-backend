"""
Export database data as fixtures using Django's dumpdata command.
Handles encoding issues on Windows.
"""
import os
import sys
import django
from pathlib import Path

# Setup Django
sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mall_server.settings')
django.setup()

from django.core.management import call_command
from django.conf import settings

def export_fixtures():
    """Export all app data to fixtures"""
    # Create fixtures directory
    fixtures_dir = Path(__file__).parent.parent / 'fixtures'
    fixtures_dir.mkdir(exist_ok=True)
    
    # Apps to export
    apps = ['users', 'products', 'orders', 'payments', 'points', 'membership', 'common']
    
    # Exclude system models
    exclude = [
        'contenttypes.contenttype',
        'sessions.session',
        'admin.logentry',
        'auth.permission',
        'auth.group',
    ]
    
    output_file = fixtures_dir / 'initial_data.json'
    
    print(f'Exporting data to {output_file}...')
    print(f'Apps: {", ".join(apps)}')
    print(f'Excluding: {", ".join(exclude)}')
    
    try:
        # Use call_command with proper encoding
        with open(output_file, 'w', encoding='utf-8') as f:
            call_command(
                'dumpdata',
                *apps,
                format='json',
                indent=2,
                exclude=exclude,
                stdout=f,
                verbosity=1,
            )
        
        file_size = output_file.stat().st_size
        print(f'\n✓ Export completed!')
        print(f'  File: {output_file}')
        print(f'  Size: {file_size:,} bytes')
        print(f'\nTo load this data, use:')
        print(f'  python manage.py loaddata fixtures/initial_data.json')
        
    except Exception as e:
        print(f'\n✗ Export failed: {str(e)}')
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    export_fixtures()



