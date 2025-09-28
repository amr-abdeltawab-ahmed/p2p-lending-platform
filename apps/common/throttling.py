"""
Custom throttling classes for the P2P lending platform.
"""

from rest_framework.throttling import UserRateThrottle, AnonRateThrottle


class FinancialOperationsThrottle(UserRateThrottle):
    """
    Throttle for financial operations like funding loans, making payments, etc.
    """
    scope = 'financial_operations'


class AuthOperationsThrottle(UserRateThrottle):
    """
    Throttle for authentication operations like login, register.
    """
    scope = 'auth_operations'


class LoanCreationThrottle(UserRateThrottle):
    """
    Throttle for loan creation operations.
    """
    scope = 'financial_operations'


class OfferThrottle(UserRateThrottle):
    """
    Throttle for offer creation operations.
    """
    scope = 'financial_operations'


class PaymentThrottle(UserRateThrottle):
    """
    Throttle for payment operations.
    """
    scope = 'financial_operations'