"""
Integration tests for the complete P2P lending platform workflow.
Tests the full happy-path scenario from loan creation to completion.

Usage:
    # Run with Django test runner (recommended):
    python manage.py test test_integration

    # Or run as standalone script:
    python test_integration.py
"""

import os
import django

# Setup Django environment before importing models
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'p2p_lending_platform.settings')
django.setup()

from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework.authtoken.models import Token
from apps.loans.models import Loan, Offer, Payment
from apps.wallets.models import Wallet, Transaction

User = get_user_model()


class P2PLendingPlatformIntegrationTest(APITestCase):
    """
    Complete integration test for the P2P lending platform.
    Tests the full workflow: loan creation → offer → acceptance → funding → payments → completion
    """

    def setUp(self):
        """Set up test users with wallets"""
        # Create borrower
        self.borrower = User.objects.create_user(
            username='john_borrower',
            email='john@example.com',
            password='testpass123',
            role='BORROWER',
            first_name='John',
            last_name='Doe'
        )

        # Create lender with sufficient funds
        self.lender = User.objects.create_user(
            username='jane_lender',
            email='jane@example.com',
            password='testpass123',
            role='LENDER',
            first_name='Jane',
            last_name='Smith'
        )

        # Create wallets
        self.lender_wallet = Wallet.objects.create(user=self.lender, balance=Decimal('10000.00'))
        self.borrower_wallet = Wallet.objects.create(user=self.borrower, balance=Decimal('2000.00'))

        # Create tokens for authentication
        self.borrower_token = Token.objects.create(user=self.borrower)
        self.lender_token = Token.objects.create(user=self.lender)

        # Test loan parameters
        self.loan_amount = Decimal('1000.00')
        self.term_months = 6
        self.requested_rate = Decimal('15.00')
        self.offer_rate = Decimal('12.00')

    def test_complete_p2p_lending_lifecycle(self):
        """Test the complete P2P lending lifecycle"""

        # Step 1: Borrower creates loan request
        print("Step 1: Borrower creates loan request")
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.borrower_token.key}')

        loan_data = {
            'amount': str(self.loan_amount),
            'term_months': self.term_months,
            'annual_interest_rate': str(self.requested_rate),
            'purpose': 'Small business expansion - need funds for inventory'
        }

        response = self.client.post('/api/loans/', loan_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        loan_id = response.data['id']
        self.assertEqual(response.data['status'], 'REQUESTED')
        self.assertEqual(Decimal(response.data['amount']), self.loan_amount)
        print(f"✓ Loan created with ID: {loan_id}")

        # Step 2: Lender retrieves available loans
        print("\nStep 2: Lender retrieves available loans")
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.lender_token.key}')

        response = self.client.get('/api/loans/available/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], loan_id)
        print(f"✓ Found {len(response.data)} available loan(s)")

        # Step 3: Lender submits offer with better rate
        print("\nStep 3: Lender submits offer")
        offer_data = {'annual_interest_rate': str(self.offer_rate)}

        response = self.client.post(f'/api/loans/{loan_id}/offer/', offer_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        offer_id = response.data['id']
        self.assertEqual(Decimal(response.data['annual_interest_rate']), self.offer_rate)
        print(f"✓ Offer created with ID: {offer_id} at {self.offer_rate}% interest")

        # Step 4: Borrower accepts the offer
        print("\nStep 4: Borrower accepts offer")
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.borrower_token.key}')

        accept_data = {'offer_id': offer_id}
        response = self.client.post(f'/api/loans/{loan_id}/accept-offer/', accept_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'PENDING_FUNDING')
        print("✓ Offer accepted, loan status: PENDING_FUNDING")

        # Step 5: Verify loan details and check balances before funding
        print("\nStep 5: Check pre-funding state")
        initial_lender_balance = self.lender_wallet.balance
        initial_borrower_balance = self.borrower_wallet.balance

        response = self.client.get(f'/api/loans/{loan_id}/')
        loan_details = response.data
        monthly_payment = Decimal(loan_details['monthly_payment'])
        print(f"✓ Monthly payment calculated: ${monthly_payment}")
        print(f"✓ Lender balance: ${initial_lender_balance}")
        print(f"✓ Borrower balance: ${initial_borrower_balance}")

        # Step 6: Lender funds the loan
        print("\nStep 6: Lender funds the loan")
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.lender_token.key}')

        response = self.client.post(f'/api/loans/{loan_id}/fund/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'FUNDED')
        print("✓ Loan funded successfully")

        # Step 7: Verify balance changes after funding
        print("\nStep 7: Verify post-funding balances")
        self.lender_wallet.refresh_from_db()
        self.borrower_wallet.refresh_from_db()

        platform_fee = Decimal('3.75')
        expected_lender_balance = initial_lender_balance - self.loan_amount - platform_fee
        expected_borrower_balance = initial_borrower_balance + self.loan_amount

        self.assertEqual(self.lender_wallet.balance, expected_lender_balance)
        self.assertEqual(self.borrower_wallet.balance, expected_borrower_balance)

        print(f"✓ Lender balance after funding: ${self.lender_wallet.balance}")
        print(f"✓ Borrower balance after funding: ${self.borrower_wallet.balance}")
        print(f"✓ Platform fee deducted: ${platform_fee}")

        # Step 8: Check payment schedule was generated
        print("\nStep 8: Verify payment schedule")
        response = self.client.get(f'/api/loans/{loan_id}/schedule/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        payments = response.data
        self.assertEqual(len(payments), self.term_months)

        # Verify all payments are pending and amounts are correct
        for i, payment in enumerate(payments, 1):
            self.assertEqual(payment['payment_number'], i)
            self.assertEqual(payment['status'], 'PENDING')
            self.assertEqual(Decimal(payment['amount']), monthly_payment)

        print(f"✓ Payment schedule generated: {len(payments)} payments of ${monthly_payment} each")

        # Step 9: Borrower makes all payments
        print("\nStep 9: Borrower makes all payments")
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.borrower_token.key}')

        for payment_num in range(1, self.term_months + 1):
            # Check borrower balance before payment
            self.borrower_wallet.refresh_from_db()
            balance_before = self.borrower_wallet.balance

            response = self.client.post(f'/api/loans/{loan_id}/pay/')
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            # Check if this is the final payment
            is_final_payment = payment_num == self.term_months
            if is_final_payment:
                self.assertIn('Loan completed!', response.data['message'])
                print(f"✓ Payment {payment_num}/{self.term_months} completed - LOAN FULLY PAID!")
            else:
                print(f"✓ Payment {payment_num}/{self.term_months} completed")

            # Verify balance was deducted
            self.borrower_wallet.refresh_from_db()
            expected_balance = balance_before - monthly_payment
            self.assertEqual(self.borrower_wallet.balance, expected_balance)

        # Step 10: Verify loan completion
        print("\nStep 10: Verify loan completion")
        response = self.client.get(f'/api/loans/{loan_id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'COMPLETED')
        print("✓ Loan status: COMPLETED")

        # Step 11: Verify all payments are marked as paid
        print("\nStep 11: Verify all payments are paid")
        response = self.client.get(f'/api/loans/{loan_id}/schedule/')
        payments = response.data

        for payment in payments:
            self.assertEqual(payment['status'], 'PAID')
            self.assertIsNotNone(payment['paid_at'])

        print("✓ All payments marked as PAID")

        # Step 12: Verify final balances
        print("\nStep 12: Final balance verification")
        self.lender_wallet.refresh_from_db()
        self.borrower_wallet.refresh_from_db()

        total_payments = monthly_payment * self.term_months
        final_lender_balance = expected_lender_balance + total_payments
        final_borrower_balance = expected_borrower_balance - total_payments

        self.assertEqual(self.lender_wallet.balance, final_lender_balance)
        self.assertEqual(self.borrower_wallet.balance, final_borrower_balance)

        print(f"✓ Final lender balance: ${self.lender_wallet.balance}")
        print(f"✓ Final borrower balance: ${self.borrower_wallet.balance}")
        print(f"✓ Total interest earned by lender: ${total_payments - self.loan_amount}")

        # Step 13: Verify transaction history
        print("\nStep 13: Verify transaction history")
        lender_transactions = Transaction.objects.filter(wallet=self.lender_wallet).count()
        borrower_transactions = Transaction.objects.filter(wallet=self.borrower_wallet).count()

        # Lender should have: 1 loan funding + 1 platform fee + 6 loan payments = 8 transactions
        self.assertEqual(lender_transactions, 8)
        # Borrower should have: 1 loan receipt + 6 loan payments = 7 transactions
        self.assertEqual(borrower_transactions, 7)

        print(f"✓ Lender transaction count: {lender_transactions}")
        print(f"✓ Borrower transaction count: {borrower_transactions}")

        print("\n🎉 COMPLETE P2P LENDING LIFECYCLE TEST PASSED! 🎉")
        print("=" * 60)
        print("Summary:")
        print(f"• Loan Amount: ${self.loan_amount}")
        print(f"• Interest Rate: {self.offer_rate}%")
        print(f"• Term: {self.term_months} months")
        print(f"• Monthly Payment: ${monthly_payment}")
        print(f"• Total Repaid: ${total_payments}")
        print(f"• Platform Fee: ${platform_fee}")
        print(f"• Lender Profit: ${total_payments - self.loan_amount}")
        print("=" * 60)

    def test_insufficient_funds_scenario(self):
        """Test scenario where lender has insufficient funds"""
        print("\nTesting insufficient funds scenario...")

        # Create lender with insufficient funds
        poor_lender = User.objects.create_user(
            username='poor_lender',
            email='poor@example.com',
            password='testpass123',
            role='LENDER'
        )
        Wallet.objects.create(user=poor_lender, balance=Decimal('100.00'))  # Not enough
        poor_lender_token = Token.objects.create(user=poor_lender)

        # Borrower creates loan
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.borrower_token.key}')
        loan_data = {
            'amount': '1000.00',
            'term_months': 6,
            'annual_interest_rate': '12.00',
            'purpose': 'Test loan'
        }
        response = self.client.post('/api/loans/', loan_data)
        loan_id = response.data['id']

        # Poor lender makes offer
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {poor_lender_token.key}')
        offer_data = {'annual_interest_rate': '10.00'}
        response = self.client.post(f'/api/loans/{loan_id}/offer/', offer_data)
        offer_id = response.data['id']

        # Borrower accepts offer
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.borrower_token.key}')
        accept_data = {'offer_id': offer_id}
        response = self.client.post(f'/api/loans/{loan_id}/accept-offer/', accept_data)
        self.assertEqual(response.data['status'], 'PENDING_FUNDING')

        # Poor lender tries to fund loan (should fail)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {poor_lender_token.key}')
        response = self.client.post(f'/api/loans/{loan_id}/fund/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Insufficient funds', response.data['error'])
        print("✓ Insufficient funds scenario handled correctly")

    def test_borrower_insufficient_funds_for_payment(self):
        """Test scenario where borrower can't make payment"""
        print("\nTesting borrower insufficient funds for payment...")

        # Create borrower with minimal funds
        broke_borrower = User.objects.create_user(
            username='broke_borrower',
            email='broke@example.com',
            password='testpass123',
            role='BORROWER'
        )
        broke_borrower_wallet = Wallet.objects.create(user=broke_borrower, balance=Decimal('50.00'))  # Not enough for payments
        broke_borrower_token = Token.objects.create(user=broke_borrower)

        # Complete loan setup (borrower creates, lender offers/accepts/funds)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {broke_borrower_token.key}')
        loan_data = {
            'amount': '500.00',
            'term_months': 6,
            'annual_interest_rate': '12.00',
            'purpose': 'Test loan'
        }
        response = self.client.post('/api/loans/', loan_data)
        loan_id = response.data['id']

        # Lender offers and funds
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.lender_token.key}')
        offer_data = {'annual_interest_rate': '10.00'}
        response = self.client.post(f'/api/loans/{loan_id}/offer/', offer_data)
        offer_id = response.data['id']

        self.client.credentials(HTTP_AUTHORIZATION=f'Token {broke_borrower_token.key}')
        accept_data = {'offer_id': offer_id}
        response = self.client.post(f'/api/loans/{loan_id}/accept-offer/', accept_data)

        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.lender_token.key}')
        response = self.client.post(f'/api/loans/{loan_id}/fund/')
        self.assertEqual(response.data['status'], 'FUNDED')

        # Manually reduce borrower's balance to simulate spending the loan money
        # After funding, borrower has $50 + $500 = $550
        # Reduce to $30 so they can't afford the ~$86 monthly payment
        broke_borrower_wallet.refresh_from_db()
        broke_borrower_wallet.balance = Decimal('30.00')
        broke_borrower_wallet.save()

        # Borrower tries to make payment (should fail due to insufficient funds)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {broke_borrower_token.key}')
        response = self.client.post(f'/api/loans/{loan_id}/pay/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Insufficient funds', response.data['error'])
        print("✓ Borrower insufficient funds for payment handled correctly")
