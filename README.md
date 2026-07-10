# Mixpanel to Tableau Hyper Pipeline

[![CI](https://github.com/kimchyoungman/mixpanel-tableau-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/kimchyoungman/mixpanel-tableau-pipeline/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Export raw Mixpanel events, flatten their properties, and write them to a
Tableau Hyper extract. Run the pipeline locally, publish directly to Tableau
Cloud, and keep incremental progress in a local file or Google Cloud Storage.

```text
Mixpanel Data Export API
          │
          ▼
  flatten · filter · deduplicate
          │
          ▼
    Tableau .hyper extract ──────► Tableau Cloud (optional)
          │
          └──────────────────────► local file or GCS state (optional)
```

> [!IMPORTANT]
> Mixpanel exports can contain user identifiers and other personal data. Never
> commit credentials, logs, state files, event payloads, or generated Hyper
> extracts. See [Security](#security) before sharing output files.

## What it does

- Streams events from the Mixpanel Data Export API.
- Flattens the event and its top-level properties into Tableau-compatible columns.
- Deduplicates events using `$insert_id` when available.
- Filters by event name, property value, or selected columns.
- Processes large date ranges in day- or month-based chunks.
- Produces a valid empty Hyper extract when a query returns no events.
- Publishes extracts to Tableau Cloud using a personal access token.
- Tracks incremental progress locally or at a `gs://` path.
- Runs manually or on a schedule through GitHub Actions or Cloud Run Jobs.

## Requirements

- Python 3.11 or newer
- A Mixpanel project ID and API secret
- A Tableau Cloud personal access token only when publishing
- Google Cloud credentials only when using GCS-backed state

## Quick start

Clone the repository and install the local Hyper generation dependencies:

```bash
git clone https://github.com/kimchyoungman/mixpanel-tableau-pipeline.git
cd mixpanel-tableau-pipeline

python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install .
```

Create a local configuration file:

```bash
cp .env.example .env
```

Set the required values in `.env`:

```ini
MIXPANEL_API_SECRET=your_mixpanel_api_secret
MIXPANEL_PROJECT_ID=your_mixpanel_project_id
MIXPANEL_TIMEZONE=UTC
```

Validate the configuration without calling an external API:

```bash
mixpanel-tableau --check-config
```

Export a date range:

```bash
mixpanel-tableau \
  --from-date 2026-01-01 \
  --to-date 2026-01-31
```

The generated extract is written to `./output` unless `--output` or
`OUTPUT_DIR` specifies another location.

## Installation options

| Use case | Installation command |
| --- | --- |
| Local Hyper generation | `pip install .` |
| Tableau Cloud publishing | `pip install ".[tableau]"` |
| GCS-backed state | `pip install ".[gcs]"` |
| Tableau and GCS | `pip install ".[tableau,gcs]"` |
| Contributor environment | `uv sync --all-extras --frozen --no-editable` |

The committed `uv.lock` provides a reproducible contributor and CI dependency
set. `requirements.txt` remains available for conventional deployment systems.

## Configuration

Configuration is loaded from environment variables and an optional `.env` file
in the directory where the command is run.

### Mixpanel

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `MIXPANEL_API_SECRET` | Yes | — | Mixpanel Data Export API secret |
| `MIXPANEL_PROJECT_ID` | Yes | — | Mixpanel project ID |
| `MIXPANEL_TIMEZONE` | No | `UTC` | Timezone used for timestamps and `--yesterday` |

### Local output and state

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `OUTPUT_DIR` | No | `./output` | Directory for generated Hyper files |
| `LOG_DIR` | No | `./logs` | Directory for pipeline logs |
| `STATE_PATH` | No | `./state.json` | Local state file or `gs://bucket/path/state.json` |

Relative paths are resolved from the directory where the CLI is run.

### Tableau Cloud

These values are required only with `--publish`.

| Variable | Required for publishing | Default | Description |
| --- | --- | --- | --- |
| `TABLEAU_SERVER_URL` | Yes | — | Tableau Cloud pod URL |
| `TABLEAU_SITE_ID` | Yes | — | Tableau site content URL / site ID |
| `TABLEAU_TOKEN_NAME` | Yes | — | Personal access token name |
| `TABLEAU_TOKEN_VALUE` | Yes | — | Personal access token secret |
| `TABLEAU_PROJECT_NAME` | No | `Default` | Target Tableau project |
| `TABLEAU_DATASOURCE_NAME` | No | `mixpanel_hyper` | Published datasource name |

Validate Mixpanel and Tableau settings together:

```bash
mixpanel-tableau --check-config --publish
```

## Usage

### Select a date range

```bash
mixpanel-tableau \
  --from-date 2026-01-01 \
  --to-date 2026-01-31 \
  --output ./output/january-events.hyper
```

Export yesterday in `MIXPANEL_TIMEZONE`:

```bash
mixpanel-tableau --yesterday
```

### Select events and properties

Export only selected event names:

```bash
mixpanel-tableau \
  --from-date 2026-01-01 \
  --to-date 2026-01-31 \
  --events "Page View" "Button Click"
```

Include selected event properties:

```bash
mixpanel-tableau \
  --from-date 2026-01-01 \
  --to-date 2026-01-31 \
  --columns mp_os mp_browser plan
```

Or load one property name per line from a file:

```bash
mixpanel-tableau \
  --from-date 2026-01-01 \
  --to-date 2026-01-31 \
  --column-file columns.txt
```

Mixpanel property names are normalized to lowercase. A leading `$` becomes
`mp_`, while spaces, hyphens, and periods become underscores. For example,
`$browser` becomes `mp_browser`. Nested dictionaries and lists are stored as JSON
text rather than expanded into additional columns.

### Filter events

Filters use flattened property names and an exact `key=value` comparison.
Multiple filters are combined with AND logic.

```bash
mixpanel-tableau \
  --from-date 2026-01-01 \
  --to-date 2026-01-31 \
  --filter "mp_country_code=US" \
  --filter "plan=pro"
```

### Process a large range in chunks

```bash
mixpanel-tableau \
  --from-date 2025-01-01 \
  --to-date 2025-12-31 \
  --chunked \
  --chunk-days 7
```

Use `--chunk-months 1` instead when monthly chunks are more appropriate.

### Run incrementally

```bash
mixpanel-tableau --auto-incremental
```

The first incremental run defaults to yesterday. Later runs start on the day
after the last successfully recorded date. To store state in GCS:

```ini
STATE_PATH=gs://your-bucket/mixpanel-tableau/state.json
```

The runtime identity must have read and write access to that object. GCS state
load or save failures stop the pipeline rather than silently restarting progress.

### Publish to Tableau Cloud

```bash
mixpanel-tableau \
  --from-date 2026-01-01 \
  --to-date 2026-01-31 \
  --publish \
  --project-name Analytics \
  --datasource-name mixpanel_events \
  --tableau-overwrite
```

Publishing uses append mode by default. Use `--tableau-overwrite` to replace the
existing datasource.

## CLI reference

| Option | Description |
| --- | --- |
| `--from-date YYYY-MM-DD` | First export date; requires `--to-date` |
| `--to-date YYYY-MM-DD` | Last export date |
| `--yesterday` | Export yesterday in `MIXPANEL_TIMEZONE` |
| `--auto-incremental` | Continue from the saved state through yesterday |
| `--check-config` | Validate configuration without exporting |
| `--output`, `-o` | Output Hyper file path |
| `--events`, `-e` | Event names to export |
| `--columns`, `-c` | Event properties to include |
| `--column-file` | File containing one property name per line |
| `--filter`, `-f` | Exact property filter in `key=value` form; repeatable |
| `--chunked` | Enable chunked processing |
| `--chunk-days` | Number of days per chunk |
| `--chunk-months` | Number of months per chunk |
| `--publish` | Publish the generated extract to Tableau Cloud |
| `--project-name` | Override the target Tableau project |
| `--datasource-name` | Override the Tableau datasource name |
| `--tableau-overwrite` | Replace instead of append during publishing |
| `--verbose`, `-v` | Enable verbose console logging |

Run `mixpanel-tableau --help` for the command's authoritative option list.

## Automation

### GitHub Actions

The included `daily_etl.yml` workflow is manual by default so a public fork
cannot start exporting data unexpectedly.

Configure these repository secrets:

- `MIXPANEL_API_SECRET`
- `MIXPANEL_PROJECT_ID`
- `TABLEAU_SERVER_URL`, `TABLEAU_SITE_ID`, `TABLEAU_TOKEN_NAME`, and
  `TABLEAU_TOKEN_VALUE` when publishing

Optional repository variables:

- `MIXPANEL_TIMEZONE`
- `TABLEAU_PROJECT_NAME`
- `TABLEAU_DATASOURCE_NAME`
- `PUBLISH_TO_TABLEAU=true` for scheduled publishing

When publishing is disabled, the workflow stores `events.hyper` as a GitHub
Actions artifact for seven days. To run on a schedule, add a `schedule` trigger
only after configuring secrets for that repository.

### Docker

Local secrets and generated data are excluded from the Docker build context.
The container runs as a non-root user.

```bash
docker build -t mixpanel-tableau-pipeline .
docker run --rm \
  --env-file .env \
  -v "$PWD/output:/app/output" \
  mixpanel-tableau-pipeline --yesterday
```

### Google Cloud

`cloudbuild.yaml` builds the image into Artifact Registry. Create the configured
repository before the first build and store runtime credentials in Secret
Manager rather than in the image or build configuration.

See [DEPLOYMENT.md](DEPLOYMENT.md) for GitHub Actions, Artifact Registry, runtime
configuration, and local scheduler guidance.

## Project structure

```text
mixpanel-tableau-pipeline/
├── .github/
│   ├── ISSUE_TEMPLATE/
│   └── workflows/
│       ├── ci.yml
│       └── daily_etl.yml
├── config/
│   └── settings.py
├── src/
│   ├── data_transformer.py
│   ├── hyper_writer.py
│   ├── mixpanel_client.py
│   ├── pipeline.py
│   ├── state_manager.py
│   └── tableau_publisher.py
├── tests/
├── Dockerfile
├── cloudbuild.yaml
├── main.py
├── pyproject.toml
└── uv.lock
```

## Development

Create the locked contributor environment and run the same checks used by CI:

```bash
uv sync --all-extras --frozen --no-editable
.venv/bin/ruff check .
.venv/bin/pytest --cov=src --cov=config --cov-report=term-missing
```

CI runs linting, tests, and CLI smoke checks on Python 3.11 and 3.12. See
[CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request.

## Troubleshooting

### The export completed but contains zero rows

This is valid. A date range or filter with no matching events produces an empty
Hyper extract containing the standard `Extract.events` table.

### Mixpanel returns an authentication or authorization error

Confirm that `MIXPANEL_API_SECRET` belongs to `MIXPANEL_PROJECT_ID` and that the
credential can access the Data Export API. Run `--check-config` to catch missing
values before starting a request.

### Timestamps or `--yesterday` use the wrong day

Set `MIXPANEL_TIMEZONE` to a valid timezone such as `UTC`, `Asia/Seoul`, or
`America/New_York`.

### GCS state cannot be loaded or saved

Confirm Application Default Credentials are available and that the runtime
identity has object read/write permissions for the configured bucket path.

## Security

Do not publish generated extracts without reviewing their contents. Mixpanel
events may contain identifiers, URLs, campaign parameters, and other personal or
commercially sensitive data.

Report vulnerabilities privately through the repository's **Security** tab.
See [SECURITY.md](SECURITY.md) for the full policy.

## Contributing

Issues and pull requests are welcome. Keep examples account-agnostic, add tests
for behavior changes, and never use production credentials or real event data in
fixtures. See [CONTRIBUTING.md](CONTRIBUTING.md) and
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## License

Released under the [MIT License](LICENSE).
