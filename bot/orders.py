"""
Order placement logic: sits between the CLI and the API client.

Responsible for:
- turning a validated OrderRequest into an API call
- printing a clear request summary before sending
- printing a clear response summary (or failure message) after sending
- logging outcomes
"""

import logging

from bot.client import BinanceAPIError, BinanceNetworkError, FuturesTestnetClient
from bot.validators import OrderRequest

logger = logging.getLogger("trading_bot.orders")


def print_request_summary(order: OrderRequest) -> None:
    print("\n--- Order Request ---")
    print(f"Symbol:        {order.symbol}")
    print(f"Side:          {order.side}")
    print(f"Type:          {order.order_type}")
    print(f"Quantity:      {order.quantity}")
    if order.price is not None:
        print(f"Price:         {order.price}")
    if order.stop_price is not None:
        print(f"Stop Price:    {order.stop_price}")
    if order.order_type in ("LIMIT", "STOP_LIMIT"):
        print(f"Time in Force: {order.time_in_force}")
    print("----------------------\n")


def print_response_summary(response: dict) -> None:
    print("--- Order Response ---")
    print(f"Order ID:      {response.get('orderId')}")
    print(f"Status:        {response.get('status')}")
    print(f"Executed Qty:  {response.get('executedQty')}")
    avg_price = response.get("avgPrice")
    if avg_price is not None:
        print(f"Avg Price:     {avg_price}")
    print("-----------------------\n")


def place_order(client: FuturesTestnetClient, order: OrderRequest) -> dict:
    """Place the given order via the client, printing and logging results.

    Returns the raw API response dict on success. Raises BinanceAPIError or
    BinanceNetworkError on failure (already logged before re-raising).
    """
    print_request_summary(order)
    logger.info(
        "Placing %s %s order: symbol=%s qty=%s price=%s stop_price=%s",
        order.order_type,
        order.side,
        order.symbol,
        order.quantity,
        order.price,
        order.stop_price,
    )

    try:
        response = client.place_order(
            symbol=order.symbol,
            side=order.side,
            order_type=order.order_type,
            quantity=order.quantity,
            price=order.price,
            stop_price=order.stop_price,
            time_in_force=order.time_in_force,
        )
    except BinanceAPIError as exc:
        logger.error("Order failed (API error): %s", exc)
        print(f"FAILED: Binance API rejected the order -> {exc.message} (code {exc.code})")
        raise
    except BinanceNetworkError as exc:
        logger.error("Order failed (network error): %s", exc)
        print(f"FAILED: Network error while placing order -> {exc}")
        raise

    print_response_summary(response)
    logger.info(
        "Order placed successfully: orderId=%s status=%s",
        response.get("orderId"),
        response.get("status"),
    )
    print("SUCCESS: Order placed.\n")
    return response
