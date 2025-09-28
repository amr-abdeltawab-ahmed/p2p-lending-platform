"""
Domain-specific exceptions for the P2P lending platform.
"""

from rest_framework import status


class LendingPlatformError(Exception):
    """Base exception for all lending platform errors."""
    default_message = "An error occurred in the lending platform"
    error_code = "PLATFORM_ERROR"
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, message=None, error_code=None):
        self.message = message or self.default_message
        self.error_code = error_code or self.error_code
        super().__init__(self.message)


class InsufficientFundsError(LendingPlatformError):
    """Raised when user has insufficient funds for an operation."""
    default_message = "Insufficient funds to complete this operation"
    error_code = "INSUFFICIENT_FUNDS"
    status_code = status.HTTP_400_BAD_REQUEST


class LoanNotFoundError(LendingPlatformError):
    """Raised when a loan is not found."""
    default_message = "The requested loan was not found"
    error_code = "LOAN_NOT_FOUND"
    status_code = status.HTTP_404_NOT_FOUND


class InvalidLoanStateError(LendingPlatformError):
    """Raised when trying to perform an operation on a loan in invalid state."""
    default_message = "Cannot perform this operation on the loan in its current state"
    error_code = "INVALID_LOAN_STATE"
    status_code = status.HTTP_409_CONFLICT


class OfferNotFoundError(LendingPlatformError):
    """Raised when an offer is not found."""
    default_message = "The requested offer was not found"
    error_code = "OFFER_NOT_FOUND"
    status_code = status.HTTP_404_NOT_FOUND


class OfferAlreadyAcceptedError(LendingPlatformError):
    """Raised when trying to accept an already accepted offer."""
    default_message = "This offer has already been accepted"
    error_code = "OFFER_ALREADY_ACCEPTED"
    status_code = status.HTTP_409_CONFLICT


class UnauthorizedLoanAccessError(LendingPlatformError):
    """Raised when user tries to access a loan they don't own."""
    default_message = "You are not authorized to access this loan"
    error_code = "UNAUTHORIZED_LOAN_ACCESS"
    status_code = status.HTTP_403_FORBIDDEN


class WalletNotFoundError(LendingPlatformError):
    """Raised when a wallet is not found."""
    default_message = "Wallet not found"
    error_code = "WALLET_NOT_FOUND"
    status_code = status.HTTP_404_NOT_FOUND


class PaymentNotFoundError(LendingPlatformError):
    """Raised when a payment is not found."""
    default_message = "Payment not found"
    error_code = "PAYMENT_NOT_FOUND"
    status_code = status.HTTP_404_NOT_FOUND


class InvalidPaymentStateError(LendingPlatformError):
    """Raised when trying to modify a payment in invalid state."""
    default_message = "Cannot modify payment in its current state"
    error_code = "INVALID_PAYMENT_STATE"
    status_code = status.HTTP_409_CONFLICT


class RolePermissionError(LendingPlatformError):
    """Raised when user's role doesn't allow the operation."""
    default_message = "Your role does not allow this operation"
    error_code = "ROLE_PERMISSION_ERROR"
    status_code = status.HTTP_403_FORBIDDEN