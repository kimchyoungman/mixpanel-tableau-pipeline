# Contributing

Thanks for improving this project. Keep changes account-agnostic so other users
can run the pipeline with their own Mixpanel, Tableau, GitHub, and cloud
accounts.

## Development

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install ".[tableau,gcs,dev]"
python main.py --check-config
```

## Guidelines

- Do not commit `.env`, logs, state files, generated `.hyper` extracts, or
  credentials.
- Keep organization-specific defaults out of code and examples.
- Prefer environment variables or CLI flags for account-specific settings.
- Keep GitHub Actions manual by default unless a scheduled workflow is clearly
  opt-in.
- Run these checks before opening a pull request:

```bash
ruff check .
pytest --cov=src --cov=config --cov-report=term-missing
python main.py --help
python main.py --check-config
```

`--check-config` may fail when credentials are intentionally absent. That is
fine for local development, but the command should still run and print clear
diagnostics.

## Pull Requests

- Keep each pull request focused and explain any user-visible behavior change.
- Add or update tests for bug fixes and new behavior.
- Never include real event payloads, generated extracts, credentials, or logs in
  fixtures or screenshots.
- Confirm CI passes on every supported Python version before requesting review.
