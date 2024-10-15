import os
import json
import random
import threading

from schedule import every, run_pending
import telebot
import snscrape.modules.twitter as sntwitter
import requests
import time
from dotenv import load_dotenv

load_dotenv()

bot_token = os.getenv('TELEGRAM_BOT_TOKEN')

bot = telebot.TeleBot(bot_token)

# File path for storing data
enabled_groups_file = 'enabled_groups.json'
influencers_file = 'influencers.json'
templates_file = 'templates.json'
message_ids_file = 'message_ids.json'
admins_file = 'admins.json'
last_tweet_ids_file = 'last_tweet_ids.json'


def load_last_tweet_ids():
    try:
        with open(last_tweet_ids_file, 'r') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_last_tweet_ids(last_tweet_ids):
    with open(last_tweet_ids_file, 'w') as file:
        json.dump(last_tweet_ids, file)


def twitter_scraper():
    with open(influencers_file, 'r') as json_file:
        usernames = json.load(json_file)

    # Load last tweet IDs
    last_tweet_ids = load_last_tweet_ids()
    all_tweets_data = {}

    for username in usernames:
        tweets_data = []
        try:
            # Використовуємо пошук через username
            query = f"from:{username}"
            scraper = sntwitter.TwitterSearchScraper(query).get_items()

            for i, tweet in enumerate(scraper):
                if last_tweet_ids.get(username) == tweet.id:
                    break

                data = {
                    "id": tweet.id,
                    "url": tweet.url,
                    "username": username
                }
                tweets_data.append(data)

                if i == 0:
                    last_tweet_ids[username] = tweet.id

            all_tweets_data[username] = tweets_data

        except requests.exceptions.SSLError as e:
            print(f"SSL error while retrieving tweets for {username}: {e}")
            session = requests.Session()
            session.get(f'https://x.com/{username}', verify=False)

    # Save the updated last tweet IDs
    save_last_tweet_ids(last_tweet_ids)

    # Send tweets to Telegram
    if all_tweets_data:
        send_tweets_to_telegram(all_tweets_data)


def send_tweets_to_telegram(tweets_data):
    with open('advertisement.json', 'r', encoding='utf-8-sig') as ads_file:
        ads_data = json.loads(ads_file.read())

    random_ad = random.choice(ads_data["adsList"])
    enabled_groups = load_enabled_groups()

    for chat_id, group_info in enabled_groups.items():
        if group_info.get("enabled", False):
            ad_message = f"Ad: [{random_ad['text']}]({random_ad['link']})"
            title = "🚀 New tweets found!\n\n"
            message = ""

            for username, profiles in tweets_data.items():
                for profile in profiles:
                    url = profile['url']
                    message += f"[{profile['username']}]({url}) || "

            message = message.rstrip(" || ")

            if message:
                combined_message = title + message + '\n\n' + ad_message
                send_message_with_link(chat_id, combined_message)


def load_enabled_groups():
    try:
        with open(enabled_groups_file, 'r') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_enabled_groups(enabled_groups):
    with open(enabled_groups_file, 'w') as file:
        json.dump(enabled_groups, file)


def load_influencers():
    try:
        with open(influencers_file, 'r') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_influencers(influencers):
    with open(influencers_file, 'w') as file:
        json.dump(influencers, file)


def load_message_ids():
    try:
        with open(message_ids_file, 'r') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_message_ids(message_ids):
    with open(message_ids_file, 'w') as file:
        json.dump(message_ids, file)


def get_saved_message_id(chat_id):
    message_ids = load_message_ids()
    return message_ids.get(str(chat_id))


def send_message_with_link(chat_id, message):
    message_id = get_saved_message_id(chat_id)
    if message_id:
        bot.delete_message(chat_id, message_id)

    sent_message = bot.send_message(
        chat_id, message, parse_mode='Markdown', disable_web_page_preview=True)

    message_id = sent_message.message_id
    save_message_id(chat_id, message_id)


def save_message_id(chat_id, message_id):
    message_ids = load_message_ids()
    message_ids[str(chat_id)] = message_id
    save_message_ids(message_ids)


# Function to run the Twitter scraper repeatedly
def run_twitter_scraper():
    every(1).minute.do(twitter_scraper)
    while True:
        run_pending()
        time.sleep(1)


# Create a thread for running the Twitter scraper
twitter_thread = threading.Thread(target=run_twitter_scraper)
twitter_thread.start()

bot.polling(none_stop=True, timeout=123)
