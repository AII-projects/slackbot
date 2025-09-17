import os
from celery import Celery
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from database import SessionLocal, RequestLog

load_dotenv()

# Initialize Celery
celery = Celery('tasks', broker=os.environ.get("CELERY_BROKER_URL"))

# Initialize components needed by the worker
slack_client = WebClient(token=os.environ.get("SLACK_BOT_TOKEN"))
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest", temperature=0.3)
SYSTEM_PROMPT = """
You are a helpful and expert programming assistant. Your specialty is answering questions about Python. Please provide clear, concise answers. When you include code examples, ALWAYS format them using Slack's markdown for code blocks (e.g., ```python\nprint("Hello")\n```).
"""

@celery.task
def process_slack_request(user_id, user_question, thread_ts, channel_id):
    db = SessionLocal()
    log_entry = None
    try:
        response = llm.invoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user_question)
        ])
        
        answer = response.content
        input_tokens = response.usage_metadata.get("input_tokens", 0)
        output_tokens = response.usage_metadata.get("output_tokens", 0)

        log_entry = RequestLog(
            slack_user_id=user_id,
            user_question=user_question,
            gemini_answer=answer,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            was_successful=True
        )

        slack_client.chat_postMessage(
            channel=channel_id,
            thread_ts=thread_ts,
            text=answer
        )
    except Exception as e:
        error_str = str(e)
        print(f"WORKER ERROR: {error_str}")
        log_entry = RequestLog(
            slack_user_id=user_id,
            user_question=user_question,
            was_successful=False,
            error_message=error_str
        )
        try:
            slack_client.chat_postMessage(
                channel=channel_id,
                thread_ts=thread_ts,
                text=f"Sorry, I ran into an error trying to answer that."
            )
        except SlackApiError as slack_err:
            print(f"WORKER ERROR: Failed to send error message to Slack: {slack_err}")
    finally:
        if log_entry:
            db.add(log_entry)
            db.commit()
        db.close()