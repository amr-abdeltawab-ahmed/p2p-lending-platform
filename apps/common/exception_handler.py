"""
Custom exception handler for DRF that provides structured error responses.
"""

from rest_framework.views import exception_handler
from rest_framework.response import Response
import logging

from .exceptions import LendingPlatformError

logger = logging.getLogger('apps.common')


def custom_exception_handler(exc, context):
    """
    Custom exception handler that returns structured JSON responses.
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)

    if response is not None:
        # Handle our custom lending platform exceptions
        if isinstance(exc, LendingPlatformError):
            custom_response_data = {
                'success': False,
                'error_code': exc.error_code,
                'message': str(exc.message),
                'details': None
            }

            # Log the error for monitoring
            logger.error(
                f"LendingPlatformError: {exc.error_code}",
                extra={
                    'error_code': exc.error_code,
                    'message': str(exc.message),
                    'user_id': getattr(context.get('request'), 'user', {}).get('id'),
                    'path': context.get('request').path if context.get('request') else None,
                    'method': context.get('request').method if context.get('request') else None,
                }
            )

            response.data = custom_response_data
            response.status_code = exc.status_code
        else:
            # Handle other DRF exceptions with consistent format
            error_message = None
            error_code = "VALIDATION_ERROR"

            if hasattr(response, 'data'):
                if isinstance(response.data, dict):
                    if 'detail' in response.data:
                        error_message = response.data['detail']
                        error_code = "DETAIL_ERROR"
                    elif 'non_field_errors' in response.data:
                        error_message = response.data['non_field_errors'][0] if response.data['non_field_errors'] else "Validation error"
                    else:
                        # Field validation errors
                        error_message = "Validation failed"

            custom_response_data = {
                'success': False,
                'error_code': error_code,
                'message': error_message or "An error occurred",
                'details': response.data if hasattr(response, 'data') else None
            }

            response.data = custom_response_data

    return response


def log_financial_operation(operation_type, user_id, amount, reference_id=None, details=None):
    """
    Helper function to log financial operations with structured data.
    """
    financial_logger = logging.getLogger('apps.financial')

    log_data = {
        'operation_type': operation_type,
        'user_id': user_id,
        'amount': float(amount) if amount else None,
        'reference_id': reference_id,
        'details': details or {}
    }

    financial_logger.info(
        f"Financial operation: {operation_type}",
        extra=log_data
    )