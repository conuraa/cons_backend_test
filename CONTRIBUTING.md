# Contributing to cons_backend

## Branch Strategy

- `main` — production-ready code, protected
- `develop` — integration branch for features
- `feature/*` — feature branches (from develop)
- `fix/*` — bugfix branches (from develop or main)

## Workflow

1. Create a branch from `develop`:
   ```bash
   git checkout develop
   git pull
   git checkout -b feature/my-feature
   ```

2. Make changes, commit with clear messages:
   ```bash
   git commit -m "feat: add user notification endpoint"
   ```

3. Push and create a PR to `develop`:
   ```bash
   git push -u origin feature/my-feature
   ```

4. CI must pass before merge
5. After review, merge to `develop`
6. Release: `develop` -> `main` via PR

## Commit Message Format

```
type: short description

type = feat | fix | refactor | docs | test | chore
```

## Code Style

- Python 3.11+
- Linting: `ruff check .`
- Formatting: `ruff format .`
- Config: `ruff.toml`

## Docker

Build locally:
```bash
docker compose build
docker compose up -d
```

## Testing

```bash
pip install -r requirements-test.txt
pytest
```
