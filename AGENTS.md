# AGENTS.md

## Cursor Cloud specific instructions

### Architecture

This is a monorepo with two products:

1. **Ghostfolio** (NestJS backend + Angular frontend) — a wealth management platform
2. **AgentForge** (`agent/` directory) — a Python/FastAPI AI agent layer using LangChain + GPT-4o

### Infrastructure Services

PostgreSQL (15) and Redis are required and run via Docker:

```bash
sudo docker compose -f docker/docker-compose.dev.yml up -d
```

The Docker daemon must be started first in the Cloud VM environment (`sudo dockerd &>/tmp/dockerd.log &`), and requires `fuse-overlayfs` storage driver and `iptables-legacy` due to the nested container setup.

### Database

After starting PostgreSQL, initialize with `npm run database:setup` (runs `prisma db push` + `prisma db seed`). The `.env` file must exist (copy from `.env.dev` and fill in passwords).

### Running Services

- **API server**: `npm run start:server` (port 3333, health check: `GET /api/v1/health`)
- **Angular client**: `npm run start:client` (port 4200 via HTTPS, requires SSL certs in `apps/client/`)
- **Agent API** (optional): `cd agent && uvicorn src.main:app --reload --port 8000` (requires `OPENAI_API_KEY`)

### SSL Certificates

The Angular dev server requires SSL. Generate certs before first client start:

```bash
openssl req -x509 -newkey rsa:2048 -nodes -keyout apps/client/localhost.pem -out apps/client/localhost.cert -days 365 \
  -subj "/C=CH/ST=State/L=City/O=Organization/OU=Unit/CN=localhost"
```

### Standard Commands

See `DEVELOPMENT.md` for the full development guide. Key npm scripts are defined in `package.json`:

- **Lint**: `npm run lint`
- **Test**: `npm test` (uses dotenv-cli to load `.env.example`)
- **Format**: `npm run format:check` / `npm run format:write`

### Gotchas

- The first user created via "Get Started" in the UI gets the `ADMIN` role.
- Python agent tests (`agent/tests/`) require `OPENAI_API_KEY` to be set — they will fail at collection time without it.
- The `postinstall` script runs `prisma generate`, so Prisma client types are always up to date after `npm install`.
- The `.husky/pre-commit` hook runs lint and format checks; these are automatically set up by `npm install` via the `prepare` script.
- The `/home/ubuntu/.local/bin` directory must be on `PATH` for Python agent tools (uvicorn, pytest, etc.).
