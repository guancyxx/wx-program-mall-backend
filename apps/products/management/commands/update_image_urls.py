"""
Django management command to update product image URLs.
Updates image URLs to use /static/beef/ prefix.
"""
from django.core.management.base import BaseCommand
from apps.products.models import ProductImage
import os


class Command(BaseCommand):
    help = 'Update product image URLs to use /static/beef/ prefix'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # Mapping of old paths to new paths
        # Based on the beef image files we copied
        image_mappings = {
            '01_匙仁_shiren.jpg': '/static/beef/01_匙仁_shiren.jpg',
            '02_里脊_liji.jpg': '/static/beef/02_里脊_liji.jpg',
            '03_肥拼_feipin.jpg': '/static/beef/03_肥拼_feipin.jpg',
            '04_匙柄_shibing.jpg': '/static/beef/04_匙柄_shibing.jpg',
            '05_吊龙_diaolong.jpg': '/static/beef/05_吊龙_diaolong.jpg',
            '06_三花趾_sanhuazhi.jpg': '/static/beef/06_三花趾_sanhuazhi.jpg',
            '07_胸口油_xiongkouyou.jpg': '/static/beef/07_胸口油_xiongkouyou.jpg',
            '08_嫩肉_nenrou.jpg': '/static/beef/08_嫩肉_nenrou.jpg',
            '09_五花趾_wuhuazhi.jpg': '/static/beef/09_五花趾_wuhuazhi.jpg',
            '10_后腿肉_houtuirou.jpg': '/static/beef/10_后腿肉_houtuirou.jpg',
            '11_三花趾_sanhuazhi_2.jpg': '/static/beef/11_三花趾_sanhuazhi_2.jpg',
        }
        
        updated_count = 0
        not_found_count = 0
        
        # Get all product images
        images = ProductImage.objects.all()
        
        self.stdout.write(f'Found {images.count()} product images in database')
        
        for image in images:
            # Extract filename from current URL
            current_url = image.image_url
            filename = os.path.basename(current_url)
            
            # Normalize filename (handle URL encoding)
            import urllib.parse
            try:
                # Decode URL-encoded filename
                decoded_filename = urllib.parse.unquote(filename)
            except:
                decoded_filename = filename
            
            # Find matching new URL by checking both encoded and decoded filenames
            new_url = None
            matched_filename = None
            
            # First try exact match
            if filename in image_mappings:
                new_url = image_mappings[filename]
                matched_filename = filename
            elif decoded_filename in image_mappings:
                new_url = image_mappings[decoded_filename]
                matched_filename = decoded_filename
            else:
                # Try to match by extracting number prefix (e.g., "01_", "10_")
                for key, value in image_mappings.items():
                    # Extract number prefix from both
                    key_prefix = key.split('_')[0] if '_' in key else ''
                    filename_prefix = filename.split('_')[0] if '_' in filename else ''
                    decoded_prefix = decoded_filename.split('_')[0] if '_' in decoded_filename else ''
                    
                    if key_prefix == filename_prefix or key_prefix == decoded_prefix:
                        new_url = value
                        matched_filename = key
                        break
            
            if new_url:
                # Normalize current_url to ensure it starts with /static/beef/
                if current_url != new_url:
                    if dry_run:
                        self.stdout.write(
                            self.style.WARNING(
                                f'Would update: ID {image.id} - {current_url} -> {new_url}'
                            )
                        )
                    else:
                        image.image_url = new_url
                        image.save(update_fields=['image_url'])
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Updated: ID {image.id} - {new_url}'
                            )
                        )
                    updated_count += 1
                else:
                    if not dry_run:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Already correct: ID {image.id} - {current_url}'
                            )
                        )
            else:
                # If it's already a /static/beef/ path, keep it
                if '/static/beef/' in current_url:
                    if not dry_run:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Already using /static/beef/: ID {image.id} - {current_url}'
                            )
                        )
                else:
                    not_found_count += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f'No mapping found: ID {image.id} - {current_url}'
                        )
                    )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'\nDRY RUN: Would update {updated_count} images, {not_found_count} not found'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nSuccessfully updated {updated_count} images, {not_found_count} not found'
                )
            )

