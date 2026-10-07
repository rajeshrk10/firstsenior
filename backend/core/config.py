import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/firstsenior")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GITHUB_WEBHOOK_SECRET: str = os.getenv("GITHUB_WEBHOOK_SECRET", "")
    WEBHOOK_URL: str = os.getenv("WEBHOOK_URL", "http://localhost:8000/webhooks/github")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "qwen-2.5-coder-32b")

settings = Settings()