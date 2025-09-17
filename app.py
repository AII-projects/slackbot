import os
import re
from dotenv import load_dotenv
from flask import Flask, request
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from datetime import datetime, timedelta
from sqlalchemy import func

from database import SessionLocal, RequestLog, Setting
from tasks import process_slack_request

load_dotenv()

# --- Caching and App Setup ---
APP_SETTINGS = {}

def load_settings_into_cache():
    db = SessionLocal()
    try:
        settings = db.query(Setting).all()
        for setting in settings:
            # Convert to integer if possible, otherwise keep as string
            try:
                APP_SETTINGS[setting.setting_name] = int(setting.setting_value)
            except ValueError:
                APP_SETTINGS[setting.setting_name] = setting.setting_value
        print("Settings loaded into cache:", APP_SETTINGS)
    finally:
        db.close()

app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET")
)
flask_app = Flask(__name__)
handler = SlackRequestHandler(app)

# --- The Bot's Main Logic ---
@app.event("app_mention")
def handle_mention(event, say):
    text = event["text"]
    user_question = re.sub(f"<@.*?>", "", text).strip()
    thread_ts = event.get("thread_ts", event["ts"])
    user_id = event["user"]
    channel_id = event["channel"]

    # --- Corner Case 1: File Upload ---
    if event.get("files"):
        say(
            text="Thanks for the file! I'm currently set up to answer text-based questions. The ability to analyze files and images is coming soon!",
            thread_ts=thread_ts
        )
        return

    # --- Corner Case 2: Daily User Limit ---
    db = SessionLocal()
    try:
        limit = APP_SETTINGS.get('daily_user_limit', 25)
        window_seconds = APP_SETTINGS.get('limit_window_seconds', 86400)
        time_window = datetime.utcnow() - timedelta(seconds=window_seconds)

        usage_count = db.query(func.count(RequestLog.id)).filter(
            RequestLog.slack_user_id == user_id,
            RequestLog.timestamp >= time_window
        ).scalar()
        
        if usage_count >= limit:
            print(f"User {user_id} has reached their daily limit of {limit}.")
            say(
                text=f"You have reached your daily limit of {limit} requests. Please try again tomorrow.",
                thread_ts=thread_ts
            )
            return
    finally:
        db.close()

    # --- If all checks pass, enqueue the job ---
    if user_question:
        say(text="Thanks! I'm thinking about that...", thread_ts=thread_ts)
        process_slack_request.delay(user_id, user_question, thread_ts, channel_id)
    else:
        say(text="Hi there! Mention me with a Python question and I'll try to answer it.", thread_ts=thread_ts)

@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)

if __name__ == "__main__":
    # This block is for local testing if you don't use waitress
    # Not recommended for production
    load_settings_into_cache()
    flask_app.run(port=8000)