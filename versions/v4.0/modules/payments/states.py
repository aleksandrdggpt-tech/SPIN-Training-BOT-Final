"""
FSM (Finite State Machine) states for payment flow.
Used with python-telegram-bot ConversationHandler.
"""

from enum import IntEnum, auto


class PaymentStates(IntEnum):
    """States for payment conversation flow."""

    # Main menu
    MAIN_MENU = auto()

    # Tariff selection
    SELECTING_TARIFF = auto()
    CONFIRMING_TARIFF = auto()

    # Payment
    SELECTING_PROVIDER = auto()
    PROCESSING_PAYMENT = auto()
    WAITING_PAYMENT = auto()

    # Promocode
    ENTERING_PROMOCODE = auto()
    VALIDATING_PROMOCODE = auto()

    # Free access
    CHECKING_SUBSCRIPTION = auto()

    # Admin
    ADMIN_MENU = auto()
    CREATING_PROMOCODE = auto()
    GIVING_ACCESS = auto()

    # SPIN sales funnel
    SPIN_S = auto()  # Situation
    SPIN_P = auto()  # Problem
    SPIN_I = auto()  # Implication
    SPIN_N = auto()  # Need-payoff


class PromoInputStates(IntEnum):
    """States for promocode input flow."""

    WAITING_CODE = auto()
    PROCESSING = auto()


# State descriptions for logging/debugging
STATE_DESCRIPTIONS = {
    PaymentStates.MAIN_MENU: "Main payment menu",
    PaymentStates.SELECTING_TARIFF: "User is selecting a tariff",
    PaymentStates.CONFIRMING_TARIFF: "User is confirming tariff selection",
    PaymentStates.SELECTING_PROVIDER: "User is selecting payment provider",
    PaymentStates.PROCESSING_PAYMENT: "Payment is being processed",
    PaymentStates.WAITING_PAYMENT: "Waiting for payment confirmation",
    PaymentStates.ENTERING_PROMOCODE: "User is entering promocode",
    PaymentStates.VALIDATING_PROMOCODE: "Validating promocode",
    PaymentStates.CHECKING_SUBSCRIPTION: "Checking channel subscription",
    PaymentStates.ADMIN_MENU: "Admin menu",
    PaymentStates.CREATING_PROMOCODE: "Admin is creating promocode",
    PaymentStates.GIVING_ACCESS: "Admin is giving access to user",
}


def get_state_description(state: PaymentStates) -> str:
    """Get human-readable state description."""
    return STATE_DESCRIPTIONS.get(state, f"Unknown state: {state}")
