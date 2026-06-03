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
git clone https://github.com/Haryy-Park00/mixpanel-tableau-pipeline.git
cd mixpanel-tableau-pipeline
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
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

## Usage

Generate a Hyper file for a date range:

```bash
python main.py --from-date 2024-01-01 --to-date 2024-01-31
```

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

To enable scheduled automation, add a `schedule` trigger to
`.github/workflows/daily_etl.yml` after confirming the repository secrets are
intended for that public repository.

## Google Cloud Build

`cloudbuild.yaml` is a generic container build example. It uses the active GCP
project ID supplied by Cloud Build and does not include project-specific
credentials. Configure deployment secrets separately in Cloud Run, Secret
Manager, or your chosen runtime.

## Tableau Prep

1. Generate a `.hyper` file.
2. Open Tableau Prep Builder.
3. Choose **Connect to Data** and select **Tableau Extract**.
4. Select the generated `.hyper` file.

## Project Structure

```text
mixpanel-tableau-pipeline/
├── config/settings.py
├── src/
│   ├── mixpanel_client.py
│   ├── data_transformer.py
│   ├── hyper_writer.py
│   ├── state_manager.py
│   ├── tableau_publisher.py
│   └── pipeline.py
├── main.py
├── columns.txt
├── cloudbuild.yaml
└── .github/workflows/daily_etl.yml
```

## Security

Mixpanel exports can contain user identifiers and other personal data. Do not
commit generated `.hyper` files, logs, state files, or credentials. See
`SECURITY.md` for the public repository checklist and `OPEN_SOURCE.md` for the
recommended publication workflow.

## License

MIT
