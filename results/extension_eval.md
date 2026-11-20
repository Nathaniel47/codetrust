# Extension evaluation

Rules were written from the 20 dev tasks; the 30 test tasks are held out. A file counts as
flagged when at least one rule fires. Positives are vulnerable solutions.

| Set | TP | FP | FN | TN | Precision | Recall |
|---|---|---|---|---|---|---|
| Task solutions, dev | 17 | 5 | 3 | 15 | 77% | 85% |
| Task solutions, test | 23 | 4 | 7 | 26 | 85% | 77% |
| scripted-60 generations, dev | 105 | 12 | 21 | 62 | 90% | 83% |
| scripted-60 generations, test | 133 | 9 | 42 | 116 | 94% | 76% |

## Missed on the test tasks

- `ac_admin_stats`
- `ac_list_invoices`
- `ac_update_profile`
- `pt_extract_zip`
- `pt_save_note`
- `pt_static_route`
- `uu_allowed_file`

## False alarms on the test tasks

- ssrf_check_webhook: request-to-variable-url
- ssrf_image_size: request-to-variable-url
- ssrf_import_feed: request-to-variable-url
- xss_profile_card: html-built-from-fstring

Caveats: one person wrote both the tasks and the rules, so the dev/test split limits but does
not remove tuning to the benchmark. Pattern matching sees one line at a time and cannot follow
data flow or detect missing checks (access control), so those families are expected misses.
