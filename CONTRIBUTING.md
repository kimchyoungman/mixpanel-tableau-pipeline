# Contributing

Thanks for improving this project. Keep changes account-agnostic so other users
can run the pipeline with their own Mixpanel, Tableau, GitHub, and cloud
accounts.

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
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
python -m py_compile main.py src/*.py config/*.py
python main.py --help
python main.py --check-config
```

`--check-config` may fail when credentials are intentionally absent. That is
fine for local development, but the command should still run and print clear
diagnostics.
