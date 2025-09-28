"""
Django signals for automatic cache invalidation on loan state changes.
"""

import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Loan, Offer, Payment
from apps.common.cache_utils import LoanCache

logger = logging.getLogger('apps.loans')


@receiver(post_save, sender=Loan)
def invalidate_loan_cache_on_save(sender, instance, created, **kwargs):
    """
    Invalidate loan-related caches when a loan is created or updated.

    This ensures that:
    - New loans appear in available loans list
    - Status changes are reflected immediately
    - Loan details are always up-to-date
    """
    loan = instance

    # Always invalidate available loans cache when any loan changes
    LoanCache.invalidate_available_loans()

    # Invalidate specific loan detail cache
    LoanCache.invalidate_loan_detail(loan.id)

    # Invalidate user loan caches
    if loan.borrower_id:
        LoanCache.invalidate_user_loans(loan.borrower_id)

    if loan.lender_id:
        LoanCache.invalidate_user_loans(loan.lender_id)

    # Log the cache invalidation
    action = "created" if created else "updated"
    logger.info(
        f"Loan {loan.id} {action} - invalidated related caches "
        f"(status: {loan.status})"
    )


@receiver(post_delete, sender=Loan)
def invalidate_loan_cache_on_delete(sender, instance, **kwargs):
    """
    Invalidate loan-related caches when a loan is deleted.
    """
    loan = instance

    # Invalidate available loans cache
    LoanCache.invalidate_available_loans()

    # Invalidate specific loan detail cache
    LoanCache.invalidate_loan_detail(loan.id)

    # Invalidate user loan caches
    if loan.borrower_id:
        LoanCache.invalidate_user_loans(loan.borrower_id)

    if loan.lender_id:
        LoanCache.invalidate_user_loans(loan.lender_id)

    logger.info(f"Loan {loan.id} deleted - invalidated related caches")


@receiver(post_save, sender=Offer)
def invalidate_loan_cache_on_offer_change(sender, instance, created, **kwargs):
    """
    Invalidate loan caches when offers are created or updated.

    This ensures that loan details with offers are always current.
    """
    offer = instance

    # Invalidate the specific loan's detail cache
    LoanCache.invalidate_loan_detail(offer.loan_id)

    # If offer was accepted, also invalidate available loans
    if offer.accepted:
        LoanCache.invalidate_available_loans()
        logger.info(f"Offer {offer.id} accepted for loan {offer.loan_id} - invalidated caches")

    action = "created" if created else "updated"
    logger.info(f"Offer {offer.id} {action} for loan {offer.loan_id}")


@receiver(post_save, sender=Payment)
def invalidate_loan_cache_on_payment_change(sender, instance, created, **kwargs):
    """
    Invalidate loan caches when payments are created or updated.

    This ensures that payment schedules and loan status are always current.
    """
    payment = instance

    # Invalidate the specific loan's detail cache
    LoanCache.invalidate_loan_detail(payment.loan_id)

    # If payment status changed, it might affect loan status
    if not created:  # Only for updates
        LoanCache.invalidate_available_loans()

    action = "created" if created else "updated"
    logger.info(
        f"Payment {payment.id} {action} for loan {payment.loan_id} "
        f"(status: {payment.status})"
    )