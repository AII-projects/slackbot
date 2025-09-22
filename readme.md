# Slack Python Q&A Bot

This project is an intelligent Slack bot that answers Python-related questions. It is built with a robust, scalable backend architecture designed to handle requests asynchronously, ensuring high availability and a responsive user experience. The bot leverages Google's Gemini API for its natural language processing capabilities.

---

## Architecture

The application is designed with a decoupled architecture to separate the fast-responding web server from the slower, resource-intensive AI processing tasks. This is achieved using a message queue (RabbitMQ) and background workers (Celery).

**Data Flow:**
1.  A user **@mentions** the bot in a Slack channel.
2.  Slack sends an **HTTP Webhook** to our public URL.
3.  The **Flask Web Server** receives the request.
    * It performs quick validation checks (file uploads, user's daily limit).
    * If checks pass, it places a "job" onto the **RabbitMQ Queue**.
    * It immediately responds `200 OK` to Slack.
4.  A **Celery Worker** process, listening to the queue, picks up the job.
5.  The Worker calls the **Google Gemini API** to generate an answer.
6.  The Worker logs the transaction details to the **PostgreSQL Database**.
7.  The Worker sends the final answer back to the correct Slack thread via the **Slack Web API**.


---

## Technology Stack

* **Backend:** Python 3
* **Web Framework:** Flask
* **Slack Integration:** `slack-bolt`
* **Web Server:** Waitress (for Windows dev) / Gunicorn (for Linux production)
* **Database:** PostgreSQL
* **Database Toolkit (ORM):** SQLAlchemy
* **Message Broker:** RabbitMQ
* **Task Queue:** Celery with Eventlet (for Windows compatibility)
* **Containerization:** Docker & Docker Compose
* **LLM:** Google Gemini API (`gemini-1.5-flash-latest`)
* **Local Tunneling:** ngrok (for local deployment)

---

## Features

* **Q&A Functionality:** Responds to direct @mentions with answers to Python coding questions.
* **Asynchronous Processing:** Uses Celery and RabbitMQ to queue and process requests, ensuring the bot remains responsive during high traffic.
* **Persistent Logging:** All requests, answers, and API usage stats are logged to a PostgreSQL database.
* **Configurable User Limits:** Daily request limits for each user are stored in the database and can be configured without changing the code.
* **Settings Caching:** Application settings are cached in memory on startup to reduce database queries on every request.
* **Graceful Error Handling:** Politely rejects requests with file uploads (Phase 1) and notifies users when they have reached their daily limit.

---

## Setup and Installation (for Local Development)

### Prerequisites

* Python 3.8+
* Docker & Docker Compose
* `ngrok` account and CLI tool
* API keys/secrets for:
    * Slack (Bot Token & Signing Secret)
    * Google AI Studio (Gemini API Key)

### 1. Configuration

Before running the application, you need to set up your environment variables. Create a file named `.env` in the root of the project directory and add the following key-value pairs:

* **`SLACK_BOT_TOKEN`**: Your bot's token, starting with `xoxb-`. Found in your Slack App's **OAuth & Permissions** section.
* **`SLACK_SIGNING_SECRET`**: Your app's Signing Secret. Found in your Slack App's **Basic Information** section.
* **`GOOGLE_API_KEY`**: Your API key for the Google Gemini service from Google AI Studio.
* **`DB_USER`**: The username for your PostgreSQL database. (Default: `botuser`)
* **`DB_PASSWORD`**: The password for your PostgreSQL database. (Default: `botpassword`)
* **`DB_HOST`**: The host where your database is running. (Default: `localhost`)
* **`DB_PORT`**: The port for the database connection. (Default: `5432`)
* **`DB_NAME`**: The name of the database to use. (Default: `slackbot_db`)
* **`CELERY_BROKER_URL`**: The connection URL for the RabbitMQ message broker. (Default: `amqp://guest:guest@localhost:5672//`)

### 2. Running the Application

This application requires multiple processes running simultaneously. You will need **three separate terminals**.

#### One-Time Setup

1.  **Install Python Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
2.  **Start Backend Services:** Make sure Docker Desktop is running, then start the PostgreSQL and RabbitMQ containers.
    ```bash
    docker-compose up -d
    ```
3.  **Initialize the Database:** This command creates the tables and seeds the initial settings. Run this only once.
    ```bash
    python -c "from database import init_db, seed_settings; init_db(); seed_settings()"
    ```

#### Launching the Bot

1.  **Terminal 1: Start the Celery Worker**
    This process listens for jobs from RabbitMQ.
    ```bash
    # On Windows
    celery -A tasks.celery worker --loglevel=INFO --pool=eventlet

    # On macOS / Linux
    celery -A tasks.celery worker --loglevel=INFO
    ```

2.  **Terminal 2: Start the Web Server**
    This process listens for webhooks from Slack.
    ```bash
    # On Windows
    waitress-serve --host 127.0.0.1 --port 8000 app:flask_app

    # On macOS / Linux
    gunicorn --workers 3 app:flask_app
    ```

3.  **Terminal 3: Start `ngrok` (only for local deployment)**
    This process exposes your local web server to the internet.
    ```bash
    ngrok http 8000
    ```
4.  **Final Slack Configuration:**
    * Copy the public `https://...` URL from your `ngrok` terminal.
    * Go to your Slack App settings -> **Event Subscriptions**.
    * Paste the `ngrok` URL into the **Request URL** box, adding `/slack/events` at the end.
    * Save changes and reinstall the app to your workspace if prompted.

---

## Usage

Once all three terminals are running and the Slack Request URL is verified, you can use the bot. Go to any channel the bot has been invited to and mention it with a question.

**Example:**
`@YourBotName what is a Python decorator?`

---
