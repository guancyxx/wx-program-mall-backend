"""
Django management command to update banner image in database.
Updates banner cover URL to use local static image.
"""
from django.core.management.base import BaseCommand
from apps.products.models import Banner


class Command(BaseCommand):
    help = 'Update banner image URL to use local static/banner.png'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # New banner image path
        new_cover_url = '/static/banner.png'
        
        # Get all active banners
        banners = Banner.objects.filter(is_active=True)
        
        if not banners.exists():
            self.stdout.write(
                self.style.WARNING('No active banners found. Creating a new banner...')
            )
            if not dry_run:
                banner = Banner.objects.create(
                    cover=new_cover_url,
                    title='Banner',
                    type=1,
                    order=0,
                    is_active=True
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Created new banner ID {banner.id} with cover: {new_cover_url}'
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f'Would create new banner with cover: {new_cover_url}'
                    )
                )
        else:
            updated_count = 0
            for banner in banners:
                if banner.cover != new_cover_url:
                    if dry_run:
                        self.stdout.write(
                            self.style.WARNING(
                                f'Would update banner ID {banner.id}: {banner.cover} -> {new_cover_url}'
                            )
                        )
                    else:
                        banner.cover = new_cover_url
                        banner.save(update_fields=['cover'])
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Updated banner ID {banner.id}: {new_cover_url}'
                            )
                        )
                    updated_count += 1
                else:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Banner ID {banner.id} already has correct cover: {new_cover_url}'
                        )
                    )
            
            if dry_run:
                self.stdout.write(
                    self.style.WARNING(
                        f'\nDRY RUN: Would update {updated_count} banners'
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'\nSuccessfully updated {updated_count} banners'
                    )
                )

