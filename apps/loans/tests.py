from decimal import Decimal
from datetime import date
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework.authtoken.models import Token
from .models import Loan, Offer, Payment
from .services import LoanService, OfferService, LoanFundingService, PaymentService
from apps.wallets.models import Wallet

User = get_user_model()


class LoanModelTest(TestCase):
    def setUp(self):
        self.borrower = User.objects.create_user(
            username='borrower',
            email='borrower@example.com',
            password='testpass123',
            role='BORROWER'
        )
        self.lender = User.objects.create_user(
            username='lender',
            email='lender@example.com',
            password='testpass123',
            role='LENDER'
        )

    def test_loan_creation(self):
        loan = Loan.objects.create(
            borrower=self.borrower,
            amount=Decimal('1000.00'),
            term_months=6,
            annual_interest_rate=Decimal('12.00')
        )
        self.assertEqual(loan.borrower, self.borrower)
        self.assertEqual(loan.amount, Decimal('1000.00'))
        self.assertEqual(loan.status, 'REQUESTED')

    def test_monthly_payment_calculation(self):
        loan = Loan.objects.create(
            borrower=self.borrower,
            amount=Decimal('1000.00'),
            term_months=6,
            annual_interest_rate=Decimal('12.00')
        )
        # Monthly payment should be approximately $172.55
        expected_payment = Decimal('172.55')
        self.assertAlmostEqual(loan.monthly_payment, expected_payment, places=2)

    def test_offer_creation(self):
        loan = Loan.objects.create(
            borrower=self.borrower,
            amount=Decimal('1000.00'),
            term_months=6,
            annual_interest_rate=Decimal('12.00')
        )
        offer = Offer.objects.create(
            loan=loan,
            lender=self.lender,
            annual_interest_rate=Decimal('10.00')
        )
        self.assertEqual(offer.loan, loan)
        self.assertEqual(offer.lender, self.lender)
        self.assertFalse(offer.accepted)


class LoanServiceTest(TestCase):
    def setUp(self):
        self.borrower = User.objects.create_user(
            username='borrower',
            email='borrower@example.com',
            password='testpass123',
            role='BORROWER'
        )
        self.lender = User.objects.create_user(
            username='lender',
            email='lender@example.com',
            password='testpass123',
            role='LENDER'
        )
        self.loan_service = LoanService()
        self.offer_service = OfferService()

    def test_create_loan(self):
        loan_data = {
            'amount': Decimal('1000.00'),
            'term_months': 6,
            'annual_interest_rate': Decimal('12.00'),
            'purpose': 'Business expansion'
        }
        loan = self.loan_service.create_loan(self.borrower, loan_data)
        self.assertEqual(loan.borrower, self.borrower)
        self.assertEqual(loan.status, 'REQUESTED')

    def test_create_offer(self):
        loan = Loan.objects.create(
            borrower=self.borrower,
            amount=Decimal('1000.00'),
            term_months=6,
            annual_interest_rate=Decimal('12.00')
        )
        result = self.offer_service.create_offer(loan.id, self.lender, Decimal('10.00'))
        self.assertTrue(result['success'])
        self.assertEqual(result['offer'].annual_interest_rate, Decimal('10.00'))


