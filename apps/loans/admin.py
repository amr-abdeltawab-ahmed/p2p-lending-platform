from django.contrib import admin
from .models import Loan, Offer, Payment


class OfferInline(admin.TabularInline):
    model = Offer
    extra = 0
    readonly_fields = ('created_at',)


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = ('created_at', 'paid_at')


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ('id', 'borrower', 'lender', 'amount', 'status', 'annual_interest_rate', 'created_at')
    list_filter = ('status', 'created_at', 'term_months')
    search_fields = ('borrower__username', 'lender__username', 'purpose')
    readonly_fields = ('created_at', 'updated_at', 'funded_at', 'monthly_payment', 'total_amount')
    inlines = [OfferInline, PaymentInline]
    ordering = ('-created_at',)

    fieldsets = (
        ('Loan Details', {
            'fields': ('borrower', 'lender', 'amount', 'term_months', 'annual_interest_rate', 'status')
        }),
        ('Additional Info', {
            'fields': ('purpose', 'monthly_payment', 'total_amount')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'funded_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = ('id', 'loan', 'lender', 'annual_interest_rate', 'accepted', 'created_at')
    list_filter = ('accepted', 'created_at', 'annual_interest_rate')
    search_fields = ('loan__id', 'lender__username')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'loan', 'payment_number', 'amount', 'due_date', 'status', 'paid_at')
    list_filter = ('status', 'due_date', 'created_at')
    search_fields = ('loan__id', 'loan__borrower__username')
    readonly_fields = ('created_at', 'paid_at', 'is_overdue')
    ordering = ('loan', 'payment_number')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('loan', 'loan__borrower')