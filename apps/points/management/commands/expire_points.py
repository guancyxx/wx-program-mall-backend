from django.core.management.base import BaseCommand
from apps.points.services import PointsService


class Command(BaseCommand):
    help = 'Expire points that are past their expiry date'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=int,
            help='Expire points for specific user ID only',
        )

    def handle(self, *args, **options):
        user_id = options.get('user_id')
        
        if user_id:
            # Expire points for specific user
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            try:
                user = User.objects.get(id=user_id)
                expired_points = PointsService.expire_user_points(user)
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Expired {expired_points} points for user {user.username}'
                    )
                )
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'User with ID {user_id} not found')
                )
        else:
            # Expire points for all users
            self.stdout.write('Starting points expiration for all users...')
            
            total_expired = PointsService.expire_all_points()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Points expiration complete. Total expired: {total_expired} points'
                )
            )