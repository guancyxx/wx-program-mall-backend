"""
Password hashing utilities with bcrypt compatibility
"""

import bcrypt
import hashlib
from django.contrib.auth.hashers import BasePasswordHasher, mask_hash
from django.utils.crypto import constant_time_compare


class BCryptPasswordHasher(BasePasswordHasher):
    """
    Secure password hasher using bcrypt with compatibility for Node.js bcrypt
    """
    algorithm = "bcrypt"
    rounds = 12  # Default rounds for security

    def encode(self, password, salt):
        """
        Encode password using bcrypt
        """
        if isinstance(password, str):
            password = password.encode('utf-8')
        
        # Generate salt if not provided
        if not salt:
            salt = bcrypt.gensalt(rounds=self.rounds)
        elif isinstance(salt, str):
            salt = salt.encode('utf-8')
        
        # Hash the password
        hash_bytes = bcrypt.hashpw(password, salt)
        hash_str = hash_bytes.decode('ascii')
        
        return f"{self.algorithm}${hash_str}"

    def verify(self, password, encoded):
        """
        Verify password against encoded hash
        """
        algorithm, hash_str = encoded.split('$', 1)
        assert algorithm == self.algorithm
        
        if isinstance(password, str):
            password = password.encode('utf-8')
        
        hash_bytes = hash_str.encode('ascii')
        
        return bcrypt.checkpw(password, hash_bytes)

    def safe_summary(self, encoded):
        """
        Return a summary of the password hash for display
        """
        algorithm, hash_str = encoded.split('$', 1)
        assert algorithm == self.algorithm
        return {
            'algorithm': algorithm,
            'hash': mask_hash(hash_str),
        }

    def harden_runtime(self, password, encoded):
        """
        Harden against timing attacks
        """
        pass

    def must_update(self, encoded):
        """
        Check if password hash needs updating
        """
        try:
            algorithm, hash_str = encoded.split('$', 1)
            # Check if rounds are sufficient
            if hash_str.startswith('$2b$'):
                rounds_str = hash_str.split('$')[2]
                rounds = int(rounds_str)
                return rounds < self.rounds
        except (ValueError, IndexError):
            return True
        return False


class NodeJSCompatiblePasswordHasher:
    """
    Password hasher compatible with Node.js bcrypt implementation
    """
    
    @staticmethod
    def hash_password(password, rounds=12):
        """
        Hash password using bcrypt (Node.js compatible)
        
        Args:
            password (str): Plain text password
            rounds (int): Number of salt rounds (default: 12)
            
        Returns:
            str: Bcrypt hash string
        """
        if isinstance(password, str):
            password = password.encode('utf-8')
        
        # Generate salt and hash
        salt = bcrypt.gensalt(rounds=rounds)
        hash_bytes = bcrypt.hashpw(password, salt)
        
        return hash_bytes.decode('ascii')
    
    @staticmethod
    def verify_password(password, hash_str):
        """
        Verify password against bcrypt hash
        
        Args:
            password (str): Plain text password
            hash_str (str): Bcrypt hash string
            
        Returns:
            bool: True if password matches hash
        """
        if isinstance(password, str):
            password = password.encode('utf-8')
        
        if isinstance(hash_str, str):
            hash_bytes = hash_str.encode('ascii')
        else:
            hash_bytes = hash_str
        
        try:
            return bcrypt.checkpw(password, hash_bytes)
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def is_bcrypt_hash(hash_str):
        """
        Check if string is a valid bcrypt hash
        
        Args:
            hash_str (str): Hash string to check
            
        Returns:
            bool: True if valid bcrypt hash
        """
        if not isinstance(hash_str, str):
            return False
        
        # Bcrypt hashes start with $2a$, $2b$, $2x$, or $2y$
        bcrypt_prefixes = ['$2a$', '$2b$', '$2x$', '$2y$']
        return any(hash_str.startswith(prefix) for prefix in bcrypt_prefixes)