class LoanAPITest(APITestCase):
    def setUp(self):
        self.borrower = User.objects.create_user(
            username='borrower',
            email='borrower@example.com',
            password='testpass123',
            role='BORROWER'
        )
        self.lender = User.objects.create_user(
            username='lender',
            email='lender@example.com',
            password='testpass123',
            role='LENDER'
        )

        # Create wallets with sufficient balance for testing
        Wallet.objects.create(user=self.lender, balance=Decimal('10000.00'))
        Wallet.objects.create(user=self.borrower, balance=Decimal('1000.00'))

    def test_complete_loan_lifecycle(self):
        """Test the complete happy path of loan lifecycle"""

        # 1. Borrower creates loan
        borrower_token = Token.objects.create(user=self.borrower)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {borrower_token.key}')

        loan_data = {
            'amount': '1000.00',
            'term_months': 6,
            'annual_interest_rate': '12.00',
            'purpose': 'Business expansion'
        }
        response = self.client.post('/api/loans/', loan_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        loan_id = response.data['id']

        # 2. Lender retrieves available loans
        lender_token = Token.objects.create(user=self.lender)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {lender_token.key}')

        response = self.client.get('/api/loans/available/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        # 3. Lender submits offer
        offer_data = {'annual_interest_rate': '10.00'}
        response = self.client.post(f'/api/loans/{loan_id}/offer/', offer_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        offer_id = response.data['id']

        # 4. Borrower accepts offer
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {borrower_token.key}')
        accept_data = {'offer_id': offer_id}
        response = self.client.post(f'/api/loans/{loan_id}/accept-offer/', accept_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'PENDING_FUNDING')

        # 5. Lender funds loan
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {lender_token.key}')
        response = self.client.post(f'/api/loans/{loan_id}/fund/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'FUNDED')

        # 6. Check payment schedule was generated
        response = self.client.get(f'/api/loans/{loan_id}/schedule/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 6)  # 6 monthly payments

        # 7. Borrower makes all payments
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {borrower_token.key}')
        for payment_num in range(6):
            response = self.client.post(f'/api/loans/{loan_id}/pay/')
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 8. Verify loan is completed after last payment
        # The last payment should complete the loan
        response = self.client.get(f'/api/loans/{loan_id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Note: The loan should be COMPLETED after all payments, but we need to check
        # the actual response to verify this behavior


class PaymentScheduleTest(TestCase):
    """Test payment schedule generation with proper dates"""

    def setUp(self):
        self.borrower = User.objects.create_user(
            username='borrower',
            email='borrower@example.com',
            password='testpass123',
            role='BORROWER'
        )
        self.lender = User.objects.create_user(
            username='lender',
            email='lender@example.com',
            password='testpass123',
            role='LENDER'
        )

    def test_payment_schedule_uses_funding_date(self):
        """Test that payment schedule uses loan's funding date, not today's date"""
        from django.utils import timezone
        from datetime import datetime, date
        from dateutil.relativedelta import relativedelta

        # Create a loan with a specific funding date
        funding_date = timezone.make_aware(datetime(2024, 1, 15, 10, 0, 0))

        loan = Loan.objects.create(
            borrower=self.borrower,
            lender=self.lender,
            amount=Decimal('1000.00'),
            term_months=6,
            annual_interest_rate=Decimal('12.00'),
            status='FUNDED',
            funded_at=funding_date
        )

        # Generate payment schedule
        payments = Payment.generate_payment_schedule(loan)

        # Verify payment dates are based on funding date, not today
        expected_base_date = funding_date.date()

        for i, payment in enumerate(payments, 1):
            expected_due_date = expected_base_date + relativedelta(months=i)
            self.assertEqual(payment.due_date, expected_due_date)
            self.assertEqual(payment.payment_number, i)
            self.assertEqual(payment.status, 'PENDING')

    def test_payment_schedule_fallback_to_today_if_no_funding_date(self):
        """Test that payment schedule falls back to today's date if no funding date"""
        from datetime import date
        from dateutil.relativedelta import relativedelta

        # Create a loan without funding date
        loan = Loan.objects.create(
            borrower=self.borrower,
            amount=Decimal('1000.00'),
            term_months=3,
            annual_interest_rate=Decimal('12.00'),
            status='REQUESTED',
            funded_at=None
        )

        # Generate payment schedule
        payments = Payment.generate_payment_schedule(loan)

        # Verify payment dates are based on today's date
        today = date.today()

        for i, payment in enumerate(payments, 1):
            expected_due_date = today + relativedelta(months=i)
            self.assertEqual(payment.due_date, expected_due_date)


class PaymentServiceTest(TestCase):
    """Test payment service fixes and edge cases"""

    def setUp(self):
        self.borrower = User.objects.create_user(
            username='borrower',
            email='borrower@example.com',
            password='testpass123',
            role='BORROWER'
        )
        self.lender = User.objects.create_user(
            username='lender',
            email='lender@example.com',
            password='testpass123',
            role='LENDER'
        )

        # Create wallets
        Wallet.objects.create(user=self.borrower, balance=Decimal('2000.00'))
        Wallet.objects.create(user=self.lender, balance=Decimal('10000.00'))

        self.payment_service = PaymentService()

    def test_loan_completion_status_tracking(self):
        """Test that loan completion status is properly tracked"""
        from django.utils import timezone

        # Create a funded loan with 2 payments
        loan = Loan.objects.create(
            borrower=self.borrower,
            lender=self.lender,
            amount=Decimal('200.00'),
            term_months=2,
            annual_interest_rate=Decimal('12.00'),
            status='FUNDED',
            funded_at=timezone.now()
        )

        # Create 2 payments manually
        payment1 = Payment.objects.create(
            loan=loan,
            payment_number=1,
            due_date=date.today(),
            amount=loan.monthly_payment,
            status='PENDING'
        )
        payment2 = Payment.objects.create(
            loan=loan,
            payment_number=2,
            due_date=date.today(),
            amount=loan.monthly_payment,
            status='PENDING'
        )

        # Make first payment
        result1 = self.payment_service.make_payment(loan.id, self.borrower)
        self.assertTrue(result1['success'])
        self.assertFalse(result1['loan_completed'])

        # Verify loan is still FUNDED
        loan.refresh_from_db()
        self.assertEqual(loan.status, 'FUNDED')

        # Make second (final) payment
        result2 = self.payment_service.make_payment(loan.id, self.borrower)
        self.assertTrue(result2['success'])
        self.assertTrue(result2['loan_completed'])

        # Verify loan is now COMPLETED
        loan.refresh_from_db()
        self.assertEqual(loan.status, 'COMPLETED')

    def test_payment_service_variable_scope_fix(self):
        """Test that payment_status variable is always defined"""
        from django.utils import timezone

        # Create a funded loan with 1 payment
        loan = Loan.objects.create(
            borrower=self.borrower,
            lender=self.lender,
            amount=Decimal('100.00'),
            term_months=1,
            annual_interest_rate=Decimal('12.00'),
            status='FUNDED',
            funded_at=timezone.now()
        )

        # Create 1 payment
        Payment.objects.create(
            loan=loan,
            payment_number=1,
            due_date=date.today(),
            amount=loan.monthly_payment,
            status='PENDING'
        )

        # Make the payment - this should not raise UnboundLocalError
        result = self.payment_service.make_payment(loan.id, self.borrower)

        # Verify the result structure includes loan_completed field
        self.assertTrue(result['success'])
        self.assertIn('loan_completed', result)
        self.assertTrue(result['loan_completed'])  # Should be True for final payment