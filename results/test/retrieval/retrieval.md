# Retrieval only: one search with the claim text (test split, 124 claims)

| Method | k | Gold recall | All gold found | Benefit | Definition | Exclusion | Condition |
|---|---|---|---|---|---|---|---|
| dense | 5 | 0.66 | 0.53 | 0.76 (96/127) | 0.00 (0/24) | 0.26 (7/27) | 0.00 (0/1) |
| dense | 10 | 0.75 | 0.60 | 0.84 (107/127) | 0.04 (1/24) | 0.41 (11/27) | 0.00 (0/1) |
| bm25 | 5 | 0.59 | 0.48 | 0.58 (74/127) | 0.38 (9/24) | 0.41 (11/27) | 1.00 (1/1) |
| bm25 | 10 | 0.69 | 0.58 | 0.70 (89/127) | 0.38 (9/24) | 0.67 (18/27) | 1.00 (1/1) |
| hybrid | 5 | 0.64 | 0.50 | 0.72 (91/127) | 0.00 (0/24) | 0.30 (8/27) | 0.00 (0/1) |
| hybrid | 10 | 0.76 | 0.65 | 0.83 (105/127) | 0.17 (4/24) | 0.59 (16/27) | 1.00 (1/1) |

_k = number of chunks retrieved (A0 uses 5). Type columns: recall of gold sections of that type (found / total). Dense at k = 5 is A0's own search. BM25 and the hybrid are analysis only._
