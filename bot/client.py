"""
Thin wrapper around the Binance Futures Testnet (USDT-M) REST API.

Implemented with plain `requests` calls (no python-binance dependency) so
the signing / request logic is fully visible and easy to audit. Every
request and response is logged via the shared logger.

Docs: https://binance-docs.github.io/apidocs/testnet/en/
Base URL: https://testnet.binancefuture.com
"""

import hashlib
import hmac
import logging
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests

from bot.logging_config import redact

logger = logging.getLogger("trading_bot.client")

DEFAULT_BASE_URL = "https://testnet.binancefuture.com"
DEFAULT_TIMEOUT = 10  # seconds
RECV_WINDOW = 5000


class BinanceAPIError(Exception):
    """Raised when the Binance API returns an error response."""

    def __init__(self, status_code: int, code: Optional[int], message: str):
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(f"Binance API error [{status_code}] code={code}: {message}")


class BinanceNetworkError(Exception):
    """Raised when a network-level failure occurs (timeout, DNS, connection)."""


class FuturesTestnetClient:
    """Minimal REST client for Binance USDT-M Futures Testnet."""

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        if not api_key or not api_secret:
            raise ValueError("api_key and api_secret must be provided.")
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"X-MBX-APIKEY": self.api_key})

    # -- internal helpers ---------------------------------------------------

    def _sign(self, params: Dict[str, Any]) -> Dict[str, Any]:
        params = dict(params)
        params["timestamp"] = int(time.time() * 1000)
        params["recvWindow"] = RECV_WINDOW
        query_string = urlencode(params, doseq=True)
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        params["signature"] = signature
        return params

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        signed: bool = False,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        params = params or {}

        if signed:
            params = self._sign(params)

        logger.debug(
            "REQUEST %s %s params=%s", method, endpoint, redact(params)
        )

        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params if method == "GET" else None,
                data=params if method != "GET" else None,
                timeout=self.timeout,
            )
        except requests.exceptions.Timeout as exc:
            logger.error("Network timeout calling %s %s: %s", method, endpoint, exc)
            raise BinanceNetworkError(f"Request to {endpoint} timed out.") from exc
        except requests.exceptions.ConnectionError as exc:
            logger.error("Connection error calling %s %s: %s", method, endpoint, exc)
            raise BinanceNetworkError(
                f"Could not connect to {self.base_url}. Check your network."
            ) from exc
        except requests.exceptions.RequestException as exc:
            logger.error("Unexpected network error calling %s %s: %s", method, endpoint, exc)
            raise BinanceNetworkError(str(exc)) from exc

        logger.debug(
            "RESPONSE %s %s status=%s body=%s",
            method,
            endpoint,
            response.status_code,
            response.text,
        )

        try:
            body = response.json()
        except ValueError:
            body = {"raw": response.text}

        if not response.ok:
            code = body.get("code") if isinstance(body, dict) else None
            message = body.get("msg") if isinstance(body, dict) else str(body)
            logger.error(
                "API error on %s %s -> status=%s code=%s msg=%s",
                method,
                endpoint,
                response.status_code,
                code,
                message,
            )
            raise BinanceAPIError(response.status_code, code, message or "Unknown error")

        return body

    # -- public endpoints -----------------------------------------------------

    def ping(self) -> Dict[str, Any]:
        return self._request("GET", "/fapi/v1/ping")

    def get_server_time(self) -> Dict[str, Any]:
        return self._request("GET", "/fapi/v1/time")

    def get_exchange_info(self) -> Dict[str, Any]:
        return self._request("GET", "/fapi/v1/exchangeInfo")

    # -- account / trading endpoints (signed) ---------------------------------

    def get_account(self) -> Dict[str, Any]:
        return self._request("GET", "/fapi/v2/account", signed=True)

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        time_in_force: str = "GTC",
    ) -> Dict[str, Any]:
        """Place an order on the USDT-M futures testnet.

        order_type: MARKET | LIMIT | STOP (stop-limit, mapped to Binance's
        'STOP' futures order type which requires stopPrice + price).
        """
        params: Dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "type": self._map_order_type(order_type),
            "quantity": quantity,
        }

        if order_type == "LIMIT":
            params["price"] = price
            params["timeInForce"] = time_in_force
        elif order_type == "STOP_LIMIT":
            params["price"] = price
            params["stopPrice"] = stop_price
            params["timeInForce"] = time_in_force
        # MARKET needs no price / timeInForce

        return self._request("POST", "/fapi/v1/order", params=params, signed=True)

    def get_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        params = {"symbol": symbol, "orderId": order_id}
        return self._request("GET", "/fapi/v1/order", params=params, signed=True)

    @staticmethod
    def _map_order_type(order_type: str) -> str:
        # Binance futures uses "STOP" for stop-limit orders
        return "STOP" if order_type == "STOP_LIMIT" else order_type
