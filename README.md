# moodle_autolearnpro

## Deployment Workflows

This repository includes two GitHub Actions workflows under `.github/workflows/`:

### 1. deploy-moodle-opcache.yml
Runs maintenance tasks on the server:
- Resets PHP opcache via `moodle-opcache-reset.service`
- Purges Moodle caches

Trigger:
- Manually via the Actions UI (workflow_dispatch)

### 2. deploy-moodle-rsync.yml
Performs a full Moodle deployment:
- Rsyncs the repository to the server (`--delete` enabled)
- Resets opcache
- Purges Moodle caches
- Optionally runs Moodle's DB upgrade (`upgrade.php`)

Trigger:
- On push to `main`
- Manually via `workflow_dispatch` (supports `run_upgrade` input)

### Required Secrets
Set these in GitHub → Settings → Secrets and variables → Actions:

- `SSH_HOST` — server hostname or IP
- `SSH_USER` — SSH user with sudo access
- `SSH_PRIVATE_KEY` — private key for the SSH user
- `SSH_PORT` (optional, defaults to 22)

### Manual Run Options
When triggering `deploy-moodle-rsync.yml` via *workflow_dispatch*:

- `run_upgrade: true` — run Moodle’s CLI upgrade
- `run_upgrade: false` — skip DB upgrade

If you want a longer explanation or an example layout for deploy paths and secrets, tell me and I'll add it.
