"""CONTRACT: registry of approaches. Change only with agreement from both members.

To add an approach, create one module in this package that defines

    APPROACH_ID = "A0"
    def run(scenario: Scenario, llm: BaseChatModel, store) -> VerdictOutput: ...

where `store` is the src.store module (or a test double with the same functions). It is picked
up automatically, so nobody edits this file to register a new approach. Modules whose names
start with "_" (shared helpers) are skipped.
"""
import importlib
import pkgutil
from typing import Callable

from src.schema import VerdictOutput

REGISTRY: dict[str, Callable[..., VerdictOutput]] = {}

for _info in pkgutil.iter_modules(__path__):
    if _info.name.startswith("_"):
        continue
    _module = importlib.import_module(f"{__name__}.{_info.name}")
    _id = getattr(_module, "APPROACH_ID", None)
    if _id and hasattr(_module, "run"):
        if _id in REGISTRY:
            raise RuntimeError(f"Duplicate APPROACH_ID {_id!r} in {_info.name}")
        REGISTRY[_id] = _module.run
