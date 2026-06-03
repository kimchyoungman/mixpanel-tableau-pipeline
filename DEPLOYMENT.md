# Deployment

The pipeline is designed to run locally first. Cloud deployment is optional and
should use each user's own secrets and infrastructure.

## GitHub Actions

The included workflow is manual by default. Configure these repository secrets
before running it:

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

To schedule the workflow, add a `schedule` trigger only after confirming that
the repository secrets are intended for automated exports.

## Google Cloud

`cloudbuild.yaml` only builds and pushes a container image for the active Cloud
Build project. Runtime configuration still belongs in your deployment
environment.

Recommended runtime settings:

- Store secrets in Secret Manager or your platform's secret store.
- Set `STATE_PATH=gs://your-bucket/path/state.json` only if you want GCS-backed
  incremental state.
- Grant the runtime service account read/write access to that GCS object.
- Keep generated `.hyper` files out of source control.

## Local Cron

For a simple daily local run, configure your scheduler to call:

```bash
cd /path/to/mixpanel-tableau-pipeline
source .venv/bin/activate
python main.py --yesterday --publish
```

Run `python main.py --check-config --publish` before enabling automation.
