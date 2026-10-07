import logging
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes
from config import settings
from trend_generator import async_generate_auto_daily_post, async_generate_single_ticker_post
from database import init_db, save_draft, update_post_status
from threads_poster import post_to_threads

# Configure Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def build_approval_keyboard(ticker: str, post_id: int) -> InlineKeyboardMarkup:
    """Creates inline action buttons embedding the database post_id."""
    keyboard = [
        [
            InlineKeyboardButton("✅ Approve & Post", callback_data=f"approve_{post_id}_{ticker}"),
            InlineKeyboardButton("🔄 Regenerate", callback_data=f"regen_{post_id}_{ticker}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject_{post_id}_{ticker}"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


async def send_automated_daily_draft(app: Application) -> None:
    """Scheduled task: Automatically selects the best stock and sends it to Telegram."""
    logger.info("⏰ Running automated daily stock selection...")

    try:
        ticker, draft_text = await async_generate_auto_daily_post()
        post_id = save_draft(ticker, draft_text)

        await app.bot.send_message(
            chat_id=settings.TELEGRAM_CHAT_ID,
            text=f"📊 **Daily Auto-Selection:** ${ticker}\n\n{draft_text}",
            reply_markup=build_approval_keyboard(ticker, post_id),
            parse_mode="Markdown"
        )
        logger.info(f"✅ Automated draft sent for ${ticker} [Post ID: {post_id}]")

    except Exception as e:
        logger.error(f"Failed to generate automated daily draft: {e}")
        await app.bot.send_message(
            chat_id=settings.TELEGRAM_CHAT_ID,
            text=f"❌ Failed to run daily automated draft picker: {e}"
        )


async def setup_scheduler(app: Application) -> None:
    """Runs after application is initialized and event loop is active."""
    scheduler = AsyncIOScheduler()
    
    # Run daily at 09:00 AM local time
    scheduler.add_job(
        send_automated_daily_draft,
        trigger="cron",
        hour=9,
        minute=0,
        args=[app]
    )
    
    scheduler.start()
    app.bot_data["scheduler"] = scheduler
    logger.info("⏰ APScheduler initialized and active!")


async def shutdown_scheduler(app: Application) -> None:
    """Shuts down scheduler gracefully on bot exit."""
    scheduler = app.bot_data.get("scheduler")
    if scheduler and scheduler.running:
        scheduler.shutdown()
        logger.info("⏰ APScheduler shut down.")


async def handle_button_click(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles Approve, Reject, and Regenerate button interactions."""
    query = update.callback_query
    await query.answer()

    data_parts = query.data.split("_")
    action = data_parts[0]
    post_id = int(data_parts[1])
    ticker = data_parts[2]

    if action == "approve":
        message_lines = query.message.text.split("\n\n")
        draft_text = message_lines[-1] if len(message_lines) > 1 else query.message.text

        await query.edit_message_text(f"🚀 Publishing ${ticker} draft to Threads...")

        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, post_to_threads, draft_text)

            update_post_status(post_id, "PUBLISHED")
            
            status_text = (
                f"{query.message.text}\n\n"
                f"🟢 **PUBLISHED (${ticker}) [ID: {post_id}]** — Posted live to Threads!"
            )
            await query.edit_message_text(text=status_text)

        except Exception as e:
            logger.error(f"Failed to post to Threads for {ticker}: {e}")
            await query.edit_message_text(
                text=f"{query.message.text}\n\n❌ **ERROR publishing (${ticker})**: {e}",
                reply_markup=build_approval_keyboard(ticker, post_id)
            )

    elif action == "reject":
        update_post_status(post_id, "REJECTED")
        status_text = (
            f"{query.message.text}\n\n"
            f"🔴 **REJECTED (${ticker}) [ID: {post_id}]** — Draft marked as rejected."
        )
        await query.edit_message_text(text=status_text)

    elif action == "regen":
        update_post_status(post_id, "REJECTED")
        await query.edit_message_text(f"🔄 Regenerating fresh AI draft for ${ticker}...")

        try:
            new_draft = await async_generate_single_ticker_post(ticker)
            new_post_id = save_draft(ticker, new_draft)
            
            await query.edit_message_text(
                text=new_draft,
                reply_markup=build_approval_keyboard(ticker, new_post_id)
            )
        except Exception as e:
            logger.error(f"Error regenerating draft for {ticker}: {e}")
            await query.edit_message_text(
                text=f"❌ Failed to regenerate draft for ${ticker}."
            )


async def pick_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manual command trigger: /pick or /draft evaluates market and picks the best stock."""
    if not update.effective_message:
        return

    status_msg = await update.effective_message.reply_text(
        "🧠 Evaluating watchlist stocks to find today's best setup..."
    )

    try:
        ticker, draft_text = await async_generate_auto_daily_post()
        post_id = save_draft(ticker, draft_text)

        await context.bot.send_message(
            chat_id=settings.TELEGRAM_CHAT_ID,
            text=f"📊 **Top Selected Stock:** ${ticker}\n\n{draft_text}",
            reply_markup=build_approval_keyboard(ticker, post_id)
        )
        await status_msg.delete()

    except Exception as e:
        logger.error(f"Error in auto pick: {e}")
        await update.effective_message.reply_text(f"❌ Failed to generate auto pick: {e}")


def main() -> None:
    init_db()

    app = (
        Application.builder()
        .token(settings.TELEGRAM_BOT_TOKEN.get_secret_value())
        .post_init(setup_scheduler)
        .post_shutdown(shutdown_scheduler)
        .build()
    )

    # Handlers
    app.add_handler(CommandHandler("pick", pick_command))
    app.add_handler(CommandHandler("draft", pick_command))
    app.add_handler(CallbackQueryHandler(handle_button_click))

    print("🤖 Telegram Bot active!")
    print("⏰ Daily draft scheduled for 09:00 AM via post_init hook.")
    print("💡 Send /pick or /draft in Telegram to run a manual test anytime.")
    
    app.run_polling()


if __name__ == "__main__":
    main()