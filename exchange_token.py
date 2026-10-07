### Need to run every 60 days to get new THREADS ACCESS TOKEN which expires every 60 days
import os
import requests
from dotenv import load_dotenv

load_dotenv()

APP_SECRET = os.getenv("THREADS_APP_SECRET")
SHORT_TOKEN = os.getenv("THREADS_ACCESS_TOKEN")

if not APP_SECRET or not SHORT_TOKEN:
    print("Error: Make sure THREADS_APP_SECRET and THREADS_ACCESS_TOKEN exist in .env")
    exit()

# Meta Threads endpoint to trade short-lived for 60-day token
url = "https://graph.threads.net/access_token"
params = {
    "grant_type": "th_exchange_token",
    "client_secret": APP_SECRET,
    "access_token": SHORT_TOKEN
}

print("Exchanging short-lived token for a 60-day token...")
response = requests.get(url, params=params).json()

if "access_token" in response:
    new_token = response["access_token"]
    print("\nSuccess! Here is your 60-day Long-Lived Token:\n")
    print(new_token)
    print("\nCopy this new token string and replace THREADS_ACCESS_TOKEN in your .env file.")
else:
    print("\nError exchanging token:", response)