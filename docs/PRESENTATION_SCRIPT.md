# IS469 presentation script (7 minutes, live demo included)

Deck: `docs/IS469_presentation.pptx`, 11 slides. Ye Zhan presents the problem, the comparison, the model finding and the
advice; Liang Than presents the workflow agent, its results and cost, and runs the live demo. Target is **6:40 spoken**, which leaves about 20 s of buffer for
slide changes and a slow first model answer. At a normal pace of about 140 words a minute, each timing below matches
its word count.

| Slides | Speaker | Time | Running total |
|---|---|---|---|
| 1–4: why it matters, problem, methods, fair test | Ye Zhan | 2:15 | 2:15 |
| 5–7: the workflow agent, results, cost | Liang Than | 1:45 | 4:00 |
| 8: the model | Ye Zhan | 0:25 | 4:25 |
| 9: live demo | Liang Than (Ye Zhan drives the laptop) | 1:30 | 5:55 |
| 10–11: advice, close | Ye Zhan | 0:45 | 6:40 |

---

## [Slide 1: Is the agent worth it?] Ye Zhan, 25 s

Hi, we're Ye Zhan and Liang Than. When something goes wrong on a trip, people want to know straight away whether
they're covered. Insurers' chatbots today mostly follow scripts to sell a policy or file a claim, and we didn't find
one that reads your policy and tells you whether your situation is covered, with the clause to back it up. So we
tested how an LLM should read the policy, looking at how accurate, how safe and how costly each way is, and asked
a simple question: is an agent worth what it costs?

## [Slide 2: One claim, three clauses, pages apart] Ye Zhan, 35 s

Take this claim: a flight to Tokyo delayed seven hours by a typhoon. To answer it properly, you need three clauses
from a 45-page FWD policy. The delay benefit on page 12 says six continuous hours is enough, but only for "scheduled
public transport", which is defined all the way back on page 44. Then the exclusion on page 31 removes cover for any
event that was already in the news before you bought the policy. A normal search with the claim's own words finds
the first clause, but the other two use words the claim never says.

## [Slide 3: Five ways to read the policy] Ye Zhan, 45 s

So we compared five ways of reading the policy. No-RAG reads nothing and answers from what the model already knows,
and simple RAG does one search that returns the top five passages; these two are our baselines. The other three are
agentic RAG, where the model decides what to retrieve. Corrective RAG grades what it found and rewrites the search if
the passages are weak. Our workflow agent works like a claims assessor and goes benefits first, then definitions, then
exclusions. ReAct, which we added after the first four had run, picks its own lookups one at a time. Everything else
stays the same, so only the reading strategy changes. We ran all of it on two models, Llama 3.1 8B and gpt-oss-20b.

## [Slide 4: How we kept the comparison fair] Ye Zhan, 30 s

We wrote 144 claims against two real policies, FWD and MSIG. We tuned on 20 of them and froze the other 124 as a test
set before any test run. A second person re-labelled 40 claims blind: we matched on 25, and settled the other 15
together against the policy text. We also wrote the winner rule before testing:
first, a method must not wrongly say "covered" more often than simple RAG; then the most accurate one wins; and if the
gap isn't statistically significant, the cheaper, faster method wins.

*(hand over)* Liang will show you how the workflow agent works, and how it did.

## [Slide 5: The workflow agent reads like a claims assessor] Liang Than, 35 s

This strip is the whole FWD policy. The workflow agent first picks up to three benefits from the contents, then looks up the
defined terms by name at the back, and then keeps the general exclusions that could apply. Simple RAG's single search
usually lands near the benefit and stops there. That's why the workflow agent reached 84 to 91% of the clauses that decide a
claim, compared with 66% for simple RAG.

## [Slide 6: The agents led, but not by enough] Liang Than, 35 s

So did all that extra reading pay off? The two agents were the most accurate, but only just: on gpt-oss, ReAct got 94 of 124 right against simple RAG's 86.
None of these gaps is statistically significant: with 124 claims, differences this small could just be luck. So they are too close to call, and the best value is simple RAG. (If asked: our planned rule picks simple RAG;
with ReAct added later, its tie-break picks the workflow agent. Either way, no agent is significantly better.)

