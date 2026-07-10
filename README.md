# Mixpanel to Tableau Hyper Pipeline

Export Mixpanel event data and convert it into a Tableau `.hyper` extract.
The pipeline can generate local Hyper files, publish them to Tableau Cloud, and
track incremental progress locally or in Google Cloud Storage.

## Features

- Export raw events from the Mixpanel Data Export API.
- Flatten event properties into Tableau-compatible columns.
- Write Tableau Hyper extracts.
- Filter by event name, property values, and selected columns.
- Process large date ranges in chunks.
- Optionally publish extracts to Tableau Cloud.
- Optionally store incremental state in a local file or a `gs://` path.

## Requirements

- Python 3.11+
- Mixpanel API secret and project ID
- Tableau Cloud personal access token, only when using `--publish`
- Google Cloud credentials, only when using a `gs://` `STATE_PATH`

## Installation

```bash
git clone https://github.com/kimchyoungman/mixpanel-tableau-pipeline.git
cd mixpanel-tableau-pipeline
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install ".[tableau,gcs]"
```

The `tableau` extra enables Tableau Cloud publishing and the `gcs` extra enables
GCS-backed incremental state. For local Hyper generation only, use
`pip install .`.

For a reproducible contributor environment using the committed lock file:

```bash
uv sync --all-extras --frozen --no-editable
```

## Configuration

Copy the example environment file and fill in your own values:

```bash
cp .env.example .env
```

Required:

```ini
MIXPANEL_API_SECRET=
MIXPANEL_PROJECT_ID=
MIXPANEL_TIMEZONE=UTC
```

Optional local paths:

```ini
OUTPUT_DIR=./output
LOG_DIR=./logs
STATE_PATH=./state.json
```

Relative paths are resolved from the directory where the CLI is run. This is
also where the default `output`, `logs`, and `state.json` paths are created.

Optional Tableau Cloud publishing:

```ini
TABLEAU_SERVER_URL=https://your-pod.online.tableau.com
TABLEAU_SITE_ID=
TABLEAU_TOKEN_NAME=
TABLEAU_TOKEN_VALUE=
TABLEAU_PROJECT_NAME=Default
TABLEAU_DATASOURCE_NAME=mixpanel_hyper
```

Optional GCS-backed state:

```ini
STATE_PATH=gs://your-bucket/path/state.json
```

When `STATE_PATH` uses `gs://`, the runtime must have Google Cloud credentials
with permission to read and write that object.

Validate configuration before exporting data:

```bash
python main.py --check-config
```

Validate Tableau publishing settings too:

```bash
python main.py --check-config --publish
```

## Usage

Generate a Hyper file for a date range:

```bash
python main.py --from-date 2024-01-01 --to-date 2024-01-31
```

If the export or filters return no events, the command still creates a valid
empty Hyper extract with the standard `Extract.events` schema.

Set a specific output file:

```bash
python main.py --from-date 2024-01-01 --to-date 2024-01-31 --output ./output/events.hyper
```

Export specific events:

```bash
python main.py --from-date 2024-01-01 --to-date 2024-01-31 --events "Page View" "Button Click"
```

Filter by flattened property values:

```bash
python main.py --from-date 2024-01-01 --to-date 2024-01-31 --filter "mp_country_code=US"
```

Include selected columns:

```bash
python main.py --from-date 2024-01-01 --to-date 2024-01-31 --columns "mp_os" "mp_browser"
```

Load selected columns from a file:

```bash
python main.py --from-date 2024-01-01 --to-date 2024-01-31 --column-file columns.txt
```

Process large ranges in chunks:

```bash
python main.py --from-date 2024-01-01 --to-date 2024-12-31 --chunked --chunk-days 7
```

Run an incremental daily export:

```bash
python main.py --auto-incremental
```

Publish to Tableau Cloud:

```bash
python main.py --from-date 2024-01-01 --to-date 2024-01-31 --publish --tableau-overwrite
```

## CLI Options

