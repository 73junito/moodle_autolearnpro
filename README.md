# moodle_autolearnpro

[![CI](https://github.com/73junito/moodle_autolearnpro/actions/workflows/devcontainer-validate.yml/badge.svg)](https://github.com/73junito/moodle_autolearnpro/actions/workflows/devcontainer-validate.yml)

## First-time setup

Quick start (recommended):

- Install Docker and VS Code with the Remote - Containers extension.
- Clone the repo and open it in VS Code.
- Choose **Reopen in Container** (Dev Containers will run `make bootstrap`).

Or run locally:

```bash
git clone <repo-url>
cd moodle_autolearnpro
make bootstrap
```

The `make bootstrap` target brings up core services, installs Python dependencies inside the `app` container, and runs project migrations (if configured).

## Troubleshooting & Devcontainer notes

If the Dev Container or compose setup doesn't behave as expected, try these quick checks:

- Ports: ensure forwarded ports (e.g. `8000`, `8443`, `8080`) are not in use on the host and are allowed by your firewall.
- Bind mounts & permissions: files created by the container may be owned by `root` — use `sudo chown` on your workspace or run the container as your user if needed.
- Docker socket access: if you need to run Docker from inside the container, bind-mount `/var/run/docker.sock` carefully and be aware of the security implications.
- Rebuild vs restart: changes to Dockerfiles or `docker-compose` require a full rebuild (`Dev Containers: Rebuild and Reopen in Container` or `$(COMPOSE_DEV) up --build`). A restart will not pick up image changes.
- If `make bootstrap` fails: inspect logs with `docker compose -f docker-compose.yml -f docker-compose.dev.yml logs -f` and re-run the failing step inside the `app` service via `make shell`.

If you still hit a blocker, open an issue describing your OS, Docker version, and the exact command you ran.

### Using Docker inside the Dev Container

This project mounts the host Docker socket into the devcontainer so you can run Docker commands from inside the container.

- Why it works: the container uses the host's Docker daemon via `/var/run/docker.sock`. You do not need to run a Docker engine inside the container.
- Tip: commands like `docker ps` or `docker build` will operate on your host Docker daemon — be careful, these affect host containers and images.
- If `docker` is missing in the container, install the CLI (`apt-get update && apt-get install -y docker.io`) or use the host's docker binary.
- Permissions: if you see permission errors against `/var/run/docker.sock`, ensure your user is in the `docker` group on the host or run privileged commands from the host.
- Rebuild the devcontainer when changing mounts or `devcontainer.json`: Command Palette → **Dev Containers: Rebuild and Reopen in Container**.

If you want a `.devcontainer/README.md` with quick commands, I can add that too.

## Quick commands

Common commands you'll use during development:

- Start the dev environment (foreground):

```bash
make dev
```

- Start services in background:

```bash
make up
```

- Bootstrap the environment (first run or rebuild):

```bash
make bootstrap
```

- Open a shell in the `app` container:

```bash
make shell
```

- Run tests inside the container:

```bash
make test
```

- See live logs for the compose services:

```bash
make logs
```

- Use Docker inside the devcontainer (affects host Docker daemon):

```bash
docker ps
docker compose -f docker-compose.yml -f docker-compose.dev.yml logs -f app
```

If you prefer these commands in a separate `.devcontainer/README.md`, tell me and I'll add it.

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

## Deployment via GitHub Actions

This repository includes automated deployment workflows under `.github/workflows/`.

### Required Secrets
Set these in GitHub → Settings → Secrets and variables → Actions:

- `SSH_HOST` — server hostname or IP
- `SSH_USER` — SSH user with sudo access for deploy commands
- `SSH_PRIVATE_KEY` — private key for `SSH_USER` (PEM format)
- `SSH_PORT` — optional (defaults to 22)

### Running a Deployment
You can trigger a deploy in two ways:

1. Push to `main`
	- Automatically runs the full rsync deployment workflow.

2. Manual trigger (workflow_dispatch)
	- Go to GitHub → Actions → *Deploy Moodle (rsync + opcache reset + purge + upgrade)* → **Run workflow**.
	- Optionally set the `run_upgrade` input to `true` to run Moodle's CLI upgrade after deployment.

Example quick-run (via GitHub UI):

```
run_upgrade: true
```

Notes:
- Keep `SSH_PRIVATE_KEY` safe; add the corresponding public key to `~/.ssh/authorized_keys` for `SSH_USER` on the server.
- Ensure `SSH_USER` has passwordless sudo for the specific commands used by the workflows (`systemctl start moodle-opcache-reset.service`, running Moodle CLI as `www-data`).