## [Slide 7: What the workflow agent costs, and what it buys] Liang Than, 35 s

The workflow agent takes 2.6 times as long per claim, and for that you get two more right answers, which isn't a
real difference. Where it does matter is safety: on the claims that are not covered, simple RAG wrongly told the
customer "you're covered" 9 times, the workflow agent only once.

*(hand back)* Ye Zhan has one more surprise for you.

## [Slide 8: The model mattered more than the method] Ye Zhan, 25 s

The model mattered more than the method. Switching to the bigger model lifted simple RAG by 13 points,
while switching method added at most 6. Without the policy, the bigger model actually did worse, but given the whole
policy in one prompt it got 76% right against the small model's 32%, at thirteen times the tokens.

*(hand over)* Liang will now show it live.

## [Slide 9: Live demo] Liang Than, 90 s (Ye Zhan switches to the browser and clicks the example)

Let's see it live. This claim is from our test set: a typhoon heading to Manila was already in the news when the
policy was bought, and the correct answer is **not covered**. We'll run all four methods at the same time on the
cluster.

*(while it runs, about 15 s)* No-RAG never opens the policy, so watch for a guess. Simple RAG does one search and
usually answers first. The workflow agent is working through its fixed steps, and ReAct is choosing its own
lookups one at a time.

*(point at the verdict labels, and the tick or cross under each)* No-RAG says it doesn't have enough information. Simple RAG
gets it wrong: it found the delay benefit but never saw the exclusion, so it says covered or asks for more detail. The workflow agent says not covered, because it found the
exclusion for events already reported by the media. ReAct chooses its own lookups, so it may or may not get there:
point at its tick or cross either way.

*(scroll down to the table under the cards)* Here are the four answers side by side, with the time, tokens and model calls
each took. It matches our test results: simple RAG is the best value, and the workflow agent is the safer one on
exactly this kind of claim.

> If live fails, or the cluster is slow: open the sidebar (arrow at the top left), untick "Run live" and say "here are
> the saved answers from the same run".
> If No-RAG says not covered, say "No-RAG got lucky: it never read the policy, and its reason (weather delays are
> excluded) is wrong; the real reason is the news exclusion the workflow agent found"
> If simple RAG says not covered this time, say "simple RAG got this one right today, but in our test run it said
> covered, and it made that mistake on 9 of the 53 not-covered claims."
> If ReAct says covered or need more detail, say "this is why we call the fixed workflow safer: ReAct picks its own
> route, and on this claim it sometimes misses the exclusion. Across our runs on this claim it got it right four times out of seven"

## [Slide 10: What we would tell an insurer] Ye Zhan, 35 s

So here's what we'd tell an insurer. For best value, use simple RAG: it's as accurate as the agents with one model call
instead of three or more. If wrongly telling a customer "you're covered" is the error you can't afford, run the
workflow agent on every claim, because it's the safer one. We also tried a cheaper mix, safe mode, where the agent only
re-checks simple RAG's "covered" answers: it stopped every wrong "covered", but got fewer claims right and cost almost
as much as the agent. The limits are that we wrote these claims ourselves from two policies, and 124 claims can only
detect fairly large gaps.

## [Slide 11: Thank you. Questions?] Ye Zhan, 10 s

So, is the agent worth it? For accuracy, not yet. For safety, yes. Thank you, and we're happy to take questions.

---

## Before you go on

- Start the server 30 to 60 minutes before the slot, open the tunnel, and ask one warm-up question (the first answer
  after a cold start takes about 20 s per method).
- Open `localhost:8502` in the browser before you start, with all four methods ticked. Click the "Typhoon already in the
  news" example instead of pasting: the wording then matches our test claim exactly, so the page shows the tick or
  cross under each verdict. After "Check my claim" the banner shrinks, so all four verdicts fit on the first screen.
- Rehearse once with a timer. If you run long, cut in this order: the "without the policy / whole policy" sentence on slide 8, the
  limits sentence on slide 10, then "We ran all of it on two models" on slide 3 (the slide still shows it).
- Say one number per point; the slides hold the rest. Avoid "McNemar", "Holm" and "kappa" unless asked.
