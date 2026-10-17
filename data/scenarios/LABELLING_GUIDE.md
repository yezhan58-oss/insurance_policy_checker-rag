# Labelling guide

Rules for setting `gold_verdict` and `gold_sections` on every scenario. Written before labelling; both members
label by this page. If a case is not covered here, decide together, add the rule below, and note it in the
scenario's `notes`.

## The question being answered

"Under this policy wording, would this claim be paid?" Judge only from the policy text and the facts stated in
the scenario. Do not use outside knowledge of how insurers behave in practice, and do not assume facts that are
not stated (except the default assumptions below).

## Default assumptions (do not label insufficient_info for these)

- The policy was bought and the trip booked before the event, the premium is paid, and the trip is within the
  period of cover.
- The claimant is the insured person and will send the documents the policy asks for (written proof of delay,
  police report, receipts). A missing document is only a problem if the scenario says it does not exist.
- The plan tier (Premium / Business / First) is unknown. A label may depend on a limit only if that limit is the
  same on every plan (e.g. the S$1,000 laptop sub-limit); otherwise do not write the scenario.

## The four verdicts

| Verdict | Use when | FWD example |
| --- | --- | --- |
| `covered` | Every condition of a benefit is met and no exclusion applies. | "My flight from Singapore to Tokyo was delayed 7 hours by a typhoon. Can I claim?" Travel delay pays for 6 continuous hours or more; weather is not excluded. |
| `not_covered` | No benefit applies, a condition is not met, or an exclusion removes the whole claim. | "My flight was delayed 4 hours." Below the 6-hour threshold. Also: "The typhoon warning was already in the news when I bought the policy" (excluded as an event known before cover). |
| `partially_covered` | Part of the claimed loss is paid and part is not: some items or costs are excluded, or a stated sub-limit cuts the claim. | "My bag with a S$1,500 laptop and S$200 of clothes was stolen." The laptop/tablet sub-limit is S$1,000 on every plan, so the laptop is only paid in part. |
| `insufficient_info` | A fact that would change the verdict is missing, and no default assumption fills it. | "My flight was delayed. Can I claim?" The length of the delay decides the verdict and is not stated. |

### Tie-break rules

1. **Exclusion beats benefit.** If a benefit's conditions are met but an exclusion clearly applies, the verdict is
   `not_covered`.
2. **Missing fact vs failed condition.** If the scenario states a fact that fails a condition, it is
   `not_covered`. If the fact is simply absent, it is `insufficient_info`.
3. **A per-period payout is not partial.** "S$100 per 6 hours" being less than the traveller's real costs is
   still `covered`. Use `partially_covered` only when a named item, cost or amount in the claim is excluded or
   capped by a sub-limit.
4. **A false assumption in the question.** If the scenario assumes cover that does not exist ("my travel
   insurance covers my missed concert ticket, right?"), label by the policy, not by the assumption. Category:
   `tricky`.
5. **Two missing facts.** Still one verdict: `insufficient_info`. Name both facts in `notes`.

## Choosing gold_sections

List the section IDs a careful assessor must read to reach the verdict, and only those.

- Always include the benefit section that the claim falls under (e.g. `fwd:travel_delay`), even for
  `not_covered`, if a benefit was the natural place to look.
- Add a definition only if the verdict depends on the defined term's meaning (e.g.
  `fwd:definitions:scheduled_public_transport` when the trip was on a ferry or a private car).
- Add an exclusion only if it decides the verdict (e.g.
  `fwd:general_exclusions:events_that_happen_before_you_book_or_take_up_cover`).
- Do not add the benefit-limits table (`fwd:benefit_limits:*`) unless an amount or sub-limit decides the verdict.
- For `insufficient_info`, list the sections that make the missing fact matter.
- Usually 1 to 3 IDs. More than 3 usually means the scenario tests too many things; consider splitting it.

Use the exact IDs from `data/index/sections.jsonl` (rebuild with `python -m src.ingest --no-embed`).

## Category

| Category | Meaning |
| --- | --- |
| `single_section` | One benefit section decides it. |
| `needs_definition` | The verdict turns on a defined term. |
| `needs_exclusion` | The verdict turns on an exclusion or condition outside the benefit section. |
| `tricky` | False assumption, missing detail, or wording designed to mislead. Most `insufficient_info` items go here. |

## When reviewing a draft

1. Read the scenario, then the actual clause text (not the draft's intended answer).
2. Decide the verdict yourself by the rules above, then compare with the draft.
3. Accept, change the verdict or sections, or delete. Delete a scenario if it is ambiguous even after reading the
   policy, or if it needs facts the policy cannot settle (such as amounts that depend on the plan tier).
4. If you change a label, write one line in `notes` saying why.
