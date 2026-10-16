"""CONTRACT: shared data types. Change only with agreement from both members.

Scenario       one line of data/scenarios/*.jsonl (brief section 6)
Chunk          one retrievable piece of a policy section (returned by store.search)
Answer         what the LLM itself returns via structured output
VerdictOutput  what every approach returns (brief section 7)
"""
from typing import Literal

from pydantic import BaseModel, ConfigDict

Verdict = Literal["covered", "not_covered", "partially_covered", "insufficient_info"]
VERDICTS: tuple[str, ...] = ("covered", "not_covered", "partially_covered", "insufficient_info")

Category = Literal["single_section", "needs_definition", "needs_exclusion", "tricky"]
SectionType = Literal["benefit", "definition", "exclusion", "condition", "other"]


class Scenario(BaseModel):
    # Extra keys (e.g. drafting metadata) are kept, so draft.py / label_app.py can add fields freely.
    model_config = ConfigDict(extra="allow")

    id: str                                # e.g. "fwd-007"
    policy: str                            # "fwd" | "msig"
    scenario: str                          # the claim question in plain English
    category: Category
    source_clause: str | None = None       # section_id the scenario was drafted from
    gold_verdict: Verdict                  # in drafts.jsonl this is the intended answer, not gold
    gold_sections: list[str] = []          # section_ids that decide the verdict
    notes: str = ""
    status: Literal["draft", "accepted", "changed", "deleted"] = "draft"


class Chunk(BaseModel):
    chunk_id: str                          # f"{section_id}#{n}", n = 0, 1, ... within the section
    section_id: str                        # e.g. "fwd:travel_delay", "fwd:definitions:public_holiday"
    policy: str
    title: str                             # section heading as printed in the policy
    type: SectionType
    page: int                              # 1-based PDF page where this chunk's text starts
    text: str
    score: float | None = None             # cosine similarity from search(); None when fetched by id


class Answer(BaseModel):
    """Structured output requested from the LLM. Approaches wrap it into a VerdictOutput."""

    verdict: Verdict
    cited_sections: list[str]              # section_ids
    explanation: str                       # plain English, quotes the deciding clause text


class VerdictOutput(BaseModel):
    verdict: Verdict
    cited_sections: list[str]              # section_ids
    explanation: str                       # plain English, quotes the deciding clause text
    steps: list[dict] = []                 # trace: each retrieval / tool call / grade
    usage: dict = {}                       # model_calls, prompt_tokens, completion_tokens, latency_s
    error: str | None = None               # e.g. "parse_error"; score.py counts any error as wrong
