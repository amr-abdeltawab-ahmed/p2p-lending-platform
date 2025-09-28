from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework.authtoken.models import Token
from .models import Wallet, Transaction
from .services import WalletService

User = get_user_model()


class WalletModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='LENDER'
        )

    def test_wallet_creation(self):
        wallet = Wallet.objects.create(user=self.user, balance=Decimal('100.00'))
        self.assertEqual(wallet.user, self.user)
        self.assertEqual(wallet.balance, Decimal('100.00'))

    def test_has_sufficient_balance(self):
        wallet = Wallet.objects.create(user=self.user, balance=Decimal('100.00'))
        self.assertTrue(wallet.has_sufficient_balance(Decimal('50.00')))
        self.assertFalse(wallet.has_sufficient_balance(Decimal('150.00')))

    def test_deduct_balance(self):
        wallet = Wallet.objects.create(user=self.user, balance=Decimal('100.00'))
        success = wallet.deduct_balance(Decimal('30.00'))
        self.assertTrue(success)
        self.assertEqual(wallet.balance, Decimal('70.00'))

    def test_credit_balance(self):
        wallet = Wallet.objects.create(user=self.user, balance=Decimal('100.00'))
        wallet.credit_balance(Decimal('50.00'))
        self.assertEqual(wallet.balance, Decimal('150.00'))


class WalletServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='LENDER'
        )
        self.wallet_service = WalletService()

    def test_deposit_funds(self):
        result = self.wallet_service.deposit_funds(self.user, Decimal('100.00'))
        self.assertTrue(result['success'])
        self.assertEqual(result['new_balance'], Decimal('100.00'))

    def test_withdraw_funds_success(self):
        # First deposit
        self.wallet_service.deposit_funds(self.user, Decimal('100.00'))

        # Then withdraw
        result = self.wallet_service.withdraw_funds(self.user, Decimal('50.00'))
        self.assertTrue(result['success'])
        self.assertEqual(result['new_balance'], Decimal('50.00'))

    def test_withdraw_funds_insufficient(self):
        result = self.wallet_service.withdraw_funds(self.user, Decimal('50.00'))
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'Wallet not found')


class WalletAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='LENDER'
        )
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

    def test_get_wallet(self):
        response = self.client.get('/api/wallets/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('balance', response.data)

    def test_deposit(self):
        data = {'amount': '100.00', 'description': 'Test deposit'}
        response = self.client.post('/api/wallets/deposit/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('wallet', response.data)

    def test_withdraw_insufficient_funds(self):
        data = {'amount': '100.00', 'description': 'Test withdrawal'}
        response = self.client.post('/api/wallets/withdraw/', data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_balance(self):
        response = self.client.get('/api/wallets/balance/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('balance', response.data)