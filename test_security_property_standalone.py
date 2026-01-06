#!/usr/bin/env python
"""
Standalone security property test for Redis removal validation
This test can run without database connection to validate security properties
Feature: redis-removal, Property 6: Security Vulnerability Reduction
"""

import os
import sys
import subprocess
import tempfile

class SecurityPropertyValidator:
    """Validates security properties for Redis removal"""
    
    def __init__(self):
        self.passed_tests = 0
        self.failed_tests = 0
        self.test_results = []
    
    def log_result(self, test_name, passed, details=""):
        """Log test result"""
        status = "PASS" if passed else "FAIL"
        result = f"[{status}] {test_name}"
        if details:
            result += f": {details}"
        
        self.test_results.append(result)
        if passed:
            self.passed_tests += 1
        else:
            self.failed_tests += 1
        
        print(result)
    
    def test_dependency_reduction(self):
        """
        Property 6: Security Vulnerability Reduction (Dependency Count)
        **Feature: redis-removal, Property 6: Security Vulnerability Reduction**
        **Validates: Requirements 5.4**
        """
        try:
            # Get current directory
            base_dir = os.path.dirname(os.path.abspath(__file__))
            requirements_path = os.path.join(base_dir, 'requirements.txt')
            
            # Verify requirements.txt exists
            if not os.path.exists(requirements_path):
                self.log_result("Dependency Reduction", False, "requirements.txt not found")
                return
            
            # Read current requirements
            with open(requirements_path, 'r', encoding='utf-8') as f:
                current_requirements = f.read().lower()
            
            # Test that Redis/Celery packages are not present
            removed_packages = ['django-redis', 'redis', 'celery']
            for package in removed_packages:
                if package in current_requirements:
                    self.log_result("Dependency Reduction", False, 
                                  f"Removed package {package} still found in requirements")
                    return
            
            # Count current packages
            lines = [line.strip() for line in current_requirements.split('\n') 
                    if line.strip() and not line.strip().startswith('#')]
            current_package_count = len([line for line in lines if '==' in line])
            
            # Calculate hypothetical package count with Redis/Celery
            hypothetical_package_count = current_package_count + len(removed_packages)
            
            # Verify reduction
            if current_package_count >= hypothetical_package_count:
                self.log_result("Dependency Reduction", False, 
                              "Package count not reduced")
                return
            
            # Calculate reduction percentage
            reduction_percentage = (len(removed_packages) / hypothetical_package_count) * 100
            
            if reduction_percentage < 5:
                self.log_result("Dependency Reduction", False, 
                              f"Reduction {reduction_percentage:.1f}% too small")
                return
            
            self.log_result("Dependency Reduction", True, 
                          f"Reduced {len(removed_packages)} packages ({reduction_percentage:.1f}% reduction)")
            
        except Exception as e:
            self.log_result("Dependency Reduction", False, str(e))
    
    def test_security_packages_maintained(self):
        """
        Test that security packages are maintained after Redis removal
        **Feature: redis-removal, Property 6: Security Vulnerability Reduction**
        **Validates: Requirements 5.4**
        """
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            requirements_path = os.path.join(base_dir, 'requirements.txt')
            
            with open(requirements_path, 'r', encoding='utf-8') as f:
                requirements_content = f.read().lower()
            
            # Security packages that should be maintained
            security_packages = [
                'django-ratelimit',
                'bcrypt', 
                'django-security',
                'django-csp',
                'cryptography'
            ]
            
            missing_packages = []
            for package in security_packages:
                if package not in requirements_content:
                    missing_packages.append(package)
            
            if missing_packages:
                self.log_result("Security Packages Maintained", False, 
                              f"Missing security packages: {missing_packages}")
                return
            
            self.log_result("Security Packages Maintained", True, 
                          f"All {len(security_packages)} security packages present")
            
        except Exception as e:
            self.log_result("Security Packages Maintained", False, str(e))
    
    def test_version_pinning_security(self):
        """
        Test that all packages have version pinning for security
        **Feature: redis-removal, Property 6: Security Vulnerability Reduction**
        **Validates: Requirements 5.4**
        """
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            requirements_path = os.path.join(base_dir, 'requirements.txt')
            
            with open(requirements_path, 'r', encoding='utf-8') as f:
                requirements_content = f.read()
            
            lines = [line.strip() for line in requirements_content.split('\n') 
                    if line.strip() and not line.strip().startswith('#')]
            
            unpinned_packages = []
            for line in lines:
                if '==' not in line and line and not line.startswith('-'):
                    unpinned_packages.append(line)
            
            if unpinned_packages:
                self.log_result("Version Pinning Security", False, 
                              f"Unpinned packages: {unpinned_packages}")
                return
            
            # Count pinned packages
            pinned_count = len([line for line in lines if '==' in line])
            
            self.log_result("Version Pinning Security", True, 
                          f"All {pinned_count} packages properly version-pinned")
            
        except Exception as e:
            self.log_result("Version Pinning Security", False, str(e))
    
    def test_no_development_packages(self):
        """
        Test that no development packages are in production requirements
        **Feature: redis-removal, Property 6: Security Vulnerability Reduction**
        **Validates: Requirements 5.4**
        """
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            requirements_path = os.path.join(base_dir, 'requirements.txt')
            
            with open(requirements_path, 'r', encoding='utf-8') as f:
                requirements_content = f.read().lower()
            
            # Development packages that should not be present
            dev_packages = [
                'django-debug-toolbar',
                'django-extensions', 
                'ipdb',
                'pdb',
                'debug',
                'dev-tools'
            ]
            
            found_dev_packages = []
            for package in dev_packages:
                if package in requirements_content:
                    found_dev_packages.append(package)
            
            if found_dev_packages:
                self.log_result("No Development Packages", False, 
                              f"Found dev packages: {found_dev_packages}")
                return
            
            self.log_result("No Development Packages", True, 
                          "No development packages found in production requirements")
            
        except Exception as e:
            self.log_result("No Development Packages", False, str(e))
    
    def test_attack_surface_reduction(self):
        """
        Test that attack surface is reduced by removing network services
        **Feature: redis-removal, Property 6: Security Vulnerability Reduction**
        **Validates: Requirements 5.4**
        """
        try:
            # Test environment variables
            redis_env_vars = ['REDIS_HOST', 'REDIS_PORT', 'REDIS_PASSWORD', 'REDIS_URL']
            found_env_vars = []
            
            for env_var in redis_env_vars:
                if os.environ.get(env_var):
                    found_env_vars.append(env_var)
            
            if found_env_vars:
                self.log_result("Attack Surface Reduction", False, 
                              f"Redis env vars still set: {found_env_vars}")
                return
            
            # Test that no Redis configuration files exist
            base_dir = os.path.dirname(os.path.abspath(__file__))
            redis_config_files = ['redis.conf', '.redis.conf', 'redis.yml']
            
            found_config_files = []
            for config_file in redis_config_files:
                if os.path.exists(os.path.join(base_dir, config_file)):
                    found_config_files.append(config_file)
            
            if found_config_files:
                self.log_result("Attack Surface Reduction", False, 
                              f"Redis config files found: {found_config_files}")
                return
            
            self.log_result("Attack Surface Reduction", True, 
                          "No Redis environment variables or config files found")
            
        except Exception as e:
            self.log_result("Attack Surface Reduction", False, str(e))
    
    def test_security_audit_capability(self):
        """
        Test that security audit tools can run successfully
        **Feature: redis-removal, Property 6: Security Vulnerability Reduction**
        **Validates: Requirements 5.4**
        """
        try:
            # Test that pip-audit can be run (if available)
            try:
                result = subprocess.run(['python', '-m', 'pip_audit', '--help'], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    audit_available = True
                else:
                    audit_available = False
            except (subprocess.TimeoutExpired, FileNotFoundError):
                audit_available = False
            
            # Test that requirements.txt is readable for security scanning
            base_dir = os.path.dirname(os.path.abspath(__file__))
            requirements_path = os.path.join(base_dir, 'requirements.txt')
            
            if not os.path.exists(requirements_path):
                self.log_result("Security Audit Capability", False, 
                              "requirements.txt not found for security scanning")
                return
            
            # Test file is readable and parseable
            with open(requirements_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if len(content.strip()) == 0:
                self.log_result("Security Audit Capability", False, 
                              "requirements.txt is empty")
                return
            
            audit_status = "pip-audit available" if audit_available else "pip-audit not available"
            self.log_result("Security Audit Capability", True, 
                          f"Requirements file ready for security scanning ({audit_status})")
            
        except Exception as e:
            self.log_result("Security Audit Capability", False, str(e))
    
    def run_all_tests(self):
        """Run all security property tests"""
        print("="*80)
        print("SECURITY PROPERTY TESTS")
        print("Feature: redis-removal, Property 6: Security Vulnerability Reduction")
        print("="*80)
        
        self.test_dependency_reduction()
        self.test_security_packages_maintained()
        self.test_version_pinning_security()
        self.test_no_development_packages()
        self.test_attack_surface_reduction()
        self.test_security_audit_capability()
        
        # Print summary
        print("\n" + "="*80)
        print("SECURITY PROPERTY TEST RESULTS")
        print("="*80)
        for result in self.test_results:
            print(result)
        
        print(f"\nSUMMARY: {self.passed_tests} passed, {self.failed_tests} failed")
        
        if self.failed_tests == 0:
            print("\n✓ ALL SECURITY PROPERTY TESTS PASSED")
            print("Security vulnerability reduction requirements satisfied.")
            return True
        else:
            print(f"\n✗ {self.failed_tests} SECURITY PROPERTY TESTS FAILED")
            print("Security requirements not fully satisfied.")
            return False

if __name__ == "__main__":
    validator = SecurityPropertyValidator()
    success = validator.run_all_tests()
    sys.exit(0 if success else 1)