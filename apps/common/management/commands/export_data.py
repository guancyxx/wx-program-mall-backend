"""
Export database data as fixtures for initial data.
Usage: python manage.py export_data [--output fixtures/] [--apps users products orders ...]
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings
import os
import json
from pathlib import Path


class Command(BaseCommand):
    help = 'Export database data as fixtures for initial data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            type=str,
            default='fixtures',
            help='Output directory for fixtures (default: fixtures/)',
        )
        parser.add_argument(
            '--apps',
            nargs='+',
            default=None,
            help='Specific apps to export (default: all local apps)',
        )
        parser.add_argument(
            '--format',
            type=str,
            default='json',
            choices=['json', 'xml', 'yaml'],
            help='Output format (default: json)',
        )
        parser.add_argument(
            '--indent',
            type=int,
            default=2,
            help='JSON indentation (default: 2)',
        )
        parser.add_argument(
            '--exclude',
            nargs='+',
            default=['contenttypes', 'sessions', 'admin', 'auth.permission', 'auth.group'],
            help='Models to exclude from export',
        )

    def handle(self, *args, **options):
        output_dir = Path(options['output'])
        apps = options['apps']
        format_type = options['format']
        indent = options['indent']
        exclude = options['exclude']

        # Create output directory if it doesn't exist
        output_dir.mkdir(parents=True, exist_ok=True)
        self.stdout.write(self.style.SUCCESS(f'Output directory: {output_dir.absolute()}'))

        # Get apps to export
        if apps is None:
            # Export all local apps
            apps = [app for app in settings.LOCAL_APPS if app.startswith('apps.')]
            apps = [app.replace('apps.', '') for app in apps]
        
        self.stdout.write(self.style.SUCCESS(f'Exporting data from apps: {", ".join(apps)}'))

        exported_files = []
        
        for app in apps:
            try:
                # Build exclude list for this app
                exclude_list = []
                for ex in exclude:
                    if '.' in ex:
                        exclude_list.append(ex)
                    else:
                        exclude_list.append(f'{app}.{ex}')
                
                # Export app data
                output_file = output_dir / f'{app}_initial_data.{format_type}'
                
                self.stdout.write(f'Exporting {app}...')
                
                # Use Django's dumpdata command
                with open(output_file, 'w', encoding='utf-8') as f:
                    call_command(
                        'dumpdata',
                        app,
                        format=format_type,
                        indent=indent,
                        exclude=exclude_list,
                        stdout=f,
                        verbosity=0,
                    )
                
                # Check if file has content
                if output_file.stat().st_size > 0:
                    exported_files.append(str(output_file))
                    self.stdout.write(self.style.SUCCESS(f'  ✓ Exported to {output_file.name}'))
                else:
                    output_file.unlink()  # Remove empty file
                    self.stdout.write(self.style.WARNING(f'  ⚠ {app} has no data to export'))
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗ Error exporting {app}: {str(e)}'))
                continue

        # Create a combined fixture file
        if exported_files:
            combined_file = output_dir / 'all_initial_data.json'
            self.stdout.write(f'\nCreating combined fixture file...')
            
            combined_data = []
            for file_path in exported_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            combined_data.extend(data)
                        else:
                            combined_data.append(data)
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'  ✗ Error reading {file_path}: {str(e)}'))
            
            if combined_data:
                with open(combined_file, 'w', encoding='utf-8') as f:
                    json.dump(combined_data, f, indent=indent, ensure_ascii=False)
                self.stdout.write(self.style.SUCCESS(f'  ✓ Combined fixture: {combined_file.name}'))

        # Summary
        self.stdout.write(self.style.SUCCESS(f'\n✓ Export completed!'))
        self.stdout.write(f'  Exported {len(exported_files)} app(s)')
        self.stdout.write(f'  Output directory: {output_dir.absolute()}')
        
        if exported_files:
            self.stdout.write(f'\nTo load this data, use:')
            self.stdout.write(f'  python manage.py loaddata {" ".join([f.name for f in map(Path, exported_files)])}')