class LegacyPasswordHasher:
    """
    Handle legacy password hashes from Node.js system
    """
    
    @staticmethod
    def verify_legacy_hash(password, hash_str, hash_type='md5'):
        """
        Verify password against legacy hash formats
        
        Args:
            password (str): Plain text password
            hash_str (str): Legacy hash string
            hash_type (str): Type of legacy hash (md5, sha1, sha256)
            
        Returns:
            bool: True if password matches hash
        """
        if hash_type == 'md5':
            computed_hash = hashlib.md5(password.encode('utf-8')).hexdigest()
        elif hash_type == 'sha1':
            computed_hash = hashlib.sha1(password.encode('utf-8')).hexdigest()
        elif hash_type == 'sha256':
            computed_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
        else:
            return False
        
        return constant_time_compare(computed_hash, hash_str)
    
    @staticmethod
    def migrate_legacy_password(password, legacy_hash, legacy_type='md5'):
        """
        Migrate legacy password to bcrypt
        
        Args:
            password (str): Plain text password
            legacy_hash (str): Legacy hash string
            legacy_type (str): Type of legacy hash
            
        Returns:
            str or None: New bcrypt hash if migration successful, None otherwise
        """
        # Verify legacy password first
        if LegacyPasswordHasher.verify_legacy_hash(password, legacy_hash, legacy_type):
            # Create new bcrypt hash
            return NodeJSCompatiblePasswordHasher.hash_password(password)
        
        return None


class SecurePasswordValidator:
    """
    Enhanced password validation for security
    """
    
    @staticmethod
    def validate_password_strength(password):
        """
        Validate password strength
        
        Args:
            password (str): Password to validate
            
        Returns:
            dict: Validation result with errors and score
        """
        errors = []
        score = 0
        
        # Length check
        if len(password) < 8:
            errors.append("密码长度至少8位")
        elif len(password) >= 12:
            score += 2
        else:
            score += 1
        
        # Character variety checks
        has_lower = any(c.islower() for c in password)
        has_upper = any(c.isupper() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
        
        if not has_lower:
            errors.append("密码必须包含小写字母")
        else:
            score += 1
        
        if not has_upper:
            errors.append("密码必须包含大写字母")
        else:
            score += 1
        
        if not has_digit:
            errors.append("密码必须包含数字")
        else:
            score += 1
        
        if not has_special:
            errors.append("密码必须包含特殊字符")
        else:
            score += 1
        
        # Common password check
        common_passwords = [
            'password', '123456', '123456789', 'qwerty', 'abc123',
            'password123', 'admin', 'root', '12345678', 'welcome'
        ]
        
        if password.lower() in common_passwords:
            errors.append("密码过于简单，请使用更复杂的密码")
            score = max(0, score - 2)
        
        # Sequential characters check
        if SecurePasswordValidator._has_sequential_chars(password):
            errors.append("密码不能包含连续字符")
            score = max(0, score - 1)
        
        # Repeated characters check
        if SecurePasswordValidator._has_repeated_chars(password):
            errors.append("密码不能包含过多重复字符")
            score = max(0, score - 1)
        
        # Calculate strength level
        if score >= 6:
            strength = "强"
        elif score >= 4:
            strength = "中"
        else:
            strength = "弱"
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'score': score,
            'strength': strength
        }
    
    @staticmethod
    def _has_sequential_chars(password, min_length=3):
        """Check for sequential characters"""
        for i in range(len(password) - min_length + 1):
            substr = password[i:i + min_length]
            if (substr.isdigit() and 
                all(ord(substr[j]) == ord(substr[0]) + j for j in range(len(substr)))):
                return True
            if (substr.isalpha() and 
                all(ord(substr[j].lower()) == ord(substr[0].lower()) + j for j in range(len(substr)))):
                return True
        return False
    
    @staticmethod
    def _has_repeated_chars(password, max_repeat=3):
        """Check for repeated characters"""
        char_count = {}
        for char in password:
            char_count[char] = char_count.get(char, 0) + 1
            if char_count[char] > max_repeat:
                return True
        return False


# Utility functions for easy use
def hash_password(password, rounds=12):
    """
    Hash password using bcrypt
    
    Args:
        password (str): Plain text password
        rounds (int): Number of salt rounds
        
    Returns:
        str: Bcrypt hash string
    """
    return NodeJSCompatiblePasswordHasher.hash_password(password, rounds)


def verify_password(password, hash_str):
    """
    Verify password against hash
    
    Args:
        password (str): Plain text password
        hash_str (str): Hash string (bcrypt or legacy)
        
    Returns:
        bool: True if password matches
    """
    # Try bcrypt first
    if NodeJSCompatiblePasswordHasher.is_bcrypt_hash(hash_str):
        return NodeJSCompatiblePasswordHasher.verify_password(password, hash_str)
    
    # Try legacy formats
    legacy_types = ['md5', 'sha1', 'sha256']
    for hash_type in legacy_types:
        if LegacyPasswordHasher.verify_legacy_hash(password, hash_str, hash_type):
            return True
    
    return False


def validate_password_strength(password):
    """
    Validate password strength
    
    Args:
        password (str): Password to validate
        
    Returns:
        dict: Validation result
    """
    return SecurePasswordValidator.validate_password_strength(password)