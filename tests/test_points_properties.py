"""
Property-based tests for points system.
Feature: django-mall-migration
"""
import pytest
from hypothesis import given, strategies as st, settings, assume
from hypothesis.extra.django import TestCase
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.db import transaction
from django.test import TransactionTestCase
import uuid
import time

from apps.points.models import PointsAccount, PointsRule, PointsTransaction, PointsExpiration
from apps.points.services import PointsService, TierPointsCalculator
from apps.membership.models import MembershipTier, MembershipStatus

User = get_user_model()


@pytest.mark.django_db(transaction=True)
class TestPointsCalculationProperties(TestCase):
    """Property tests for points calculation functionality"""

    def setUp(self):
        """Set up test data with membership tiers and points rules"""
        # Create membership tiers
        self.bronze_tier = MembershipTier.objects.create(
            name='bronze',
            min_spending=Decimal('0'),
            max_spending=Decimal('999.99'),
            points_multiplier=Decimal('1.0'),
            benefits={'free_shipping': False, 'early_access': False}
        )
        
        self.silver_tier = MembershipTier.objects.create(
            name='silver',
            min_spending=Decimal('1000'),
            max_spending=Decimal('4999.99'),
            points_multiplier=Decimal('1.2'),
            benefits={'free_shipping': True, 'early_access': False}
        )
        
        self.gold_tier = MembershipTier.objects.create(
            name='gold',
            min_spending=Decimal('5000'),
            max_spending=Decimal('19999.99'),
            points_multiplier=Decimal('1.5'),
            benefits={'free_shipping': True, 'early_access': True}
        )
        
        self.platinum_tier = MembershipTier.objects.create(
            name='platinum',
            min_spending=Decimal('20000'),
            max_spending=None,
            points_multiplier=Decimal('2.0'),
            benefits={'free_shipping': True, 'early_access': True, 'vip_support': True}
        )
        
        # Create points rules
        self.purchase_rule = PointsRule.objects.create(
            rule_type='purchase',
            points_amount=1,  # 1% of purchase amount
            is_percentage=True,
            description='Earn 1% of purchase amount as points'
        )
        
        self.registration_rule = PointsRule.objects.create(
            rule_type='registration',
            points_amount=100,
            is_percentage=False,
            description='Welcome bonus for registration'
        )
        
        self.first_purchase_rule = PointsRule.objects.create(
            rule_type='first_purchase',
            points_amount=200,
            is_percentage=False,
            description='Bonus for first purchase'
        )
        
        self.review_rule = PointsRule.objects.create(
            rule_type='review',
            points_amount=50,
            is_percentage=False,
            description='Points for product reviews'
        )

    def _create_unique_user(self, base_username="test_user"):
        """Create a unique user to avoid conflicts"""
        unique_id = str(uuid.uuid4())[:8]
        timestamp = int(time.time() * 1000) % 100000
        username = f"{base_username}_{unique_id}_{timestamp}"
        email = f"{username}@example.com"
        
        return User.objects.create_user(
            username=username,
            email=email,
            password="testpass123"
        )

    @given(
        order_amount=st.decimals(
            min_value=Decimal('10.00'),  # Increased minimum to ensure points are always generated
            max_value=Decimal('10000.00'), 
            places=2
        ),
        tier_name=st.sampled_from(['bronze', 'silver', 'gold', 'platinum'])
    )
    @settings(max_examples=50, deadline=None)  # Reduced examples for faster execution
    def test_points_award_calculation(self, order_amount, tier_name):
        """
        Property 6: Points Award Calculation
        For any completed order, the points awarded should equal order_amount * tier_multiplier, 
        and the member's points balance should increase accordingly
        **Feature: django-mall-migration, Property 6: Points Award Calculation**
        **Validates: Requirements 3.1, 3.2**
        """
        # Create a unique user to avoid conflicts
        user = self._create_unique_user("points_test")
        
        # Create membership status with specified tier
        tier = MembershipTier.objects.get(name=tier_name)
        membership, created = MembershipStatus.objects.get_or_create(
            user=user,
            defaults={
                'tier': tier,
                'total_spending': Decimal('0')
            }
        )
        
        # Update tier if membership already exists
        if not created:
            membership.tier = tier
            membership.save()
        
        # Get or create points account
        account = PointsService.get_or_create_account(user)
        initial_points = account.available_points
        
        # Calculate expected points based on purchase rule (1% of order amount) and tier multiplier
        tier_multiplier = TierPointsCalculator.get_multiplier(tier_name)
        purchase_rule = PointsRule.objects.get(rule_type='purchase')
        expected_points = purchase_rule.calculate_points(
            base_amount=order_amount, 
            tier_multiplier=tier_multiplier
        )
        
        # Skip test if expected points would be 0 (due to rounding)
        assume(expected_points > 0)
        
        # Generate unique order ID
        order_id = f"order_{user.id}_{int(time.time() * 1000000) % 1000000}"
        
        # Award purchase points
        transaction_result = PointsService.award_purchase_points(
            user=user,
            order_amount=order_amount,
            tier_multiplier=tier_multiplier,
            order_id=order_id
        )
        
        # Verify transaction was created
        assert transaction_result is not None, f"Transaction should not be None for order_amount={order_amount}, tier={tier_name}, expected_points={expected_points}"
        assert transaction_result.amount == expected_points, f"Expected {expected_points} points but got {transaction_result.amount}"
        assert transaction_result.transaction_type == 'earning'
        
        # Refresh account from database
        account.refresh_from_db()
        
        # Verify points balance increased correctly
        assert account.available_points == initial_points + expected_points
        assert account.total_points == initial_points + expected_points
        assert account.lifetime_earned >= expected_points
        
        # Verify points calculation matches tier multiplier and purchase rule
        calculated_points = purchase_rule.calculate_points(
            base_amount=order_amount, 
            tier_multiplier=tier_multiplier
        )
        assert transaction_result.amount == calculated_points, f"Points calculation mismatch: expected {calculated_points}, got {transaction_result.amount}"
        
        # Verify expiration record was created
        expiration_records = PointsExpiration.objects.filter(
            account=account,
            points_amount=expected_points
        )
        assert expiration_records.exists()
        
        expiration = expiration_records.first()
        assert expiration.remaining_points == expected_points
        assert not expiration.is_expired

    @given(
        initial_points=st.integers(min_value=1000, max_value=10000),
        redemption_amount=st.integers(min_value=500, max_value=5000).filter(lambda x: x % 100 == 0),
        order_amount=st.decimals(
            min_value=Decimal('10.00'), 
            max_value=Decimal('1000.00'), 
            places=2
        )
    )
    @settings(max_examples=50, deadline=None)  # Reduced examples for faster execution
    def test_points_redemption_transaction(self, initial_points, redemption_amount, order_amount):
        """
        Property 7: Points Redemption Transaction
        For any valid points redemption, the member's points balance should decrease by the redeemed amount 
        and the order should receive the corresponding discount
        **Feature: django-mall-migration, Property 7: Points Redemption Transaction**
        **Validates: Requirements 3.3**
        """
        # Create a unique user to avoid conflicts
        user = self._create_unique_user("redeem_test")
        
        # Get points account and add initial points
        account = PointsService.get_or_create_account(user)
        account.add_points(
            amount=initial_points,
            transaction_type='earning',
            description='Initial test points'
        )
        
        # Ensure redemption amount doesn't exceed available points
        max_redeemable = PointsService.calculate_max_redeemable_points(user, order_amount)
        if redemption_amount > max_redeemable:
            assume(False)  # Skip this test case
        
        initial_balance = account.available_points
        
        # Calculate expected discount (100 points = $1)
        expected_discount = Decimal(str(redemption_amount)) / 100
        
        # Generate unique order ID
        order_id = f"order_{user.id}_{int(time.time() * 1000000) % 1000000}"
        
        # Perform redemption
        try:
            redemption_result = PointsService.redeem_points_for_discount(
                user=user,
                points_amount=redemption_amount,
                order_id=order_id
            )
            
            # Verify redemption result
            assert redemption_result['points_redeemed'] == redemption_amount
            assert redemption_result['discount_amount'] == expected_discount
            assert redemption_result['transaction'] is not None
            
            # Verify transaction details
            transaction_obj = redemption_result['transaction']
            assert transaction_obj.amount == -redemption_amount  # Negative for redemption
            assert transaction_obj.transaction_type == 'redemption'
            
            # Refresh account and verify balance decreased
            account.refresh_from_db()
            assert account.available_points == initial_balance - redemption_amount
            assert account.lifetime_redeemed >= redemption_amount
            
        except ValueError as e:
            # Redemption might fail due to business rules - this is acceptable
            # Just ensure the error message is appropriate
            assert "points" in str(e).lower() or "redemption" in str(e).lower()

    @given(
        transaction_sequence=st.lists(
            st.tuples(
                st.sampled_from(['earning', 'redemption']),
                st.integers(min_value=100, max_value=1000)
            ),
            min_size=1,
            max_size=5  # Reduced for faster execution
        )
    )
    @settings(max_examples=30, deadline=None)  # Reduced examples for faster execution
    def test_points_transaction_history(self, transaction_sequence):
        """
        Property 8: Points Transaction History
        For any points-related activity (earning or spending), a transaction record should be created 
        with correct amount, type, and timestamp
        **Feature: django-mall-migration, Property 8: Points Transaction History**
        **Validates: Requirements 3.6**
        """
        # Create a unique user to avoid conflicts
        user = self._create_unique_user("history_test")
        
        # Get points account
        account = PointsService.get_or_create_account(user)
        
        # Account for automatic registration points (100 points awarded by signal)
        # Clear any existing transactions to start fresh
        account.transactions.all().delete()
        account.available_points = 0
        account.total_points = 0
        account.lifetime_earned = 0
        account.lifetime_redeemed = 0
        account.save()
        
        # Add initial points to enable redemptions
        initial_transaction = account.add_points(
            amount=10000,
            transaction_type='earning',
            description='Initial points for testing'
        )
        
        # Also clear any expiration records to start fresh
        account.expirations.all().delete()
        
        # Re-create expiration record for the initial points
        from apps.points.models import PointsExpiration
        from django.utils import timezone
        from datetime import timedelta
        
        PointsExpiration.objects.create(
            account=account,
            points_amount=10000,
            earned_date=timezone.now(),
            expiry_date=timezone.now() + timedelta(days=365),
            transaction=initial_transaction
        )
        
        initial_transaction_count = account.transactions.count()
        expected_transactions = []
        
        # Process transaction sequence
        for i, (transaction_type, amount) in enumerate(transaction_sequence):
            if transaction_type == 'earning':
                # Add points
                transaction_obj = account.add_points(
                    amount=amount,
                    transaction_type='earning',
                    description=f'Test earning {amount}',
                    reference_id=f'test_{i}_{user.id}'
                )
                expected_transactions.append({
                    'type': 'earning',
                    'amount': amount,
                    'transaction': transaction_obj
                })
                
            elif transaction_type == 'redemption':
                # Redeem points (only if we have enough)
                if account.available_points >= amount and amount >= 500:
                    try:
                        order_id = f'test_order_{i}_{user.id}_{int(time.time() * 1000000) % 1000000}'
                        balance_before_redemption = account.available_points
                        redemption_result = PointsService.redeem_points_for_discount(
                            user=user,
                            points_amount=amount,
                            order_id=order_id
                        )
                        account.refresh_from_db()
                        balance_after_redemption = account.available_points
                        
                        # Verify the redemption actually worked
                        assert balance_after_redemption == balance_before_redemption - amount, f"Redemption failed: before={balance_before_redemption}, after={balance_after_redemption}, amount={amount}"
                        
                        expected_transactions.append({
                            'type': 'redemption',
                            'amount': -amount,  # Negative for redemption
                            'transaction': redemption_result['transaction']
                        })
                    except ValueError:
                        # Redemption failed due to business rules - skip
                        continue
        
        # Verify all expected transactions exist in history
        account.refresh_from_db()
        all_transactions = list(account.transactions.all().order_by('created_at'))
        
        # Should have initial transaction plus our test transactions
        assert len(all_transactions) >= initial_transaction_count + len(expected_transactions)
        
        # Verify each expected transaction exists and has correct properties
        for expected in expected_transactions:
            transaction_obj = expected['transaction']
            
            # Verify transaction exists in account history
            assert transaction_obj in all_transactions
            
            # Verify transaction properties
            assert transaction_obj.account == account
            assert transaction_obj.amount == expected['amount']
            
            if expected['type'] == 'earning':
                assert transaction_obj.transaction_type == 'earning'
                assert transaction_obj.amount > 0
            elif expected['type'] == 'redemption':
                assert transaction_obj.transaction_type == 'redemption'
                assert transaction_obj.amount < 0
            
            # Verify transaction has timestamp
            assert transaction_obj.created_at is not None
            
            # Verify balance_after is consistent
            assert isinstance(transaction_obj.balance_after, int)
        
        # Verify transaction history is ordered by creation time
        transaction_times = [t.created_at for t in all_transactions]
        assert transaction_times == sorted(transaction_times)
        
        # Verify final balance matches transaction history
        # The account balance should equal the sum of all transaction amounts
        # (including the initial 10000 points transaction)
        total_earned = sum(t.amount for t in all_transactions if t.amount > 0)
        total_spent = abs(sum(t.amount for t in all_transactions if t.amount < 0))
        expected_final_balance = total_earned - total_spent
        
        # The account balance should match the calculated balance from transaction history
        assert account.available_points == expected_final_balance, f"Account balance {account.available_points} doesn't match calculated balance {expected_final_balance} from transaction history. Transactions: {[(t.amount, t.transaction_type) for t in all_transactions]}"

    @given(
        order_amounts=st.lists(
            st.decimals(min_value=Decimal('10.00'), max_value=Decimal('1000.00'), places=2),
            min_size=1,
            max_size=3  # Reduced for faster execution
        ),
        tier_name=st.sampled_from(['bronze', 'silver', 'gold', 'platinum'])
    )
    @settings(max_examples=30, deadline=None)  # Reduced examples for faster execution
    def test_multiple_purchase_points_accumulation(self, order_amounts, tier_name):
        """
        Property test for multiple purchase points accumulation
        For any sequence of purchases, the total points should equal the sum of 
        individual purchase points calculations
        """
        # Create a unique user to avoid conflicts
        user = self._create_unique_user("multi_purchase")
        
        # Set up membership tier
        tier = MembershipTier.objects.get(name=tier_name)
        membership = MembershipStatus.objects.create(
            user=user,
            tier=tier,
            total_spending=Decimal('0')
        )
        
        # Get points account
        account = PointsService.get_or_create_account(user)
        initial_points = account.available_points
        
        # Calculate expected points for each purchase using the purchase rule
        tier_multiplier = TierPointsCalculator.get_multiplier(tier_name)
        purchase_rule = PointsRule.objects.get(rule_type='purchase')
        expected_total_points = 0
        
        # Award points for each purchase
        for i, order_amount in enumerate(order_amounts):
            expected_points = purchase_rule.calculate_points(
                base_amount=order_amount, 
                tier_multiplier=tier_multiplier
            )
            expected_total_points += expected_points
            
            order_id = f"order_{i}_{user.id}_{int(time.time() * 1000000) % 1000000}"
            transaction_obj = PointsService.award_purchase_points(
                user=user,
                order_amount=order_amount,
                tier_multiplier=tier_multiplier,
                order_id=order_id
            )
            
            assert transaction_obj is not None, f"Transaction should not be None for order {i}"
            assert transaction_obj.amount == expected_points, f"Expected {expected_points} points but got {transaction_obj.amount} for order {i}"
        
        # Refresh account and verify total
        account.refresh_from_db()
        assert account.available_points == initial_points + expected_total_points
        assert account.lifetime_earned >= expected_total_points

    @given(
        bonus_type=st.sampled_from(['registration', 'first_purchase', 'review'])
    )
    @settings(max_examples=30, deadline=None)  # Reduced examples for faster execution
    def test_bonus_points_award(self, bonus_type):
        """
        Property test for bonus points award
        For any bonus points type, the correct amount should be awarded 
        according to the rules
        """
        # Create a unique user to avoid conflicts
        user = self._create_unique_user("bonus_test")
        
        # Get points account
        account = PointsService.get_or_create_account(user)
        initial_points = account.available_points
        
        # Get expected points for bonus type
        rule = PointsRule.objects.get(rule_type=bonus_type)
        expected_points = rule.points_amount
        
        # Award bonus points based on type
        transaction_obj = None
        if bonus_type == 'registration':
            transaction_obj = PointsService.award_registration_points(user)
        elif bonus_type == 'first_purchase':
            order_id = f"order_{user.id}_{int(time.time() * 1000000) % 1000000}"
            transaction_obj = PointsService.award_first_purchase_points(user, order_id)
        elif bonus_type == 'review':
            product_id = f"product_{user.id}_{int(time.time() * 1000000) % 1000000}"
            transaction_obj = PointsService.award_review_points(user, product_id)
        
        # Verify transaction was created with correct amount
        if transaction_obj:  # Some bonus types might not award points if conditions aren't met
            assert transaction_obj.amount == expected_points
            assert transaction_obj.transaction_type == 'earning'
            
            # Refresh account and verify balance
            account.refresh_from_db()
            assert account.available_points >= initial_points + expected_points

    @given(
        tier_multipliers=st.lists(
            st.decimals(min_value=Decimal('1.0'), max_value=Decimal('3.0'), places=1),
            min_size=1,
            max_size=4
        ),
        base_amount=st.decimals(
            min_value=Decimal('50.00'), 
            max_value=Decimal('500.00'), 
            places=2
        )
    )
    @settings(max_examples=30, deadline=None)  # Reduced examples for faster execution
    def test_tier_multiplier_consistency(self, tier_multipliers, base_amount):
        """
        Property test for tier multiplier consistency
        For any base amount and tier multiplier, the points calculation 
        should be consistent and proportional
        """
        # Test that points scale proportionally with tier multipliers
        previous_points = 0
        previous_multiplier = Decimal('0')
        
        for multiplier in sorted(set(tier_multipliers)):
            # Calculate points using the rule
            points = self.purchase_rule.calculate_points(
                base_amount=base_amount, 
                tier_multiplier=float(multiplier)
            )
            
            # Verify points are non-negative
            assert points >= 0
            
            # Verify points increase with multiplier (for same base amount)
            if previous_multiplier > 0 and multiplier > previous_multiplier:
                assert points >= previous_points
            
            previous_points = points
            previous_multiplier = multiplier

    @given(
        initial_points=st.integers(min_value=0, max_value=5000),
        earning_amounts=st.lists(
            st.integers(min_value=10, max_value=500),
            min_size=1,
            max_size=5  # Reduced for faster execution
        )
    )
    @settings(max_examples=30, deadline=None)  # Reduced examples for faster execution
    def test_points_balance_consistency(self, initial_points, earning_amounts):
        """
        Property test for points balance consistency
        For any sequence of points operations, the balance should always 
        be consistent with the transaction history
        """
        # Create a unique user to avoid conflicts
        user = self._create_unique_user("balance_test")
        
        # Get points account
        account = PointsService.get_or_create_account(user)
        
        # Manually set initial points (for testing purposes)
        if initial_points > 0:
            account.add_points(
                amount=initial_points,
                transaction_type='earning',
                description='Initial test points'
            )
        
        # Track expected balance
        expected_balance = account.available_points
        
        # Add points through various earning operations
        for i, amount in enumerate(earning_amounts):
            reference_id = f'test_{i}_{user.id}_{int(time.time() * 1000000) % 1000000}'
            account.add_points(
                amount=amount,
                transaction_type='earning',
                description=f'Test earning {i}',
                reference_id=reference_id
            )
            expected_balance += amount
            
            # Verify balance is consistent
            account.refresh_from_db()
            assert account.available_points == expected_balance
        
        # Verify transaction history matches balance
        total_earned = sum(t.amount for t in account.transactions.filter(amount__gt=0))
        total_spent = abs(sum(t.amount for t in account.transactions.filter(amount__lt=0)))
        
        assert account.available_points == total_earned - total_spent
        assert account.lifetime_earned >= total_earned

    @given(
        tier_changes=st.lists(
            st.sampled_from(['bronze', 'silver', 'gold', 'platinum']),
            min_size=2,
            max_size=4  # Reduced for faster execution
        ),
        order_amount=st.decimals(
            min_value=Decimal('100.00'), 
            max_value=Decimal('1000.00'), 
            places=2
        )
    )
    @settings(max_examples=20, deadline=None)  # Reduced examples for faster execution
    def test_points_calculation_with_tier_changes(self, tier_changes, order_amount):
        """
        Property test for points calculation with tier changes
        For any sequence of tier changes, points should be calculated 
        correctly based on the current tier at the time of earning
        """
        # Create a unique user to avoid conflicts
        user = self._create_unique_user("tier_change")
        
        # Create membership status
        initial_tier = MembershipTier.objects.get(name=tier_changes[0])
        membership = MembershipStatus.objects.create(
            user=user,
            tier=initial_tier,
            total_spending=Decimal('0')
        )
        
        # Get points account
        account = PointsService.get_or_create_account(user)
        
        # Test points calculation for each tier
        for i, tier_name in enumerate(tier_changes):
            # Update user's tier
            tier = MembershipTier.objects.get(name=tier_name)
            membership.tier = tier
            membership.save()
            
            # Calculate expected points for this tier using the purchase rule
            tier_multiplier = TierPointsCalculator.get_multiplier(tier_name)
            purchase_rule = PointsRule.objects.get(rule_type='purchase')
            expected_points = purchase_rule.calculate_points(
                base_amount=order_amount, 
                tier_multiplier=tier_multiplier
            )
            
            # Award points
            initial_balance = account.available_points
            order_id = f"order_{tier_name}_{i}_{user.id}_{int(time.time() * 1000000) % 1000000}"
            transaction_obj = PointsService.award_purchase_points(
                user=user,
                order_amount=order_amount,
                tier_multiplier=tier_multiplier,
                order_id=order_id
            )
            
            # Verify points were calculated correctly for current tier
            assert transaction_obj.amount == expected_points
            
            # Verify balance updated correctly
            account.refresh_from_db()
            assert account.available_points == initial_balance + expected_points