from typing import Optional, Dict, Any
from decimal import Decimal
from django.db import transaction
from django.contrib.auth import get_user_model
from .repositories import WalletRepository, TransactionRepository
from .models import Wallet

User = get_user_model()


class WalletService:
    def __init__(self):
        self.wallet_repo = WalletRepository()
        self.transaction_repo = TransactionRepository()

    def get_or_create_wallet(self, user: User) -> Wallet:
        return self.wallet_repo.get_or_create_wallet(user)

    def get_wallet_balance(self, user: User) -> Decimal:
        wallet = self.wallet_repo.get_wallet_by_user(user)
        return wallet.balance if wallet else Decimal('0.00')

    def deposit_funds(self, user: User, amount: Decimal, description: str = None) -> Dict[str, Any]:
        with transaction.atomic():
            wallet = self.wallet_repo.get_or_create_wallet(user)

            # Update wallet balance
            self.wallet_repo.update_balance(wallet, amount, 'add')

            # Create transaction record
            transaction_record = self.transaction_repo.create_transaction(
                wallet=wallet,
                transaction_type='DEPOSIT',
                amount=amount,
                description=description or f"Deposit of ${amount}"
            )

            return {
                'success': True,
                'new_balance': wallet.balance,
                'transaction': transaction_record
            }

    def withdraw_funds(self, user: User, amount: Decimal, description: str = None) -> Dict[str, Any]:
        with transaction.atomic():
            wallet = self.wallet_repo.get_wallet_by_user(user)
            if not wallet:
                return {'success': False, 'error': 'Wallet not found'}

            if not self.wallet_repo.has_sufficient_balance(wallet, amount):
                return {'success': False, 'error': 'Insufficient funds'}

            # Update wallet balance
            self.wallet_repo.update_balance(wallet, amount, 'subtract')

            # Create transaction record
            transaction_record = self.transaction_repo.create_transaction(
                wallet=wallet,
                transaction_type='WITHDRAWAL',
                amount=amount,
                description=description or f"Withdrawal of ${amount}"
            )

            return {
                'success': True,
                'new_balance': wallet.balance,
                'transaction': transaction_record
            }

    def transfer_funds(self, from_user: User, to_user: User, amount: Decimal,
                      transaction_type: str = 'LOAN_FUNDING', reference_id: str = None) -> Dict[str, Any]:
        with transaction.atomic():
            from_wallet = self.wallet_repo.get_wallet_by_user(from_user)
            to_wallet = self.wallet_repo.get_or_create_wallet(to_user)

            if not from_wallet:
                return {'success': False, 'error': 'Sender wallet not found'}

            if not self.wallet_repo.has_sufficient_balance(from_wallet, amount):
                return {'success': False, 'error': 'Insufficient funds'}

            # Deduct from sender
            self.wallet_repo.update_balance(from_wallet, amount, 'subtract')

            # Add to receiver
            self.wallet_repo.update_balance(to_wallet, amount, 'add')

            # Create transaction records
            from_transaction = self.transaction_repo.create_transaction(
                wallet=from_wallet,
                transaction_type=transaction_type,
                amount=-amount,  # Negative for outgoing
                description=f"Transfer to {to_user.username}",
                reference_id=reference_id
            )

            to_transaction = self.transaction_repo.create_transaction(
                wallet=to_wallet,
                transaction_type=transaction_type,
                amount=amount,  # Positive for incoming
                description=f"Transfer from {from_user.username}",
                reference_id=reference_id
            )

            return {
                'success': True,
                'from_balance': from_wallet.balance,
                'to_balance': to_wallet.balance,
                'from_transaction': from_transaction,
                'to_transaction': to_transaction
            }

    def deduct_platform_fee(self, user: User, amount: Decimal, reference_id: str = None) -> Dict[str, Any]:
        with transaction.atomic():
            wallet = self.wallet_repo.get_wallet_by_user(user)
            if not wallet:
                return {'success': False, 'error': 'Wallet not found'}

            if not self.wallet_repo.has_sufficient_balance(wallet, amount):
                return {'success': False, 'error': 'Insufficient funds for platform fee'}

            # Deduct fee
            self.wallet_repo.update_balance(wallet, amount, 'subtract')

            # Create transaction record
            transaction_record = self.transaction_repo.create_transaction(
                wallet=wallet,
                transaction_type='PLATFORM_FEE',
                amount=-amount,  # Negative for fee deduction
                description=f"Platform fee of ${amount}",
                reference_id=reference_id
            )

            return {
                'success': True,
                'new_balance': wallet.balance,
                'transaction': transaction_record
            }

    def get_transaction_history(self, user: User, limit: int = None) -> list:
        wallet = self.wallet_repo.get_wallet_by_user(user)
        if not wallet:
            return []
        return self.transaction_repo.get_transactions_by_wallet(wallet, limit)

    def check_balance(self, user: User, required_amount: Decimal) -> bool:
        wallet = self.wallet_repo.get_wallet_by_user(user)
        return wallet and self.wallet_repo.has_sufficient_balance(wallet, required_amount)