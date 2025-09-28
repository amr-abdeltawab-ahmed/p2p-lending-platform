from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.openapi import OpenApiTypes
from .models import Loan, Offer, Payment


class PaymentSerializer(serializers.ModelSerializer):
    is_overdue = serializers.SerializerMethodField()

    @extend_schema_field(OpenApiTypes.BOOL)
    def get_is_overdue(self, obj):
        return obj.is_overdue

    class Meta:
        model = Payment
        fields = ['id', 'payment_number', 'due_date', 'amount', 'status', 'paid_at', 'is_overdue', 'created_at']
        read_only_fields = ['id', 'created_at', 'paid_at']


class OfferSerializer(serializers.ModelSerializer):
    lender_username = serializers.CharField(source='lender.username', read_only=True)

    class Meta:
        model = Offer
        fields = ['id', 'lender_username', 'annual_interest_rate', 'accepted', 'created_at']
        read_only_fields = ['id', 'lender_username', 'accepted', 'created_at']


class LoanSerializer(serializers.ModelSerializer):
    borrower_username = serializers.CharField(source='borrower.username', read_only=True)
    lender_username = serializers.CharField(source='lender.username', read_only=True)
    offers = OfferSerializer(many=True, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)
    monthly_payment = serializers.SerializerMethodField()
    total_amount = serializers.SerializerMethodField()

    @extend_schema_field(OpenApiTypes.DECIMAL)
    def get_monthly_payment(self, obj):
        return obj.monthly_payment

    @extend_schema_field(OpenApiTypes.DECIMAL)
    def get_total_amount(self, obj):
        return obj.total_amount

    class Meta:
        model = Loan
        fields = [
            'id', 'borrower_username', 'lender_username', 'amount', 'term_months',
            'annual_interest_rate', 'status', 'purpose', 'monthly_payment',
            'total_amount', 'offers', 'payments', 'funded_at', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'borrower_username', 'lender_username', 'status',
            'funded_at', 'created_at', 'updated_at'
        ]

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Loan amount must be greater than 0")
        if value > 1000000:  # 1 million max
            raise serializers.ValidationError("Loan amount cannot exceed $1,000,000")
        return value

    def validate_term_months(self, value):
        if value < 1:
            raise serializers.ValidationError("Term must be at least 1 month")
        if value > 360:  # 30 years max
            raise serializers.ValidationError("Term cannot exceed 360 months")
        return value

    def validate_annual_interest_rate(self, value):
        if value < 0:
            raise serializers.ValidationError("Interest rate cannot be negative")
        if value > 50:  # 50% max
            raise serializers.ValidationError("Interest rate cannot exceed 50%")
        return value


class CreateLoanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Loan
        fields = ['amount', 'term_months', 'annual_interest_rate', 'purpose']

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Loan amount must be greater than 0")
        if value > 1000000:  # 1 million max
            raise serializers.ValidationError("Loan amount cannot exceed $1,000,000")
        return value

    def validate_term_months(self, value):
        if value < 1:
            raise serializers.ValidationError("Term must be at least 1 month")
        if value > 360:  # 30 years max
            raise serializers.ValidationError("Term cannot exceed 360 months")
        return value

    def validate_annual_interest_rate(self, value):
        if value < 0:
            raise serializers.ValidationError("Interest rate cannot be negative")
        if value > 50:  # 50% max
            raise serializers.ValidationError("Interest rate cannot exceed 50%")
        return value


class CreateOfferSerializer(serializers.ModelSerializer):
    class Meta:
        model = Offer
        fields = ['annual_interest_rate']

    def validate_annual_interest_rate(self, value):
        if value < 0:
            raise serializers.ValidationError("Interest rate cannot be negative")
        if value > 50:  # 50% max
            raise serializers.ValidationError("Interest rate cannot exceed 50%")
        return value


class AcceptOfferSerializer(serializers.Serializer):
    offer_id = serializers.IntegerField()

    def validate_offer_id(self, value):
        try:
            offer = Offer.objects.get(id=value)
            if offer.accepted:
                raise serializers.ValidationError("This offer has already been accepted")
        except Offer.DoesNotExist:
            raise serializers.ValidationError("Offer not found")
        return value