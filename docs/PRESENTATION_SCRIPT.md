# IS469 presentation script (7 minutes, live demo included)

Deck: `docs/IS469_presentation.pptx`, 11 slides. The split follows the brief: Ye Zhan presents the comparison and
results, and Liang Than presents the agent and runs the live demo. Target is **6:15 spoken**, which leaves about 45 s of buffer for
slide changes and a slow first model answer. At a normal pace of about 140 words a minute, each timing below matches
its word count.

| Slides | Speaker | Time | Running total |
|---|---|---|---|
| 1–4: problem, methods, fair test | Ye Zhan | 2:00 | 2:00 |
| 5: how A4 reads the policy | Liang Than | 0:35 | 2:35 |
| 6–8: results, cost, the model | Ye Zhan | 1:25 | 4:00 |
| 9: live demo | Liang Than (Ye Zhan drives the laptop) | 1:30 | 5:30 |
| 10–11: advice, close | Ye Zhan | 0:45 | 6:15 |

---

## [Slide 1: Is the agent worth it?] Ye Zhan, 10 s

Hi, we're Ye Zhan and Liang Than. Agents are the hot thing in RAG right now, so we asked a simple question: for
checking travel insurance claims, is an agent actually worth what it costs?

## [Slide 2: One claim, three clauses, pages apart] Ye Zhan, 35 s

Take this claim: a flight to Tokyo delayed seven hours by a typhoon. To answer it properly, you need three clauses
from a 45-page FWD policy. The delay benefit on page 12 says six continuous hours is enough, but only for "scheduled
public transport", which is defined all the way back on page 44. Then the exclusion on page 31 removes cover for any
event that was already in the news before you bought the policy. A normal search with the claim's own words finds
the first clause, but the other two use words the claim never says.

## [Slide 3: Four ways to read the policy] Ye Zhan, 45 s

So we compared four ways of reading the policy. B0 reads nothing and answers from what the model already knows. A0
is simple RAG, with one search that returns the top five passages. A2 is corrective RAG: it grades what it found and
rewrites the search if the passages are weak. A4 is our workflow agent, which works like a claims assessor and goes
benefits first, then definitions, then exclusions. Everything else stays the same in all four (the index, the prompt
and the final answer step), so only the reading strategy changes. We ran all of it on two models, Llama 3.1 8B and
gpt-oss-20b. We also tried three extra setups after the plan was fixed, but they were never allowed to win.

## [Slide 4: How we kept the comparison fair] Ye Zhan, 30 s

We wrote 144 claims against two real policies, FWD and MSIG. We tuned on 20 of them and froze the other 124 as a test
set before any test run. A second labeller checked 40 claims blind. We also wrote the winner rule before testing:
first, a method must not wrongly say "covered" more often than simple RAG; then the most accurate one wins; and if the
gap isn't statistically significant, the cheaper, faster method wins.

*(hand over)* Liang will show you how the agent works.

## [Slide 5: A4 reads the policy like a claims assessor] Liang Than, 35 s

This strip is the whole FWD policy. A4 first picks up to three benefits from the contents, then looks up the defined
terms by name at the back, and then keeps the general exclusions that could apply. A0's single search usually lands
near the benefit and stops there. That's why A4 reached 84 to 91% of the clauses that decide a claim, compared with
66% for simple RAG.

*(hand back)* Ye Zhan will take you through the results.

## [Slide 6: A4 was most accurate, but not by enough] Ye Zhan, 35 s

A4 was the most accurate method on both models, but only just. On gpt-oss it got 88 claims right against A0's 86, and
on Llama it got 76 against 70. Neither gap is statistically significant, with p-values of 0.88 and 0.38. On 124
claims the two are too close to call, so our pre-registered rule picks the cheaper one, which is A0.

## [Slide 7: What the agent costs, and what it buys] Ye Zhan, 35 s

The agent takes 2.6 times as long per claim, 15.2 seconds against 5.8, so checking a thousand claims would take
4.2 hours instead of 1.6. For that, you get two more right answers, which isn't a real difference. Where it does
matter is safety: out of the 53 claims that are not covered, A0 wrongly told the customer "you're covered" 9 times,
while A4 did it only once.

## [Slide 8: The model mattered more than the method] Ye Zhan, 15 s

One surprise: the model mattered more than the method. Switching to the bigger model lifted simple RAG by 13 points,
while switching method added about 2. Without the policy, though, the bigger model actually did worse.

*(hand over)* Liang will now show it live.

## [Slide 9: Live demo] Liang Than, 90 s (Ye Zhan switches to the browser and pastes the claim)

Let's see it live. This claim is from our test set: a typhoon heading to Manila was already in the news when the
policy was bought, and the correct answer is **not covered**. We'll run B0, A0 and A4 at the same time on the cluster.

*(while it runs, about 15 s)* B0 never opens the policy, so watch for a guess. A0 does one search and usually answers
first. A4 is working through its steps: benefits, definitions, then exclusions.

*(point at the stamps)* B0 says it doesn't have enough information. A0 says covered, because it found the delay
benefit and stopped. A4 says not covered, because it found the exclusion for events already reported by the media,
and you can see the clause it used right here.

*(point at the "Which one wins?" panel)* This panel sums up the study: A0 is our best-value pick, and A4 is the safer
one on exactly this kind of claim.

> If live fails, or the cluster is slow: untick "Run live" and say "here are the saved answers from the same run".
> If A0 says not covered this time, say "A0 got this one right today, but in our test run it said covered, and it
> made that mistake on 9 of the 53 not-covered claims."

## [Slide 10: What we would tell an insurer] Ye Zhan, 35 s

So here's what we'd tell an insurer. For best value, use simple RAG: it's as accurate as the agent with a third of the
model calls. If wrongly telling a customer "you're covered" is the error you can't afford, the agent is safer, with 1
wrong out of 53 against 9. Our advice is to combine them: let A0 answer everything, and have A4 re-check only the
claims A0 says are covered, which brought the wrong "covered" count to 0 of 53 at 66% accuracy. The limits are that
we wrote these claims ourselves from two policies, and 124 claims can only detect fairly large gaps.

## [Slide 11: Thank you. Questions?] Ye Zhan, 10 s

So, is the agent worth it? For accuracy, not yet. For safety, yes. Thank you, and we're happy to take questions.

---

## Before you go on

- Start the server 30 to 60 minutes before the slot, open the tunnel, and ask one warm-up question (the first answer
  after a cold start takes about 20 s per method).
- Open `localhost:8502` in the browser before you start, with B0, A0 and A4 ticked and the Manila claim ready to paste.
- On the cover and the last slide, replace "[presentation date]" with **13 November 2026**.
- Rehearse once with a timer. If you run long, cut the last sentence of slide 3 and the slide 8 "Without the policy"
  line first.
