"""
Django management command to fix product image URLs.
Directly updates all image URLs to use correct /static/beef/ paths.
"""
from django.core.management.base import BaseCommand
from apps.products.models import ProductImage


class Command(BaseCommand):
    help = 'Fix product image URLs to use correct /static/beef/ paths'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # Direct mapping of image IDs to correct URLs
        # Based on the actual files in /static/beef/
        image_updates = {
            1: '/static/beef/01_匙仁_shiren.jpg',
            2: '/static/beef/02_里脊_liji.jpg',
            3: '/static/beef/03_肥拼_feipin.jpg',
            4: '/static/beef/04_匙柄_shibing.jpg',
            5: '/static/beef/05_吊龙_diaolong.jpg',
            6: '/static/beef/06_三花趾_sanhuazhi.jpg',
            7: '/static/beef/07_胸口油_xiongkouyou.jpg',
            8: '/static/beef/08_嫩肉_nenrou.jpg',
            9: '/static/beef/09_五花趾_wuhuazhi.jpg',
            10: '/static/beef/10_后腿肉_houtuirou.jpg',
            11: '/static/beef/11_三花趾_sanhuazhi_2.jpg',
        }
        
        updated_count = 0
        
        for image_id, correct_url in image_updates.items():
            try:
                image = ProductImage.objects.get(id=image_id)
                # Always update to ensure correct encoding
                current_url = image.image_url
                if current_url != correct_url or '/static/beef/' not in current_url:
                    if dry_run:
                        self.stdout.write(
                            self.style.WARNING(
                                f'Would update ID {image_id}: {current_url} -> {correct_url}'
                            )
                        )
                    else:
                        image.image_url = correct_url
                        image.save(update_fields=['image_url'])
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Updated ID {image_id}: {correct_url}'
                            )
                        )
                    updated_count += 1
                else:
                    if not dry_run:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Already correct ID {image_id}: {correct_url}'
                            )
                        )
            except ProductImage.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(
                        f'Image ID {image_id} not found in database'
                    )
                )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'\nDRY RUN: Would update {updated_count} images'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nSuccessfully updated {updated_count} images'
                )
            )

