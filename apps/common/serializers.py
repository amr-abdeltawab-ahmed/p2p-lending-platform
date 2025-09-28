"""
Common serializers for API responses and error handling
"""
from rest_framework import serializers


class ErrorResponseSerializer(serializers.Serializer):
    """Standard error response serializer"""
    error = serializers.CharField(help_text="Error message describing what went wrong")


class ValidationErrorResponseSerializer(serializers.Serializer):
    """Validation error response serializer"""
    error = serializers.CharField(required=False, help_text="General error message")
    field_errors = serializers.DictField(
        required=False,
        help_text="Field-specific validation errors",
        child=serializers.ListField(child=serializers.CharField())
    )


class SuccessMessageSerializer(serializers.Serializer):
    """Success message response serializer"""
    message = serializers.CharField(help_text="Success message")


class TokenResponseSerializer(serializers.Serializer):
    """Authentication token response serializer"""
    token = serializers.CharField(help_text="Authentication token")
    user = serializers.DictField(help_text="User information")


class BalanceResponseSerializer(serializers.Serializer):
    """Wallet balance response serializer"""
    balance = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Current wallet balance"
    )


class DepositResponseSerializer(serializers.Serializer):
    """Deposit success response serializer"""
    message = serializers.CharField(help_text="Success message")
    wallet = serializers.DictField(help_text="Updated wallet information")


class WithdrawalResponseSerializer(serializers.Serializer):
    """Withdrawal success response serializer"""
    message = serializers.CharField(help_text="Success message")
    wallet = serializers.DictField(help_text="Updated wallet information")


class PaymentResponseSerializer(serializers.Serializer):
    """Payment success response serializer"""
    message = serializers.CharField(help_text="Success message")
    payment = serializers.DictField(help_text="Payment information")


# Empty serializer for endpoints without specific input
class EmptySerializer(serializers.Serializer):
    """Empty serializer for endpoints that don't require input"""
    pass