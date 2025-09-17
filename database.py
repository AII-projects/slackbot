import os
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class RequestLog(Base):
    __tablename__ = "request_logs"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    slack_user_id = Column(String, index=True)
    user_question = Column(Text)
    gemini_answer = Column(Text, nullable=True)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    was_successful = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)

class Setting(Base):
    __tablename__ = "settings"
    setting_name = Column(String, primary_key=True, index=True)
    setting_value = Column(Text)
    description = Column(Text, nullable=True)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

def init_db():
    print("Initializing the database...")
    Base.metadata.create_all(bind=engine)
    print("Database initialized.")

def seed_settings():
    db = SessionLocal()
    try:
        print("Seeding initial settings...")
        default_settings = [
            Setting(setting_name='daily_user_limit', setting_value='25', description='Max requests per user in the defined window.'),
            Setting(setting_name='limit_window_seconds', setting_value='86400', description='The duration of the user limit window in seconds (24 hours).')
        ]
        
        for setting in default_settings:
            exists = db.query(Setting).filter(Setting.setting_name == setting.setting_name).first()
            if not exists:
                db.add(setting)
        
        db.commit()
        print("Settings seeded.")
    finally:
        db.close()