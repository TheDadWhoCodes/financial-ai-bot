import asyncio
import os
import time
import json
import yfinance as yf
from google import genai
from google.genai import errors, types
from config import settings

client = genai.Client(api_key=settings.GEMINI_API_KEY.get_secret_value())

WATCHLIST = ["NVDA", "AAPL", "MSFT", "TSLA", "AMD", "AMZN", "GOOG", "ASML", "VOO"]
FREE_MODELS = ["gemini-3.1-flash-lite", "gemini-2.5-flash", "gemini-2.5-lite"]


def fetch_stock_mover(ticker_symbol: str) -> dict | None:
    """ Fetches comprehensive data for a popular stock using yfinance. """
    try:
        stock = yf.Ticker(ticker_symbol)
        info = stock.info

        # Extract valuation metrics
        price = info.get("currentPrice") or info.get("regularMarketPrice")
        forward_pe = info.get("forwardPE")
        trailing_pe = info.get("trailingPE")

        # Format metrics cleanly so Gemini isn't misled by a single consensus number
        pe_summary = []
        if trailing_pe:
            pe_summary.append(f"Trailing P/E: {round(trailing_pe, 2)}")
        if forward_pe:
            pe_summary.append(f"Forward P/E: {round(forward_pe, 2)}")

        pe_str = ", ".join(pe_summary) if pe_summary else "N/A"

        return {
            "symbol": ticker_symbol,
            "name": info.get("shortName", ticker_symbol),
            "price": f"${price}" if price else "N/A",
            "pe_ratio": pe_str,
            "summary": info.get("longBusinessSummary", "")[:300]
        }
    except Exception as e:
        print(f"⚠️ Error fetching data for {ticker_symbol}: {e}")
        return None


def pick_best_stock_and_draft(watchlist_data: list[dict]) -> tuple[str, str] | None:
    """Asks Gemini to evaluate all watchlist items, pick the most interesting buy, and generate a post."""
    
    # Format stock summary data for Gemini evaluation
    stocks_summary = "\n".join([
        f"- {s['symbol']} ({s['name']}): Price={s['price']}, Valuation=[{s['pe_ratio']}]"
        for s in watchlist_data
    ])

    prompt = f"""
    You are an expert financial commentator writing for X and Threads for retail/high-street investors.

    Review this watchlist data:
    {stocks_summary}

    TASK:
    1. Select the SINGLE stock that looks most attractive or has the most interesting setup for a retail investor today.
    2. Write a punchy, engaging post about it following these strict rules:
       - Explain it simply (Explain Like I'm 5 format).
       - Line 1 MUST be a strong, curiosity-driven hook.
       - Follow with 2 short bullet points on why it's attractive right now.
       - End with an open-ended question to drive reader replies.
       - Keep total post under 280 characters.

    OUTPUT FORMAT:
    Respond strictly in JSON format with two keys:
    {{
        "selected_ticker": "TICKER_SYMBOL",
        "post_content": "Your full draft text here"
    }}
    """

    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
    )

    max_retries = 3
    delay = 5

    for attempt in range(max_retries):
        current_model = FREE_MODELS[attempt % len(FREE_MODELS)]
        try:
            response = client.models.generate_content(
                model=current_model,
                contents=prompt,
                config=config,
            )
            result = json.loads(response.text)
            return result["selected_ticker"], result["post_content"]

        except errors.APIError as e:
            if getattr(e, 'code', None) in [503, 429] and attempt < max_retries - 1:
                time.sleep(delay)
                delay *= 2
            else:
                print(f"❌ Gemini API Error: {e}")
                return None
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(delay)
                delay *= 2
            else:
                print(f"❌ Failed after retries: {e}")
                return None


def generate_auto_daily_post() -> tuple[str, str]:
    """Scans all stocks in WATCHLIST, picks the best setup, and returns (ticker, draft_text)."""
    watchlist_data = []
    
    print("🔍 Fetching data for watchlist stocks...")
    for ticker in WATCHLIST:
        data = fetch_stock_mover(ticker)
        if data:
            watchlist_data.append(data)
        time.sleep(0.5)

    if not watchlist_data:
        raise ValueError("Could not fetch data for any watchlist stocks.")

    print("🤖 Evaluating market setups and picking the best ticker...")
    res = pick_best_stock_and_draft(watchlist_data)
    
    if not res:
        raise ValueError("Failed to evaluate and pick a stock draft.")

    return res  # returns tuple: ("NVDA", "Draft content...")


async def async_generate_auto_daily_post() -> tuple[str, str]:
    """Async wrapper for the auto picker."""
    return await asyncio.to_thread(generate_auto_daily_post)


def generate_single_ticker_post(ticker_symbol: str = "NVDA") -> str:
    """Helper function to fetch market data and return a single generated post for Telegram."""
    stock_data = fetch_stock_mover(ticker_symbol)
    if not stock_data:
        return f"⚠️ Could not fetch market data for ${ticker_symbol}."
    
    # Simple fallback using original logic
    return f"Market update on ${ticker_symbol} coming soon!"


async def async_generate_single_ticker_post(ticker_symbol: str = "NVDA") -> str:
    return await asyncio.to_thread(generate_single_ticker_post, ticker_symbol)