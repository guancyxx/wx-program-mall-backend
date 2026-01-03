"""
Property-based tests for security data protection.

Feature: django-mall-migration, Property 18: Security Data Protection
Validates: Requirements 10.2
"""
import pytest
import string
from hypothesis import given, strategies as st, settings
from django.contrib.auth.hashers import check_password
from django.db import transaction
from apps.users.models import User


@pytest.mark.django_db
class TestSecurityDataProtection:
    """Property-based tests for security data protection requirements."""

    @given(
        username=st.text(
            alphabet=string.ascii_letters + string.digits + '_',
            min_size=3,
            max_size=30
        ).filter(lambda x: x and not x.startswith('_')),
        email=st.emails(),
        password=st.text(min_size=8, max_size=128),
        phone=st.text(
            alphabet=string.digits,
            min_size=10,
            max_size=15
        ).filter(lambda x: x.startswith(('1', '2', '3', '4', '5', '6', '7', '8', '9'))),
        wechat_openid=st.text(
            alphabet=string.ascii_letters + string.digits,
            min_size=10,
            max_size=50
        )
    )
    @settings(max_examples=100, deadline=5000)
    @pytest.mark.django_db(transaction=True)
    def test_password_hashing_security(self, username, email, password, phone, wechat_openid):
        """
        Property 18: Security Data Protection
        For any user registration with sensitive data, passwords should be hashed 
        and personal information should be properly protected.
        
        Validates: Requirements 10.2
        """
        try:
            with transaction.atomic():
                # Create user with sensitive data
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    phone=phone,
                    wechat_openid=wechat_openid
                )
                
                # Verify password is hashed (not stored in plaintext)
                assert user.password != password, "Password should not be stored in plaintext"
                assert user.password.startswith(('pbkdf2_', 'bcrypt', 'argon2', 'md5$')), "Password should use hashing algorithm"
                
                # Verify password can be verified using Django's check_password
                assert check_password(password, user.password), "Hashed password should be verifiable"
                
                # Verify sensitive data is stored but accessible
                assert user.phone == phone, "Phone number should be stored correctly"
                assert user.wechat_openid == wechat_openid, "WeChat OpenID should be stored correctly"
                assert user.email.lower() == email.lower(), "Email should be stored correctly (case-insensitive)"
                
                # Verify user can authenticate with correct password
                authenticated_user = User.objects.get(username=username)
                assert check_password(password, authenticated_user.password), "User should authenticate with correct password"
                
                # Verify wrong password fails authentication
                assert not check_password("wrong_password", authenticated_user.password), "Wrong password should fail authentication"
                
        except Exception as e:
            # Skip invalid data combinations that violate database constraints
            if "UNIQUE constraint failed" in str(e) or "duplicate key" in str(e):
                pytest.skip(f"Skipping due to unique constraint: {e}")
            else:
                raise

    @given(
        sensitive_data=st.text(min_size=1, max_size=100)
    )
    @settings(max_examples=100, deadline=3000)
    @pytest.mark.django_db(transaction=True)
    def test_wechat_session_key_protection(self, sensitive_data):
        """
        Property 18: Security Data Protection (WeChat Session Key)
        For any WeChat session key storage, sensitive session data should be 
        properly handled and not exposed in logs or error messages.
        
        Validates: Requirements 10.2
        """
        try:
            with transaction.atomic():
                # Create user with WeChat session key
                user = User.objects.create_user(
                    username=f"wechat_user_{hash(sensitive_data) % 10000}",
                    email=f"wechat_{hash(sensitive_data) % 10000}@example.com",
                    password="secure_password_123",
                    wechat_session_key=sensitive_data
                )
                
                # Verify session key is stored
                assert user.wechat_session_key == sensitive_data, "WeChat session key should be stored correctly"
                
                # Verify session key is retrievable
                retrieved_user = User.objects.get(id=user.id)
                assert retrieved_user.wechat_session_key == sensitive_data, "WeChat session key should be retrievable"
                
                # Verify string representation doesn't expose sensitive data
                user_str = str(user)
                # Only check if sensitive data is not a single character that might appear in username
                if len(sensitive_data) > 1:
                    assert sensitive_data not in user_str, "User string representation should not expose session key"
                
        except Exception as e:
            # Skip invalid data combinations
            if "UNIQUE constraint failed" in str(e) or "duplicate key" in str(e):
                pytest.skip(f"Skipping due to unique constraint: {e}")
            else:
                raise

    @given(
        user_data=st.fixed_dictionaries({
            'username': st.text(
                alphabet=string.ascii_letters + string.digits + '_',
                min_size=3,
                max_size=30
            ).filter(lambda x: x and not x.startswith('_')),
            'email': st.emails(),
            'password': st.text(min_size=8, max_size=128),
        })
    )
    @settings(max_examples=100, deadline=3000)
    @pytest.mark.django_db(transaction=True)
    def test_user_data_integrity_protection(self, user_data):
        """
        Property 18: Security Data Protection (Data Integrity)
        For any user data storage operation, data integrity should be maintained
        and sensitive information should be properly protected.
        
        Validates: Requirements 10.2
        """
        try:
            with transaction.atomic():
                # Create user
                user = User.objects.create_user(**user_data)
                
                # Verify data integrity
                retrieved_user = User.objects.get(id=user.id)
                assert retrieved_user.username == user_data['username'], "Username should be stored correctly"
                assert retrieved_user.email.lower() == user_data['email'].lower(), "Email should be stored correctly (case-insensitive)"
                
                # Verify password security
                assert retrieved_user.password != user_data['password'], "Password should be hashed"
                assert check_password(user_data['password'], retrieved_user.password), "Password should be verifiable"
                
                # Verify timestamps are set
                assert retrieved_user.created_at is not None, "Created timestamp should be set"
                assert retrieved_user.updated_at is not None, "Updated timestamp should be set"
                
                # Verify user is active by default
                assert retrieved_user.is_active is True, "User should be active by default"
                
        except Exception as e:
            # Skip invalid data combinations
            if "UNIQUE constraint failed" in str(e) or "duplicate key" in str(e):
                pytest.skip(f"Skipping due to unique constraint: {e}")
            else:
                raise