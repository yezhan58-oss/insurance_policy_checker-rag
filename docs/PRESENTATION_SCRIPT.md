# IS469 presentation script (7 minutes, live demo included)

Deck: 10 slides (the Canva deck is the one presented; `docs/IS469_presentation.pptx` is the repo copy). Ye Zhan
presents the problem, the methods, the fair test and the advice; Liang Than presents the workflow agent, its results
and cost, and runs the live demo. Target is **6:45 spoken**, which leaves about 15 s of buffer for slide changes and a
slow first model answer. At a normal pace of about 140 words a minute, each timing below matches its word count.

| Slides | Speaker | Time | Running total |
|---|---|---|---|
| 1–4: the idea, one claim, five methods, fair test | Ye Zhan | 2:50 | 2:50 |
| 5–7: the workflow agent, results, cost | Liang Than | 1:45 | 4:35 |
| 8: live demo | Liang Than (Ye Zhan drives the laptop) | 1:30 | 6:05 |
| 9–10: advice, close | Ye Zhan | 0:40 | 6:45 |

---

## [Slide 1: Is agentic RAG worth it?] Ye Zhan, 30 s

Hi, we're Group 5. I'm Ye Zhan, and this is Liang Than.

Our project idea came from travelling. When something goes wrong overseas, the first thing someone wants to know is
whether they're covered for their particular situation.

For this project, we used the FWD and MSIG travel policies. The answer to a customer's question sits in a policy of
45 to 70 pages, and the clauses that decide it can be pages apart.

So we tested how an AI should read the policy, using different AI methods, and whether an agent is worth the extra
cost.

## [Slide 2: One claim needs three clauses, pages apart] Ye Zhan, 35 s

Take this claim: a flight to Tokyo delayed seven hours by a typhoon. To answer it properly, you need three clauses
from a 45-page FWD policy. The delay benefit on page 12 says six continuous hours is enough, but only for "scheduled
public transport", which is defined all the way back on page 44. Then the exclusion on page 31 removes cover for any
event that was already in the news before you bought the policy. A normal search with the claim's own words finds
the first clause, but the other two use words the claim never says.

## [Slide 3: Five ways to read a policy] Ye Zhan, 45 s

So we compared five ways of reading the policy. No-RAG reads nothing and answers from what the model already knows,
and simple RAG does one search that returns the top five passages; these two are our baselines. The other three are
agentic RAG, where the model decides what to retrieve. Corrective RAG grades what it found and rewrites the search if
the passages are weak. Our workflow agent works like a claims assessor and goes benefits first, then definitions, then
exclusions. ReAct, which we added after the first four had run, picks its own lookups one at a time. Everything else
stays the same, so only the reading strategy changes. We ran all of it on two models, Llama 3.1 8B and gpt-oss-20b.

## [Slide 4: How we kept the test fair] Ye Zhan, 60 s

We wrote 144 claims against two real policies, FWD and MSIG. We used only 20 of them to adjust our prompts, and kept
the other 124 locked away until the final test, so we couldn't tweak our methods to fit them.

To check our answer key, I re-labelled 40 claims without seeing Liang's answers. We matched on 25, and settled the
other 15 together by going back to the policy.

Before seeing any results, we also fixed how we'd pick the best method, so we couldn't change the rules afterwards. A
method first has to be at least as safe as simple RAG, meaning it doesn't tell customers "you're covered" when they're
not any more often. Among the safe ones, the most accurate wins. But if two methods are so close that the difference
could just be luck, we pick the cheaper one.

*(hand over)* Liang will show you how the workflow agent works, and how it did.

## [Slide 5: Agents find the clauses a search misses] Liang Than, 35 s

Back to the Tokyo claim. Simple RAG does one search, finds the delay benefit, and stops there. Our workflow agent
reads like a claims assessor: the benefit first, then the definition, then the exclusions, so it finds all three.
Across all four methods, the two that look things up step by step, the workflow agent and
ReAct, got 77 to 91% of the deciding clauses in front of the model. Simple RAG and corrective RAG, which only search,
stayed at about two thirds.

## [Slide 6: Slightly more accurate, but it could be luck] Liang Than, 35 s

So did all that extra reading pay off? The two agents were the most accurate, but only just: on gpt-oss, ReAct got
76% right against simple RAG's 69%. None of these gaps is statistically significant: with 124 claims, differences this
small could just be luck. So they are too close to call, and the best value is simple RAG. (If asked: our planned rule
picks simple RAG; with ReAct added later, its tie-break picks the workflow agent. Either way, no agent is
significantly better.)

## [Slide 7: Slower, but far fewer wrong "covered"] Liang Than, 35 s

The workflow agent takes 2.6 times as long per claim, and for that you get two more right answers, which isn't a
real difference. Where it does matter is safety: on the claims that are not covered, simple RAG wrongly told the
customer "you're covered" 9 times, the workflow agent only once.

*(Ye Zhan switches to the browser)*

## [Slide 8: Live demo: one claim, four methods] Liang Than, 90 s (Ye Zhan drives the laptop and clicks the example)

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

*(hand back)* Ye Zhan will wrap up.

> If live fails, or the cluster is slow: open the sidebar (arrow at the top left), untick "Run live" and say "here are
> the saved answers from the same run".
> If No-RAG says not covered, say "No-RAG got lucky: it never read the policy, and its reason (weather delays are
> excluded) is wrong; the real reason is the news exclusion the workflow agent found"
> If simple RAG says not covered this time, say "simple RAG got this one right today, but in our test run it said
> covered, and it made that mistake on 9 of the 53 not-covered claims."
> If ReAct says covered or need more detail, say "this is why we call the fixed workflow safer: ReAct picks its own
> route, and on this claim it sometimes misses the exclusion. Across our runs on this claim it got it right four times out of seven"

## [Slide 9: Our advice to insurers] Ye Zhan, 30 s

So what would we tell an insurer?

If you want the best value, use simple RAG. It's just as accurate, and it's much cheaper.

But if telling a customer "you're covered" by mistake is a big problem for you, use the workflow agent. It's the
safest.

We also tried mixing the two. It was safe, but it got fewer claims right, and it cost almost the same as the agent.
So it's not worth it.

## [Slide 10: Thank you] Ye Zhan, 10 s

So, is agentic RAG worth it? For accuracy, not yet. For safety, yes. Thank you, and we're happy to take questions.

---

## Before you go on

- Start the server 30 to 60 minutes before the slot, open the tunnel, and ask one warm-up question (the first answer
  after a cold start takes about 20 s per method).
- Open `localhost:8502` in the browser before you start, with all four methods ticked. Click the "Typhoon already in the
  news" example instead of pasting: the wording then matches our test claim exactly, so the page shows the tick or
  cross under each verdict. After "Check my claim" the banner shrinks, so all four verdicts fit on the first screen.
- Rehearse once with a timer. If you run long, cut in this order: the label-check paragraph on slide 4 (the slide
  shows the 25 / 15 grid), then "We ran all of it on two models" on slide 3 (the slide still shows it).
- Say one number per point; the slides hold the rest. Avoid "McNemar", "Holm" and "kappa" unless asked; limits
  (our own claims, two policies, 124 claims) are on slide 9 for Q&A.
