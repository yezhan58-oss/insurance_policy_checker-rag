from src.approaches import REGISTRY
from src.approaches._common import NO_POLICY_TEXT
from src.eval.traces import context_sections
from tests.test_approaches import GOOD, SCENARIO, FakeLLM, FakeStore

REWRITE = '{"query": "travel delay due to weather"}'


def steps_of(out):
    return [s["step"] for s in out.steps]


def test_enough_relevant_chunks_answers_without_rewriting():
    llm, store = FakeLLM('{"relevant": [1, 3]}', GOOD), FakeStore()
    out = REGISTRY["A2"](SCENARIO, llm, store)
    assert out.verdict == "covered" and out.error is None
    assert steps_of(out) == ["search", "grade", "decide", "answer"]
    assert store.queries == [(SCENARIO.scenario, "fwd", 5)]
    assert out.usage["model_calls"] == 2
    answer_prompt = llm.calls[-1][1].content
    assert "chunk 0" in answer_prompt and "chunk 2" in answer_prompt and "chunk 1" not in answer_prompt
    assert context_sections(out.steps) == {"fwd:travel_delay"}


def test_too_few_relevant_rewrites_and_searches_again():
    llm, store = FakeLLM('{"relevant": [2]}', REWRITE, '{"relevant": [4]}', GOOD), FakeStore()
    out = REGISTRY["A2"](SCENARIO, llm, store)
    assert steps_of(out) == ["search", "grade", "rewrite", "search", "grade", "decide", "answer"]
    assert [q for q, _, _ in store.queries] == [SCENARIO.scenario, "travel delay due to weather"]
    assert SCENARIO.scenario in llm.calls[1][1].content          # the rewriter sees the earlier query
    assert SCENARIO.scenario in llm.calls[2][1].content          # the grader judges against the claim, not the query
    assert out.usage["model_calls"] == 4


def test_nothing_relevant_after_max_rewrites_answers_without_policy_text():
    llm = FakeLLM('{"relevant": []}', REWRITE, '{"relevant": []}', '{"query": "weather delay"}',
                  '{"relevant": []}', GOOD)
    out = REGISTRY["A2"](SCENARIO, llm, FakeStore())
    assert steps_of(out).count("search") == 3 and steps_of(out).count("rewrite") == 2   # max_rewrites = 2
    assert NO_POLICY_TEXT in llm.calls[-1][1].content
    assert out.steps[-2] == {"step": "decide", "context": []}
    assert out.usage["model_calls"] == 6


def test_unusable_grade_keeps_every_hit():
    out = REGISTRY["A2"](SCENARIO, FakeLLM("not json", GOOD), FakeStore())
    grade = out.steps[1]
    assert grade["step"] == "grade" and grade["fallback"] and len(grade["picked"]) == 5
    assert steps_of(out) == ["search", "grade", "decide", "answer"]


def test_repeated_rewrite_stops_the_loop():
    repeat = '{"query": "%s"}' % SCENARIO.scenario.upper()
    llm, store = FakeLLM('{"relevant": []}', repeat, GOOD), FakeStore()
    out = REGISTRY["A2"](SCENARIO, llm, store)
    assert steps_of(out) == ["search", "grade", "rewrite", "decide", "answer"] and len(store.queries) == 1
    assert out.steps[2]["repeated"] and out.usage["model_calls"] == 3
