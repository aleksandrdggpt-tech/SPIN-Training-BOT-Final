"""
Payment providers for SPIN Training Bot v4.
Supports CloudPayments, YooKassa, and Prodamus.
"""

from .base import PaymentProvider, PaymentResult, PaymentStatus
from .yookassa import YooKassaProvider
from .cloudpayments import CloudPaymentsProvider
from .prodamus import ProdamusProvider

__all__ = [
    'PaymentProvider',
    'PaymentResult',
    'PaymentStatus',
    'YooKassaProvider',
    'CloudPaymentsProvider',
    'ProdamusProvider'
]


def get_payment_provider(provider_name: str) -> PaymentProvider:
    """
    Get payment provider instance by name.

    Args:
        provider_name: 'yookassa', 'cloudpayments', or 'prodamus'

    Returns:
        PaymentProvider instance

    Raises:
        ValueError: If provider not found
    """
    providers = {
        'yookassa': YooKassaProvider,
        'cloudpayments': CloudPaymentsProvider,
        'prodamus': ProdamusProvider
    }

    provider_class = providers.get(provider_name.lower())
    if not provider_class:
        raise ValueError(f"Unknown payment provider: {provider_name}")

    return provider_class()
