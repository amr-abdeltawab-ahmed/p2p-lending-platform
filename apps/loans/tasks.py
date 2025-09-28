"""
Celery tasks for loan management and payment processing.
"""

import logging
from datetime import date
from typing import Dict, Any
from celery import shared_task
from django.db.models import Q
from django.utils import timezone
from .models import Loan, Payment
from .repositories import PaymentRepository, LoanRepository

logger = logging.getLogger('apps.loans')


@shared_task(bind=True)
def check_overdue_payments(self) -> Dict[str, Any]:
    """
    Hourly task to check and mark overdue payments.

    This task:
    1. Finds all pending payments that are past their due date
    2. Marks them as OVERDUE
    3. Logs the results for monitoring
    4. Returns a summary of actions taken
    """
    task_id = self.request.id
    logger.info(f"Starting overdue payment check task {task_id}")

    try:
        # Get all pending payments that are past due
        today = date.today()
        overdue_payments = Payment.objects.filter(
            status='PENDING',
            due_date__lt=today
        ).select_related('loan', 'loan__borrower')

        # Count totals before making changes
        total_overdue = overdue_payments.count()

        if total_overdue == 0:
            logger.info("No overdue payments found")
            return {
                'task_id': task_id,
                'status': 'completed',
                'overdue_payments_found': 0,
                'payments_marked_overdue': 0,
                'timestamp': timezone.now().isoformat()
            }

        # Track affected loans and borrowers for logging
        affected_loans = set()
        affected_borrowers = set()
        payments_updated = 0

        # Update overdue payments
        for payment in overdue_payments:
            payment.status = 'OVERDUE'
            payment.save(update_fields=['status'])

            affected_loans.add(payment.loan.id)
            affected_borrowers.add(payment.loan.borrower.id)
            payments_updated += 1

            logger.warning(
                f"Payment {payment.id} for loan {payment.loan.id} marked as OVERDUE. "
                f"Due: {payment.due_date}, Amount: ${payment.amount}"
            )

        # Log summary
        logger.info(
            f"Overdue payment check completed. "
            f"Payments marked overdue: {payments_updated}, "
            f"Affected loans: {len(affected_loans)}, "
            f"Affected borrowers: {len(affected_borrowers)}"
        )

        return {
            'task_id': task_id,
            'status': 'completed',
            'overdue_payments_found': total_overdue,
            'payments_marked_overdue': payments_updated,
            'affected_loans': len(affected_loans),
            'affected_borrowers': len(affected_borrowers),
            'timestamp': timezone.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error in overdue payment check task {task_id}: {str(e)}")
        return {
            'task_id': task_id,
            'status': 'failed',
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }


@shared_task(bind=True)
def loan_status_summary_report(self) -> Dict[str, Any]:
    """
    Daily task to generate a summary report of loan statuses.

    This provides insights into platform performance and loan lifecycle.
    """
    task_id = self.request.id
    logger.info(f"Starting loan status summary report task {task_id}")

    try:
        # Count loans by status
        loan_counts = {
            'REQUESTED': Loan.objects.filter(status='REQUESTED').count(),
            'PENDING_FUNDING': Loan.objects.filter(status='PENDING_FUNDING').count(),
            'FUNDED': Loan.objects.filter(status='FUNDED').count(),
            'COMPLETED': Loan.objects.filter(status='COMPLETED').count(),
            'CANCELLED': Loan.objects.filter(status='CANCELLED').count(),
        }

        # Count payments by status
        payment_counts = {
            'PENDING': Payment.objects.filter(status='PENDING').count(),
            'PAID': Payment.objects.filter(status='PAID').count(),
            'OVERDUE': Payment.objects.filter(status='OVERDUE').count(),
        }

        # Calculate some metrics
        total_loans = sum(loan_counts.values())
        total_payments = sum(payment_counts.values())
        completion_rate = (loan_counts['COMPLETED'] / total_loans * 100) if total_loans > 0 else 0
        overdue_rate = (payment_counts['OVERDUE'] / total_payments * 100) if total_payments > 0 else 0

        report = {
            'task_id': task_id,
            'timestamp': timezone.now().isoformat(),
            'loan_status_counts': loan_counts,
            'payment_status_counts': payment_counts,
            'metrics': {
                'total_loans': total_loans,
                'total_payments': total_payments,
                'loan_completion_rate': round(completion_rate, 2),
                'payment_overdue_rate': round(overdue_rate, 2)
            }
        }

        logger.info(f"Loan status summary report completed: {report}")
        return report

    except Exception as e:
        logger.error(f"Error in loan status summary report task {task_id}: {str(e)}")
        return {
            'task_id': task_id,
            'status': 'failed',
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }


@shared_task(bind=True)
def cleanup_expired_loan_cache(self) -> Dict[str, Any]:
    """
    Task to manually cleanup expired cache entries.

    This is a maintenance task that can be run periodically.
    """
    task_id = self.request.id
    logger.info(f"Starting cache cleanup task {task_id}")

    try:
        from apps.common.cache_utils import LoanCache, WalletCache

        # For now, we'll just log that the task ran
        # In a production environment, you might want to implement
        # more sophisticated cache cleanup logic

        logger.info("Cache cleanup task completed (no actions needed - Redis handles TTL)")

        return {
            'task_id': task_id,
            'status': 'completed',
            'message': 'Cache cleanup completed - Redis handles TTL automatically',
            'timestamp': timezone.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error in cache cleanup task {task_id}: {str(e)}")
        return {
            'task_id': task_id,
            'status': 'failed',
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }