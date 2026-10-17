"""Review page for scenario drafts: accept, change, or delete each one (brief section 6, step 3).

    streamlit run app/label_app.py

Reads data/scenarios/drafts.jsonl, writes data/scenarios/reviewed.jsonl (one line per reviewed draft, rewritten
on every save, so going back and re-reviewing a draft replaces its earlier line).
"""
import json
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import store  # noqa: E402
from src.schema import VERDICTS, Scenario  # noqa: E402

DRAFTS = ROOT / "data" / "scenarios" / "drafts.jsonl"
REVIEWED = ROOT / "data" / "scenarios" / "reviewed.jsonl"
CATEGORIES = ["single_section", "needs_definition", "needs_exclusion", "tricky"]


def load(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    return {r["id"]: r for r in map(json.loads, path.read_text(encoding="utf-8").splitlines()) if r}


def save(row: dict) -> None:
    reviewed = load(REVIEWED)
    reviewed[row["id"]] = Scenario.model_validate(row).model_dump()
    order = list(load(DRAFTS))   # keep drafts order
    REVIEWED.write_text("".join(json.dumps(reviewed[i]) + "\n" for i in order if i in reviewed), encoding="utf-8")


st.set_page_config(page_title="Label scenarios", layout="wide")
drafts, reviewed = load(DRAFTS), load(REVIEWED)
todo = [i for i in drafts if i not in reviewed]
st.sidebar.progress(len(reviewed) / max(len(drafts), 1), f"{len(reviewed)} / {len(drafts)} reviewed")
ids = list(drafts)
pick = st.sidebar.selectbox("Scenario", ids, index=ids.index(todo[0]) if todo else 0,
                            format_func=lambda i: f"{i}  ({reviewed[i]['status']})" if i in reviewed else i)
d = reviewed.get(pick, drafts[pick])
st.sidebar.caption("Rules: data/scenarios/LABELLING_GUIDE.md")

left, right = st.columns([2, 3])
with left:
    st.subheader(pick)
    st.markdown(f"> {d['scenario']}")
    with st.expander("Draft's intended answer (decide yourself first)"):
        st.write(f"**{drafts[pick]['gold_verdict']}**: {drafts[pick]['notes']}")
        st.write(drafts[pick]["gold_sections"])

    with st.form(f"f_{pick}"):
        verdict = st.radio("Verdict", VERDICTS, index=VERDICTS.index(d["gold_verdict"]), horizontal=True)
        options = [c.section_id for c in store.list_sections(d["policy"])]
        sections = st.multiselect("Gold sections", options, default=[s for s in d["gold_sections"] if s in options])
        category = st.selectbox("Category", CATEGORIES, index=CATEGORIES.index(d["category"]))
        scenario = st.text_area("Scenario text", d["scenario"])
        notes = st.text_input("Notes (say why if you change anything)", d["notes"])
        accept, delete = st.columns(2)
        do_save = accept.form_submit_button("Save", type="primary", use_container_width=True)
        do_delete = delete.form_submit_button("Delete", use_container_width=True)

    if do_save or do_delete:
        row = {**drafts[pick], "gold_verdict": verdict, "gold_sections": sections, "category": category,
               "scenario": scenario, "notes": notes}
        same = all(row[k] == drafts[pick][k] for k in ("gold_verdict", "gold_sections", "category", "scenario"))
        row["status"] = "deleted" if do_delete else "accepted" if same else "changed"
        save(row)
        st.rerun()

with right:
    for sid in dict.fromkeys([d["source_clause"], *d["gold_sections"]]):
        c = sid and store.get_section(sid)
        if c:
            with st.expander(f"{sid}  (p{c.page})", expanded=True):
                st.text(c.text)
