import asyncio
from telegram import Bot
from config import settings

async def main():
    # instantiate bot using validated secret from config
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN.get_secret_value())

    chat_id = settings.TELEGRAM_CHAT_ID

    print("Sending test message to Telegram...")
    await bot.send_message(
        chat_id=chat_id,
        text="🚀 **financial-ai-bot** system check: Telegram integration connected successfully!"
        parse_mode="Markdown"
    )
    print("✅ Message sent! Check your Telegram chat.")

if __name__ == "__main__":
    asyncio.run(main())