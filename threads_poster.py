import os
import time
import requests
from dotenv import load_dotenv

# Load credentials from .env
load_dotenv()

USER_ID = os.getenv("THREADS_APP_ID")
TOKEN = os.getenv("THREADS_ACCESS_TOKEN")

def post_to_threads(text_content):
    if not USER_ID or not TOKEN:
        print("Missing THREADS_USER_ID or THREADS_ACCESS_TOKEN in environment variables.")
        return

    # STEP A: Create the media/text container
    container_url = f"https://graph.threads.net/v1.0/{USER_ID}/threads"
    container_payload = {
        "media_type": "TEXT",
        "text": text_content,
        "access_token": TOKEN
    }

    print("Creating Threads draft container...")
    res_container = requests.post(container_url, data=container_payload).json()

    if "id" not in res_container:
        print(f"Error creating container: {res_container}")
        return

    creation_id = res_container["id"]
    print(f"Container created! Container ID: {creation_id}")

    # Small pause to allow Meta's backend to process the container
    time.sleep(2)

    # STEP B: Publish the container live
    publish_url = f"https://graph.threads.net/v1.0/{USER_ID}/threads_publish"
    publish_payload = {
        "creation_id": creation_id,
        "access_token": TOKEN
    }

    print("Publishing to Threads...")
    res_publish = requests.post(publish_url, data=publish_payload).json()

    if "id" in res_publish:
        print(f"Success! Published post ID: {res_publish['id']}")
    else:
        print(f"Failed to publish: {res_publish}")

if __name__ == "__main__":
    test_message = "Hello from automated Python script! 🚀"
    post_to_threads(test_message)