| Option | Description |
| --- | --- |
| `--from-date` | Start date in `YYYY-MM-DD` format |
| `--to-date` | End date in `YYYY-MM-DD` format |
| `--yesterday` | Export yesterday in `MIXPANEL_TIMEZONE` |
| `--check-config` | Validate configuration without exporting data |
| `--auto-incremental` | Start from the saved state and run through yesterday |
| `--output`, `-o` | Output `.hyper` path |
| `--events`, `-e` | Event names to export |
| `--columns`, `-c` | Event properties to include |
| `--column-file` | Text file containing one property name per line |
| `--filter`, `-f` | Property filter in `key=value` format |
| `--chunked` | Enable chunked date processing |
| `--chunk-days` | Days per chunk |
| `--chunk-months` | Months per chunk |
| `--publish` | Publish the generated file to Tableau Cloud |
| `--project-name` | Tableau Cloud project name |
| `--datasource-name` | Tableau datasource name |
| `--tableau-overwrite` | Overwrite instead of append during publish |
| `--verbose`, `-v` | Enable verbose logging |

## GitHub Actions

The included workflow is manual by default so a public repository does not run
scheduled exports unexpectedly. Configure these repository secrets before using
it:

- `MIXPANEL_API_SECRET`
- `MIXPANEL_PROJECT_ID`
- `TABLEAU_SERVER_URL`
- `TABLEAU_SITE_ID`
- `TABLEAU_TOKEN_NAME`
- `TABLEAU_TOKEN_VALUE`

Optional repository variables:

- `MIXPANEL_TIMEZONE`
- `TABLEAU_PROJECT_NAME`
- `TABLEAU_DATASOURCE_NAME`
- `PUBLISH_TO_TABLEAU` (`true` to publish scheduled runs)

When publishing is disabled, the workflow uploads the generated Hyper file as a
GitHub Actions artifact with a seven-day retention period. This prevents a
successful run from discarding its output.

To enable scheduled automation, add a `schedule` trigger to
`.github/workflows/daily_etl.yml` after confirming the repository secrets are
intended for that public repository. Set `PUBLISH_TO_TABLEAU=true` if scheduled
runs should publish; otherwise each run preserves the extract as an artifact.

## Google Cloud Build

`cloudbuild.yaml` builds to Artifact Registry using the active GCP project ID
and configurable region, repository, and image substitutions. Create the
Artifact Registry repository before the first build. Configure runtime secrets
separately in Cloud Run, Secret Manager, or your chosen runtime.

For deployment details, see `DEPLOYMENT.md`.

## Tableau Prep

1. Generate a `.hyper` file.
2. Open Tableau Prep Builder.
3. Choose **Connect to Data** and select **Tableau Extract**.
4. Select the generated `.hyper` file.

## Project Structure

```text
mixpanel-tableau-pipeline/
├── .github/workflows/
│   ├── ci.yml
│   └── daily_etl.yml
├── config/settings.py
├── src/
│   ├── mixpanel_client.py
│   ├── data_transformer.py
│   ├── hyper_writer.py
│   ├── state_manager.py
│   ├── tableau_publisher.py
│   └── pipeline.py
├── main.py
├── pyproject.toml
├── tests/
├── columns.txt
├── cloudbuild.yaml
└── Dockerfile
```

## Development

Install development tools and run the local checks:

```bash
pip install ".[tableau,gcs,dev]"
ruff check .
pytest --cov=src --cov=config --cov-report=term-missing
```

Pull requests run the same checks on Python 3.11 and 3.12.

## Docker

Build and validate the container without copying local credentials or generated
data into the image:

```bash
docker build -t mixpanel-tableau-pipeline .
docker run --rm --env-file .env mixpanel-tableau-pipeline --check-config
```

## Security

Mixpanel exports can contain user identifiers and other personal data. Do not
commit generated `.hyper` files, logs, state files, or credentials. See
`SECURITY.md` for the public repository checklist and `OPEN_SOURCE.md` for the
recommended publication workflow.

## License

MIT
