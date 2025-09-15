import os
import re
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# v-- NEW IMPORTS --v
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
# ^-- NEW IMPORTS --^

# Load environment variables from .env
load_dotenv()
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")

# Initialize the Bolt app with your Slack tokens
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

# Initialize the Gemini LLM
try:
    # This is the NEW, fixed line:
    # This line uses the high-quota "Flash" model:
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest", temperature=0.3)
    print("Gemini model loaded successfully.")
except Exception as e:
    print(f"Error loading Gemini model: {e}")
    llm = None

# This is the "persona" we give our bot.
# It focuses the generalist model on its specific job.
SYSTEM_PROMPT = """
You are a helpful and expert programming assistant.
Your specialty is answering questions about Python.
Please provide clear, concise answers.
When you include code examples,
ALWAYS format them using Slack's markdown for code blocks
(e.g., ```python\nprint("Hello")\n```).
"""

# This event listener fires when the bot is @mentioned
@app.event("app_mention")
def handle_mention(event, say):
    
    # Get the user's question, removing the @mention part
    text = event["text"]
    user_question = re.sub(f"<@.*?>", "", text).strip()

    # Get the thread timestamp to reply in a thread
    thread_ts = event.get("thread_ts", event["ts"])

    if not user_question:
        say("Hi there! Mention me with a Python question and I'll try to answer it.", thread_ts=thread_ts)
        return

    if llm is None:
        say("Sorry, the AI model isn't available right now. Please check the logs.", thread_ts=thread_ts)
        return
        
    # Acknowledge the question immediately
    say("Thanks! I'm thinking about that...", thread_ts=thread_ts)

    try:
        print(f"User question: {user_question}")

        # Send the system prompt and user question to Gemini
        response = llm.invoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user_question)
        ])
        
        answer = response.content

        print("Got answer from Gemini. Sending to Slack.")
        
        # Send the answer using Block Kit for best formatting
        # The "mrkdwn" block type will correctly render the
        # ```python ... ``` code blocks.
        say(
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": answer
                    }
                }
            ],
            thread_ts=thread_ts
        )
    except Exception as e:
        print(f"Error: {e}")
        say(f"Sorry, I ran into an error trying to answer that: {e}", thread_ts=thread_ts)

# --- Start the app ---
if __name__ == "__main__":
    print("⚡️ Bolt app is running...")
    # SocketModeHandler uses your App-Level Token
    handler = SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN"))
    handler.start()