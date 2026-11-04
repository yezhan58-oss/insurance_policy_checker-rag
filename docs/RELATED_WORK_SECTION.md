# Report draft: Related work (Member B)

About half a page. Goes after the Introduction. Test numbers are from `results/test/report/leaderboard.md` and RESULTS 7.9.
Rewrite in your own words before submitting.

## 2. Related work

**Retrieval-augmented generation.** RAG gives a language model passages fetched from an outside corpus at answer time
(Lewis et al., 2020). Our A0 is the plain form of this: one search with the claim text, five chunks, one answer.
Policy wordings are hard for it because the deciding text is spread out. A benefit section sets the rule, a
definition at the back of the document narrows a term, and a general exclusion many pages away can cancel the cover.
One search with the claim text rarely finds all three.

**Corrective and self-reflective retrieval.** Corrective RAG (CRAG; Yan et al., 2024) adds an evaluator that grades
the retrieved passages. When they are weak, it rewrites the query and searches again, or falls back to web search.
Self-RAG (Asai et al., 2024) trains the model to decide when to retrieve and to critique its own output. Our A2
follows CRAG with an LLM grader in place of the fine-tuned evaluator, and no web search, because the corpus is closed.
Its grader worked, but its rewrites rarely found a missing section: a "search again" loop cannot know that a
definition or an exclusion is needed.

**Tool-using agents.** ReAct (Yao et al., 2023) lets a model mix reasoning steps with tool calls, so it can choose what
to look up next. A ReAct agent (A3) was an optional setup that we did not build; our plan already flagged tool calling with an 8B
model as a risk.
Our A4 takes the opposite approach: a fixed LangGraph workflow that follows how a claims assessor reads a policy
(benefit, then definitions, then exclusions, then a decision). The domain knowledge sits in the graph, not in the
model's choices.

**Long context instead of retrieval.** Models with long context windows can read a whole document. Li et al. (2024) find that long context can beat RAG
when enough resources are available, while RAG costs far less. Models also use information in the middle of a long
prompt less well than information at the start or end (Liu et al., 2024). Our exploratory L0 fits the first finding:
with the whole policy (28k to 45k tokens) in the prompt, gpt-oss-20b had the best accuracy of any run (0.76) at
5 to 6 times the tokens of A4, while Llama 3.1 8B fell to 0.32, mostly by answering insufficient_info (79 of 124 claims).
We could not test the second finding, because where a clause sits and the claim category go together.

**LLM as judge.** Strong LLMs can grade open-ended answers with agreement close to human raters, with known biases
such as favouring their own outputs (Zheng et al., 2023). We use Claude Haiku 5.5 to judge whether each explanation
is supported by the cited text. It comes from a different company than both tested models. We also checked it
against 30 human labels per model (77% and 80% agreement, kappa 0.64 and 0.52).

### References

- Asai, A., Wu, Z., Wang, Y., Sil, A., & Hajishirzi, H. (2024). Self-RAG: Learning to retrieve, generate, and critique
  through self-reflection. ICLR 2024. https://arxiv.org/abs/2310.11511
- Lewis, P., et al. (2020). Retrieval-augmented generation for knowledge-intensive NLP tasks. NeurIPS 2020.
  https://arxiv.org/abs/2005.11401
- Li, Z., Li, C., Zhang, M., Mei, Q., & Bendersky, M. (2024). Retrieval augmented generation or long-context LLMs? A
  comprehensive study and hybrid approach. EMNLP 2024 Industry Track. https://arxiv.org/abs/2407.16833
- Liu, N. F., et al. (2024). Lost in the middle: How language models use long contexts. TACL 12.
  https://arxiv.org/abs/2307.03172
- Yan, S.-Q., Gu, J.-C., Zhu, Y., & Ling, Z.-H. (2024). Corrective retrieval augmented generation.
  arXiv:2401.15884. https://arxiv.org/abs/2401.15884
- Yao, S., et al. (2023). ReAct: Synergizing reasoning and acting in language models. ICLR 2023.
  https://arxiv.org/abs/2210.03629
- Zheng, L., et al. (2023). Judging LLM-as-a-judge with MT-Bench and Chatbot Arena. NeurIPS 2023 Datasets and
  Benchmarks. https://arxiv.org/abs/2306.05685
