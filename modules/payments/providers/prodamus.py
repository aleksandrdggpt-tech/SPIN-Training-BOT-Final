"""
Prodamus payment provider.
Documentation: https://help.prodamus.ru/
"""

import logging
import os
from typing import Optional, Dict, Any
from .base import PaymentProvider, PaymentResult, PaymentStatus

logger = logging.getLogger(__name__)


class ProdamusProvider(PaymentProvider):
    """Prodamus payment provider (stub implementation)."""

    def __init__(self):
        self.api_key = os.getenv('PRODAMUS_API_KEY', '')

        if not self.api_key:
            logger.warning("Prodamus credentials not configured")

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
        Create payment in Prodamus.

        TODO: Implement actual Prodamus API integration.
        """
        logger.info(f"Creating Prodamus payment: {amount} {currency} for user {user_id}")

        # TODO: Implement Prodamus API
        # https://help.prodamus.ru/api-documentation

        # Stub response
        return PaymentResult(
            success=True,
            payment_id="prodamus_stub_id_12345",
            payment_url="https://prodamus.ru/pay/stub",
            status=PaymentStatus.PENDING,
            metadata={"stub": True}
        )

    async def check_payment_status(self, payment_id: str) -> PaymentResult:
        """Check payment status in Prodamus."""
        logger.info(f"Checking Prodamus payment status: {payment_id}")

        # TODO: Implement status checking

        # Stub response
        return PaymentResult(
            success=True,
            payment_id=payment_id,
            status=PaymentStatus.PENDING,
            metadata={"stub": True}
        )

    async def refund(self, payment_id: str, amount: Optional[float] = None) -> PaymentResult:
        """Refund payment in Prodamus."""
        logger.info(f"Refunding Prodamus payment: {payment_id}, amount: {amount}")

        # TODO: Implement refund

        # Stub response
        return PaymentResult(
            success=True,
            payment_id=payment_id,
            status=PaymentStatus.SUCCEEDED,
            metadata={"stub": True, "refund": True}
        )
