import asyncio
import logging
import httpx
from config import settings
from trend_generator import async_generate_auto_daily_post

# Configure logging for daily runs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

GRAPH_API_URL = "https://graph.threads.net/v1.0"
THREADS_CHAR_LIMIT = 500


async def post_to_threads(text_content: str) -> str:
    """Publishes a text post to Threads using Meta's official Graph API."""
    access_token = settings.THREADS_ACCESS_TOKEN.get_secret_value()
    user_id = settings.THREADS_APP_ID

    if not access_token or not settings.THREADS_USER_ID:
        raise ValueError("Missing THREADS_ACCESS_TOKEN or THREADS_USER_ID in settings.")

    async with httpx.AsyncClient() as client:
        # Step 1: Create Container
        container_res = await client.post(
            f"{GRAPH_API_URL}/{user_id}/threads",
            data={
                "media_type": "TEXT",
                "text": text_content,
                "access_token": access_token
            },
            timeout=15.0
        )
        container_res.raise_for_status()
        creation_id = container_res.json().get("id")

        # Step 2: Publish Container
        publish_res = await client.post(
            f"{GRAPH_API_URL}/{user_id}/threads_publish",
            data={
                "creation_id": creation_id,
                "access_token": access_token
            },
            timeout=15.0
        )
        publish_res.raise_for_status()
        return publish_res.json().get("id")


def validate_and_format_post(content: str) -> str:
    """Enforces Threads' 500-character limit."""
    content = content.strip()
    if len(content) > THREADS_CHAR_LIMIT:
        logger.warning(f"⚠️ Truncating post ({len(content)} chars -> {THREADS_CHAR_LIMIT}).")
        content = content[: THREADS_CHAR_LIMIT - 3].strip() + "..."
    return content


async def run_daily_job():
    """Main orchestrator function for the headless automated pipeline."""
    logger.info("🚀 Starting automated morning post job...")
    try:
        # 1. Fetch S&P 500 top dip and generate draft via Gemini
        ticker, raw_content = await async_generate_auto_daily_post()
        logger.info(f"📌 Picked ${ticker}:\n{raw_content}\n")

        # 2. Validate length
        final_content = validate_and_format_post(raw_content)

        # 3. Post to Threads
        post_id = await post_to_threads(final_content)
        logger.info(f"✅ Successfully posted live to Threads! [ID: {post_id}]")

    except Exception as e:
        logger.error(f"❌ Failed to complete daily post job: {e}", exc_info=True)


if __name__ == "__main__":
    # Allows you to trigger the whole job by running: python threads_poster.py
    asyncio.run(run_daily_job())