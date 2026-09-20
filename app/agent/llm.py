"""LLM 单例：全局共享一个 chat model 实例。"""

import sys
from pathlib import Path

from langchain.chat_models import init_chat_model

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.conf.app_config import app_config

llm = init_chat_model(
    model=app_config.llm.model_name,
    model_provider="openai",
    base_url=app_config.llm.base_url,
    api_key=app_config.llm.api_key,
    temperature=0,
)
