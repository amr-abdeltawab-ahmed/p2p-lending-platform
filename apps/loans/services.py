from typing import Optional, Dict, Any, List
from decimal import Decimal
import logging
from django.db import transaction
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model
from .repositories import LoanRepository, OfferRepository, PaymentRepository
from .models import Loan, Offer, Payment
from apps.wallets.services import WalletService
from apps.common.cache_utils import LoanCache
from apps.common.exception_handler import log_financial_operation
from apps.common.exceptions import (
    RolePermissionError, LoanNotFoundError, InvalidLoanStateError,
    OfferNotFoundError, OfferAlreadyAcceptedError, UnauthorizedLoanAccessError,
    InsufficientFundsError
)

User = get_user_model()
logger = logging.getLogger('apps.loans')


class LoanService:
    def __init__(self):
        self.loan_repo = LoanRepository()
        self.offer_repo = OfferRepository()
        self.payment_repo = PaymentRepository()
        self.wallet_service = WalletService()

    def create_loan(self, borrower: User, loan_data: Dict[str, Any]) -> Loan:
        # Validate borrower role
        if borrower.role != 'BORROWER':
            raise RolePermissionError("Only borrowers can create loan requests")

        loan = self.loan_repo.create_loan(borrower=borrower, **loan_data)

        # Log loan creation
        logger.info(
            f"Loan created by user {borrower.id}",
            extra={
                'user_id': borrower.id,
                'loan_id': loan.id,
                'amount': float(loan.amount),
                'term_months': loan.term_months,
                'interest_rate': float(loan.annual_interest_rate)
            }
        )

        # Invalidate available loans cache
        LoanCache.invalidate_available_loans()

        return loan

    def get_available_loans(self) -> List[Loan]:
        # Try to get from cache first
        cached_loans = LoanCache.get_available_loans()
        if cached_loans is not None:
            logger.info("Retrieved available loans from cache")
            return cached_loans

        # Get from database and cache
        loans = self.loan_repo.get_available_loans()
        LoanCache.set_available_loans(loans)
        logger.info(f"Retrieved {len(loans)} available loans from database and cached")

        return loans

    def get_loan_details(self, loan_id: int) -> Optional[Loan]:
        # Try to get from cache first
        cached_loan = LoanCache.get_loan_detail(loan_id)
        if cached_loan is not None:
            logger.info(f"Retrieved loan {loan_id} from cache")
            return cached_loan

        # Get from database and cache
        loan = self.loan_repo.get_loan_by_id(loan_id)
        if loan:
            LoanCache.set_loan_detail(loan_id, loan)
            logger.info(f"Retrieved loan {loan_id} from database and cached")

        return loan

    def get_loans_by_user(self, user: User) -> List[Loan]:
        if user.role == 'BORROWER':
            return self.loan_repo.get_loans_by_borrower(user)
        elif user.role == 'LENDER':
            return self.loan_repo.get_loans_by_lender(user)
        return []


class OfferService:
    def __init__(self):
        self.offer_repo = OfferRepository()
        self.loan_repo = LoanRepository()

    def create_offer(self, loan_id: int, lender: User, annual_interest_rate: Decimal) -> Dict[str, Any]:
        # Validate lender role
        if lender.role != 'LENDER':
            return {'success': False, 'error': 'Only lenders can make offers'}

        loan = self.loan_repo.get_loan_by_id(loan_id)
        if not loan:
            return {'success': False, 'error': 'Loan not found'}

        if loan.status != 'REQUESTED':
            return {'success': False, 'error': 'Loan is not available for offers'}

        if loan.borrower == lender:
            return {'success': False, 'error': 'Cannot make offer on your own loan'}

        # Check if lender already made an offer
        if self.offer_repo.check_existing_offer(loan, lender):
            return {'success': False, 'error': 'You have already made an offer on this loan'}

        offer = self.offer_repo.create_offer(loan, lender, annual_interest_rate)
        return {'success': True, 'offer': offer}

    def get_offers_for_loan(self, loan_id: int) -> List[Offer]:
        loan = self.loan_repo.get_loan_by_id(loan_id)
        if not loan:
            return []
        return self.offer_repo.get_offers_for_loan(loan)

    def accept_offer(self, loan_id: int, offer_id: int, borrower: User) -> Dict[str, Any]:
        loan = self.loan_repo.get_loan_by_id(loan_id)
        if not loan:
            return {'success': False, 'error': 'Loan not found'}

        if loan.borrower != borrower:
            return {'success': False, 'error': 'You can only accept offers on your own loans'}

        if loan.status != 'REQUESTED':
            return {'success': False, 'error': 'Loan is not available for offer acceptance'}

        offer = self.offer_repo.get_offer_by_id(offer_id)
        if not offer or offer.loan != loan:
            return {'success': False, 'error': 'Offer not found'}

        if offer.accepted:
            return {'success': False, 'error': 'Offer has already been accepted'}

        with transaction.atomic():
            # Accept the offer
            self.offer_repo.accept_offer(offer)

            # Update loan with accepted terms and lender
            self.loan_repo.update_loan(
                loan,
                lender=offer.lender,
                annual_interest_rate=offer.annual_interest_rate,
                status='PENDING_FUNDING'
            )

        return {'success': True, 'loan': loan}


