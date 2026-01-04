from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.common.models import SystemConfiguration, SystemNotification
from apps.common.security import SecurityReportGenerator
import logging

User = get_user_model()


class Command(BaseCommand):
    help = 'Set up security monitoring configuration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Reset all security configurations to defaults',
        )

    def handle(self, *args, **options):
        self.stdout.write('Setting up security monitoring...')
        
        # Security configuration settings
        security_configs = [
            {
                'key': 'SECURITY_RATE_LIMIT_ENABLED',
                'value': 'true',
                'description': 'Enable rate limiting for API endpoints'
            },
            {
                'key': 'SECURITY_MAX_LOGIN_ATTEMPTS',
                'value': '5',
                'description': 'Maximum failed login attempts before blocking IP'
            },
            {
                'key': 'SECURITY_LOGIN_ATTEMPT_WINDOW',
                'value': '900',
                'description': 'Time window for login attempts in seconds (15 minutes)'
            },
            {
                'key': 'SECURITY_AUDIT_LOG_RETENTION',
                'value': '90',
                'description': 'Number of days to retain audit logs'
            },
            {
                'key': 'SECURITY_ALERT_EMAIL_ENABLED',
                'value': 'false',
                'description': 'Enable email alerts for security events'
            },
            {
                'key': 'SECURITY_ALERT_EMAIL_RECIPIENTS',
                'value': 'admin@example.com',
                'description': 'Comma-separated list of email recipients for security alerts'
            },
            {
                'key': 'SECURITY_SUSPICIOUS_ACTIVITY_THRESHOLD',
                'value': '10',
                'description': 'Number of rapid actions that trigger suspicious activity alert'
            },
            {
                'key': 'SECURITY_AUTO_BLOCK_ENABLED',
                'value': 'false',
                'description': 'Automatically block IPs with suspicious activity'
            },
            {
                'key': 'SECURITY_SESSION_TIMEOUT',
                'value': '3600',
                'description': 'Session timeout in seconds (1 hour)'
            },
            {
                'key': 'SECURITY_REQUIRE_STRONG_PASSWORDS',
                'value': 'true',
                'description': 'Require strong passwords for user accounts'
            }
        ]
        
        # Create or update security configurations
        for config in security_configs:
            obj, created = SystemConfiguration.objects.get_or_create(
                key=config['key'],
                defaults={
                    'value': config['value'],
                    'description': config['description']
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created security config: {config["key"]}')
                )
            elif options['reset']:
                obj.value = config['value']
                obj.description = config['description']
                obj.save()
                self.stdout.write(
                    self.style.WARNING(f'Reset security config: {config["key"]}')
                )
            else:
                self.stdout.write(f'Security config exists: {config["key"]}')
        
        # Set up logging configuration
        self.setup_security_logging()
        
        # Create initial security notification
        self.create_initial_notification()
        
        # Generate initial security report
        self.generate_initial_report()
        
        self.stdout.write(
            self.style.SUCCESS('Security monitoring setup completed successfully!')
        )

    def setup_security_logging(self):
        """Set up security logging configuration"""
        self.stdout.write('Configuring security logging...')
        
        # Create logging configuration
        logging_config = {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'security': {
                    'format': '{asctime} {levelname} {name} {message}',
                    'style': '{',
                },
            },
            'handlers': {
                'security_file': {
                    'level': 'INFO',
                    'class': 'logging.handlers.RotatingFileHandler',
                    'filename': 'logs/security.log',
                    'maxBytes': 1024*1024*10,  # 10MB
                    'backupCount': 5,
                    'formatter': 'security',
                },
            },
            'loggers': {
                'security': {
                    'handlers': ['security_file'],
                    'level': 'INFO',
                    'propagate': False,
                },
            },
        }
        
        # Store logging configuration
        SystemConfiguration.objects.update_or_create(
            key='SECURITY_LOGGING_CONFIG',
            defaults={
                'value': str(logging_config),
                'description': 'Security logging configuration'
            }
        )
        
        self.stdout.write(self.style.SUCCESS('Security logging configured'))

    def create_initial_notification(self):
        """Create initial security monitoring notification"""
        SystemNotification.objects.get_or_create(
            title='Security Monitoring Activated',
            defaults={
                'message': '''Security monitoring has been successfully activated for the Mall Management System.

Features enabled:
- Authentication event logging
- Failed login attempt tracking
- Administrative action auditing
- Rate limiting protection
- Suspicious activity detection

Please review the security configuration in the admin panel and adjust settings as needed for your environment.''',
                'notification_type': 'success',
                'priority': 'medium',
                'is_active': True,
            }
        )
        
        self.stdout.write(self.style.SUCCESS('Initial security notification created'))

    def generate_initial_report(self):
        """Generate initial security report"""
        try:
            summary = SecurityReportGenerator.get_security_summary(7)
            
            self.stdout.write('Security Summary (Last 7 days):')
            self.stdout.write(f'  Total Events: {summary["total_events"]}')
            self.stdout.write(f'  Login Events: {summary["login_events"]}')
            self.stdout.write(f'  Failed Logins: {summary["failed_logins"]}')
            self.stdout.write(f'  Admin Actions: {summary["admin_actions"]}')
            self.stdout.write(f'  Suspicious Activities: {summary["suspicious_activities"]}')
            self.stdout.write(f'  Security Score: {summary["security_score"]}/100')
            
            if summary['security_score'] < 80:
                self.stdout.write(
                    self.style.WARNING('Security score is below 80. Please review recent activities.')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS('Security score is healthy.')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Failed to generate security report: {e}')
            )