"""
LLM and Environment Configuration for Multi-Agent Supply Chain System.
Manages .env loading and provides standardized LLM invocation or mock mode fallback.
"""

import os
import json
import logging
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file at project root if present
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

logger = logging.getLogger("supply_chain_command_center")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def get_llm_configuration() -> Dict[str, Any]:
    """
    Evaluate available API keys and determine whether to run in live LLM or mock mode.
    Never exposes raw secrets in return values.
    """
    provider = os.getenv("LLM_PROVIDER", "").strip().lower()
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    model = os.getenv("LLM_MODEL", "").strip()

    # Determine active mode
    if (provider == "google" or (not provider and gemini_key)) and gemini_key and gemini_key != "your_gemini_api_key_here":
        return {
            "mode": "live_llm",
            "provider": "google",
            "model": model or "gemini-1.5-flash",
            "has_key": True
        }
    elif (provider == "openai" or (not provider and openai_key)) and openai_key and openai_key != "your_openai_api_key_here":
        return {
            "mode": "live_llm",
            "provider": "openai",
            "model": model or "gpt-4o-mini",
            "has_key": True
        }
    elif (provider == "groq" or (not provider and groq_key)) and groq_key and groq_key != "your_groq_api_key_here":
        return {
            "mode": "live_llm",
            "provider": "groq",
            "model": model or "llama3-70b-8192",
            "has_key": True
        }

    return {
        "mode": "deterministic_mock",
        "provider": "mock",
        "model": "rule_based_deterministic_reasoner",
        "has_key": False
    }


def call_llm(prompt: str, system_prompt: str = "You are an expert supply chain intelligence agent.") -> Optional[str]:
    """
    Attempt to invoke configured live LLM provider.
    Returns None if in deterministic mock mode or if invocation fails, enabling graceful fallback.
    """
    cfg = get_llm_configuration()
    if cfg["mode"] != "live_llm":
        return None

    try:
        if cfg["provider"] == "google":
            from langchain_google_genai import ChatGoogleGenerativeAI
            api_key = os.getenv("GEMINI_API_KEY")
            llm = ChatGoogleGenerativeAI(model=cfg["model"], google_api_key=api_key, temperature=0.2)
            messages = [("system", system_prompt), ("human", prompt)]
            response = llm.invoke(messages)
            return response.content

        elif cfg["provider"] == "openai":
            from langchain_openai import ChatOpenAI
            api_key = os.getenv("OPENAI_API_KEY")
            llm = ChatOpenAI(model=cfg["model"], openai_api_key=api_key, temperature=0.2)
            messages = [("system", system_prompt), ("human", prompt)]
            response = llm.invoke(messages)
            return response.content

    except Exception as exc:
        logger.warning(f"Live LLM invocation failed ({cfg['provider']}): {exc}. Falling back to deterministic reasoning.")
        return None

    return None
