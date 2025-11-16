"""
Base payment provider class.
All payment providers should inherit from this class.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any


class PaymentStatus(Enum):
    """Payment status enum."""
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"


@dataclass
class PaymentResult:
    """Result of payment operation."""
    success: bool
    payment_id: Optional[str] = None
    payment_url: Optional[str] = None
    status: PaymentStatus = PaymentStatus.PENDING
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class PaymentProvider(ABC):
    """Base class for payment providers."""

    @abstractmethod
    async def create_payment(
        self,
        amount: float,
        currency: str,
        description: str,
        user_id: int,
        return_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> PaymentResult:
        """
        Create new payment.

        Args:
            amount: Payment amount
            currency: Currency code (e.g., 'RUB', 'USD')
            description: Payment description
            user_id: User's Telegram ID
            return_url: URL to return after payment
            metadata: Additional metadata

        Returns:
            PaymentResult
        """
        pass

    @abstractmethod
    async def check_payment_status(self, payment_id: str) -> PaymentResult:
        """
        Check payment status.

        Args:
            payment_id: Payment ID from provider

        Returns:
            PaymentResult with current status
        """
        pass

    @abstractmethod
    async def refund(self, payment_id: str, amount: Optional[float] = None) -> PaymentResult:
        """
        Refund payment.

        Args:
            payment_id: Payment ID from provider
            amount: Amount to refund (None = full refund)

        Returns:
            PaymentResult
        """
        pass

    def get_provider_name(self) -> str:
        """Get provider name."""
        return self.__class__.__name__.replace('Provider', '').lower()
