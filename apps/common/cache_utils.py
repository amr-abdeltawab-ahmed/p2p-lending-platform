"""
Caching utilities for the P2P lending platform.
"""

import logging
from django.core.cache import cache
from django.conf import settings
from typing import Optional, Any

logger = logging.getLogger('apps.common')


class CacheKeys:
    """Cache key constants for the platform."""

    AVAILABLE_LOANS = "loans:available"
    LOAN_DETAIL = "loan:detail:{loan_id}"
    USER_LOANS = "user:loans:{user_id}"
    LOAN_OFFERS = "loan:offers:{loan_id}"
    PAYMENT_SCHEDULE = "loan:payments:{loan_id}"
    USER_WALLET = "wallet:{user_id}"

    # Cache timeouts (in seconds)
    DEFAULT_TIMEOUT = 300  # 5 minutes
    LOAN_TIMEOUT = 600     # 10 minutes
    WALLET_TIMEOUT = 120   # 2 minutes


class CacheManager:
    """Centralized cache management for the lending platform."""

    @staticmethod
    def get(key: str, default: Any = None) -> Any:
        """Get value from cache."""
        try:
            return cache.get(key, default)
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return default

    @staticmethod
    def set(key: str, value: Any, timeout: int = CacheKeys.DEFAULT_TIMEOUT) -> bool:
        """Set value in cache."""
        try:
            cache.set(key, value, timeout)
            logger.info(f"Cache set for key: {key}")
            return True
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False

    @staticmethod
    def delete(key: str) -> bool:
        """Delete key from cache."""
        try:
            cache.delete(key)
            logger.info(f"Cache deleted for key: {key}")
            return True
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False

    @staticmethod
    def delete_pattern(pattern: str) -> bool:
        """Delete keys matching pattern."""
        try:
            keys = cache.keys(pattern)
            if keys:
                cache.delete_many(keys)
                logger.info(f"Cache deleted for pattern: {pattern}, keys: {len(keys)}")
            return True
        except Exception as e:
            logger.error(f"Cache delete pattern error for {pattern}: {e}")
            return False


class LoanCache:
    """Cache management for loan-related data."""

    @staticmethod
    def get_available_loans():
        """Get cached available loans."""
        return CacheManager.get(CacheKeys.AVAILABLE_LOANS)

    @staticmethod
    def set_available_loans(loans_data):
        """Cache available loans."""
        return CacheManager.set(
            CacheKeys.AVAILABLE_LOANS,
            loans_data,
            CacheKeys.LOAN_TIMEOUT
        )

    @staticmethod
    def invalidate_available_loans():
        """Invalidate available loans cache."""
        return CacheManager.delete(CacheKeys.AVAILABLE_LOANS)

    @staticmethod
    def get_loan_detail(loan_id: int):
        """Get cached loan detail."""
        key = CacheKeys.LOAN_DETAIL.format(loan_id=loan_id)
        return CacheManager.get(key)

    @staticmethod
    def set_loan_detail(loan_id: int, loan_data):
        """Cache loan detail."""
        key = CacheKeys.LOAN_DETAIL.format(loan_id=loan_id)
        return CacheManager.set(key, loan_data, CacheKeys.LOAN_TIMEOUT)

    @staticmethod
    def invalidate_loan_detail(loan_id: int):
        """Invalidate loan detail cache."""
        key = CacheKeys.LOAN_DETAIL.format(loan_id=loan_id)
        return CacheManager.delete(key)

    @staticmethod
    def invalidate_user_loans(user_id: int):
        """Invalidate user's loans cache."""
        key = CacheKeys.USER_LOANS.format(user_id=user_id)
        return CacheManager.delete(key)

    @staticmethod
    def invalidate_loan_related_caches(loan_id: int, borrower_id: int = None, lender_id: int = None):
        """Invalidate all caches related to a loan."""
        # Invalidate specific loan
        LoanCache.invalidate_loan_detail(loan_id)

        # Invalidate available loans
        LoanCache.invalidate_available_loans()

        # Invalidate user loans if provided
        if borrower_id:
            LoanCache.invalidate_user_loans(borrower_id)
        if lender_id:
            LoanCache.invalidate_user_loans(lender_id)

        # Invalidate offers cache
        key = CacheKeys.LOAN_OFFERS.format(loan_id=loan_id)
        CacheManager.delete(key)

        # Invalidate payment schedule cache
        key = CacheKeys.PAYMENT_SCHEDULE.format(loan_id=loan_id)
        CacheManager.delete(key)


class WalletCache:
    """Cache management for wallet-related data."""

    @staticmethod
    def get_wallet(user_id: int):
        """Get cached wallet data."""
        key = CacheKeys.USER_WALLET.format(user_id=user_id)
        return CacheManager.get(key)

    @staticmethod
    def set_wallet(user_id: int, wallet_data):
        """Cache wallet data."""
        key = CacheKeys.USER_WALLET.format(user_id=user_id)
        return CacheManager.set(key, wallet_data, CacheKeys.WALLET_TIMEOUT)

    @staticmethod
    def invalidate_wallet(user_id: int):
        """Invalidate wallet cache."""
        key = CacheKeys.USER_WALLET.format(user_id=user_id)
        return CacheManager.delete(key)