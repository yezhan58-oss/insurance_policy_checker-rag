import json

from langchain_core.messages import AIMessage

from src.approaches import REGISTRY
from src.approaches._common import BASE_PROMPT, NO_POLICY_TEXT
from src.schema import Chunk, Scenario

GOOD = json.dumps({"verdict": "covered", "cited_sections": ["fwd:travel_delay"],
                   "explanation": "The policy pays for delays of '6 continuous hours or more'."})


class FakeLLM:
    """Returns scripted replies in order and records every call."""

    def __init__(self, *replies):
        self.replies, self.calls = list(replies), []

    def bind(self, **kwargs):
        self.kwargs = kwargs
        return self

    def invoke(self, messages):
        self.calls.append(messages)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return AIMessage(content=reply,
                         usage_metadata={"input_tokens": 100, "output_tokens": 20, "total_tokens": 120,
                                         "output_token_details": {"reasoning": 5}})


class FakeStore:
    def __init__(self):
        self.queries = []

    def search(self, query, policy, k=5):
        self.queries.append((query, policy, k))
        return [Chunk(chunk_id=f"fwd:travel_delay#{i}", section_id="fwd:travel_delay", policy="fwd",
                      title="Travel delay", type="benefit", page=12, text=f"FWD > Travel delay\nchunk {i}",
                      score=0.7) for i in range(k)]


class WholePolicyStore(FakeStore):
    def list_sections(self, policy, type=None):
        return [Chunk(chunk_id=i, section_id=i, policy=policy, title=i, type="benefit", page=1, text=f"FWD > {i}\ntext")
                for i in ("fwd:travel_delay", "fwd:definitions:trip", "fwd:general_exclusions:war")]


SCENARIO = Scenario(id="smoke-1", policy="fwd", category="single_section", gold_verdict="covered",
                    scenario="My flight was delayed 7 hours by a typhoon. Can I claim?")


def test_registry_has_b0_and_a0():
    assert {"B0", "A0"} <= set(REGISTRY)


def test_b0_sends_no_policy_text():
    llm = FakeLLM(GOOD)
    out = REGISTRY["B0"](SCENARIO, llm, FakeStore())
    system, user = llm.calls[0]
    assert system.content == BASE_PROMPT
    assert NO_POLICY_TEXT in user.content and SCENARIO.scenario in user.content
    assert out.verdict == "covered" and out.error is None
    assert llm.kwargs["response_format"]["type"] == "json_schema"


def test_a0_searches_once_and_shows_section_ids():
    llm, store = FakeLLM(GOOD), FakeStore()
    out = REGISTRY["A0"](SCENARIO, llm, store)
    assert store.queries == [(SCENARIO.scenario, "fwd", 5)]                  # top_k from configs/approaches.yaml
    user = llm.calls[0][1].content
    assert user.count("[Section ID: fwd:travel_delay]") == 5
    assert out.cited_sections == ["fwd:travel_delay"]
    assert out.steps[0]["step"] == "search" and len(out.steps[0]["hits"]) == 5
    assert out.usage["model_calls"] == 1 and out.usage["prompt_tokens"] == 100
    assert out.usage["reasoning_tokens"] == 5 and out.usage["latency_s"] >= out.usage["llm_latency_s"] >= 0


def test_unparseable_answer_is_retried_once():
    llm = FakeLLM("not json", GOOD)
    out = REGISTRY["A0"](SCENARIO, llm, FakeStore())
    assert out.verdict == "covered" and out.error is None
    assert out.usage["model_calls"] == 2
    assert [s["step"] for s in out.steps] == ["search", "parse_failed", "answer"]


def test_length_limit_reply_is_retried_then_parse_error():
    from types import SimpleNamespace

    import openai
    cut_off = openai.LengthFinishReasonError(
        completion=SimpleNamespace(usage=SimpleNamespace(prompt_tokens=2000, completion_tokens=4096)))
    out = REGISTRY["A0"](SCENARIO, FakeLLM(cut_off, GOOD), FakeStore())
    assert out.verdict == "covered" and out.error is None
    assert out.usage["model_calls"] == 2 and out.usage["completion_tokens"] == 4096 + 20
    out = REGISTRY["B0"](SCENARIO, FakeLLM(cut_off, cut_off), FakeStore())
    assert out.error == "parse_error"


def test_two_bad_answers_record_parse_error():
    llm = FakeLLM('{"verdict": "maybe"}', "still not json")
    out = REGISTRY["B0"](SCENARIO, llm, FakeStore())
    assert out.error == "parse_error" and out.cited_sections == []
    assert out.usage["model_calls"] == 2


def test_l0_puts_the_whole_policy_in_one_call_without_search():
    llm, store = FakeLLM(GOOD), WholePolicyStore()
    out = REGISTRY["L0"](SCENARIO, llm, store)
    system, user = llm.calls[0]
    assert system.content == BASE_PROMPT and store.queries == []          # same prompt, no retrieval
    assert all(f"[Section ID: {i}]" in user.content for i in out.steps[0]["context"])
    assert out.steps[0] == {"step": "long_context",
                            "context": ["fwd:travel_delay", "fwd:definitions:trip", "fwd:general_exclusions:war"]}
    assert out.usage["model_calls"] == 1 and out.error is None
