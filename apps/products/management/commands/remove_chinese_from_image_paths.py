"""
Django management command to remove Chinese characters from image paths.
Renames files and updates database paths.
"""
from django.core.management.base import BaseCommand
from apps.products.models import ProductImage
import os
import shutil
from pathlib import Path


class Command(BaseCommand):
    help = 'Remove Chinese characters from image file names and update database paths'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # Base directory for images (relative to project root)
        # From: mall-server/apps/products/management/commands/remove_chinese_from_image_paths.py
        # To: mall-server/static/beef
        project_root = Path(__file__).resolve().parent.parent.parent.parent.parent.parent
        base_dir = project_root / 'mall-server' / 'static' / 'beef'
        
        # Mapping: old filename -> new filename (without Chinese)
        filename_mappings = {
            '01_匙仁_shiren.jpg': '01_shiren.jpg',
            '02_里脊_liji.jpg': '02_liji.jpg',
            '03_肥拼_feipin.jpg': '03_feipin.jpg',
            '04_匙柄_shibing.jpg': '04_shibing.jpg',
            '05_吊龙_diaolong.jpg': '05_diaolong.jpg',
            '06_三花趾_sanhuazhi.jpg': '06_sanhuazhi.jpg',
            '07_胸口油_xiongkouyou.jpg': '07_xiongkouyou.jpg',
            '08_嫩肉_nenrou.jpg': '08_nenrou.jpg',
            '09_五花趾_wuhuazhi.jpg': '09_wuhuazhi.jpg',
            '10_后腿肉_houtuirou.jpg': '10_houtuirou.jpg',
            '11_三花趾_sanhuazhi_2.jpg': '11_sanhuazhi_2.jpg',
        }
        
        # Mapping: old URL -> new URL
        url_mappings = {
            '/static/beef/01_匙仁_shiren.jpg': '/static/beef/01_shiren.jpg',
            '/static/beef/02_里脊_liji.jpg': '/static/beef/02_liji.jpg',
            '/static/beef/03_肥拼_feipin.jpg': '/static/beef/03_feipin.jpg',
            '/static/beef/04_匙柄_shibing.jpg': '/static/beef/04_shibing.jpg',
            '/static/beef/05_吊龙_diaolong.jpg': '/static/beef/05_diaolong.jpg',
            '/static/beef/06_三花趾_sanhuazhi.jpg': '/static/beef/06_sanhuazhi.jpg',
            '/static/beef/07_胸口油_xiongkouyou.jpg': '/static/beef/07_xiongkouyou.jpg',
            '/static/beef/08_嫩肉_nenrou.jpg': '/static/beef/08_nenrou.jpg',
            '/static/beef/09_五花趾_wuhuazhi.jpg': '/static/beef/09_wuhuazhi.jpg',
            '/static/beef/10_后腿肉_houtuirou.jpg': '/static/beef/10_houtuirou.jpg',
            '/static/beef/11_三花趾_sanhuazhi_2.jpg': '/static/beef/11_sanhuazhi_2.jpg',
        }
        
        files_renamed = 0
        db_updated = 0
        
        # Step 1: Rename files
        self.stdout.write('Step 1: Renaming image files...')
        for old_name, new_name in filename_mappings.items():
            old_path = base_dir / old_name
            new_path = base_dir / new_name
            
            if old_path.exists():
                if dry_run:
                    self.stdout.write(
                        self.style.WARNING(
                            f'Would rename: {old_name} -> {new_name}'
                        )
                    )
                else:
                    try:
                        shutil.move(str(old_path), str(new_path))
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Renamed: {old_name} -> {new_name}'
                            )
                        )
                        files_renamed += 1
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(
                                f'Error renaming {old_name}: {e}'
                            )
                        )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f'File not found: {old_name}'
                    )
                )
        
        # Step 2: Update database
        self.stdout.write('\nStep 2: Updating database paths...')
        images = ProductImage.objects.all()
        
        for image in images:
            current_url = image.image_url
            
            # Find matching new URL
            new_url = None
            for old_url, new_url_value in url_mappings.items():
                # Check if current URL matches (handle URL encoding)
                import urllib.parse
                try:
                    decoded_url = urllib.parse.unquote(current_url)
                    if old_url in current_url or old_url in decoded_url:
                        new_url = new_url_value
                        break
                except:
                    if old_url in current_url:
                        new_url = new_url_value
                        break
            
            # Also check by extracting filename
            if not new_url:
                filename = os.path.basename(current_url)
                # Try to decode URL-encoded filename
                try:
                    decoded_filename = urllib.parse.unquote(filename)
                except:
                    decoded_filename = filename
                
                # Find matching new filename
                for old_name, new_name in filename_mappings.items():
                    if old_name in filename or old_name in decoded_filename:
                        new_url = f'/static/beef/{new_name}'
                        break
            
            if new_url and current_url != new_url:
                if dry_run:
                    self.stdout.write(
                        self.style.WARNING(
                            f'Would update ID {image.id}: {current_url} -> {new_url}'
                        )
                    )
                else:
                    image.image_url = new_url
                    image.save(update_fields=['image_url'])
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Updated ID {image.id}: {new_url}'
                        )
                    )
                db_updated += 1
            elif new_url:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Already correct ID {image.id}: {new_url}'
                    )
                )
        
        # Summary
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'\nDRY RUN: Would rename {files_renamed} files, update {db_updated} database records'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nSuccessfully renamed {files_renamed} files, updated {db_updated} database records'
                )
            )

