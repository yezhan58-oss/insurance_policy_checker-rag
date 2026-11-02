""""Am I covered?" demo on the winning approach (brief section 10).

    streamlit run app/streamlit_app.py

Answers come from app/demo_cache.json when the same (policy, model, approach, question) was asked before, so the
scripted demo questions work offline. Anything else calls the cluster model live (tunnel open) and is then cached.
"""
import json
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import store  # noqa: E402
from src.approaches import REGISTRY  # noqa: E402
from src.approaches._common import POLICY_NAMES  # noqa: E402
from src.schema import Scenario, VerdictOutput  # noqa: E402

WINNER = "A0"            # decision rule on test (results/test/report/leaderboard.md), both models
BASELINE = "A4"          # agent shown side by side: fewer wrong "covered" answers on test
MODELS = ["vllm_gptoss20b", "vllm_llama8b"]   # gpt-oss first: only it has cached demo answers
CACHE = ROOT / "app" / "demo_cache.json"
DISCLAIMER = ("This is a student research demo, not insurance or legal advice. Only the insurer can decide a claim; "
              "always read your full policy wording.")
HEADLINE = {
    "covered": "Likely covered under {secs}, subject to the insurer's assessment.",
    "partially_covered": "Likely partly covered under {secs}: some costs or a sub-limit may not be paid, "
                         "subject to the insurer's assessment.",
    "not_covered": "Likely not covered, based on {secs}.",
    "insufficient_info": "Not enough information to say. See below for what detail is missing.",
}


def load_cache() -> dict:
    return json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}


def answer(policy: str, question: str, model: str, approach: str) -> VerdictOutput:
    key = f"{policy}|{model}|{approach}|{question.strip()}"
    cache = load_cache()
    if key in cache:
        return VerdictOutput(**cache[key])
    from src.llm import get_llm
    sc = Scenario(id="demo", policy=policy, scenario=question.strip(), category="single_section",
                  gold_verdict="insufficient_info")
    out = REGISTRY[approach](sc, get_llm(model), store)
    if out.error is None:
        cache[key] = out.model_dump()
        CACHE.write_text(json.dumps(cache, indent=1, ensure_ascii=False), encoding="utf-8")
    return out


def guard(out: VerdictOutput) -> VerdictOutput:
    """Never state a verdict without a real clause behind it: no valid citation -> insufficient_info."""
    valid = [s for s in out.cited_sections if store.get_section(s)]
    if out.error or (not valid and out.verdict != "insufficient_info"):
        return out.model_copy(update={"verdict": "insufficient_info", "cited_sections": valid,
                                      "explanation": "No policy clause could be found that decides this claim. "
                                                     "Add details such as the cause, dates, amounts and what you "
                                                     "are claiming for."})
    return out.model_copy(update={"cited_sections": valid})


def show(out: VerdictOutput, title: str) -> None:
    st.subheader(title)
    secs = ", ".join(f"`{s}`" for s in out.cited_sections) or "the policy"
    msg = HEADLINE[out.verdict].format(secs=secs)
    {"covered": st.success, "partially_covered": st.warning, "not_covered": st.error,
     "insufficient_info": st.info}[out.verdict](msg)
    st.markdown(out.explanation)
    for sid in out.cited_sections:
        sec = store.get_section(sid)
        with st.expander(f"Clause `{sid}`: {sec.title} (page {sec.page})"):
            st.text(sec.text)
    with st.expander(f"Trace ({len(out.steps)} steps, {out.usage.get('latency_s', 0):.1f}s, "
                     f"{out.usage.get('model_calls', 0)} model calls)"):
        st.json(out.steps)


st.set_page_config(page_title="Am I covered?", layout="wide")
st.title("Am I covered?")
st.caption(DISCLAIMER)
with st.sidebar:
    policy = st.selectbox("Policy", list(POLICY_NAMES), format_func=POLICY_NAMES.get)
    model = st.selectbox("Model", MODELS)
    compare = st.toggle(f"Compare with the claims-workflow agent ({BASELINE})")
question = st.text_area("Describe what happened",
                        placeholder="My flight to Tokyo was delayed 7 hours because of a typhoon. Can I claim?")
if st.button("Check", type="primary", disabled=not question.strip()):
    approaches = [WINNER] + ([BASELINE] if compare else [])
    cols = st.columns(len(approaches))
    for col, aid in zip(cols, approaches):
        with col:
            try:
                with st.spinner(f"Reading the {POLICY_NAMES[policy]} wording..."):
                    out = guard(answer(policy, question, model, aid))
            except Exception as e:   # server down or tunnel closed: say so instead of a stack trace
                st.error(f"Could not reach {model} ({type(e).__name__}). Open the SSH tunnel, or ask a cached question.")
                continue
            show(out, "Answer" if aid == WINNER else f"Claims-workflow agent ({aid})")
st.divider()
st.caption(DISCLAIMER)
