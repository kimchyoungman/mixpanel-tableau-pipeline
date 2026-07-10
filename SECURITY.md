# Security Policy

## Supported Versions

Security fixes are applied to the latest commit on the default branch. Tagged
releases will be listed here once the project starts publishing releases.

## Reporting a Vulnerability

Do not open a public issue containing a credential, exported event, user
identifier, or vulnerability detail.

Use GitHub private vulnerability reporting from the repository's **Security**
tab. If that option is unavailable, contact the repository owner through their
GitHub profile without including sensitive details and request a private channel.

Include the affected commit or version, impact, reproduction steps, and a
minimal proof of concept with all credentials and personal data removed. An
initial acknowledgement should be provided within seven days.

## Secrets and Exported Data

Configure credentials through environment variables, a local `.env` file,
GitHub Actions secrets, or the secret manager of the deployment platform.

Required secrets:

- `MIXPANEL_API_SECRET`
- `MIXPANEL_PROJECT_ID`

Optional Tableau publishing secrets:

- `TABLEAU_SERVER_URL`
- `TABLEAU_SITE_ID`
- `TABLEAU_TOKEN_NAME`
- `TABLEAU_TOKEN_VALUE`

Never commit `.env`, state files, generated `.hyper` extracts, logs, or real
Mixpanel event fixtures. Docker builds exclude these files through
`.dockerignore`, but contributors must still inspect the build context and image
history before distribution.

## Public Repository Checklist

- Rotate credentials that were ever committed or printed in CI logs.
- Confirm generated data and credentials are not tracked by Git.
- Publish from a cleaned history or a fresh snapshot if private artifacts were
  committed previously.
- Keep scheduled exports opt-in and use least-privilege runtime identities.
- Review Hyper extracts before sharing because event data can contain personal
  identifiers, URLs, and marketing parameters.
