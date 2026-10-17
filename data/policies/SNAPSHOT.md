# Policy document snapshot

The policy PDFs are committed so every machine ingests exactly the same files. If a file is
re-downloaded and its SHA-256 changes, re-check `table_transcriptions.yaml` and the parsed sections.

| Policy | File | Source URL | Downloaded | Size | SHA-256 |
| --- | --- | --- | --- | --- | --- |
| FWD Travel Insurance policy wording (V4, Apr 2024; 45 PDF pages, printed pages 1-43) | `fwd_travel_policy_wording.pdf` | https://www.fwd.com.sg/wp-content/uploads/2024/04/FWD-Travel-Insurance-Policy-Wording.pdf | 2026-10-16 10:20 UTC | 1,932,321 bytes | `b7f4ffe30ad484a4fb434dda9ec4529e394249804393bd08a859bdf5bc3f0f76` |
| MSIG TravelEasy / TravelEasy Pre-Ex insurance policy (QTD052510, PDF created 26 Sep 2025; 70 pages, 52 benefit sections) | `msig_traveleasy_policy.pdf` | https://www.msig.com.sg/sites/msig_sg/files/downloads/traveleasy_policy.pdf | 2026-10-17 06:59 UTC | 1,081,779 bytes | `9aa3138d4e291f20b085a15a8c8ef9dbc7fc914c3ce7b7265ec058ad7a15e50b` |

Notes

- Page numbers in section metadata are 1-based **PDF** pages (FWD printed page = PDF page - 2).
- FWD prints its tick/cross coverage tables as images, so those tables (and a few multi-column
  tables whose cells interleave when extracted) are hand-transcribed in `table_transcriptions.yaml`.
- MSIG has no images: everything is parsed from the text layer (MSIG page = PDF page). Its plan
  tables are rendered as `label [Lite Plan ...; Standard Plan ...]`, and merged "Not covered" cells
  are applied to every row they span.
