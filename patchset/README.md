Patchset: autolearnpro review patches

Contents:
- 0001..0015: review patches that add `autocomplete` attributes to password inputs and add `accept` handling for file inputs.
- smoke_check.php: CLI smoke-test that validates `assign` file submission accepted types fallback, draft file creation, file_storage verification, and messaging.

How to use:
1. Inspect the patches in `patchset/`.
2. Apply patches to a Moodle checkout (review-only).
3. To run the smoke-check locally on the Moodle instance, copy `smoke_check.php` into `local/smoketests/` and run as web user:

   sudo -u www-data php /var/www/html/moodle/local/smoketests/smoke_check.php --run-expanded

Test summary (from this environment):
- `get_file_options()` returned `accepted_types => '*'` (fallback present).
- Draft file written and verified (filename, filesize, content, mime).
- Messaging send succeeded.

Notes:
- The script avoids `add_moduleinfo()` (web-only); it will attempt plugin save only if an `assign` instance exists.
- These patches are low-risk UX/security improvements; include them as review diffs.

