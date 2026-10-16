# Policy document snapshot

The policy PDFs are committed so every machine ingests exactly the same files. If a file is
re-downloaded and its SHA-256 changes, re-check `table_transcriptions.yaml` and the parsed sections.

| Policy | File | Source URL | Downloaded | Size | SHA-256 |
| --- | --- | --- | --- | --- | --- |
| FWD Travel Insurance policy wording (V4, Apr 2024; 45 PDF pages, printed pages 1-43) | `fwd_travel_policy_wording.pdf` | https://www.fwd.com.sg/wp-content/uploads/2024/04/FWD-Travel-Insurance-Policy-Wording.pdf | 2026-10-16 10:20 UTC | 1,932,321 bytes | `b7f4ffe30ad484a4fb434dda9ec4529e394249804393bd08a859bdf5bc3f0f76` |

Notes

- Page numbers in section metadata are 1-based **PDF** pages (FWD printed page = PDF page - 2).
- FWD prints its tick/cross coverage tables as images, so those tables (and a few multi-column
  tables whose cells interleave when extracted) are hand-transcribed in `table_transcriptions.yaml`.
