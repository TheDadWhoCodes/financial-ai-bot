import os
import time
import yfinance as yf
from google import genai
from google.genai import errors, types

# 1. Configure your free Gemini API Key
GEMINI_API_KEY = "AQ.Ab8RN6KL21cpFi7UE2jjS81n5oewoakBP4XZZtDxNa5u_G2Y8Q"
client = genai.Client(api_key=GEMINI_API_KEY)

# A watchlist of trending market tickers to analyze
WATCHLIST = ["NVDA", "AAPL", "MSFT", "TSLA", "AMD", "AMZN", "GOOG", "ASML", "VOO"]

# Fallback pool of free-tier models in case one is busy (503)
FREE_MODELS = ["gemini-3.8-flash", "gemini-3.5-flash", "gemini-3.1-flash-lite"]

def fetch_stock_mover(ticker_symbol):
    """ Fetches key data for a popular stock using yfinance. """
    try:
        stock = yf.Ticker(ticker_symbol)
        info = stock.info

        return {
            "symbol": ticker_symbol,
            "name": info.get("shortName", ticker_symbol),
            "price": info.get("currentPrice", info.get("regularMarketPrice")),
            "pe_ratio": info.get("forwardPE"),
            "summary": info.get("longBusinessSummary", "")[:300]
        }
    except Exception as e:
        print(f"⚠️ Error fetching data for {ticker_symbol}: {e}")
        return None

def generate_social_post(stock_data):
    """Generates post with AFC explicitly disabled and automatic model fallback for 503 errors."""
    
    prompt = f"""
    You are an expert financial commentator writing for X (Twitter) and Threads.
    
    Analyze this market data:
    Stock: {stock_data['name']} (${stock_data['symbol']})
    Current Price: ${stock_data['price']}
    Forward P/E Ratio: {stock_data['pe_ratio']}
    Business Snippet: {stock_data['summary']}

    Write a punchy, engaging post following these strict rules:
    1. Line 1 MUST be a strong, curiosity-driven hook.
    2. Follow with 2 short bullet points highlighting why it's interesting or looking attractive.
    3. End with an open-ended question to drive reader replies.
    4. Keep the total post under 280 characters.
    5. Add a subtle line: "Educational only, DYOR."

    content should be understandable like a 'explain like i'm 5' format, and aimed at the high street investors
    """

    # Explicit config disabling AFC to eliminate SDK warnings
    config = types.GenerateContentConfig(
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
    )

    max_retries = 3
    delay = 3

    for attempt in range(max_retries):
        # Rotate model string on retries if the main model is under heavy load
        current_model = FREE_MODELS[attempt % len(FREE_MODELS)]
        try:
            response = client.models.generate_content(
                model=current_model,
                contents=prompt,
                config=config,
            )
            return response.text

        except errors.APIError as e:
            if getattr(e, 'code', None) in [503, 429] and attempt < max_retries - 1:
                print(f"⚠️ {current_model} busy ({e.code}). Retrying with fallback in {delay}s...")
                time.sleep(delay)
                delay *= 2
            else:
                print(f"❌ Gemini API Error: {e}")
                return None
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"⚠️ Unexpected error ({e}). Retrying in {delay}s...")
                time.sleep(delay)
                delay *= 2
            else:
                print(f"❌ Failed after retries: {e}")
                return None

if __name__ == "__main__":
    print("🚀 Starting Daily Trend Generator...\n")

    for ticker in WATCHLIST:
        print("🔍 Fetching market data...")
        stock_data = fetch_stock_mover(ticker)

        if stock_data:
            print("🤖 Generating AI post draft...\n")
            post_draft = generate_social_post(stock_data)
    
            print("----------------------------------------")
            print(post_draft)
            print("----------------------------------------")

        # RATE LIMIT GUARD: Pause for 4 seconds between requests
        # (Keeps you safely under Gemini's 15 requests per minute limit)
        print("⏳ Pausing 4 seconds to respect API rate limits...\n")
        time.sleep(4)

    print("✅ Completed processing watchlist!")