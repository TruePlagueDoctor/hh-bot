import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass
class BotConfig:
    token: str
    database_url: str
    llm_base_url: str
    llm_api_key: str
    llm_model_name: str


TG_BOT_API_KEY = os.getenv("TG_BOT_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
LLM_BASE_URL = os.getenv("LLM_BASE_URL")
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME")

if not TG_BOT_API_KEY:
    raise RuntimeError("TG_BOT_API_KEY is not set in .env")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set in .env")
if not (LLM_BASE_URL and LLM_API_KEY and LLM_MODEL_NAME):
    raise RuntimeError("LLM_BASE_URL, LLM_API_KEY, LLM_MODEL_NAME must be set in .env")

config = BotConfig(
    token=TG_BOT_API_KEY,
    database_url=DATABASE_URL,
    llm_base_url=LLM_BASE_URL,
    llm_api_key=LLM_API_KEY,
    llm_model_name=LLM_MODEL_NAME,
)
