"""CONTRACT: one client interface for every model. Change only with agreement from both members.

    from src.llm import get_llm
    llm = get_llm("vllm_llama8b")          # name = a top-level key in configs/models.yaml

Returns a LangChain chat model: ChatOpenAI (vLLM, Ollama) or ChatAnthropic (Claude), chosen by
the `provider` field. Approach code never changes when the model changes.
"""
import os
import re
from pathlib import Path

import yaml
from dotenv import load_dotenv
from langchain_core.language_models.chat_models import BaseChatModel

ROOT = Path(__file__).resolve().parents[1]
MODELS_PATH = ROOT / "configs" / "models.yaml"
_VAR = re.compile(r"\$\{(\w+)\}")


def _expand(value: str, name: str) -> str:
    def sub(m: re.Match) -> str:
        var = m.group(1)
        if not os.environ.get(var):
            raise RuntimeError(f"{var} is not set (needed by model '{name}'). Add it to .env.")
        return os.environ[var]

    return _VAR.sub(sub, value)


def load_model_config(name: str) -> dict:
    """The models.yaml entry for `name`, with ${VAR} filled in from .env / the environment."""
    load_dotenv(ROOT / ".env")
    configs = yaml.safe_load(MODELS_PATH.read_text(encoding="utf-8"))
    if name not in configs:
        raise KeyError(f"Unknown model '{name}'. Choose from: {', '.join(configs)}")
    return {k: _expand(v, name) if isinstance(v, str) else v for k, v in configs[name].items()}


def get_llm(name: str, temperature: float = 0.0, **overrides) -> BaseChatModel:
    cfg = load_model_config(name)
    provider = cfg.pop("provider")
    if provider == "openai":
        from langchain_openai import ChatOpenAI

        kwargs = dict(model=cfg["model"], base_url=cfg["base_url"], api_key=cfg["api_key"],
                      temperature=temperature, seed=0)
        return ChatOpenAI(**{**kwargs, **overrides})
    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        # No temperature: Claude 5.5 models (our Haiku judge) reject any value other than the default.
        kwargs = dict(model=cfg["model"], api_key=cfg["api_key"], max_tokens=2048)
        return ChatAnthropic(**{**kwargs, **overrides})
    raise ValueError(f"Unknown provider '{provider}' for model '{name}'")
