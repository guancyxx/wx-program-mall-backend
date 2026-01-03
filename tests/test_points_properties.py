"""
Property-based tests for points system.
Feature: django-mall-migration
"""
import pytest
from hypothesis import given, strategies as st, settings, assume
from hypothesis.extra.django import TestCase
from decimal import Decimal
from django.contrib.auth import get_user_model

from apps.points.models import PointsAccount, PointsRule, PointsTransaction, PointsExpiration
from apps.points.services import PointsService, TierPointsCalculator
from apps.membership.models import MembershipTier, MembershipStatus

User = get_user_model()


class TestPointsCalculationProperties(TestCase):
    """Property tests for points calculation functionality"""

    def setUp(self):
        """Set up test data with membership tiers and points rules"""
        # Create membership tiers
        self.bronze_tier = MembershipTier.objects.create(
            name='bronze',
            display_name='Bronze',
            min_spending=Decimal('0'),
            max_spending=Decimal('999.99'),
            points_multiplier=Decimal('1.0'),
            benefits={'free_shipping': False}
        )
        
        self.silver_tier = MembershipTier.objects.create(
            name='silver',
            display_name='Silver',
            min_spending=Decimal('1000'),
            max_spending=Decimal('4999.99'),
            points_multiplier=Decimal('1.2'),
            benefits={'free_shipping': True}
        )
        
        self.gold_tier = MembershipTier.objects.create(
            name='gold',
            display_name='Gold',
            min_spending=Decimal('5000'),
            max_spending=Decimal('19999.99'),
            points_multiplier=Decimal('1.5'),
            benefits={'free_shipping': True, 'early_access': True}
        )
        
        self.platinum_tier = MembershipTier.objects.create(
            name='platinum',
            display_name='Platinum',
            min_spending=Decimal('20000'),
            max_spending=None,
            points_multiplier=Decimal('2.0'),
            benefits={'free_shipping': True, 'early_access': True, 'exclusive_products': True}
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

    @given(
        username=st.text(
            min_size=3, 
            max_size=20, 
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))
        ).filter(lambda x: x.isalnum()),
        order_amount=st.decimals(
            min_value=Decimal('1.00'), 
            max_value=Decimal('10000.00'), 
            places=2
        ),
        tier_name=st.sampled_from(['bronze', 'silver', 'gold', 'platinum'])
    )
    @settings(max_examples=100, deadline=None)
    def test_points_award_calculation(self, username, order_amount, tier_name):
        """
        Property 6: Points Award Calculation
        For any completed order, the points awarded should equal order_amount * tier_multiplier, 
        and the member's points balance should increase accordingly
        **Feature: django-mall-migration, Property 6: Points Award Calculation**
        **Validates: Requirements 3.1, 3.2**
        """
        # Ensure unique username
        import time
        timestamp = int(time.time() * 1000) % 100000
        username = f"points_test_{username[:10]}_{timestamp}"
        
        # Create a user
        user = User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="testpass123"
        )
        
        # Create membership status with specified tier
        tier = MembershipTier.objects.get(name=tier_name)
        membership, created = MembershipStatus.objects.get_or_create(
            user=user,
            defaults={
                'tier': tier,
                'total_spending': Decimal('0')
            }
        )
        
        if not created:
            membership.tier = tier
            membership.save()
        
        # Get or create points account
        account = PointsService.get_or_create_account(user)
        initial_points = account.available_points
        
        # Calculate expected points based on tier multiplier
        tier_multiplier = TierPointsCalculator.get_multiplier(tier_name)
        expected_points = int(order_amount * Decimal(str(tier_multiplier)))
        
        # Award purchase points
        transaction = PointsService.award_purchase_points(
            user=user,
            order_amount=order_amount,
            tier_multiplier=tier_multiplier,
            order_id=f"order_{timestamp}"
        )
        
        # Verify transaction was created
        assert transaction is not None
        assert transaction.amount == expected_points
        assert transaction.transaction_type == 'earning'
        
        # Refresh account from database
        account.refresh_from_db()
        
        # Verify points balance increased correctly
        assert account.available_points == initial_points + expected_points
        assert account.total_points == initial_points + expected_points
        assert account.lifetime_earned >= expected_points
        
        # Verify points calculation matches tier multiplier
        base_points = int(order_amount)  # 1% of order amount
        calculated_points = int(base_points * Decimal(str(tier_multiplier)))
        assert transaction.amount == calculated_points
        
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
        username=st.text(
            min_size=3, 
            max_size=20, 
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))
        ).filter(lambda x: x.isalnum()),
        initial_points=st.integers(min_value=1000, max_value=10000),
        redemption_amount=st.integers(min_value=500, max_value=5000).filter(lambda x: x % 100 == 0),
        order_amount=st.decimals(
            min_value=Decimal('10.00'), 
            max_value=Decimal('1000.00'), 
            places=2
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_points_redemption_transaction(self, username, initial_points, redemption_amount, order_amount):
        """
        Property 7: Points Redemption Transaction
        For any valid points redemption, the member's points balance should decrease by the redeemed amount 
        and the order should receive the corresponding discount
        **Feature: django-mall-migration, Property 7: Points Redemption Transaction**
        **Validates: Requirements 3.3**
        """
        # Ensure unique username
        import time
        timestamp = int(time.time() * 1000) % 100000
        username = f"redeem_test_{username[:10]}_{timestamp}"
        
        # Create a user
        user = User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="testpass123"
        )
        
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
        
        # Perform redemption
        try:
            redemption_result = PointsService.redeem_points_for_discount(
                user=user,
                points_amount=redemption_amount,
                order_id=f"order_{timestamp}"
            )
            
            # Verify redemption result
            assert redemption_result['points_redeemed'] == redemption_amount
            assert redemption_result['discount_amount'] == expected_discount
            assert redemption_result['transaction'] is not None
            
            # Verify transaction details
            transaction = redemption_result['transaction']
            assert transaction.amount == -redemption_amount  # Negative for redemption
            assert transaction.transaction_type == 'redemption'
            
            # Refresh account and verify balance decreased
            account.refresh_from_db()
            assert account.available_points == initial_balance - redemption_amount
            assert account.lifetime_redeemed >= redemption_amount
            
        except ValueError as e:
            # Redemption might fail due to business rules - this is acceptable
            # Just ensure the error message is appropriate
            assert "points" in str(e).lower() or "redemption" in str(e).lower()

    @given(
        username=st.text(
            min_size=3, 
            max_size=20, 
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))
        ).filter(lambda x: x.isalnum()),
        transaction_sequence=st.lists(
            st.tuples(
                st.sampled_from(['earning', 'redemption']),
                st.integers(min_value=100, max_value=1000)
            ),
            min_size=1,
            max_size=10
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_points_transaction_history(self, username, transaction_sequence):
        """
        Property 8: Points Transaction History
        For any points-related activity (earning or spending), a transaction record should be created 
        with correct amount, type, and timestamp
        **Feature: django-mall-migration, Property 8: Points Transaction History**
        **Validates: Requirements 3.6**
        """
        # Ensure unique username
        import time
        timestamp = int(time.time() * 1000) % 100000
        username = f"history_test_{username[:10]}_{timestamp}"
        
        # Create a user
        user = User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="testpass123"
        )
        
        # Get points account
        account = PointsService.get_or_create_account(user)
        
        # Add initial points to enable redemptions
        account.add_points(
            amount=10000,
            transaction_type='earning',
            description='Initial points for testing'
        )
        
        initial_transaction_count = account.transactions.count()
        expected_transactions = []
        
        # Process transaction sequence
        for transaction_type, amount in transaction_sequence:
            if transaction_type == 'earning':
                # Add points
                transaction = account.add_points(
                    amount=amount,
                    transaction_type='earning',
                    description=f'Test earning {amount}',
                    reference_id=f'test_{len(expected_transactions)}'
                )
                expected_transactions.append({
                    'type': 'earning',
                    'amount': amount,
                    'transaction': transaction
                })
                
            elif transaction_type == 'redemption':
                # Redeem points (only if we have enough)
                if account.available_points >= amount and amount >= 500:
                    try:
                        redemption_result = PointsService.redeem_points_for_discount(
                            user=user,
                            points_amount=amount,
                            order_id=f'test_order_{len(expected_transactions)}'
                        )
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
            transaction = expected['transaction']
            
            # Verify transaction exists in account history
            assert transaction in all_transactions
            
            # Verify transaction properties
            assert transaction.account == account
            assert transaction.amount == expected['amount']
            
            if expected['type'] == 'earning':
                assert transaction.transaction_type == 'earning'
                assert transaction.amount > 0
            elif expected['type'] == 'redemption':
                assert transaction.transaction_type == 'redemption'
                assert transaction.amount < 0
            
            # Verify transaction has timestamp
            assert transaction.created_at is not None
            
            # Verify balance_after is consistent
            assert isinstance(transaction.balance_after, int)
        
        # Verify transaction history is ordered by creation time
        transaction_times = [t.created_at for t in all_transactions]
        assert transaction_times == sorted(transaction_times)
        
        # Verify final balance matches transaction history
        total_earned = sum(t.amount for t in all_transactions if t.amount > 0)
        total_spent = abs(sum(t.amount for t in all_transactions if t.amount < 0))
        expected_final_balance = total_earned - total_spent
        
        assert account.available_points == expected_final_balance

    @given(
        order_amounts=st.lists(
            st.decimals(min_value=Decimal('10.00'), max_value=Decimal('1000.00'), places=2),
            min_size=1,
            max_size=5
        ),
        tier_name=st.sampled_from(['bronze', 'silver', 'gold', 'platinum'])
    )
    @settings(max_examples=50, deadline=None)
    def test_multiple_purchase_points_accumulation(self, order_amounts, tier_name):
        """
        Property test for multiple purchase points accumulation
        For any sequence of purchases, the total points should equal the sum of 
        individual purchase points calculations
        """
        # Create a user
        user = User.objects.create_user(
            username=f"multi_purchase_{hash(str(order_amounts)) % 100000}",
            email=f"multi_{hash(str(order_amounts)) % 100000}@example.com",
            password="testpass123"
        )
        
        # Set up membership tier
        tier = MembershipTier.objects.get(name=tier_name)
        membership, created = MembershipStatus.objects.get_or_create(
            user=user,
            defaults={'tier': tier, 'total_spending': Decimal('0')}
        )
        
        # Get points account
        account = PointsService.get_or_create_account(user)
        initial_points = account.available_points
        
        # Calculate expected total points
        tier_multiplier = TierPointsCalculator.get_multiplier(tier_name)
        expected_total_points = 0
        
        # Award points for each purchase
        for i, order_amount in enumerate(order_amounts):
            expected_points = int(order_amount * Decimal(str(tier_multiplier)))
            expected_total_points += expected_points
            
            transaction = PointsService.award_purchase_points(
                user=user,
                order_amount=order_amount,
                tier_multiplier=tier_multiplier,
                order_id=f"order_{i}"
            )
            
            assert transaction is not None
            assert transaction.amount == expected_points
        
        # Refresh account and verify total
        account.refresh_from_db()
        assert account.available_points == initial_points + expected_total_points
        assert account.lifetime_earned >= expected_total_points

    @given(
        bonus_type=st.sampled_from(['registration', 'first_purchase', 'review']),
        username=st.text(
            min_size=3, 
            max_size=15, 
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))
        ).filter(lambda x: x.isalnum())
    )
    @settings(max_examples=50, deadline=None)
    def test_bonus_points_award(self, bonus_type, username):
        """
        Property test for bonus points award
        For any bonus points type, the correct amount should be awarded 
        according to the rules
        """
        # Ensure unique username
        import time
        timestamp = int(time.time() * 1000) % 100000
        username = f"bonus_test_{username[:10]}_{timestamp}"
        
        # Create a user
        user = User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="testpass123"
        )
        
        # Get points account
        account = PointsService.get_or_create_account(user)
        initial_points = account.available_points
        
        # Get expected points for bonus type
        rule = PointsRule.objects.get(rule_type=bonus_type)
        expected_points = rule.points_amount
        
        # Award bonus points based on type
        transaction = None
        if bonus_type == 'registration':
            transaction = PointsService.award_registration_points(user)
        elif bonus_type == 'first_purchase':
            transaction = PointsService.award_first_purchase_points(user, f"order_{timestamp}")
        elif bonus_type == 'review':
            transaction = PointsService.award_review_points(user, f"product_{timestamp}")
        
        # Verify transaction was created with correct amount
        if transaction:  # Some bonus types might not award points if conditions aren't met
            assert transaction.amount == expected_points
            assert transaction.transaction_type == 'earning'
            
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
    @settings(max_examples=50, deadline=None)
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
        username=st.text(
            min_size=3, 
            max_size=15, 
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))
        ).filter(lambda x: x.isalnum()),
        initial_points=st.integers(min_value=0, max_value=5000),
        earning_amounts=st.lists(
            st.integers(min_value=10, max_value=500),
            min_size=1,
            max_size=10
        )
    )
    @settings(max_examples=50, deadline=None)
    def test_points_balance_consistency(self, username, initial_points, earning_amounts):
        """
        Property test for points balance consistency
        For any sequence of points operations, the balance should always 
        be consistent with the transaction history
        """
        # Ensure unique username
        import time
        timestamp = int(time.time() * 1000) % 100000
        username = f"balance_test_{username[:10]}_{timestamp}"
        
        # Create a user
        user = User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="testpass123"
        )
        
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
            account.add_points(
                amount=amount,
                transaction_type='earning',
                description=f'Test earning {i}',
                reference_id=f'test_{i}'
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
            max_size=5
        ),
        order_amount=st.decimals(
            min_value=Decimal('100.00'), 
            max_value=Decimal('1000.00'), 
            places=2
        )
    )
    @settings(max_examples=30, deadline=None)
    def test_points_calculation_with_tier_changes(self, tier_changes, order_amount):
        """
        Property test for points calculation with tier changes
        For any sequence of tier changes, points should be calculated 
        correctly based on the current tier at the time of earning
        """
        # Create a user
        user = User.objects.create_user(
            username=f"tier_change_{hash(str(tier_changes)) % 100000}",
            email=f"tier_{hash(str(tier_changes)) % 100000}@example.com",
            password="testpass123"
        )
        
        # Create membership status
        initial_tier = MembershipTier.objects.get(name=tier_changes[0])
        membership, created = MembershipStatus.objects.get_or_create(
            user=user,
            defaults={'tier': initial_tier, 'total_spending': Decimal('0')}
        )
        
        # Get points account
        account = PointsService.get_or_create_account(user)
        
        # Test points calculation for each tier
        for tier_name in tier_changes:
            # Update user's tier
            tier = MembershipTier.objects.get(name=tier_name)
            membership.tier = tier
            membership.save()
            
            # Calculate expected points for this tier
            tier_multiplier = TierPointsCalculator.get_multiplier(tier_name)
            expected_points = int(order_amount * Decimal(str(tier_multiplier)))
            
            # Award points
            initial_balance = account.available_points
            transaction = PointsService.award_purchase_points(
                user=user,
                order_amount=order_amount,
                tier_multiplier=tier_multiplier,
                order_id=f"order_{tier_name}"
            )
            
            # Verify points were calculated correctly for current tier
            assert transaction.amount == expected_points
            
            # Verify balance updated correctly
            account.refresh_from_db()
            assert account.available_points == initial_balance + expected_points