import os
import json
import random
import threading
import telebot
import tweepy
import schedule
import time
from dotenv import load_dotenv

load_dotenv()

bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
twitter_bearer_token = os.getenv('X_BEARER_TOKEN')

client = tweepy.Client(bearer_token=twitter_bearer_token)

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
            user = client.get_user(username=username)
            tweets = client.get_users_tweets(user.data.id, max_results=10)

            for tweet in tweets.data:
                tweet_id = tweet.id
                if tweets.data is None:
                    print(f"No tweets found for {username}")
                    continue

                if last_tweet_ids.get(username) == tweet_id:
                    break

                data = {
                    "id": tweet_id,
                    "url": f"https://x.com/{username}/status/{tweet_id}",
                    "username": username
                }
                tweets_data.append(data)

                if len(tweets_data) == 0:
                    last_tweet_ids[username] = tweet_id

            all_tweets_data[username] = tweets_data

        except tweepy.errors.TweepyException as e:
            print(f"Error fetching tweets for {username}: {e}")

    # Save the updated last tweet IDs
    save_last_tweet_ids(last_tweet_ids)

    # Send tweets to Telegram
    if all_tweets_data:
        send_tweets_to_telegram(all_tweets_data)


def send_tweets_to_telegram(tweets_data):
    with open('advertisement.json', 'r', encoding='utf-8-sig') as ads_file:
        ads_data = json.loads(ads_file.read())

    random_ad = random.choice(ads_data["adsList"])
    templates = load_templates()
    enabled_groups = load_enabled_groups()

    for chat_id, group_info in enabled_groups.items():
        if group_info.get("enabled", False):
            ad_message = f"Ad: [{random_ad['text']}]({random_ad['link']})"
            title = "🚀 New tweets found!\n\n"
            message = ""

            for username, profiles in tweets_data.items():
                for profile in profiles:
                    if 'id' in profile and 'username' in profile:
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


def load_templates():
    try:
        with open(templates_file, 'r') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_templates(templates):
    with open(templates_file, 'w') as file:
        json.dump(templates, file)


def load_admins():
    try:
        with open(admins_file, 'r') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


admins = load_admins()


def load_selected_group():
    try:
        with open('selected_groups.json', 'r') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


selected_groups = load_selected_group()


def save_admins(admins):
    with open(admins_file, 'w') as file:
        json.dump(admins, file)


def is_group_admin(message: telebot.types.Message):
    user_id = message.from_user.id
    chat_member = bot.get_chat_member(message.chat.id, user_id)
    if chat_member.status in ['administrator', 'creator']:
        return True


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


def get_saved_message_id(chat_id):
    message_ids = load_message_ids()
    return message_ids.get(str(chat_id))


def load_message_ids():
    try:
        with open(message_ids_file, 'r') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_message_ids(message_ids):
    with open(message_ids_file, 'w') as file:
        json.dump(message_ids, file)


# Function to run the Twitter scraper repeatedly
def run_twitter_scraper():
    schedule.every(1).minute.do(twitter_scraper)
    while True:
        schedule.run_pending()
        time.sleep(1)


# Create a thread for running the Twitter scraper
twitter_thread = threading.Thread(target=run_twitter_scraper)
twitter_thread.start()

bot.polling(none_stop=True, timeout=123)
