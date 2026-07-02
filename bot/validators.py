"""
Input validation for order parameters.

Keeping validation isolated from both the CLI and the API client makes it
independently testable and reusable (e.g. if a GUI or web layer is added
later, it can reuse the same rules).
"""

import re
from dataclasses import dataclass
from typing import Optional

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_LIMIT"}
SYMBOL_PATTERN = re.compile(r"^[A-Z0-9]{5,20}$")


class ValidationError(Exception):
    """Raised when user-supplied order parameters fail validation."""


@dataclass
class OrderRequest:
    symbol: str
    side: str
    order_type: str
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: str = "GTC"


def validate_symbol(symbol: str) -> str:
    symbol = symbol.strip().upper()
    if not SYMBOL_PATTERN.match(symbol):
        raise ValidationError(
            f"Invalid symbol '{symbol}'. Expected format like 'BTCUSDT'."
        )
    return symbol


def validate_side(side: str) -> str:
    side = side.strip().upper()
    if side not in VALID_SIDES:
        raise ValidationError(f"Invalid side '{side}'. Must be one of {VALID_SIDES}.")
    return side


def validate_order_type(order_type: str) -> str:
    order_type = order_type.strip().upper()
    if order_type not in VALID_ORDER_TYPES:
        raise ValidationError(
            f"Invalid order type '{order_type}'. Must be one of {VALID_ORDER_TYPES}."
        )
    return order_type


def validate_quantity(quantity) -> float:
    try:
        quantity = float(quantity)
    except (TypeError, ValueError):
        raise ValidationError(f"Quantity must be numeric, got '{quantity}'.")
    if quantity <= 0:
        raise ValidationError("Quantity must be greater than 0.")
    return quantity


def validate_price(price, required: bool) -> Optional[float]:
    if price is None:
        if required:
            raise ValidationError("Price is required for LIMIT / STOP_LIMIT orders.")
        return None
    try:
        price = float(price)
    except (TypeError, ValueError):
        raise ValidationError(f"Price must be numeric, got '{price}'.")
    if price <= 0:
        raise ValidationError("Price must be greater than 0.")
    return price


def build_order_request(
    symbol: str,
    side: str,
    order_type: str,
    quantity,
    price=None,
    stop_price=None,
    time_in_force: str = "GTC",
) -> OrderRequest:
    """Validate raw CLI input and return a clean OrderRequest, or raise
    ValidationError with a human-readable message."""
    symbol = validate_symbol(symbol)
    side = validate_side(side)
    order_type = validate_order_type(order_type)
    quantity = validate_quantity(quantity)

    needs_price = order_type in ("LIMIT", "STOP_LIMIT")
    price = validate_price(price, required=needs_price)

    stop_needed = order_type == "STOP_LIMIT"
    if stop_needed:
        stop_price = validate_price(stop_price, required=True)
    else:
        stop_price = None

    return OrderRequest(
        symbol=symbol,
        side=side,
        order_type=order_type,
        quantity=quantity,
        price=price,
        stop_price=stop_price,
        time_in_force=time_in_force.strip().upper() if time_in_force else "GTC",
    )
