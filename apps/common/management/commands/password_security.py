"""
Django management command for password security operations.

This command provides utilities for:
- Testing password security configuration
- Generating security reports
- Migrating legacy passwords
- Validating password hashes
- Monitoring security events

Usage:
    python manage.py password_security --test-config
    python manage.py password_security --security-report --days 7
    python manage.py password_security --validate-hashes
    python manage.py password_security --migrate-legacy --dry-run
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.conf import settings
from apps.common.password_utils import (
    get_password_security_controller,
    PasswordSecurityController,
    ValidationResult
)
import json
from datetime import datetime, timedelta


class Command(BaseCommand):
    help = 'Password security management utilities'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-config',
            action='store_true',
            help='Test password security configuration'
        )
        
        parser.add_argument(
            '--security-report',
            action='store_true',
            help='Generate security report'
        )
        
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days for security report (default: 7)'
        )
        
        parser.add_argument(
            '--validate-hashes',
            action='store_true',
            help='Validate all user password hashes'
        )
        
        parser.add_argument(
            '--migrate-legacy',
            action='store_true',
            help='Identify users with legacy password hashes'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )
        
        parser.add_argument(
            '--test-password',
            type=str,
            help='Test password strength validation'
        )
        
        parser.add_argument(
            '--user-id',
            type=int,
            help='Specific user ID for operations'
        )

    def handle(self, *args, **options):
        """Handle the management command."""
        try:
            controller = get_password_security_controller()
            
            if options['test_config']:
                self.test_configuration(controller)
            elif options['security_report']:
                self.generate_security_report(controller, options['days'])
            elif options['validate_hashes']:
                self.validate_password_hashes(controller, options.get('user_id'))
            elif options['migrate_legacy']:
                self.identify_legacy_passwords(controller, options['dry_run'])
            elif options['test_password']:
                self.test_password_strength(controller, options['test_password'])
            else:
                self.stdout.write(
                    self.style.WARNING('No action specified. Use --help for available options.')
                )
                
        except Exception as e:
            raise CommandError(f'Command failed: {str(e)}')

    def test_configuration(self, controller: PasswordSecurityController):
        """Test password security configuration."""
        self.stdout.write(self.style.SUCCESS('Testing Password Security Configuration'))
        self.stdout.write('=' * 50)
        
        # Test configuration loading
        config = controller.config
        self.stdout.write(f"Configuration loaded: {len(config)} settings")
        
        # Display key configuration values
        key_settings = [
            'BCRYPT_ROUNDS',
            'MIN_PASSWORD_LENGTH',
            'ENABLE_LEGACY_MIGRATION',
            'LOG_SECURITY_EVENTS',
            'BRUTE_FORCE_THRESHOLD'
        ]
        
        for setting in key_settings:
            value = config.get(setting, 'Not set')
            self.stdout.write(f"  {setting}: {value}")
        
        # Test password hashing
        self.stdout.write('\nTesting password hashing...')
        try:
            test_password = 'TestPassword123!'
            hashed = controller.hash_password(test_password)
            self.stdout.write(f"  Hash generated: {hashed[:50]}...")
            
            # Test verification
            verified = controller.verify_password(test_password, hashed)
            if verified:
                self.stdout.write(self.style.SUCCESS('  ✓ Password verification successful'))
            else:
                self.stdout.write(self.style.ERROR('  ✗ Password verification failed'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ✗ Hashing test failed: {str(e)}'))
        
        # Test password validation
        self.stdout.write('\nTesting password validation...')
        try:
            test_passwords = [
                ('StrongPass123!', 'Strong password'),
                ('weak', 'Weak password'),
                ('password123', 'Common password'),
                ('UPPERCASE123!', 'Missing lowercase'),
                ('lowercase123!', 'Missing uppercase')
            ]
            
            for password, description in test_passwords:
                result = controller.validate_password_strength(password)
                status = '✓' if result.is_valid else '✗'
                self.stdout.write(f"  {status} {description}: {result.strength_level} ({result.strength_score}/100)")
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ✗ Validation test failed: {str(e)}'))
        
        # Test Django settings integration
        self.stdout.write('\nTesting Django settings integration...')
        
        # Check PASSWORD_HASHERS
        hashers = getattr(settings, 'PASSWORD_HASHERS', [])
        if 'apps.common.password_utils.SecurePasswordHasher' in hashers:
            self.stdout.write('  ✓ SecurePasswordHasher configured in PASSWORD_HASHERS')
        else:
            self.stdout.write(self.style.WARNING('  ⚠ SecurePasswordHasher not found in PASSWORD_HASHERS'))
        
        # Check AUTHENTICATION_BACKENDS
        backends = getattr(settings, 'AUTHENTICATION_BACKENDS', [])
        if 'apps.common.password_utils.SecureAuthenticationBackend' in backends:
            self.stdout.write('  ✓ SecureAuthenticationBackend configured')
        else:
            self.stdout.write(self.style.WARNING('  ⚠ SecureAuthenticationBackend not found in AUTHENTICATION_BACKENDS'))
        
        self.stdout.write(self.style.SUCCESS('\nConfiguration test completed'))

    def generate_security_report(self, controller: PasswordSecurityController, days: int):
        """Generate and display security report."""
        self.stdout.write(self.style.SUCCESS(f'Generating Security Report ({days} days)'))
        self.stdout.write('=' * 50)
        
        try:
            report = controller.get_security_report(days)
            
            # Display report summary
            self.stdout.write(f"Report ID: {report.report_id}")
            self.stdout.write(f"Generated: {report.generated_at}")
            self.stdout.write(f"Timeframe: {report.timeframe_start} to {report.timeframe_end}")
            self.stdout.write(f"Total Events: {report.total_events}")
            
            # Events by type
            if report.events_by_type:
                self.stdout.write('\nEvents by Type:')
                for event_type, count in report.events_by_type.items():
                    self.stdout.write(f"  {event_type}: {count}")
            
            # Events by severity
            if report.events_by_severity:
                self.stdout.write('\nEvents by Severity:')
                for severity, count in report.events_by_severity.items():
                    self.stdout.write(f"  {severity.upper()}: {count}")
            
            # Key metrics
            self.stdout.write('\nKey Metrics:')
            self.stdout.write(f"  Successful Authentications: {report.successful_authentications}")
            self.stdout.write(f"  Failed Authentications: {report.failed_authentications}")
            self.stdout.write(f"  Password Migrations: {report.password_migrations}")
            self.stdout.write(f"  Brute Force Attempts: {report.brute_force_attempts}")
            self.stdout.write(f"  Unique Users: {report.unique_users}")
            self.stdout.write(f"  Unique IPs: {report.unique_ips}")
            
            # Top failure reasons
            if report.top_failure_reasons:
                self.stdout.write('\nTop Failure Reasons:')
                for reason_info in report.top_failure_reasons[:5]:
                    self.stdout.write(f"  {reason_info['reason']}: {reason_info['count']}")
            
            # Security recommendations
            if report.security_recommendations:
                self.stdout.write('\nSecurity Recommendations:')
                for i, recommendation in enumerate(report.security_recommendations, 1):
                    self.stdout.write(f"  {i}. {recommendation}")
            
            # Save report to file
            report_file = f"security_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w') as f:
                json.dump(report.to_dict(), f, indent=2, default=str)
            
            self.stdout.write(f'\nReport saved to: {report_file}')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to generate security report: {str(e)}'))

    def validate_password_hashes(self, controller: PasswordSecurityController, user_id: int = None):
        """Validate password hashes for users."""
        self.stdout.write(self.style.SUCCESS('Validating Password Hashes'))
        self.stdout.write('=' * 50)
        
        User = get_user_model()
        
        try:
            if user_id:
                users = User.objects.filter(id=user_id)
                if not users.exists():
                    self.stdout.write(self.style.ERROR(f'User with ID {user_id} not found'))
                    return
            else:
                users = User.objects.all()
            
            total_users = users.count()
            self.stdout.write(f"Validating {total_users} user(s)...")
            
            stats = {
                'secure_bcrypt': 0,
                'bcrypt': 0,
                'legacy': 0,
                'unknown': 0,
                'needs_update': 0,
                'errors': 0
            }
            
            for user in users:
                try:
                    hash_info = controller.get_password_hash_info(user.password)
                    algorithm = hash_info.get('algorithm', 'unknown')
                    needs_update = controller.check_password_needs_update(user.password)
                    
                    # Categorize hash type
                    if algorithm == 'secure_bcrypt':
                        stats['secure_bcrypt'] += 1
                    elif 'bcrypt' in algorithm:
                        stats['bcrypt'] += 1
                    elif 'legacy' in algorithm:
                        stats['legacy'] += 1
                    else:
                        stats['unknown'] += 1
                    
                    if needs_update:
                        stats['needs_update'] += 1
                    
                    if user_id:  # Show detailed info for single user
                        self.stdout.write(f"\nUser {user.id} ({user.username}):")
                        self.stdout.write(f"  Algorithm: {algorithm}")
                        self.stdout.write(f"  Hash: {hash_info.get('hash', 'N/A')}")
                        self.stdout.write(f"  Needs Update: {'Yes' if needs_update else 'No'}")
                        if 'legacy_type' in hash_info:
                            self.stdout.write(f"  Legacy Type: {hash_info['legacy_type']}")
                        if 'error' in hash_info:
                            self.stdout.write(f"  Error: {hash_info['error']}")
                    
                except Exception as e:
                    stats['errors'] += 1
                    if user_id:
                        self.stdout.write(self.style.ERROR(f"Error validating user {user.id}: {str(e)}"))
            
            # Display summary
            self.stdout.write('\nValidation Summary:')
            self.stdout.write(f"  Secure BCrypt: {stats['secure_bcrypt']}")
            self.stdout.write(f"  BCrypt (other): {stats['bcrypt']}")
            self.stdout.write(f"  Legacy formats: {stats['legacy']}")
            self.stdout.write(f"  Unknown formats: {stats['unknown']}")
            self.stdout.write(f"  Need updates: {stats['needs_update']}")
            self.stdout.write(f"  Errors: {stats['errors']}")
            
            # Recommendations
            if stats['legacy'] > 0:
                self.stdout.write(self.style.WARNING(f"\n⚠ {stats['legacy']} users have legacy password hashes"))
                self.stdout.write("  Consider running password migration during user login")
            
            if stats['unknown'] > 0:
                self.stdout.write(self.style.ERROR(f"\n✗ {stats['unknown']} users have unknown hash formats"))
                self.stdout.write("  These users may need password resets")
            
            if stats['needs_update'] > 0:
                self.stdout.write(self.style.WARNING(f"\n⚠ {stats['needs_update']} users need password hash updates"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Validation failed: {str(e)}'))

    def identify_legacy_passwords(self, controller: PasswordSecurityController, dry_run: bool):
        """Identify users with legacy password hashes."""
        action = "Identifying" if dry_run else "Migrating"
        self.stdout.write(self.style.SUCCESS(f'{action} Legacy Password Hashes'))
        self.stdout.write('=' * 50)
        
        User = get_user_model()
        
        try:
            users_with_legacy = []
            
            for user in User.objects.all():
                if controller.legacy_handler.is_legacy_hash(user.password):
                    hash_type = controller.legacy_handler.detect_hash_type(user.password)
                    users_with_legacy.append({
                        'user': user,
                        'hash_type': hash_type
                    })
            
            if not users_with_legacy:
                self.stdout.write(self.style.SUCCESS('No legacy password hashes found'))
                return
            
            self.stdout.write(f"Found {len(users_with_legacy)} users with legacy password hashes:")
            
            legacy_stats = {}
            for user_info in users_with_legacy:
                user = user_info['user']
                hash_type = user_info['hash_type']
                
                legacy_stats[hash_type] = legacy_stats.get(hash_type, 0) + 1
                
                self.stdout.write(f"  User {user.id} ({user.username}): {hash_type}")
            
            # Display statistics
            self.stdout.write('\nLegacy Hash Statistics:')
            for hash_type, count in legacy_stats.items():
                self.stdout.write(f"  {hash_type}: {count} users")
            
            if dry_run:
                self.stdout.write('\n' + self.style.WARNING('DRY RUN - No changes made'))
                self.stdout.write('To migrate these passwords, users need to log in successfully')
                self.stdout.write('The system will automatically migrate passwords during authentication')
            else:
                self.stdout.write('\n' + self.style.SUCCESS('Legacy passwords identified'))
                self.stdout.write('These will be automatically migrated when users log in')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Legacy identification failed: {str(e)}'))

    def test_password_strength(self, controller: PasswordSecurityController, password: str):
        """Test password strength validation."""
        self.stdout.write(self.style.SUCCESS('Testing Password Strength'))
        self.stdout.write('=' * 50)
        
        try:
            result = controller.validate_password_strength(password)
            
            self.stdout.write(f"Password: {'*' * len(password)}")
            self.stdout.write(f"Valid: {'Yes' if result.is_valid else 'No'}")
            self.stdout.write(f"Strength Level: {result.strength_level}")
            self.stdout.write(f"Strength Score: {result.strength_score}/100")
            
            if result.errors:
                self.stdout.write('\nErrors:')
                for error in result.errors:
                    self.stdout.write(f"  ✗ {error}")
            
            if result.warnings:
                self.stdout.write('\nWarnings:')
                for warning in result.warnings:
                    self.stdout.write(f"  ⚠ {warning}")
            
            if result.suggestions:
                self.stdout.write('\nSuggestions:')
                for suggestion in result.suggestions:
                    self.stdout.write(f"  💡 {suggestion}")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Password strength test failed: {str(e)}'))