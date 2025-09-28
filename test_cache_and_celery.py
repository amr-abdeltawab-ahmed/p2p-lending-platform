#!/usr/bin/env python
"""
Test script for Redis caching and Celery functionality.
Run this after starting the Docker services to verify everything works.

Usage:
    docker-compose exec p2p_lending_web python test_cache_and_celery.py
"""

import os
import sys
import django
import time
from datetime import date, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'p2p_lending_platform.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.loans.models import Loan, Payment
from apps.loans.tasks import check_overdue_payments, loan_status_summary_report
from apps.common.cache_utils import LoanCache
from apps.wallets.models import Wallet
from decimal import Decimal

User = get_user_model()

def test_redis_caching():
    """Test Redis caching functionality."""
    print("🗄️  Testing Redis Caching...")

    try:
        # Test basic cache operations
        LoanCache.set_available_loans(['test_loan_1', 'test_loan_2'])
        cached_loans = LoanCache.get_available_loans()

        if cached_loans == ['test_loan_1', 'test_loan_2']:
            print("✅ Basic cache get/set works")
        else:
            print("❌ Basic cache get/set failed")
            return False

        # Test cache invalidation
        LoanCache.invalidate_available_loans()
        cached_loans = LoanCache.get_available_loans()

        if cached_loans is None:
            print("✅ Cache invalidation works")
        else:
            print("❌ Cache invalidation failed")
            return False

        print("✅ Redis caching tests passed!")
        return True

    except Exception as e:
        print(f"❌ Redis caching test failed: {e}")
        return False

def test_celery_tasks():
    """Test Celery task execution."""
    print("\n⚡ Testing Celery Tasks...")

    try:
        # Test overdue payment check task
        print("Testing overdue payment check...")
        result = check_overdue_payments.delay()

        # Wait for task to complete (max 30 seconds)
        task_result = result.get(timeout=30)

        if task_result and task_result.get('status') == 'completed':
            print("✅ Overdue payment check task works")
            print(f"   Found {task_result.get('overdue_payments_found', 0)} overdue payments")
        else:
            print("❌ Overdue payment check task failed")
            print(f"   Result: {task_result}")
            return False

        # Test loan status summary report
        print("Testing loan status summary report...")
        result = loan_status_summary_report.delay()
        task_result = result.get(timeout=30)

        if task_result and task_result.get('metrics'):
            print("✅ Loan status summary report works")
            metrics = task_result.get('metrics', {})
            print(f"   Total loans: {metrics.get('total_loans', 0)}")
            print(f"   Total payments: {metrics.get('total_payments', 0)}")
        else:
            print("❌ Loan status summary report failed")
            print(f"   Result: {task_result}")
            return False

        print("✅ Celery task tests passed!")
        return True

    except Exception as e:
        print(f"❌ Celery task test failed: {e}")
        return False

def test_cache_signals():
    """Test that Django signals properly invalidate cache."""
    print("\n📡 Testing Cache Signal Integration...")

    try:
        # Create test user if doesn't exist
        borrower, created = User.objects.get_or_create(
            username='test_cache_borrower',
            defaults={
                'email': 'test_cache@example.com',
                'role': 'BORROWER'
            }
        )

        # Set cache with test data
        LoanCache.set_available_loans(['cached_loan_before'])

        # Create a new loan (should trigger signal to invalidate cache)
        loan = Loan.objects.create(
            borrower=borrower,
            amount=Decimal('1000.00'),
            term_months=6,
            annual_interest_rate=Decimal('12.00'),
            status='REQUESTED'
        )

        # Check if cache was invalidated
        cached_loans = LoanCache.get_available_loans()

        if cached_loans is None:
            print("✅ Cache signals work - cache invalidated on loan creation")
        else:
            print("❌ Cache signals failed - cache not invalidated")
            return False

        # Clean up
        loan.delete()
        if created:
            borrower.delete()

        print("✅ Cache signal integration tests passed!")
        return True

    except Exception as e:
        print(f"❌ Cache signal test failed: {e}")
        return False

def test_overdue_payment_logic():
    """Test the overdue payment marking logic."""
    print("\n📅 Testing Overdue Payment Logic...")

    try:
        # Create test user and loan
        borrower, created = User.objects.get_or_create(
            username='test_overdue_borrower',
            defaults={
                'email': 'test_overdue@example.com',
                'role': 'BORROWER'
            }
        )

        loan = Loan.objects.create(
            borrower=borrower,
            amount=Decimal('500.00'),
            term_months=3,
            annual_interest_rate=Decimal('10.00'),
            status='FUNDED'
        )

        # Create an overdue payment (due yesterday)
        yesterday = date.today() - timedelta(days=1)
        payment = Payment.objects.create(
            loan=loan,
            payment_number=1,
            due_date=yesterday,
            amount=Decimal('100.00'),
            status='PENDING'
        )

        # Run the overdue check task
        result = check_overdue_payments()

        # Refresh payment from database
        payment.refresh_from_db()

        if payment.status == 'OVERDUE':
            print("✅ Overdue payment logic works")
            print(f"   Payment {payment.id} correctly marked as OVERDUE")
        else:
            print("❌ Overdue payment logic failed")
            print(f"   Payment {payment.id} status: {payment.status} (expected OVERDUE)")
            return False

        # Clean up
        payment.delete()
        loan.delete()
        if created:
            borrower.delete()

        print("✅ Overdue payment logic tests passed!")
        return True

    except Exception as e:
        print(f"❌ Overdue payment logic test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 Testing P2P Lending Platform Cache & Celery Features")
    print("=" * 60)

    tests = [
        test_redis_caching,
        test_celery_tasks,
        test_cache_signals,
        test_overdue_payment_logic,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("🎉 All tests passed! Redis caching and Celery are working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Check the logs above for details.")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)