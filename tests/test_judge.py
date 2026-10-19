import json

from src.eval import judge as judge_mod


def row(sid, cited=("fwd:travel_delay",), error=None):
    return {"scenario_id": sid, "approach": "A0",
            "output": {"verdict": "covered", "cited_sections": list(cited), "explanation": "x", "error": error}}


class FakeJudge:
    def __init__(self, fail_times=0):
        self.calls, self.fail_times = 0, fail_times

    def invoke(self, messages):
        self.calls += 1
        if self.calls <= self.fail_times:
            raise ValueError("bad json")
        return judge_mod.Judgement(faithfulness="yes", reason="ok")


def test_run_judges_skips_errors_and_resumes(tmp_path, monkeypatch):
    monkeypatch.setattr(judge_mod, "cited_text", lambda ids: "text")
    out = tmp_path / "judged.jsonl"
    rows = [row("s0"), row("s1", cited=()), row("s2", error="parse_error")]
    fake = FakeJudge(fail_times=1)                          # first call fails, retried once
    assert judge_mod.run(rows, fake, out, log=lambda *_: None) == 2
    got = {j["scenario_id"]: j["faithfulness"] for j in map(json.loads, out.open(encoding="utf-8"))}
    assert got == {"s0": "yes", "s1": "no"}                 # no citations -> "no" without a call
    assert fake.calls == 2
    assert judge_mod.run(rows, fake, out, log=lambda *_: None) == 0


def test_estimate_cost_ignores_uncited_rows(monkeypatch):
    monkeypatch.setattr(judge_mod, "cited_text", lambda ids: "a" * 4000)
    assert judge_mod.estimate_cost([row("s1", cited=())]) == 0
    assert 0 < judge_mod.estimate_cost([row("s0")]) < 0.001
