# Report draft: Data and labelling (Member B)

Placeholders in [brackets] are filled after the 15 disagreements are resolved with Member A.

## Policy documents

We use two real, publicly available Singapore travel insurance policy wordings: FWD Travel Insurance (V4, April 2024; 45 PDF pages) and MSIG TravelEasy (70 pages, 52 benefit sections). The PDFs were downloaded on 16 and 17 October 2026 and committed with their SHA-256 hashes, so every machine ingests identical files. The two documents differ in structure, which tests whether each approach generalises across layouts: FWD places definitions at the back and prints its coverage tables as images (these tables were hand-transcribed), while MSIG is text-only and cross-references its general exclusions by number from each benefit section.

## Ingestion

Each policy is split along its own headings into 284 sections (FWD 131, MSIG 153), each with a stable ID of the form `{policy}:{section}` (e.g. `fwd:travel_delay`, `msig:section_33`) and a type: benefit (93), definition (66), condition (56), exclusion (46) or other (23). Sections of up to 500 words stay whole; longer ones are packed into chunks of about 400 words with a 50-word overlap, giving 323 chunks that all keep their section ID. Chunks are embedded with `BAAI/bge-small-en-v1.5` on CPU and stored in one Chroma collection shared by every approach. Ingestion is deterministic, so both members and the cluster rebuild an identical index. Defined terms are also stored in a lookup table so that the definition tool can fetch a definition without search.

## Scenarios

We built 156 claim scenarios by construction rather than collecting real claims, which are not public. For each scenario an LLM was given one specific policy clause and asked to write a short first-person claim designed to land on a chosen verdict, recording the source clause, an intended verdict and the sections that decide it. Scenarios were written in sets around the same clause so that small changes in the facts flip the answer (for example, a 7-hour delay is covered, a 4-hour delay is not, and "my flight was delayed" is insufficient_info).

Each scenario carries one of four verdicts: covered, not_covered, partially_covered (part of the claimed loss is excluded or capped by a sub-limit) and insufficient_info (a fact that would change the verdict is missing). It also has a category: single_section (one clause decides it), needs_definition, needs_exclusion, or tricky (false assumptions, missing details or misleading wording).

## Labelling

Because the drafts come from an LLM, grading the tested models against the drafter's own answers would bias the results, so no intended answer became a gold label without human review. Before reviewing, Member B wrote a one-page labelling guide that defines the four verdicts with an example each, sets default assumptions (for example, the policy was bought before the trip and required documents will be supplied), and gives tie-break rules: an exclusion that clearly applies beats a benefit; a stated fact that fails a condition gives not_covered, while an absent fact gives insufficient_info; a per-period payout below real costs is still covered.

Member B then reviewed every draft against the actual clause text in a small Streamlit labelling page, accepting, correcting or deleting it. Of 156 drafts, 143 were accepted unchanged, 1 was corrected and 12 were deleted (all not_covered drafts that repeated a pattern already tested by another scenario, removed to keep the verdict mix balanced), leaving 144 scenarios. These were split with a fixed seed into a 20-scenario dev set (10 per policy), used only for prompt tuning, and a 124-scenario test set (80 FWD, 44 MSIG), scored once at the end.

| | Dev | Test |
|---|---|---|
| Scenarios (FWD / MSIG) | 20 (10 / 10) | 124 (80 / 44) |
| covered / not_covered / partially / insufficient | 5 / 6 / 4 / 5 | 46 / 53 / 14 / 11 |
| single_section / definition / exclusion / tricky | 8 / 3 / 5 / 4 | 65 / 20 / 25 / 14 |

The test set is skewed towards FWD and single_section scenarios compared with our 50/50 and 40% targets, because more FWD drafts survived review; we report per-category results so that this does not hide weaknesses on harder categories.

## Blind check

To measure how reliable the gold labels are, Member A labelled 40 random test scenarios blind, without seeing the drafts or Member B's labels. Agreement was moderate: 25/40 on the four-way verdict (Cohen's kappa 0.46, 95% bootstrap CI 0.24 to 0.64) and 30/40 on the binary covered-or-not split (kappa 0.50, CI 0.21 to 0.75). The two labellers chose at least one common gold section in 39 of 40 cases, so the disagreements were about how to read the clause, not which clause applies. Most disagreements followed one pattern: in six cases the blind label was insufficient_info where a stated fact or a named exclusion decides the claim under the guide's tie-break rules. The 15 disagreements were resolved together against the policy text: [N] kept Member B's label, [N] took Member A's label, and [N] scenarios were [reworded / removed]. [Guide change, if any.] The test set was then frozen on [date].

Report wording: "Scenarios were drafted by an LLM from specific policy clauses and verified by a human; a second member labelled a 40-scenario subset blind (Cohen's kappa = 0.46 four-way, 0.50 binary)."
