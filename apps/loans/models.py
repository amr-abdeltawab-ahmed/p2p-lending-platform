from django.db import models
from django.contrib.auth import get_user_model
from decimal import Decimal
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

User = get_user_model()


class Loan(models.Model):
    STATUS_CHOICES = [
        ('REQUESTED', 'Requested'),
        ('PENDING_FUNDING', 'Pending Funding'),
        ('FUNDED', 'Funded'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]

    borrower = models.ForeignKey(User, on_delete=models.CASCADE, related_name='borrowed_loans')
    lender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lent_loans', null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    term_months = models.IntegerField()
    annual_interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='REQUESTED')
    purpose = models.TextField(blank=True, null=True)
    funded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Loan #{self.id} - ${self.amount} for {self.borrower.username}"

    @property
    def monthly_payment(self):
        if self.term_months == 0:
            return Decimal('0.00')

        monthly_rate = self.annual_interest_rate / Decimal('100') / Decimal('12')
        if monthly_rate == 0:
            return self.amount / self.term_months

        payment = (self.amount * monthly_rate * (1 + monthly_rate) ** self.term_months) / \
                  ((1 + monthly_rate) ** self.term_months - 1)
        return payment.quantize(Decimal('0.01'))

    @property
    def total_amount(self):
        return self.monthly_payment * self.term_months


class Offer(models.Model):
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='offers')
    lender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='loan_offers')
    annual_interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    accepted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['annual_interest_rate']  # Lowest rates first
        unique_together = ['loan', 'lender']  # One offer per lender per loan

    def __str__(self):
        return f"Offer by {self.lender.username} - {self.annual_interest_rate}% for Loan #{self.loan.id}"


class Payment(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
        ('OVERDUE', 'Overdue'),
    ]

    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='payments')
    payment_number = models.IntegerField()  # 1, 2, 3, etc.
    due_date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['payment_number']
        unique_together = ['loan', 'payment_number']

    def __str__(self):
        return f"Payment {self.payment_number} for Loan #{self.loan.id} - ${self.amount}"

    @property
    def is_overdue(self):
        return self.status == 'PENDING' and self.due_date < date.today()

    def mark_as_paid(self):
        from django.utils import timezone
        self.status = 'PAID'
        self.paid_at = timezone.now()
        self.save()

    @classmethod
    def generate_payment_schedule(cls, loan):
        """Generate payment schedule for a funded loan"""
        payments = []
        monthly_payment = loan.monthly_payment

        # Use the loan's funding date as the base date for payment schedule
        funding_date = loan.funded_at.date() if loan.funded_at else date.today()

        for month in range(1, loan.term_months + 1):
            due_date = funding_date + relativedelta(months=month)
            payment = cls(
                loan=loan,
                payment_number=month,
                due_date=due_date,
                amount=monthly_payment,
                status='PENDING'
            )
            payments.append(payment)

        return cls.objects.bulk_create(payments)