# Supreme Court — Matters to Watch

Data behind `onecourt.in/sc/matters-to-watch.html`: a short list of important pending
Supreme Court matters with the court, bench and next date of hearing.

```
sc-cause-list (parsed SCI lists) ──► check_listings.py (GitHub Action, every 2 h) ──┐
LiveLaw / Bar & Bench / SCO / SCI ──► daily Claude routine (8 PM IST, weekdays) ────┼─► data/matters.json ──► page (raw.githubusercontent.com)
                                                                                    └─► data/history.json (every change, with source)
```

## Files

| File | What |
|---|---|
| `data/matters.json` | The watchlist. The page reads only this. |
| `data/history.json` | Append-only log: who changed what, old → new, source. Use it to trace or revert a wrong update. |
| `check_listings.py` | Finds watched matters in the SCI cause lists for today … +7 days and marks them `listed` with court, bench, item no. and PDF link. |
| `test_check_listings.py` | `python -m pytest -q` |

## A matter record

| Field | Meaning |
|---|---|
| `id` | Stable slug. Never change it. |
| `title`, `issue`, `parties` | Short name, one-line question, cause title. |
| `category` | Subject icon on the page: `elections` · `liberty` · `constitution` · `heritage` · `education` · `criminal` · `nuclear` · `rights` · `profession` · `environment` · `citizenship` · `tax` · `health`. |
| `case_nos` | Case numbers **as printed in SCI lists** (`W.P.(C) No. 276/2025`, `Diary No. 63858/2026`). Used for matching. |
| `match_parties` | Regexes tried against `"PETITIONER \| RESPONDENT"` in the list. Only distinctive names; prefer `case_nos`. |
| `court`, `bench` | e.g. `Chief Justice's Court`, `["Chief Justice", "Joymalya Bagchi J"]`. |
| `next_date` | `YYYY-MM-DD` or `null`. |
| `date_status` | `listed` (in an SCI cause list — set only by `check_listings.py`) · `fixed` (date in an order or a dated news report) · `tentative` (month or approximate) · `not-fixed` · `reserved` (judgment reserved) · `decided`. |
| `date_text` | Free text when there is no exact date ("November 2026 (day not fixed)"). |
| `last_hearing` | `{date, outcome}` |
| `listing` | Written by `check_listings.py` (court, judges, time, item, list_url, matched_by). |
| `sources` | `[{outlet, url, date}]`, newest first. |
| `note` | Short remark shown under the matter. |

## Rules for the daily routine (and for anyone editing by hand)

1. **Never invent a date, bench or case number.** Change one only with a dated source, and add that source to `sources`.
2. **A cause-list hit outranks news.** Do not overwrite a `listed` date that is today or later with a news date.
3. A news report's next date without a cause-list confirmation is `fixed` if it quotes the order ("list on 11 November"), otherwise `tentative`.
4. After a hearing date passes, find what happened (adjourned / part-heard / reserved / decided / new date) and update `last_hearing`, `next_date`, `date_status`. If nothing is reported yet, leave the record and set `note` to "Outcome of <date> hearing not yet reported".
5. Never delete a matter. A decided matter gets `date_status: "decided"` and the outcome in `last_hearing`; the page moves it to "Recently concluded".
6. Fill in missing `case_nos` when a source gives them (they make the cause-list check work).
7. Log only real changes (old ≠ new) — never write a history entry for an unchanged field. Log every change in `history.json` (`{at, id, fields: {f: {old, new}}, source, by: "routine"}`) and update `updated` in `matters.json`.
8. New matters are **not** added directly. On Mondays, open a GitHub issue "Proposed matters — <date>" listing candidates with sources; add them only after the owner approves.
