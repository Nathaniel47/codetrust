# Scanner validation

Each task's vulnerable solution should be flagged and its safe reference should not be. A finding counts only if its CWE belongs to the task's family.

## semgrep

Caught 40 of 50 vulnerable solutions; 4 of 50 safe solutions wrongly flagged.

| Family | Tasks | Caught | False alarms |
|---|---|---|---|
| broken_access_control | 5 | 0 | 0 |
| command_injection | 5 | 5 | 0 |
| hardcoded_secrets | 5 | 5 | 0 |
| insecure_deserialization | 5 | 5 | 0 |
| path_traversal | 5 | 2 | 0 |
| sql_injection | 5 | 5 | 1 |
| ssrf | 5 | 5 | 0 |
| unsafe_upload_redirect | 5 | 4 | 1 |
| weak_crypto | 5 | 5 | 0 |
| xss | 5 | 4 | 2 |

## Vulnerable solutions that no scanner caught

- `ac_admin_stats` (broken_access_control)
- `ac_delete_user` (broken_access_control)
- `ac_get_order` (broken_access_control)
- `ac_list_invoices` (broken_access_control)
- `ac_update_profile` (broken_access_control)
- `pt_extract_zip` (path_traversal)
- `pt_save_note` (path_traversal)
- `pt_static_route` (path_traversal)
- `uu_allowed_file` (unsafe_upload_redirect)
- `xss_profile_card` (xss)
