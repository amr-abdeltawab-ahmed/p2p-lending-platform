from django.db import models
from django.contrib.auth import get_user_model
from decimal import Decimal

User = get_user_model()


class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Wallet of {self.user.username} - Balance: ${self.balance}"

    def has_sufficient_balance(self, amount: Decimal) -> bool:
        return self.balance >= amount

    def deduct_balance(self, amount: Decimal) -> bool:
        if self.has_sufficient_balance(amount):
            self.balance -= amount
            self.save()
            return True
        return False

    def credit_balance(self, amount: Decimal):
        self.balance += amount
        self.save()


class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('DEPOSIT', 'Deposit'),
        ('WITHDRAWAL', 'Withdrawal'),
        ('LOAN_FUNDING', 'Loan Funding'),
        ('LOAN_PAYMENT', 'Loan Payment'),
        ('PLATFORM_FEE', 'Platform Fee'),
    ]

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    reference_id = models.CharField(max_length=100, blank=True, null=True)  # For linking to loans/payments
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.transaction_type} - ${self.amount} - {self.wallet.user.username}"