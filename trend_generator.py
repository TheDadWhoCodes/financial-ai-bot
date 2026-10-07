import asyncio
import json
import pandas as pd
import time
import yfinance as yf
from google import genai
from google.genai import errors, types
from config import settings

# Initialize Gemini client
client = genai.Client(api_key=settings.GEMINI_API_KEY.get_secret_value())

def get_sp500_tickers() -> list[str]:
    """Dynamically fetches the current list of S&P 500 tickers from Wikipedia."""
    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        tables = pd.read_html(url)
        df = tables[0]
        tickers = df["Symbol"].str.replace(".", "-", regex=False).tolist()
        return tickers
    except Exception as e:
        print(f"⚠️ Could not fetch S&P 500 list, falling back to static list: {e}")
        return [    "NVDA", "AAPL", "MSFT", "TSLA", "AMD", "AMZN", "GOOG", "ASML", "VOO", "META", "SCHG", "NFLX", "COST", "MA"]

def scan_market_for_top_dips(limit: int = 5) -> list[dict]:
    """Scans S&P 500 stocks, finds top losers, and fetches their valuation metrics."""
    tickers = get_sp500_tickers()
    print(f"🔍 Batch-scanning {len(tickers)} S&P 500 stocks...")

    # Fast batch download using yfinance
    data = yf.download(tickers, period="2d", group_by="ticker", progress=False)

    candidates = []
    for symbol in tickers:
        try:
            stock_data = data[symbol]
            if len(stock_data) < 2:
                continue

            prev_close = stock_data["Close"].iloc[-2]
            current_price = stock_data["Close"].iloc[-1]

            if prev_close > 0:
                change_pct = round(((current_price - prev_close) / prev_close) * 100, 2)
                # Filter strictly for stocks down at least 1.0%
                if change_pct < -1.0:
                    candidates.append({
                        "symbol": symbol,
                        "price": current_price,
                        "change_pct": change_pct
                    })
        except Exception:
            continue

    # Sort candidates by biggest drop first
    candidates.sort(key=lambda x: x["change_pct"])
    top_candidates = candidates[:limit]

    # Fetch detailed P/E and summary for only the top selected candidates
    detailed_candidates = []
    for item in top_candidates:
        symbol = item["symbol"]
        try:
            info = yf.Ticker(symbol).info
            forward_pe = info.get("forwardPE")
            trailing_pe = info.get("trailingPE")

            pe_summary = []
            if trailing_pe:
                pe_summary.append(f"Trailing P/E: {round(trailing_pe, 2)}")
            if forward_pe:
                pe_summary.append(f"Forward P/E: {round(forward_pe, 2)}")

            detailed_candidates.append({
                "symbol": symbol,
                "name": info.get("shortName", symbol),
                "price": f"${item['price']:.2f}",
                "change_pct": item["change_pct"],
                "pe_ratio": ", ".join(pe_summary) if pe_summary else "N/A",
                "summary": info.get("longBusinessSummary", "")[:300]
            })
        except Exception as e:
            print(f"⚠️ Error enriching data for {symbol}: {e}")

    return detailed_candidates

# # Broadened watchlist for dip scanning
# WATCHLIST = [
    # "NVDA", "AAPL", "MSFT", "TSLA", "AMD", "AMZN", 
    # "GOOG", "ASML", "VOO", "META", "SCHG", "NFLX", "COST", "MA"
# ]

# Updated valid Gemini models
MODELS = ["gemini-3.8-flash", "gemini-3.1-flash-lite", "gemini-2.5-flash-lite"]


def pick_best_dip_and_draft(dip_candidates: list[dict]) -> tuple[str, str] | None:
    """Evaluates stock dip candidates and generates a concise post for Threads/X."""
    
    stocks_summary = "\n".join([
        f"- {s['symbol']} ({s['name']}): Price={s['price']}, Daily Change={s['change_pct']}%, Valuation=[{s['pe_ratio']}]"
        for s in dip_candidates
    ])

    prompt = f"""
    You are an expert financial commentator writing for X and Threads for retail/high-street investors.

    Review these stocks that have recently dipped or pulled back in value:
    {stocks_summary}

    TASK:
    1. Choose the single most attractive buying opportunity or interesting dip set up among these candidates.
    2. Write a concise, highly readable post following these strict rules:
       - No introductory headers, role labels (e.g. "Ed:", "Bot:"), or conversational fluff. Start directly with the post content.
       - Explain simply (ELI5 tone), no jargon.
       - One short analytical hook sentence (curiosity-driven, clean, no dramatic overhype or massive icons).
       - 1 to 2 sentences explaining why this dip/pullback makes it attractive right now from a valuation or setup standpoint.
       - End with an open-ended question to encourage replies and discussion.
       - Total output MUST be under 275 characters.

    OUTPUT FORMAT:
    Respond strictly in JSON format with two keys:
    {{
        "selected_ticker": "TICKER_SYMBOL",
        "post_content": "Your full post text here"
    }}
    """

    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
    )

    # Use standard gemini-2.5-flash-lite
    MODELS = ["gemini-3.8-flash", "gemini-3.1-flash-lite", "gemini-2.5-flash-lite"]
    max_retries = 3
    delay = 3

    for attempt in range(max_retries):
        current_model = MODELS[attempt % len(MODELS)]
        try:
            response = client.models.generate_content(
                model=current_model,
                contents=prompt,
                config=config,
            )
            
            raw_text = response.text.strip()
            
            # Clean off Markdown fences if present
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            if raw_text.startswith("```"):
                raw_text = raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
            raw_text = raw_text.strip()

            result = json.loads(raw_text)
            return result["selected_ticker"], result["post_content"]

        except errors.APIError as e:
            print(f"❌ Gemini API Error ({current_model}): {e}")
            if getattr(e, 'code', None) in [503, 429] and attempt < max_retries - 1:
                time.sleep(delay)
                delay *= 2
        except Exception as e:
            print(f"❌ JSON/Parsing Error on attempt {attempt + 1}: {e}")
            print(f"   Raw output was: {getattr(response, 'text', 'None')}")
            if attempt < max_retries - 1:
                time.sleep(delay)
                delay *= 2

    return None


def generate_auto_daily_post() -> tuple[str, str]:
    """Scans S&P 500 for top daily dips and generates the daily post draft."""

    print("🔍 Scanning S&P 500 for top daily dips...")
    dip_candidates = scan_market_for_top_dips(limit=5)

    if not dip_candidates:
        raise ValueError("No eligible dip candidates found today.")

    print(f"📉 Found {len(dip_candidates)} top market dips: {[s['symbol'] for s in dip_candidates]}")

    print("🤖 Gemini is selecting the best dip opportunity...")
    res = pick_best_dip_and_draft(dip_candidates)

    if not res:
        raise ValueError("Failed to evaluate and pick a stock draft.")

    return res  # returns ("TICKER", "Post content...")


async def async_generate_auto_daily_post() -> tuple[str, str]:
    """Async wrapper for headless runner execution."""
    return await asyncio.to_thread(generate_auto_daily_post)