class LoanFundingService:
    def __init__(self):
        self.loan_repo = LoanRepository()
        self.wallet_service = WalletService()
        self.payment_repo = PaymentRepository()

    def fund_loan(self, loan_id: int, lender: User) -> Dict[str, Any]:
        loan = self.loan_repo.get_loan_by_id(loan_id)
        if not loan:
            raise LoanNotFoundError("Loan not found")

        if loan.lender != lender:
            raise UnauthorizedLoanAccessError("You are not the assigned lender for this loan")

        if loan.status != 'PENDING_FUNDING':
            raise InvalidLoanStateError("Loan is not ready for funding")

        # Calculate total amount needed (loan amount + platform fee)
        platform_fee = Decimal(str(settings.PLATFORM_FUNDING_FEE))
        total_needed = loan.amount + platform_fee

        # Check lender's wallet balance
        if not self.wallet_service.check_balance(lender, total_needed):
            raise InsufficientFundsError(
                f'Insufficient funds. Need ${total_needed} (${loan.amount} + ${platform_fee} fee)'
            )

        with transaction.atomic():
            # Transfer loan amount to borrower
            transfer_result = self.wallet_service.transfer_funds(
                from_user=lender,
                to_user=loan.borrower,
                amount=loan.amount,
                transaction_type='LOAN_FUNDING',
                reference_id=f'loan_{loan.id}'
            )

            if not transfer_result['success']:
                return {'success': False, 'error': transfer_result['error']}

            # Deduct platform fee
            fee_result = self.wallet_service.deduct_platform_fee(
                user=lender,
                amount=platform_fee,
                reference_id=f'loan_{loan.id}_fee'
            )

            if not fee_result['success']:
                return {'success': False, 'error': fee_result['error']}

            # Update loan status
            self.loan_repo.update_loan(
                loan,
                status='FUNDED',
                funded_at=timezone.now()
            )

            # Generate payment schedule
            Payment.generate_payment_schedule(loan)

            # Log financial operations
            log_financial_operation(
                operation_type='LOAN_FUNDING',
                user_id=lender.id,
                amount=loan.amount,
                reference_id=f'loan_{loan.id}',
                details={
                    'loan_id': loan.id,
                    'borrower_id': loan.borrower.id,
                    'platform_fee': float(platform_fee),
                    'total_deducted': float(total_needed)
                }
            )

            # Invalidate related caches
            LoanCache.invalidate_loan_related_caches(
                loan.id,
                borrower_id=loan.borrower.id,
                lender_id=lender.id
            )

        return {'success': True, 'loan': loan}


class PaymentService:
    def __init__(self):
        self.payment_repo = PaymentRepository()
        self.loan_repo = LoanRepository()
        self.wallet_service = WalletService()

    def make_payment(self, loan_id: int, borrower: User) -> Dict[str, Any]:
        loan = self.loan_repo.get_loan_by_id(loan_id)
        if not loan:
            return {'success': False, 'error': 'Loan not found'}

        if loan.borrower != borrower:
            return {'success': False, 'error': 'You can only make payments on your own loans'}

        if loan.status != 'FUNDED':
            return {'success': False, 'error': 'Loan is not in a state where payments can be made'}

        # Get next pending payment
        next_payment = self.payment_repo.get_next_pending_payment(loan)
        if not next_payment:
            return {'success': False, 'error': 'No pending payments found'}

        # Check borrower's wallet balance
        if not self.wallet_service.check_balance(borrower, next_payment.amount):
            return {
                'success': False,
                'error': f'Insufficient funds. Need ${next_payment.amount} for payment'
            }

        with transaction.atomic():
            # Transfer payment to lender
            transfer_result = self.wallet_service.transfer_funds(
                from_user=borrower,
                to_user=loan.lender,
                amount=next_payment.amount,
                transaction_type='LOAN_PAYMENT',
                reference_id=f'payment_{next_payment.id}'
            )

            if not transfer_result['success']:
                return {'success': False, 'error': transfer_result['error']}

            # Mark payment as paid
            self.payment_repo.mark_payment_as_paid(next_payment)

            # Check if all payments are completed
            payment_status = self.payment_repo.get_all_payments_for_loan_status(loan)
            if payment_status['all_paid']:
                self.loan_repo.update_loan(loan, status='COMPLETED')

        return {
            'success': True,
            'payment': next_payment,
            'loan_completed': payment_status['all_paid']
        }

    def get_payment_schedule(self, loan_id: int, user: User) -> List[Payment]:
        loan = self.loan_repo.get_loan_by_id(loan_id)
        if not loan:
            return []

        # Only allow loan participants to view payment schedule
        if user not in [loan.borrower, loan.lender]:
            return []

        return self.payment_repo.get_payments_for_loan(loan)

    def get_pending_payments(self, borrower: User) -> List[Payment]:
        return self.payment_repo.get_pending_payments_by_borrower(borrower)