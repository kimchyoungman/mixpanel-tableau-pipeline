# Security Policy

## Secrets

Do not commit credentials or generated data files. Configure credentials through
environment variables, a local `.env` file, GitHub Actions secrets, or the
secret manager of your deployment platform.

Required secrets:

- `MIXPANEL_API_SECRET`
- `MIXPANEL_PROJECT_ID`

Optional Tableau publishing secrets:

- `TABLEAU_SERVER_URL`
- `TABLEAU_SITE_ID`
- `TABLEAU_TOKEN_NAME`
- `TABLEAU_TOKEN_VALUE`

## Public Repository Checklist

Before making a fork or repository public:

- Rotate any credentials that were ever committed or used in CI logs.
- Confirm `.env`, `state.json`, generated `.hyper` files, and logs are not
  tracked by Git.
- If generated files or logs were committed in the past, publish from a cleaned
  history or a fresh orphan branch instead of exposing the old private history.
- Keep scheduled CI disabled unless the repository secrets are intentionally
  configured for automation.
- Review exported Hyper files before sharing them because Mixpanel events can
  contain user identifiers or other personal data.
