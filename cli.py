#!/usr/bin/env python3
"""
CLI entry point for the simplified Binance Futures Testnet trading bot.

Examples:
    # Market order
    python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01

    # Limit order
    python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 65000

    # Stop-limit order (bonus order type)
    python cli.py --symbol BTCUSDT --side BUY --type STOP_LIMIT --quantity 0.01 \\
        --price 64000 --stop-price 64100

Credentials are read from environment variables BINANCE_API_KEY and
BINANCE_API_SECRET (see README.md), or from a .env file if python-dotenv
is installed.
"""

import argparse
import logging
import os
import sys

from bot.client import BinanceAPIError, BinanceNetworkError, FuturesTestnetClient
from bot.logging_config import setup_logging
from bot.orders import place_order
from bot.validators import ValidationError, build_order_request

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass  # python-dotenv is optional; env vars can be set directly


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading-bot",
        description="Place MARKET / LIMIT / STOP_LIMIT orders on Binance Futures Testnet (USDT-M).",
    )
    parser.add_argument("--symbol", required=True, help="Trading pair, e.g. BTCUSDT")
    parser.add_argument("--side", required=True, choices=["BUY", "SELL", "buy", "sell"])
    parser.add_argument(
        "--type",
        dest="order_type",
        required=True,
        choices=["MARKET", "LIMIT", "STOP_LIMIT", "market", "limit", "stop_limit"],
        help="Order type",
    )
    parser.add_argument("--quantity", required=True, help="Order quantity, e.g. 0.01")
    parser.add_argument(
        "--price", required=False, default=None, help="Required for LIMIT / STOP_LIMIT"
    )
    parser.add_argument(
        "--stop-price",
        dest="stop_price",
        required=False,
        default=None,
        help="Required for STOP_LIMIT",
    )
    parser.add_argument(
        "--time-in-force",
        dest="time_in_force",
        default="GTC",
        help="GTC / IOC / FOK (default: GTC, LIMIT/STOP_LIMIT only)",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("BINANCE_BASE_URL", "https://testnet.binancefuture.com"),
        help="Override API base URL (default: Futures Testnet)",
    )
    return parser


def main(argv=None) -> int:
    logger = setup_logging(level=logging.INFO)
    parser = build_parser()
    args = parser.parse_args(argv)

    # 1. Validate input
    try:
        order = build_order_request(
            symbol=args.symbol,
            side=args.side,
            order_type=args.order_type,
            quantity=args.quantity,
            price=args.price,
            stop_price=args.stop_price,
            time_in_force=args.time_in_force,
        )
    except ValidationError as exc:
        logger.warning("Input validation failed: %s", exc)
        print(f"Invalid input: {exc}")
        return 1

    # 2. Load credentials
    api_key = os.environ.get("BINANCE_API_KEY")
    api_secret = os.environ.get("BINANCE_API_SECRET")
    if not api_key or not api_secret:
        logger.error("Missing API credentials in environment.")
        print(
            "Missing credentials. Set BINANCE_API_KEY and BINANCE_API_SECRET "
            "(see README.md for setup)."
        )
        return 1

    client = FuturesTestnetClient(
        api_key=api_key, api_secret=api_secret, base_url=args.base_url
    )

    # 3. Place order
    try:
        place_order(client, order)
    except (BinanceAPIError, BinanceNetworkError):
        # Already logged and printed inside place_order/client
        return 1
    except Exception as exc:  # noqa: BLE001 - final safety net for CLI
        logger.exception("Unexpected error while placing order: %s", exc)
        print(f"FAILED: Unexpected error -> {exc}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
