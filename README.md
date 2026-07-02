# Simplified Trading Bot — Binance Futures Testnet (USDT-M)

A small, structured Python CLI application that places **MARKET**, **LIMIT**,
and **STOP_LIMIT** (bonus) orders on the Binance Futures Testnet, with input
validation, structured logging, and clean console output.

Built with plain `requests` calls (no `python-binance` dependency) so the
request signing and error handling are fully visible and easy to review.

## Project Structure

```
trading_bot/
bot/
init.py
client.py          # Binance REST client wrapper (signing, requests, errors)
orders.py           # Order placement logic (summary printing, logging)
validators.py        # Input validation -> OrderRequest
logging_config.py    # File + console logging setup
cli.py                 # CLI entry point (argparse)
logs/
trading_bot.log      # Generated log file (includes sample MARKET + LIMIT orders)
README.md
requirements.txt
.env.example
```

## Setup

### 1. Create a Binance Futures Testnet account

As of late 2025, Binance retired the standalone `testnet.binancefuture.com`
web login and merged it into **Demo Trading** inside a regular Binance.com
account. Setup now looks like this:

1. Log in to https://www.binance.com with your Binance account (or create one).
2. Navigate to **Demo Trading** (Binance will often redirect you here
   automatically if you visit the old testnet URL) and click **Start demo
   trading**.
3. Inside Demo Trading, find the **API Management** / **Demo Trading API**
   section and generate an API Key / Secret pair. These are separate,
   sandboxed credentials — they do not grant access to your real funds.

The REST API base URL has also changed accordingly:
https://demo-fapi.binance.com

(previously `https://testnet.binancefuture.com`). This project's default
base URL is already set to the new endpoint in `bot/client.py`, and can be
overridden with `--base-url` or the `BINANCE_BASE_URL` env var if Binance
changes it again.


### 2. Install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure credentials

Copy `.env.example` to `.env` and fill in your testnet keys:

```bash
cp .env.example .env
```

```
BINANCE_API_KEY=your_testnet_api_key_here
BINANCE_API_SECRET=your_testnet_api_secret_here
```

The app loads these automatically via `python-dotenv`. Alternatively, export
them directly in your shell:

```bash
export BINANCE_API_KEY=your_testnet_api_key_here
export BINANCE_API_SECRET=your_testnet_api_secret_here
```

The app loads these automatically via `python-dotenv`. Alternatively, export
them directly in your shell:

```bash
export BINANCE_API_KEY=your_testnet_api_key_here
export BINANCE_API_SECRET=your_testnet_api_secret_here
```

## Usage

### Market order

```bash
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01
```

### Limit order

```bash
python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 65000
```

### Stop-limit order (bonus order type)

```bash
python cli.py --symbol BTCUSDT --side BUY --type STOP_LIMIT --quantity 0.01 \
  --price 64000 --stop-price 64100
```

### All CLI options

| Flag                | Required        | Description                                |
|----------------------|-----------------|---------------------------------------------|
| `--symbol`           | yes             | Trading pair, e.g. `BTCUSDT`                |
| `--side`             | yes             | `BUY` or `SELL`                             |
| `--type`             | yes             | `MARKET`, `LIMIT`, or `STOP_LIMIT`          |
| `--quantity`         | yes             | Order quantity (must be > 0)                |
| `--price`            | LIMIT/STOP_LIMIT| Limit price                                 |
| `--stop-price`       | STOP_LIMIT only | Stop trigger price                          |
| `--time-in-force`    | no (default GTC)| `GTC` / `IOC` / `FOK`                       |
| `--base-url`         | no              | Override API base URL (defaults to Demo Trading) |

On success, the CLI prints an order **request summary**, the **response**
(order ID, status, executed quantity, avg price), and a `SUCCESS` message.
On failure (bad input, API rejection, or network error), it prints a clear
`FAILED` message and exits with a non-zero status code.

## Logging

All requests, responses, and errors are logged to `logs/trading_bot.log`
(rotates at 2MB, keeps 5 backups). API signatures are redacted before
logging. Console output stays at INFO level and only shows human-readable
progress/errors, keeping day-to-day use uncluttered.

`logs/trading_bot.log` in this repository already contains one successful
MARKET order and one successful LIMIT order as required deliverables.

## Error Handling

- **Invalid input** (bad symbol format, non-numeric quantity, missing price
  for LIMIT/STOP_LIMIT, etc.) is caught by `bot/validators.py` before any
  network call is made, and reported with a specific message.
- **API errors** (e.g. insufficient margin, invalid symbol, filters not met)
  raise `BinanceAPIError`, which is logged with the Binance error code/message
  and printed to the console as a `FAILED` line.
- **Network errors** (timeouts, connection failures) raise
  `BinanceNetworkError` and are handled the same way.

## Assumptions

- Only USDT-M Futures Testnet is targeted (`/fapi/v1` endpoints), not Spot or
  Coin-M futures.
- `STOP_LIMIT` was chosen as the bonus order type; it is mapped to Binance's
  futures `STOP` order type (requires both `price` and `stopPrice`).
- The account is assumed to already have testnet USDT funds (obtained via the
  testnet faucet) and appropriate leverage/margin settings for the requested
  symbol — the bot does not manage leverage or margin mode itself.
- `recvWindow` is fixed at 5000ms; system clock is assumed to be reasonably
  in sync (Binance rejects requests with too much timestamp drift).
- Default `timeInForce` is `GTC` for LIMIT/STOP_LIMIT orders unless
  overridden.

## Verified Runs

This bot has been run successfully against the live Binance Demo Trading API
(not just mocked). Sample results:

- MARKET BUY 0.01 BTCUSDT → `orderId=18457195764`, status `NEW`
- LIMIT SELL 0.01 BTCUSDT @ 65000 → `orderId=18457402503`, status `NEW`

Full request/response detail for both is in `logs/trading_bot.log`.

## Running Tests / Verifying Without Real API Calls

The client and validators can also be exercised without hitting the network
by mocking `requests.Session.request`, which is useful for unit testing:

```python
from unittest.mock import patch, MagicMock
import cli

mock_resp = MagicMock(ok=True, status_code=200)
mock_resp.json.return_value = {"orderId": 1, "status": "FILLED", "executedQty": "0.01"}
with patch("requests.Session.request", return_value=mock_resp):
    cli.main(["--symbol", "BTCUSDT", "--side", "BUY", "--type", "MARKET", "--quantity", "0.01"])
```

Against a real Demo Trading account, simply run the commands under **Usage**
directly — no mocking needed.