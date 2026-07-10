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
- `PUBLISH_TO_TABLEAU`

When publishing is disabled, the workflow uploads `output/events.hyper` as an
artifact for seven days. Set `PUBLISH_TO_TABLEAU=true` for scheduled runs that
should publish directly to Tableau Cloud.

To schedule the workflow, add a `schedule` trigger only after confirming that
the repository secrets are intended for automated exports.

## Google Cloud

`cloudbuild.yaml` builds and pushes to Artifact Registry. Before the first
build, create the configured repository (default: `mixpanel-tableau`) in the
configured region (default: `asia-northeast3`):

```bash
gcloud artifacts repositories create mixpanel-tableau \
  --repository-format=docker \
  --location=asia-northeast3
gcloud builds submit --config cloudbuild.yaml .
```

Override `_REGION`, `_REPOSITORY`, or `_IMAGE` with Cloud Build substitutions
when deploying elsewhere. Runtime configuration still belongs in the deployment
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
