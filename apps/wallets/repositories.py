from typing import Optional, List
from decimal import Decimal
from django.contrib.auth import get_user_model
from .models import Wallet, Transaction

User = get_user_model()


class WalletRepository:
    @staticmethod
    def get_or_create_wallet(user: User) -> Wallet:
        wallet, created = Wallet.objects.get_or_create(user=user)
        return wallet

    @staticmethod
    def get_wallet_by_user(user: User) -> Optional[Wallet]:
        try:
            return Wallet.objects.get(user=user)
        except Wallet.DoesNotExist:
            return None

    @staticmethod
    def update_balance(wallet: Wallet, amount: Decimal, operation: str = 'add') -> Wallet:
        if operation == 'add':
            wallet.balance += amount
        elif operation == 'subtract':
            wallet.balance -= amount
        wallet.save()
        return wallet

    @staticmethod
    def has_sufficient_balance(wallet: Wallet, amount: Decimal) -> bool:
        return wallet.balance >= amount


class TransactionRepository:
    @staticmethod
    def create_transaction(
        wallet: Wallet,
        transaction_type: str,
        amount: Decimal,
        description: str = None,
        reference_id: str = None
    ) -> Transaction:
        transaction = Transaction.objects.create(
            wallet=wallet,
            transaction_type=transaction_type,
            amount=amount,
            description=description,
            reference_id=reference_id
        )
        return transaction

    @staticmethod
    def get_transactions_by_wallet(wallet: Wallet, limit: int = None) -> List[Transaction]:
        queryset = Transaction.objects.filter(wallet=wallet).order_by('-created_at')
        if limit:
            queryset = queryset[:limit]
        return list(queryset)

    @staticmethod
    def get_transaction_by_id(transaction_id: int) -> Optional[Transaction]:
        try:
            return Transaction.objects.get(id=transaction_id)
        except Transaction.DoesNotExist:
            return None

    @staticmethod
    def get_transactions_by_type(wallet: Wallet, transaction_type: str) -> List[Transaction]:
        return Transaction.objects.filter(
            wallet=wallet,
            transaction_type=transaction_type
        ).order_by('-created_at')